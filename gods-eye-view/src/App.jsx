import { useState } from "react";
import "./App.css";

function App() {
  const [activeView, setActiveView] = useState("dashboard");

  const navItems = [
    { id: "dashboard", label: "الرئيسية" },
    { id: "monitors", label: "المonitor" },
    { id: "services", label: "الخدمات" },
    { id: "robots", label: "الروبوتات" },
    { id: "knowledge", label: "المعرفة" },
  ];

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">🔭</span>
          <span className="logo-text">
            God's Eye View
            <span className="logo-sub">/ منصة المراقبة</span>
          </span>
        </div>
        <nav className="nav">
          {navItems.map(item => (
            <button
              key={item.id}
              className={activeView === item.id ? "nav-btn active" : "nav-btn"}
              onClick={() => setActiveView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="status-badge">● متصل</div>
      </header>

      <main className="main">
        {activeView === "dashboard" && (
          <div className="view-panel">
            <h2 className="panel-title">لوحة التحكم العامة</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">10/10</div>
                <div className="stat-label">الخدمات تعمل</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">6/6</div>
                <div className="stat-label">العقول النشطة</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">11</div>
                <div className="stat-label">الوكيلات الذكية</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">164</div>
                <div className="stat-label">ملاحظات Obsidian</div>
              </div>
            </div>
            <div className="section">
              <h3 className="section-title">ملخص النظام</h3>
              <div className="summary-text">
                منصة المراقبة الشاملة لنظام EsprieAether — وحدة المراقبة المركزية
                تعرض حالة كل الخدمات والروبوتات والعقول والمعرفة.
              </div>
            </div>
          </div>
        )}

        {activeView === "monitors" && (
          <div className="view-panel">
            <h2 className="panel-title">مراقبة الخدمات في الوقت الفعلي</h2>
            <div className="section">
              <div className="empty-state">
                <p>سوف تظهر هنا قائمة المكونات ووضع كل خادم</p>
                <p style={{ fontSize: "13px", color: "#64748b" }}>
                  الدعم: Router, Agent Mesh, Web Dashboard, Cloud Desktop, Sunna, Integrations, Kanban, HomeDock, DSH Relay
                </p>
              </div>
            </div>
          </div>
        )}

        {activeView === "services" && (
          <div className="view-panel">
            <h2 className="panel-title">الخدمات المم modkولنة</h2>
            <div className="section">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الخدمة</th>
                    <th>النظام</th>
                    <th>الوضع</th>
                    <th>الواجهة</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Ollama</td>
                    <td>AI - JARVIS</td>
                    <td>🟢 متصل</td>
                    <td>11434</td>
                  </tr>
                  <tr>
                    <td>Aether Router</td>
                    <td>AI - Router</td>
                    <td>🟢 متصل</td>
                    <td>11435</td>
                  </tr>
                  <tr>
                    <td>Agent Mesh</td>
                    <td>AI - Mesh</td>
                    <td>🟢 متصل</td>
                    <td>11437</td>
                  </tr>
                  <tr>
                    <td>Web Dashboard</td>
                    <td>فلاسك</td>
                    <td>🟢 متصل</td>
                    <td>5000</td>
                  </tr>
                  <tr>
                    <td>Cloud Desktop</td>
                    <td>السحابة</td>
                    <td>🟢 متصل</td>
                    <td>5001</td>
                  </tr>
                  <tr>
                    <td>Telegram Bot</td>
                    <td>البوت</td>
                    <td>🟢 متصل</td>
                    <td>@Esprieaether_bot</td>
                  </tr>
                  <tr>
                    <td>Sunna API</td>
                    <td>Sunna</td>
                    <td>🟢 متصل</td>
                    <td>5100</td>
                  </tr>
                  <tr>
                    <td>Integrations</td>
                    <td>التكاملات</td>
                    <td>🟢 متصل</td>
                    <td>5102</td>
                  </tr>
                  <tr>
                    <td>Kanban</td>
                    <td>الكانبان</td>
                    <td>🟢 متصل</td>
                    <td>5103</td>
                  </tr>
                  <tr>
                    <td>HomeDock</td>
                    <td>HomeDock</td>
                    <td>🟢 متصل</td>
                    <td>5104</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeView === "robots" && (
          <div className="view-panel">
            <h2 className="panel-title">روبوتات النظام</h2>
            <div className="section">
              <div className="empty-state">
                <p>سوف تظهر هنا قائمة الروبوتات النشطة</p>
                <p style={{ fontSize: "13px", color: "#64748b" }}>
                  الانتقال لقسم الروبوتات في الخادم الرئيسي
                </p>
              </div>
            </div>
          </div>
        )}

        {activeView === "knowledge" && (
          <div className="view-panel">
            <h2 className="panel-title">معرفة Obsidian - تصنيف الملاحظات</h2>
            <div className="section">
              <div className="empty-state">
                <p>سوف تظهر هنا تصنيفات ومحتويات دليل Obsidian</p>
                <p style={{ fontSize: "13px", color: "#64748b" }}>
                  الدليل: /c/Users/ESPRIEAETHER/ObsidianVault/EsprieAether
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        God's Eye View &nbsp;·&nbsp; مراقبة متقدمة للنظام &nbsp;·&nbsp; إصدار 1.0
      </footer>
    </div>
  );
}

export default App;
