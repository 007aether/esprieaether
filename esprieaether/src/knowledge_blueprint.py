#!/usr/bin/env python3
"""
KNOWLEDGE BASE BLUEPRINT
------------------------
Flask blueprint للواجهة البشرية للمعرفة (knowledge base UI).
يعرّض قاعدة المعرفة للبشر على:
  - استعراض كل معلومة مخزنة
  - البحث عن معلومة محددة
  - تعرض بصفحة (HTML) أو API (JSON)
"""

from flask import Blueprint, request, jsonify, render_template_string
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "data" / "knowledge_base"
KB_FILE = KB_DIR / "knowledge_index.json"

bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")

# ─── Templates ───────────────────────────────────────────────

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>📦 نظام المعرفة - EsprieAether</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; color: #333; }
  .container { max-width: 1200px; margin: 0 auto; }
  h1 { color: #2c3e50; }
  h2 { color: #34495e; }
  .card { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  .search-box { padding: 15px; background: #f8f9fa; border-radius: 8px; margin-bottom: 20px; }
  .search-box input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
  .search-box button { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 10px; }
  .tag { display: inline-block; background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 3px; font-size: 12px; margin-right: 5px; }
  .result-item { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; background: #fafafa; }
  .result-item .tags { margin-top: 10px; }
  .btn { padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
  .btn-json { padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }
  .btn-danger { padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; }
  .stats { display: flex; gap: 20px; flex-wrap: wrap; }
  .stat { flex: 1; min-width: 200px; padding: 15px; background: #f8f9fa; border-radius: 8px; text-align: center; }
  .stat .number { font-size: 24px; font-weight: bold; color: #3498db; }
  .stat .label { color: #6c757d; }
  .empty { text-align: center; color: #6c757d; padding: 40px; }
  footer { text-align: center; color: #999; padding: 20px; }
</style>
</head>
<body>
<div class="container">
  <h1>📦 نظام المعرفة - EsprieAether</h1>
  <p class="subtitle">معرفة النظام المجمعة والمنظمة</p>

  <div class="card">
    <h2>🔍 بحث سريع</h2>
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="ابحث عن معلومة (كلمة مفتاح)...)" onkeydown="handleSearch(event)">
      <button onclick="handleSearch()">بحث</button>
      <a href="/knowledge" class="btn">عرض الكل</a>
      <a href="/knowledge/refresh" class="btn">تحديث القاعدة</a>
    </div>
  </div>

  <div id="results">
    <div class="card">
      <h2>📦 المعرفة المخزنة</h2>
      <p class="subtitle">عدد العناصر: <span id="count">0</span></p>
      <div id="items">
        <div class="empty">جارِ التحميل...</div>
      </div>
    </div>
  </div>

  <footer>
    <p>EsprieAether Sovereign Local AI · المعرفة المُجمّعة والمنظمة</p>
  </footer>
</div>

<script>
function handleSearch(e) {
  if (e && e.keyCode && e.keyCode !== 13) return;
  const q = document.getElementById('searchInput').value;
  fetch(`/knowledge/search?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => renderResults(data))
    .catch(console.error);
}

function renderResults(data) {
  const container = document.getElementById('items');
  const count = document.getElementById('count');
  count.textContent = data.total;

  if (data.items.length === 0) {
    container.innerHTML = '<div class="empty">لا توجد نتائج مطابقة</div>';
    return;
  }

  // build HTML safely (all tags escaped via escapeHtml() before insertion)
  let html = '';
  data.items.forEach(item => {
    html += `<div class="result-item">`;
    html += `<div class="tags">`;
    item.tags.forEach(t => {
      html += `<span class="tag">${escapeHtml(t)}</span>`;
    });
    html += `<span class="tag" style="background:#e8f5e9;color:#2e7d32;">${escapeHtml(item.source)}</span>`;
    html += `</div>`;
    html += `<p>${escapeHtml(item.text)}</p>`;
    html += `<p style="font-size:12px;color:#999;">*من المخزن* ${new Date(item.stored_at).toLocaleString('ar')}</p>`;
    html += `</div>`;
  });
  container.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
</script>
</body>
</html>
"""

JSON_TEMPLATE = {
    "total": 0,
    "items": [],
    "search_query": "",
}


@bp.route("/")
def index():
    """العرض البشري للمعرفة."""
    items = load_items()
    return render_template_string(HTML_TEMPLATE, items=items, count=len(items))


@bp.route("/search")
def search():
    """API للبحث في المعرفة."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"total": 0, "items": [], "search_query": q})

    items = load_items()
    q_lower = q.lower()
    results = [
        item for item in items
        if q_lower in item["text"].lower()
        or q_lower in " ".join(item.get("tags", [])).lower()
        or q_lower in item.get("source", "").lower()
    ]

    # حدود النتائج
    results = results[:50]
    return jsonify({
        "total": len(results),
        "items": results,
        "search_query": q,
    })


@bp.route("/all")
def list_all():
    """عرض كل المعرفة (تنسيق HTML)."""
    items = load_items()
    return render_template_string(HTML_TEMPLATE, items=items, count=len(items))


@bp.route("/api")
def api_list():
    """عرض كل المعرفة (تنسيق JSON)."""
    items = load_items()
    return jsonify({
        "total": len(items),
        "items": items,
        "source": "knowledge_api",
    })


@bp.route("/refresh")
def refresh():
    """تحديث قاعدة المعرفة (إعادة التحميل)."""
    # إعادة تحميل من الملفات المصدرة
    items = load_items()
    return jsonify({
        "total": len(items),
        "status": "refreshed",
        "message": "تم تحديث قاعدة المعرفة",
    })


# ─── Helpers ─────────────────────────────────────────────────

def load_items():
    """تحميل العناصر من قاعدة المعرفة."""
    if not KB_FILE.exists():
        return []
    try:
        with open(KB_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except Exception:
        return []


@bp.route("/health")
def health():
    """التحقق من صحة الواجهة."""
    if KB_FILE.exists():
        size = KB_FILE.stat().st_size
    else:
        size = 0
    return jsonify({
        "status": "ok",
        "file": str(KB_FILE),
        "size": size,
        "records": load_items(),
        "total": len(load_items()),
        "service": "knowledge_base",
    })
