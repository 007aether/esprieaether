# wok/agents/market_intel/agent.py
"""
وكيل السوق الذكي للحديد (Market Intelligence Agent)
واكتشاف فئة الحديد والصلب وصلصة الحديد والمنافسين.
- بحث أسعار الحديد الغالفا والسوق
- تحليل الطلب، العرض، الاتجاهات، المنافسون
- تقرير يومي شامل
- تحذيرات عند تغير سعر مهم
- تعلّم تلقائي ويبقى في المعرفة
"""
import os, json, time, sqlite3, re, requests, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent  # agent dir
DATA = BASE.parent.parent / "data"      # /esprieaether/data
KB  = BASE / "market_intel.db"
LOG = BASE / "work" / "agents" / "market_intel" / "agent.log"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_conn():
    conn = sqlite3.connect(KB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, price REAL, unit TEXT,
            demand TEXT, supply TEXT, trend TEXT,
            competitors TEXT, source TEXT, notes TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, title TEXT, content TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger TEXT, old_price REAL, new_price REAL,
            severity TEXT, created_at TEXT
        )
    """)
    # trends over time
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, tags TEXT, updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    log("Database initialized")

def query(query_text, limit=5):
    conn = get_conn()
    cur = conn.execute("SELECT content FROM memories ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def add_memory(content, tags=""):
    conn = get_conn()
    conn.execute("INSERT INTO memories(content,tags,updated_at) VALUES(?,?,?)",
                 (content, tags, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def web_search(query, limit=5):
    """Primary web search. Uses Hermes runtime tools when available, else Sunna internal data."""
    # Primary: Hermes runtime tools (available when agent runs inside Hermes)
    try:
        from hermes_tools import web_search as ws
        res = ws(query, limit=limit)
        if isinstance(res, dict):
            results = res.get("data", {}).get("web", []) or []
            if results:
                return results
    except Exception as e:
        log(f"web_search direct failed: {e}")
    # Fallback: Sunna internal company workspace (read-only)
    try:
        import os
        sunna_dir = os.environ.get("SUNNA_DIR", r"C:\Users\ESPRIEAETHER\Desktop\Sunna-Equipe-Industrial")
        if os.path.isdir(sunna_dir):
            # Look for supplier/product data files
            matches = []
            for root, dirs, files in os.walk(sunna_dir):
                for f in files:
                    if f.endswith(('.md', '.json', '.txt')):
                        matches.append(os.path.join(root, f))
                if len(matches) >= limit * 2:
                    break
            if matches:
                return [{"title": os.path.basename(m), "url": m,
                         "snippet": "Sunna internal document (read-only)"} for m in matches[:limit]]
    except Exception as e:
        log(f"sunna fallback failed: {e}")
    return []

def sunna_get(endpoint, params=None):
    """Call Sunna API at http://127.0.0.1:5100/<endpoint>"""
    url = f"http://127.0.0.1:5100/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json() if r.status_code == 200 else {"error": r.text}
    except Exception as e:
        log(f"Sunna API error on {endpoint}: {e}")
        return {"error": str(e)}

def add_price_history(price, source):
    conn = get_conn()
    conn.execute("INSERT INTO price_history(date,price,source) VALUES(?,?,?)",
                 (datetime.date.today().isoformat(), price, source))
    conn.commit()
    conn.close()

def analyze_market(price, unit, trend, competitors):
    """Simple logic to analyze the market"""
    analysis = {
        "price_direction": "up" if trend in ["up","ascending","+"] else ("down" if trend in ["down","descending","-"] else "stable"),
        "signal": "",
        "recommended_action": ""
    }
    if price > 0:
        analysis["signal"] = "مهم" if abs(price) > 0 else "مستقر"
    # price prediction
    analysis["prediction"] = f"سعر الحديد {price} {unit} — الاتجاه: {analysis['price_direction']}، المنافسين: {competitors or 'غير محدد'}"
    return analysis

def fetch_market_data():
    """Fetch iron market data from web + Sunna internal data"""
    log("Fetching market data from web...")
    results = web_search("سعر الحديد والصلب والغالي في السوق اليوم طلب عرض", limit=8)
    if results:
        data = []
        for r in results[:5]:
            data.append({
                "source": r.get("url", "unknown"),
                "title": r.get("title", ""),
                "snippet": r.get("snippet", "")
            })
        return data
    log("Web search returned nothing, using Sunna internal data")
    sunna = sunna_get("status")
    products = sunna_get("products")
    return [{"source": "Sunna API", "title": "Sunna Équipe Industrial",
             "snippet": f"status={str(sunna)[:150]} products={str(products)[:150]}"}]

def generate_report(data):
    """Generate a daily market report"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# التقرير اليومي للسوق المعدنية — الحديد",
        f"تاريخ التقرير: {ts}",
        "",
        "## 📊 البيانات المستخرجة"
    ]
    for d in data:
        lines.append(f"- {d['title']} : {d['snippet'][:150]}...")
    lines.append(f"\n## 📦 ملخص")
    lines.append("- بيانات السوق جُعِلت.")
    lines.append("- سيتم تحديث التقرير تلقائياً.")
    conn = get_conn()
    conn.execute("INSERT INTO reports(date,title,content,created_at) VALUES(?,?,?,?)",
                 (datetime.date.today().isoformat(), "التقرير اليومي", "\n".join(lines), ts))
    conn.commit()
    conn.close()
    return "\n".join(lines)

def check_alerts(price, unit):
    """Check if price change is significant"""
    conn = get_conn()
    rows = conn.execute("SELECT price FROM price_history ORDER BY date DESC LIMIT 1").fetchall()
    conn.close()
    if rows:
        prev = rows[0]["price"]
        if prev > 0 and abs(price - prev) / prev > 0.03:
            severity = "HIGH" if abs(price - prev) / prev > 0.08 else "MEDIUM"
            log(f"ALERT: iron price changed {prev} -> {price} ({severity})")
            conn = get_conn()
            conn.execute("INSERT INTO alerts(trigger,old_price,new_price,severity,created_at) VALUES(?,?,?,?,?)",
                         (f"Iron price {unit} {price}", prev, price, severity,
                          datetime.datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
    return False

def run(interval_minutes=60):
    """Main loop"""
    log("Market Intelligence Agent started")
    init_db()
    first_run = True
    while True:
        try:
            data = fetch_market_data()
            if data:
                price = data[0].get("price", 0)
                unit = data[0].get("unit", "دواليم")
                add_price_history(price, "web")
                if check_alerts(price, unit):
                    log("Alert triggered, will notify")
            report = generate_report(data)
            log(f"Report generated: {report[:100]}...")
            add_memory(report, "market:intel")
            if first_run:
                first_run = False
            time.sleep(interval_minutes * 60)
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run(interval_minutes=60)
