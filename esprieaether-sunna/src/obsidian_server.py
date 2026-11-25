#!/usr/bin/env python3
"""
obsidian_server.py — Serve Obsidian vault at http://localhost:5000/obsidian
Uses only Python standard library (http.server) — no Flask needed.
"""

import os
import sys
import json
import mimetypes
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

HOME = Path(os.path.expanduser("~"))
VAULT = HOME / "ObsidianVault" / "EsprieAether"
GRAPH_HTML = VAULT / "graph.html"

PORT = 5000


class ObsidianHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(VAULT), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # /obsidian -> serve graph.html
        if path == "/obsidian" or path == "/obsidian/":
            self.serve_graph()
            return

        # /obsidian/graph -> serve graph.html
        if path == "/obsidian/graph":
            self.serve_graph()
            return

        # /obsidian/api/graph.json -> return graph data as JSON
        if path == "/obsidian/api/graph.json":
            self.serve_graph_json()
            return

        # /obsidian/api/nodes -> return nodes list
        if path == "/obsidian/api/nodes":
            self.serve_nodes_json()
            return

        # /obsidian/api/edges -> return edges list
        if path == "/obsidian/api/edges":
            self.serve_edges_json()
            return

        # /obsidian/note/NAME -> serve note content
        if path.startswith("/obsidian/note/"):
            note_name = path.split("/obsidian/note/", 1)[1]
            self.serve_note(note_name)
            return

        # Default: serve files from vault
        super().do_GET()

    def serve_graph(self):
        """Serve the interactive graph.html"""
        if GRAPH_HTML.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(GRAPH_HTML.read_bytes())
        else:
            self.send_error(404, "Graph not found. Run: python src/obsidian_graph_web.py")

    def serve_graph_json(self):
        """Return graph data as JSON for API consumers"""
        nodes, edges = self.parse_vault()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False).encode())

    def serve_nodes_json(self):
        nodes, _ = self.parse_vault()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(nodes, ensure_ascii=False).encode())

    def serve_edges_json(self):
        _, edges = self.parse_vault()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(edges, ensure_ascii=False).encode())

    def serve_note(self, note_name):
        """Serve a specific note content as HTML"""
        note_path = VAULT / f"{note_name}.md"
        if note_path.exists():
            content = note_path.read_text(encoding="utf-8", errors="ignore")
            html = self.md_to_html(content, note_name)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            # Try with .md extension
            note_path2 = VAULT / f"{note_name}.md"
            if note_path2.exists():
                content = note_path2.read_text(encoding="utf-8", errors="ignore")
                html = self.md_to_html(content, note_name)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())
            else:
                self.send_error(404, f"Note not found: {note_name}")

    def md_to_html(self, content, title):
        """Simple markdown to HTML conversion"""
        lines = content.split('\n')
        html_parts = [
            f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - EsprieAether</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;
       background:#0b1120;color:#e2e8f0;line-height:1.6}}
 h1,h2,h3{{color:#22d3ee;margin-top:2rem}}
 a{{color:#818cf8}} a:hover{{color:#22d3ee}}
 code{{background:#1e293b;padding:0.1rem 0.3rem;border-radius:4px}}
 pre{{background:#1e293b;padding:1rem;border-radius:8px;overflow-x:auto}}
 .wiki-link{{color:#818cf8;text-decoration:none}}
 .wiki-link:hover{{color:#22d3ee;text-decoration:underline}}
 .tags{{margin-bottom:1rem}} .tag{{display:inline-block;background:#1e293b;
       padding:0.1rem 0.5rem;border-radius:999px;font-size:0.8rem;margin-right:0.3rem}}
 hr{{border:none;border-top:1px solid #1e293b;margin:2rem 0}}
 .back{{display:inline-block;margin-bottom:1rem;color:#94a3b8;text-decoration:none}}
 .back:hover{{color:#22d3ee}}
</style></head><body>
<a class="back" href="/obsidian">Back to Graph</a>
"""
        ]

        in_code = False
        code_lines = []

        for line in lines:
            # Handle code blocks
            if line.startswith('```'):
                if not in_code:
                    in_code = True
                    lang = line[3:].strip()
                    html_parts.append(f'<pre><code class="language-{lang}">')
                else:
                    in_code = False
                    html_parts.append('</code></pre>')
                continue

            if in_code:
                code_lines.append(line)
                continue

            # Headings
            if line.startswith('# '):
                html_parts.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_parts.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_parts.append(f'<h3>{line[4:]}</h3>')
            # Bold
            elif '**' in line:
                line = line.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                html_parts.append(f'<p>{line}</p>')
            # Wiki links [[link]] or [[link|alias]]
            elif '[[' in line and ']]' in line:
                import re
                def replace_wiki(match):
                    link = match.group(1)
                    if '|' in link:
                        target, alias = link.split('|', 1)
                        return f'<a class="wiki-link" href="/obsidian/note/{target.strip()}">{alias.strip()}</a>'
                    return f'<a class="wiki-link" href="/obsidian/note/{link.strip()}">{link.strip()}</a>'
                line = re.sub(r'\[\[([^\]]+)\]\]', replace_wiki, line)
                html_parts.append(f'<p>{line}</p>')
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                html_parts.append(f'<li>{line[2:]}</li>')
            # Horizontal rule
            elif line.strip() == '---':
                html_parts.append('<hr>')
            # Empty line
            elif not line.strip():
                html_parts.append('<br>')
            else:
                html_parts.append(f'<p>{line}</p>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def parse_vault(self):
        """Parse vault for graph data"""
        import re
        from collections import Counter

        nodes, edges = {}, []
        files = list(VAULT.rglob("*.md"))
        for f in files:
            if f.name.startswith("_") or ".graphify" in str(f) or "graph" in f.stem:
                continue
            name = f.stem
            rel = str(f.relative_to(VAULT))
            parts = Path(rel).parts
            cat = "meta"
            if len(parts) > 1:
                cat = parts[0].lower()
            nodes[name] = {"id": name, "label": name, "group": cat, "size": 12}
            text = f.read_text(encoding="utf-8", errors="ignore")
            links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", text)
            for l in links:
                l = l.strip()
                if l and l != name:
                    edges.append({"from": name, "to": l})
                    nodes.setdefault(l, {"id": l, "label": l, "group": "meta", "size": 8})

        deg = Counter()
        for e in edges:
            deg[e["from"]] += 1
            deg[e["to"]] += 1
        for n in nodes.values():
            n["value"] = min(40, 10 + deg.get(n["id"], 0) * 3)
        return list(nodes.values()), edges


def run_server():
    server = HTTPServer(("0.0.0.0", PORT), ObsidianHandler)
    print(f"Obsidian server running at http://localhost:{PORT}/obsidian")
    print(f"   Graph: http://localhost:{PORT}/obsidian")
    print(f"   Graph JSON API: http://localhost:{PORT}/obsidian/api/graph.json")
    print(f"   Nodes API: http://localhost:{PORT}/obsidian/api/nodes")
    print(f"   Edges API: http://localhost:{PORT}/obsidian/api/edges")
    server.serve_forever()


if __name__ == "__main__":
    run_server()