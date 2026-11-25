"""Routeur IA local : 3 modèles GGUF uncensored servis par llama.cpp.

Une seule modèle actif à la fois (RAM limitée sur cette machine). API compatible
OpenAI sur 127.0.0.1:31416, sans clé et sans toucher à .env.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = Path(os.getenv("LOCAL_BRAIN_MODELS_DIR", ROOT / "models" / "uncensored-3b"))
BIN_DIR = Path(os.getenv("LOCAL_BRAIN_BIN_DIR", ROOT / ".tools" / "llama-b12633"))
SERVER_EXE = BIN_DIR / "llama-server.exe"
ROUTER_PORT = int(os.getenv("LOCAL_BRAIN_PORT", "31416"))
ACTIVE_FILE = ROOT / "esprieaether" / "state" / "local_brain.active"
PID_FILE = ROOT / "esprieaether" / "state" / "local_brain.pid"
LOG_FILE = ROOT / "esprieaether" / "state" / "local_brain.log"
DEFAULT_MODEL = os.getenv("LOCAL_BRAIN_MODEL", "dolphin3")
START_TIMEOUT = float(os.getenv("LOCAL_BRAIN_START_TIMEOUT", "120"))
# OpenCode envoie ~32k tokens de prompt : 2048 (valeur historique) était insuffisant.
# Un seul slot + KV quantifié garde la RAM sous contrôle sur cette machine (16 Go).
CONTEXT_TOKENS = int(os.getenv("LOCAL_BRAIN_CONTEXT", "49152"))
KV_CACHE_TYPE = os.getenv("LOCAL_BRAIN_KV_TYPE", "q4_0")
THREADS = int(os.getenv("LOCAL_BRAIN_THREADS", "6"))
CHAT_TIMEOUT = float(os.getenv("LOCAL_BRAIN_CHAT_TIMEOUT", "900"))
# llama-server tourne avec un seul slot (-np 1) : on file les appels au lieu de
# laisser ThreadingHTTPServer engorger le CPU et renvoyer des 503 trompeurs.
MAX_CONCURRENT_CHATS = max(1, int(os.getenv("LOCAL_BRAIN_MAX_CONCURRENT", "1")))
CHAT_QUEUE_TIMEOUT = float(os.getenv("LOCAL_BRAIN_QUEUE_TIMEOUT", "5"))
chat_slots = threading.BoundedSemaphore(MAX_CONCURRENT_CHATS)

# قاعدة اللغة مفروضة فالـ routeur باش أي client (OpenCode، صوت، curl) يردّ بالدارجة.
# Mesuré sur :31501 (Dolphin3 3B) : une consigne courte en français est obéie,
# alors que la même consigne écrite en arabe a donné une réponse anglaise.
DARIJA_DIRECTIVE = (
    "Réponds en arabe marocain avec lettres arabes. Une seule phrase courte. "
    "N'écris aucune lettre latine dans la réponse."
)


def apply_language_policy(payload: dict) -> dict:
    """يضيف توجيه الدارجة بلا ما يمسخ system prompt ديال الـ client."""
    out = dict(payload or {})
    enabled = os.getenv("ESPRIA_FORCE_DARIJA", "1").strip() not in ("0", "false", "no")
    if not enabled:
        return out
    messages = out.get("messages")
    if not isinstance(messages, list):
        out["messages"] = [{"role": "system", "content": DARIJA_DIRECTIVE}]
        return out
    messages = [dict(m) for m in messages if isinstance(m, dict)]
    # Seule la consigne française testée sur le modèle est fiable : un prompt
    # qui contient seulement « دارجة » ne doit pas faire sauter l'injection.
    joined = " ".join(str(m.get("content") or "") for m in messages)
    if DARIJA_DIRECTIVE in joined:
        out["messages"] = messages
        return out
    if messages and messages[0].get("role") == "system":
        first = dict(messages[0])
        first["content"] = DARIJA_DIRECTIVE + "\n" + str(first.get("content") or "")
        messages[0] = first
    else:
        messages.insert(0, {"role": "system", "content": DARIJA_DIRECTIVE})
    out["messages"] = messages
    return out

# Tailles exactes annoncées par Hugging Face (blobs API). Un fichier partiel
# n'est jamais annoncé comme un modèle disponible.
CATALOG = [
    {
        "id": "dolphin3",
        "file": "Dolphin3.0-Llama3.2-3B-Q4_K_M.gguf",
        "port": 31501,
        "bytes": 2019382400,
        "label": "Dolphin 3.0 Llama 3.2 3B (uncensored)",
    },
    {
        "id": "hermes3",
        "file": "Hermes-3-Llama-3.2-3B-Q4_K_M.gguf",
        "port": 31502,
        "bytes": 2019374176,
        "label": "Hermes 3 Llama 3.2 3B (uncensored)",
    },
    {
        "id": "llama32uncensored",
        "file": "Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf",
        "port": 31503,
        "bytes": 2241003904,
        "label": "Llama 3.2 3B Instruct uncensored",
    },
]

_lock = threading.Lock()


def available_models() -> list[dict]:
    """Un modèle n'est proposé que si le GGUF est complet (taille HF vérifiée)."""
    found = []
    for model in CATALOG:
        path = MODELS_DIR / model["file"]
        try:
            complete = path.is_file() and path.stat().st_size >= model["bytes"]
        except OSError:
            complete = False
        if complete:
            found.append(dict(model))
    return found


def select_model(requested: str | None, models: list[dict] | None = None) -> dict | None:
    models = available_models() if models is None else models
    if not models:
        return None
    if requested:
        for model in models:
            aliases = (model["id"], model["file"], model["file"].removesuffix(".gguf"))
            if requested in aliases:
                return model
    for model in models:
        if model["id"] == DEFAULT_MODEL:
            return model
    return models[0]


def active_id() -> str:
    try:
        return ACTIVE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build_cmd(model: dict) -> list[str]:
    """Commande llama-server : loopback uniquement, CPU, pas de GPU requis."""
    return [
        str(SERVER_EXE),
        "-m", str(MODELS_DIR / model["file"]),
        "--host", "127.0.0.1",
        "--port", str(model["port"]),
        "-c", str(CONTEXT_TOKENS),
        "-np", "1",
        "-ctk", KV_CACHE_TYPE,
        "-ctv", KV_CACHE_TYPE,
        "-t", str(THREADS),
        "-tb", str(THREADS),
        "-fa", "on",
        "--n-gpu-layers", "0",
    ]


def _port_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def stop_active() -> None:
    """Arrête uniquement le serveur démarré par ce routeur."""
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        pid = 0
    if pid:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, timeout=10)
            else:
                os.kill(pid, 15)
        except Exception:
            pass
    for path in (PID_FILE, ACTIVE_FILE):
        try:
            path.unlink()
        except OSError:
            pass


def ensure_active(model: dict) -> bool:
    """Démarre le modèle demandé, en remplaçant le précédent si besoin."""
    with _lock:
        if active_id() == model["id"] and _port_ready(model["port"]):
            return True
        stop_active()
        if not SERVER_EXE.is_file():
            _log("llama-server.exe absent")
            return False
        log = open(LOG_FILE, "a", encoding="utf-8", errors="replace")
        try:
            proc = subprocess.Popen(build_cmd(model), stdout=log, stderr=subprocess.STDOUT)
        except OSError as exc:
            _log(f"start failed: {type(exc).__name__}")
            log.close()
            return False
        finally:
            try:
                log.close()
            except Exception:
                pass
        ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_FILE.write_text(model["id"], encoding="utf-8")
        PID_FILE.write_text(str(proc.pid), encoding="utf-8")
        deadline = time.time() + START_TIMEOUT
        while time.time() < deadline:
            if _port_ready(model["port"]):
                return True
            if proc.poll() is not None:
                _log(f"server exited code={proc.returncode}")
                stop_active()
                return False
            time.sleep(1)
        _log("server start timeout")
        stop_active()
        return False


def _log(message: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8", errors="replace") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")
    except OSError:
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, payload: bytes, status: int = 200,
              content_type: str = "application/json", headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, str(value))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, obj: dict, status: int = 200, headers: dict | None = None) -> None:
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"), status, headers=headers)

    def do_GET(self):
        if self.path == "/health":
            models = available_models()
            self._json({
                "status": "ok",
                "router": "local-brain",
                "port": ROUTER_PORT,
                "active": active_id() or None,
                "available": [m["id"] for m in models],
                "count": len(models),
            })
        elif self.path == "/v1/models":
            models = available_models()
            self._json({
                "object": "list",
                "data": [
                    {"id": m["id"], "object": "model", "owned_by": "local", "label": m["label"]}
                    for m in models
                ],
            })
        else:
            self._json({"error": {"message": "not found"}}, 404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._json({"error": {"message": "not found"}}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error": {"message": "invalid json"}}, 400)
            return
        model = select_model(body.get("model"))
        if model is None:
            self._json({"error": {"message": "no local model installed"}}, 503)
            return
        if not ensure_active(model):
            self._json({"error": {"message": f"local model unavailable: {model['id']}"}}, 503)
            return
        if not chat_slots.acquire(timeout=CHAT_QUEUE_TIMEOUT):
            self._json({"error": {"message": "local model busy", "code": "BUSY"}},
                       429, {"Retry-After": "1"})
            return
        try:
            payload = apply_language_policy(body)
            payload["model"] = model["id"]
            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                f"http://127.0.0.1:{model['port']}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=CHAT_TIMEOUT) as response:
                    raw = response.read()
                    status = response.status
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                status = exc.code
            except Exception as exc:
                self._json({"error": {"message": type(exc).__name__}}, 502)
                return
            self._send(raw, status)
        finally:
            chat_slots.release()


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", ROUTER_PORT), Handler)
    _log(f"local brain router listening on 127.0.0.1:{ROUTER_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        stop_active()


if __name__ == "__main__":
    main()
