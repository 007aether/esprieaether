# wok/agents/business_dev/agent.py
"""
وكيل التنمية والشراكات (Business Development Agent)
- البحث عن فرص الشراكات
- البحث عن فرص التطوير للمؤسسة
- تحليل السوق والاحتياجات
- اقتراحات استراتيجية
"""
import os, json, time, sqlite3, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE.parent.parent / "data"
KB  = BASE / "business_dev.db"
LOG = BASE / "work" / "agents" / "business_dev" / "agent.log"

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
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, type TEXT, location TEXT,
            capabilities TEXT, contact TEXT,
            score REAL, status TEXT, notes TEXT,
            discovered_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, title TEXT, description TEXT,
            status TEXT, priority TEXT, source TEXT,
            created_at TEXT
        )
    """)
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
    """Go to the Web Search tool (hermes_web_search)."""
    try:
        from hermes_tools import web_search as ws
        res = ws(query, limit=limit)
        return res.get("data", {}).get("web", []) if res else []
    except Exception as e:
        log(f"web_search direct failed: {e}")
        return []

def sunna_get(endpoint, params=None):
    """Call Sunna API at http://127.0.0.1:5100/<endpoint>"""
    import requests
    url = f"http://127.0.0.1:5100/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json() if r.status_code == 200 else {"error": r.text}
    except Exception as e:
        log(f"Sunna API error on {endpoint}: {e}")
        return {"error": str(e)}

def find_partners():
    """Search for potential partners"""
    log("Searching for potential partners...")
    queries = [
        "الحديد والمعدن شريك محتمل توزيع",
        "شركات الصلب والصلب جمعيات صناعية",
        "موردو الحديد والصلب توزيع",
        "مشاريع بناء والصلب شراكة",
        "مصنعون للحديد والصلب كبرى"
    ]
    partners = []
    for q in queries:
        results = web_search(q, limit=5)
        for r in results[:3]:
            partners.append({
                "query": q,
                "source": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("description", "")
            })
    # Add Sunna internal data
    sunna_data = sunna_get("status")
    if sunna_data:
        partners.append({
            "query": "Sunna internal",
            "source": "Sunna API",
            "title": "Sunna Équipe Industrial",
            "snippet": f"Company status: {str(sunna_data)[:200]}"
        })
    return partners

def find_opportunities():
    """Search for development opportunities"""
    log("Searching for development opportunities...")
    queries = [
        "تطوير مصنع الحديد والصلب فرص",
        "مزايدات الصلب مشاريع تنموية",
        "تجار الجبس والحديد شراكة",
        "تصنيع البوابات والحواجز مقاومة للصدأ",
        "الصلب ورشة زجاج شراكة طاقة"
    ]
    opportunities = []
    for q in queries:
        results = web_search(q, limit=5)
        for r in results[:3]:
            opportunities.append({
                "query": q,
                "type": "market",
                "title": r.get("title", ""),
                "description": r.get("description", ""),
                "source": r.get("url", "")
            })
    return opportunities

def generate_strategy():
    """Generate strategic recommendations"""
    log("Generating strategic recommendations...")
    opportunities = find_opportunities()
    partners = find_partners()
    strategy = {
        "market_analysis": {
            "opportunities": len(opportunities),
            "partners_found": len(partners),
            "analysis": "التحليل الأولي لفرص السوق والشراكات"
        },
        "recommendations": [
            "تعزيز الشراكات في قطاع الصلب والمعدن",
            "توسيع نطاق الإنتاج عبر المشاريع القائمة",
            "جذب المستوردين والخصم من الموردين الداخليين",
            "تطوير منتجات جديدة: سلّم مقاوم للصدأ، بوابة، درج",
            "مشاركة المنصات الصناعية والجهات الحكومية"
        ]
    }
    conn = get_conn()
    conn.execute("INSERT INTO strategies(category,content,created_at) VALUES(?,?,?)",
                 ("market:strategy", json.dumps(strategy), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return strategy

def run(interval_minutes=120):
    """Main loop"""
    log("Business Development Agent started")
    init_db()
    first_run = True
    while True:
        try:
            partners = find_partners()
            opportunities = find_opportunities()
            strategy = generate_strategy()
            # Store in knowledge
            log(f"Found {len(partners)} partners, {len(opportunities)} opportunities")
            add_memory(json.dumps({"partners": partners, "opportunities": opportunities, "strategy": strategy}),
                       "business:dev")
            if first_run:
                first_run = False
            time.sleep(interval_minutes * 60)
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run(interval_minutes=120)
