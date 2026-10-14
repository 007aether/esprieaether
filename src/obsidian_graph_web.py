#!/usr/bin/env python3
"""
obsidian_graph_web.py — render the Obsidian vault as a live web page
(served by web_interface.py at /obsidian + a standalone graph.html).

Parses [[wiki-links]] from every note in the vault → vis-network graph.
"""

import json
import os
import re
from pathlib import Path

VAULT = Path(os.path.expanduser("~")) / "ObsidianVault" / "EsprieAether"
OUT_HTML = Path(os.path.expanduser("~")) / "ObsidianVault" / "EsprieAether" / "graph.html"

# category colors
COLORS = {
    "service": "#22d3ee",     # cyan
    "bot": "#a78bfa",         # violet
    "integration": "#34d399", # green
    "company": "#f59e0b",     # amber (Sunna)
    "brain": "#f472b6",       # pink
    "infra": "#f87171",       # red
    "api": "#60a5fa",         # blue
    "web": "#fb923c",         # orange
    "meta": "#94a3b8",        # slate
}


def parse_vault():
    """Return (nodes, edges) from all .md notes + their wiki-links."""
    nodes, edges = {}, []
    files = list(VAULT.rglob("*.md"))
    for f in files:
        if f.name.startswith("_") or ".graphify" in str(f) or "graph" in f.stem:
            continue
        name = f.stem
        rel = str(f.relative_to(VAULT))
        parts = Path(rel).parts
        # category = first dir (Services/Bots/...) or frontmatter tag
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
    # degree sizing
    from collections import Counter
    deg = Counter()
    for e in edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1
    for n in nodes.values():
        n["value"] = min(40, 10 + deg.get(n["id"], 0) * 3)
    return list(nodes.values()), edges


def render_html(nodes, edges):
    groups = {k: {"color": v} for k, v in COLORS.items()}
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧠 EsprieAether — Knowledge Graph</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
 body{{background:#0b1120;color:#e2e8f0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0}}
 header{{padding:14px 20px;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
 h1{{font-size:17px;margin:0;font-weight:600}}
 .stat{{font-size:12px;color:#94a3b8}} .stat b{{color:#22d3ee}}
 #legend{{display:flex;gap:10px;flex-wrap:wrap;padding:10px 20px;font-size:11px}}
 .lg{{display:flex;align-items:center;gap:5px}} .dot{{width:9px;height:9px;border-radius:50%}}
 #net{{width:100%;height:calc(100vh - 92px);background:#0b1120}}
 #tip{{position:fixed;left:12px;bottom:12px;font-size:11px;color:#64748b}}
</style></head><body>
<header><h1>🧠 EsprieAether — Knowledge Graph</h1>
 <span class="stat">📝 <b>{len(nodes)}</b> notes</span>
 <span class="stat">🔗 <b>{len(edges)}</b> links</span>
 <span class="stat">~ObsidianVault/EsprieAether</span></header>
<div id="legend">{''.join(f'<span class="lg"><span class="dot" style="background:{c}"></span>{k}</span>' for k,c in COLORS.items())}</div>
<div id="net"></div><div id="tip">drag to pan · scroll to zoom · click a node</div>
<script>
const nodes=new vis.DataSet({json.dumps(nodes)});
const edges=new vis.DataSet({json.dumps(edges)}.map(e=>({{from:e.from,to:e.to,color:{{color:'#334155',highlight:'#22d3ee'}},width:1}})));
const net=new vis.Network(document.getElementById('net'),{{nodes,edges}},{{
  nodes:{{shape:'dot',font:{{color:'#cbd5e1',size:11}},borderWidth:1.5}},
  edges:{{smooth:{{type:'continuous'}},hoverWidth:1.8}},
  physics:{{stabilization:true,barnesHut:{{gravitationalConstant:-9000,springLength:130}}}},
  groups:{json.dumps(groups)}
}});
net.on('click',p=>{{if(p.nodes.length){{const n=nodes.get(p.nodes[0]);net.selectNodes([n.id]);}}}});
</script></body></html>"""


def main():
    if not VAULT.exists():
        print(f"❌ vault not found: {VAULT} — run obsidian_vault_builder.py first")
        return
    nodes, edges = parse_vault()
    OUT_HTML.write_text(render_html(nodes, edges), encoding="utf-8")
    print(f"✅ graph.html: {OUT_HTML}")
    print(f"   {len(nodes)} nodes · {len(edges)} edges")
    from collections import Counter
    cats = Counter(n["group"] for n in nodes)
    for c, n in cats.most_common():
        print(f"   {c}: {n}")


if __name__ == "__main__":
    main()
