#!/usr/bin/env python3
"""
ollama_mcp.py — MCP server لـ Ollama (محلي، مجاني، بلا limit).
كيتواصل مع DSH / Claude / أي MCP client عبر stdio.

الاستعمال فـ DSH:
  Settings → MCP → Add Server:
    command: python
    args: ["C:/Users/ESPRIEAETHER/Desktop/esprieaether/robots/ollama_mcp.py"]
"""
import json, sys, urllib.request, urllib.error

OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"

def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_HOST}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

def _get(path: str) -> dict:
    req = urllib.request.Request(f"{OLLAMA_HOST}{path}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# ── MCP tools ──
TOOLS = [
    {
        "name": "ollama_chat",
        "description": "Chat with local Ollama model (free, no rate limit). Use for any LLM task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to send"},
                "model": {"type": "string", "description": "Model name (default: qwen2.5:3b)"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "ollama_list",
        "description": "List available Ollama models",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ollama_embed",
        "description": "Generate embeddings for text using local Ollama",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to embed"},
                "model": {"type": "string", "description": "Embedding model (default: qwen2.5:3b)"},
            },
            "required": ["text"],
        },
    },
]

def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    params = req.get("params", {})
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ollama-mcp", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})

        if name == "ollama_chat":
            model = args.get("model", DEFAULT_MODEL)
            prompt = args.get("prompt", "")
            try:
                r = _post("/api/chat", {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                })
                content = r.get("message", {}).get("content", "")
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": content}]}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -1, "message": str(e)}}

        if name == "ollama_list":
            try:
                r = _get("/api/tags")
                models = [m["name"] for m in r.get("models", [])]
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(models, indent=2)}]}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -1, "message": str(e)}}

        if name == "ollama_embed":
            model = args.get("model", DEFAULT_MODEL)
            text = args.get("text", "")
            try:
                r = _post("/api/embed", {"model": model, "input": text})
                embeddings = r.get("embeddings", [[]])
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(embeddings[0][:10])}]}}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -1, "message": str(e)}}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    if method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            if resp:
                print(json.dumps(resp), flush=True)
        except Exception as e:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
