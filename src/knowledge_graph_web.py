#!/usr/bin/env python3
"""
KNOWLEDGE GRAPH VISUALIZER
-------------------------
يعرض العلاقات بين المعرفة في صورة رسم توضيحي تفاعلي.
يغير من طريقة البشر لفهم المعلومات.

المدة: 1-3 دقائق
المدخلات: data/knowledge_base/knowledge_index.json
المخرجات: data/knowledge_graph_web.py (واجهة تفاعلية)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "data" / "knowledge_base"
KB_FILE = KB_DIR / "knowledge_index.json"
GRAPH_FILE = BASE_DIR / "data" / "knowledge_graph.json"
WEB_FILE = BASE_DIR / "src" / "knowledge_graph_web.py"

COLORS = ["#4ade80", "#f59e0b", "#60a5fa", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#f87171", "#60a5fa", "#a78bfa"]


def load_kb():
    if not KB_FILE.exists():
        return []
    with open(KB_FILE, encoding="utf-8") as f:
        return json.load(f).get("items", [])


def build_graph(items):
    """Build knowledge graph from items."""
    graph = {"nodes": [], "edges": [], "metadata": {}}

    tag_count = {}
    source_count = {}

    for i, item in enumerate(items):
        node_id = f"n{i}#{item.get('text', 'unknown')[:20]}"
        graph["nodes"].append({
            "id": node_id,
            "label": item.get("text", "Unknown")[:80],
            "type": "knowledge",
            "color": COLORS[i % len(COLORS)],
            "source": item.get("source", "unknown"),
            "tags": item.get("tags", []),
            "stored_at": item.get("stored_at", "")
        })

        for tag in item.get("tags", []):
            tag_count[tag] = tag_count.get(tag, 0) + 1

        src = item.get("source", "unknown")
        source_count[src] = source_count.get(src, 0) + 1

    for i, item in enumerate(items):
        for j, item2 in enumerate(items):
            if i >= j:
                continue
            tags1 = set(item.get("tags", []))
            tags2 = set(item2.get("tags", []))
            common_tags = tags1 & tags2
            if common_tags:
                graph["edges"].append({
                    "from": f"n{i}#{item.get('text', 'unknown')[:20]}",
                    "to": f"n{j}#{item2.get('text', 'unknown')[:20]}",
                    "label": f"tags: {', '.join(common_tags)}",
                    "weight": len(common_tags)
                })

    graph["metadata"] = {
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "total_tags": len(tag_count),
        "top_tags": sorted(tag_count.items(), key=lambda x: -x[1])[:10],
        "top_sources": sorted(source_count.items(), key=lambda x: -x[1])[:5],
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

    return graph


def generate_html(graph):
    """Generate the HTML web interface."""
    tags_rows = ""
    for t, count in graph["metadata"]["top_tags"][:10]:
        tags_rows += f"<tr><td style='color: #4ade80'>{t}</td><td>{count}</td></tr>\n"

    sources_rows = ""
    for s, count in graph["metadata"]["top_sources"][:5]:
        sources_rows += f"<tr><td style='color: #f59e0b'>{s}</td><td>{count}</td></tr>\n"

    nodes_json = json.dumps(graph["nodes"], ensure_ascii=False)
    tags_json = json.dumps(graph["metadata"]["top_tags"], ensure_ascii=False)
    sources_json = json.dumps(graph["metadata"]["top_sources"], ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Graph — EsprieAether</title>
<style>
  :root {{
    --bg: #0a0d08;
    --bg-card: #121610;
    --foreground: #c8d6b0;
    --accent: #4ade80;
    --muted: #8a9a7e;
    --border: #2a3a28;
    --accent-dim: #1a2a18;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Sans Arabic', 'Inter', system-ui, sans-serif;
    background: var(--bg);
    color: var(--foreground);
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }}
  .header {{
    text-align: center;
    padding: 2rem;
    border-bottom: 2px solid var(--border);
    margin-bottom: 2rem;
    background: linear-gradient(180deg, var(--bg-card), var(--bg));
    border-radius: 8px;
  }}
  .header h1 {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.1em;
  }}
  .header .subtitle {{
    color: var(--muted);
    font-size: 1rem;
  }}
  .stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .stat-box {{
    flex: 1;
    min-width: 200px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
  }}
  .stat-box .number {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-box .label {{
    font-size: 0.85rem;
    color: var(--muted);
  }}
  .graph-container {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
  }}
  .graph-container h2 {{
    color: var(--accent);
    margin-bottom: 1rem;
  }}
  .controls {{
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }}
  .controls input {{
    padding: 0.6rem 1rem;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--foreground);
    font-family: inherit;
    flex: 1;
    min-width: 200px;
  }}
  .controls button {{
    padding: 0.6rem 1.2rem;
    border-radius: 4px;
    border: 1px solid var(--border);
    background: var(--accent);
    color: var(--bg);
    font-weight: 600;
    cursor: pointer;
  }}
  .controls button:hover {{
    background: #22c55e;
  }}
  .heatmap {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-top: 1rem;
  }}
  .heatmap-item {{
    flex: 1;
    min-width: 150px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
  }}
  .heatmap-item h3 {{
    color: var(--accent);
    margin-bottom: 0.5rem;
  }}
  .heatmap-item table {{
    width: 100%;
    border-collapse: collapse;
  }}
  .heatmap-item th, .heatmap-item td {{
    padding: 0.5rem;
    text-align: right;
    border: 1px solid var(--border);
  }}
  .heatmap-item th {{
    background: var(--accent-dim);
    color: var(--accent);
    font-weight: 600;
  }}
  .footer {{
    text-align: center;
    padding: 1.5rem;
    border-top: 2px solid var(--border);
    color: var(--muted);
    font-size: 0.8rem;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 knowledge graph (معلومات مرتبطة)</h1>
  <p class="subtitle">نظام EsprieAether — التفاعل بين المعلومات والمفاهيم</p>
</div>

<div class="stats">
  <div class="stat-box">
    <div class="number">{graph['metadata']['total_nodes']}</div>
    <div class="label">عقدة معرفة</div>
  </div>
  <div class="stat-box">
    <div class="number">{graph['metadata']['total_edges']}</div>
    <div class="label">علاقة</div>
  </div>
  <div class="stat-box">
    <div class="number">{graph['metadata']['total_tags']}</div>
    <div class="label">وسم (Tags)</div>
  </div>
</div>

<div class="graph-container">
  <h2>🔍 بحث في المعرفة</h2>
  <div class="controls">
    <input type="text" id="searchInput" placeholder="ابحث عن كلمة مفتاحية...">
    <button onclick="searchKnowledge()">🔍 بحث</button>
    <button onclick="clearSearch()">✕ مسح</button>
  </div>
  <div id="results"></div>
</div>

<div class="heatmap">
  <div class="heatmap-item">
    <h3>📊 الوسوم (Tags)</h3>
    <table id="heatmap-tags">
      <tr><th>وسم</th><th>العدد</th></tr>
      {tags_rows}
    </table>
  </div>
  <div class="heatmap-item">
    <h3>📊 المصادر (Sources)</h3>
    <table id="heatmap-sources">
      <tr><th>المصدر</th><th>العدد</th></tr>
      {sources_rows}
    </table>
  </div>
</div>

<div class="footer">
  <p>📘 نظام EsprieAether Knowledge Graph — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}</p>
</div>

<script>
const nodes_data = {nodes_json};
const tags_data = {tags_json};
const sources_data = {sources_json};

function searchKnowledge() {{
  const q = document.getElementById('searchInput').value.toLowerCase();
  const results = document.getElementById('results');
  const matches = nodes_data.filter(n => n.label.toLowerCase().includes(q));
  let html = '<h3>نتائج البحث: ' + matches.length + ' نتائج</h3>';
  matches.forEach(n => {{
    html += `<div class="result-item" style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; padding: 0.8rem;">
      <strong>${{n.label}}</strong><br>
      <span style="color: var(--muted); font-size: 0.85rem;">${{n.source}} | tags: ${{n.tags.join(', ')}}</span>
    </div>`;
  }});
  results.innerHTML = html;
}}

function clearSearch() {{
  document.getElementById('searchInput').value = '';
  document.getElementById('results').innerHTML = '';
}}

function buildTagsTable(tags) {{
  let html = '<tr><th>وسم</th><th>العدد</th></tr>';
  tags.forEach((t, i) => {{
    const color = ['#4ade80', '#f59e0b', '#60a5fa', '#a78bfa', '#f472b6', '#34d399', '#fbbf24', '#f87171', '#60a5fa', '#a78bfa'][i % 10];
    html += `<tr><td style="color: ${color}">${{t[0]}}</td><td>${{t[1]}}</td></tr>`;
  }});
  return html;
}}

function buildSourcesTable(sources) {{
  let html = '<tr><th>المصدر</th><th>العدد</th></tr>';
  sources.forEach((s, i) => {{
    const colors = ['#4ade80', '#f59e0b', '#60a5fa', '#a78bfa', '#f472b6'];
    html += `<tr><td style="color: ${{colors[i % 5]}}">${{s[0]}}</td><td>${{s[1]}}</td></tr>`;
  }});
  return html;
}}

document.addEventListener('DOMContentLoaded', () => {{
  const resultsEl = document.getElementById('results');
  resultsEl.innerHTML = '<div style="color: var(--muted);">اكتب كلمة مفتاحية في حقل البحث واضغط على بحث...</div>';
  document.getElementById('heatmap-tags').innerHTML = buildTagsTable(tags_data);
  document.getElementById('heatmap-sources').innerHTML = buildSourcesTable(sources_data);
}});
</script>

</body>
</html>"""
    return html_content


def generate_web_interface(graph):
    """Generate the full web interface."""
    html_content = generate_html(graph)
    with open(WEB_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Graph web interface generated: {WEB_FILE}")


def generate_stats():
    """Generate summary statistics."""
    items = load_kb()
    graph = build_graph(items)

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_items": len(items),
        "total_nodes": graph["metadata"]["total_nodes"],
        "total_edges": graph["metadata"]["total_edges"],
        "total_tags": graph["metadata"]["total_tags"],
        "top_tags": graph["metadata"]["top_tags"],
        "top_sources": graph["metadata"]["top_sources"],
        "output_files": [
            str(WEB_FILE),
            str(GRAPH_FILE)
        ]
    }

    with open(BASE_DIR / "data" / "knowledge_graph_stats.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"✅ Stats generated: {BASE_DIR / 'data' / 'knowledge_graph_stats.json'}")
    return summary


def run():
    print(f"\n📊 {C.CYAN}🔬 Knowledge Graph Visualizer{C.RESET}")
    print(f"   Reading: {KB_FILE}")
    print(f"   Generating: {WEB_FILE}")

    try:
        items = load_kb()
        print(f"   📊 Loaded {len(items)} knowledge items")

        if len(items) == 0:
            print(f"   ⚠️  No knowledge items found")
            return False

        graph = build_graph(items)
        generate_web_interface(graph)
        generate_stats()

        print(f"\n{'═' * 50}")
        print(f"   📊 Summary:")
        print(f"      Total knowledge items: {len(items)}")
        print(f"      Total graph nodes: {graph['metadata']['total_nodes']}")
        print(f"      Total graph edges: {graph['metadata']['total_edges']}")
        print(f"      Total tags: {graph['metadata']['total_tags']}")
        print(f"      Top tags: {', '.join([t[0] for t in graph['metadata']['top_tags'][:5]])}")
        print(f"   ✅ Done")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run()
