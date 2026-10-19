import { useState, useEffect, useCallback } from "react";
import "./App.css";

function App() {
  const [robots, setRobots] = useState([]);
  const [stats, setStats] = useState({});
  const [obsidian, setObsidian] = useState({ categories: {}, agents: [], bots: [], integrations: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState("dashboard");

  const API = "http://127.0.0.1:5000";

  const fetchRobots = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/robots`);
      const data = await res.json();
      setRobots(data.robots || []);
      setStats(data.stats || {});
    } catch (e) {
      setError("لا يمكن الاتصال بخادم EsprieAether: " + e.message);
    }
  }, [API]);

  const fetchObsidian = useCallback(async () => {
    try {
      const res = await fetch(`${API}/obsidian`);
      const text = await res.text();
      const links = text.match(/\[\[([^\]]+)\]\]/g) || [];
      const names = links.map(l => l.slice(2, -2)).filter(Boolean);
      const unique = [...new Set(names)];
      const categories = {};
      unique.forEach(name => {
        const cat = name.split("/")[0] || "misc";
        if (!categories[cat]) categories[cat] = [];
        if (categories[cat].length < 10) categories[cat].push(name);
      });
      setObsidian({
        categories,
        agents: unique.filter(n => n.includes("-agent") || n.includes("agent")),
        bots: unique.filter(n => n.includes("-bot") || n.includes("bot")),
        integrations: unique.filter(n => n.includes("-integration") || n.includes("integration")),
        total: unique.length
      });
    } catch (e) {
      setError("لا يمكن تحميل بيانات Obsidian: " + e.message);
    }
  }, [API]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRobots();
      fetchObsidian();
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, [fetchRobots, fetchObsidian]);

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">&#9679;</span>
          <span className="logo-text">
            AETHER <span className="logo-sub">/ عين الاه</span>
          </span>
        </div>
        <nav className="nav">
          {["dashboard", "robots", "graph", "knowledge"].map(view => (
            <button
              key={view}
              className={activeView === view ? "nav-btn active" : "nav-btn"}
              onClick={() => setActiveView(view)}
            >
              {view === "dashboard" && "الرئيسية"}
              {view === "robots" && "الروبوتات"}
              {view === "graph" && "الرسم البياني"}
              {view === "knowledge" && "المعرفة"}
            </button>
          ))}
        </nav>
        <div className="status-badge">
          {loading ? "جاري التحميل..." : "متصل"}
        </div>
      </header>

      <main className="main">
        {activeView === "dashboard" && (
          <div className="view-panel">
            <h2 className="panel-title">لوحة التحكم العامة</h2>
            {error && <div className="error-msg">{error}</div>}
            {loading ? (
              <div className="loading-spinner">&#12300;</div>
            ) : (
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{robots.length}</div>
                  <div className="stat-label">روبوتات نشطة</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{obsidian.total}</div>
                  <div className="stat-label">عنصر معرفة في Obsidian</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{Object.keys(stats).length}</div>
                  <div className="stat-label">إحصائيات نظام</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">10/10</div>
                  <div className="stat-label">الخدمات تعمل</div>
                </div>
              </div>
            )}
            {robots.length > 0 && (
              <div className="section">
                <h3 className="section-title">روبوتات النشطة</h3>
                <ul className="robos-list">
                  {robots.map(r => (
                    <li key={r.id} className="robot-item">
                      <span className={`robot-badge robot-${r.system || "unknown"}`}>{r.system || "unknown"}</span>
                      <span className="robot-name">{r.name}</span>
                      <span className="robot-role">{r.role}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeView === "robots" && (
          <div className="view-panel">
            <h2 className="panel-title">روبوتات النظام</h2>
            <div className="section">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الاسم</th>
                    <th>النظام</th>
                    <th>الدور</th>
                    <th>الحالة</th>
                  </tr>
                </thead>
                <tbody>
                  {robots.map(r => (
                    <tr key={r.id}>
                      <td>{r.name}</td>
                      <td>{r.system || "-"}</td>
                      <td>{r.role || "-"}</td>
                      <td><span className="status-dot">&#9679;</span> {r.status || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeView === "graph" && (
          <div className="view-panel">
            <h2 className="panel-title">الرسم البياني للمعرفة (Obsidian)</h2>
            <div className="section">
              <iframe
                title="obsidian-graph"
                src={`${API}/obsidian`}
                style={{ width: "100%", height: "700px", border: "1px solid #1e293b", borderRadius: "8px" }}
                loading="lazy"
              />
            </div>
          </div>
        )}

        {activeView === "knowledge" && (
          <div className="view-panel">
            <h2 className="panel-title">معرفة Obsidian - كود التصنيف</h2>
            {Object.keys(obsidian.categories).length === 0 ? (
              <div className="empty-state">جاري تحميل المعرفة...</div>
            ) : (
              <div className="categories-grid">
                {Object.entries(obsidian.categories).map(([cat, items]) => (
                  <div key={cat} className="cat-card">
                    <div className="cat-header">
                      <span className="cat-color">&#9632;</span>
                      <span className="cat-name">{cat}</span>
                      <span className="cat-count">{items.length}</span>
                    </div>
                    <ul className="cat-list">
                      {items.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        AETHER / عين الاه &nbsp;·&nbsp; تدعم obsidian &nbsp;·&nbsp; خادم: {API}
      </footer>
    </div>
  );
}

export default App;
