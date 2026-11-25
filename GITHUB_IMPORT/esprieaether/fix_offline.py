#!/usr/bin/env python3
"""Fix offline_mode.py syntax errors"""
import os

BASE = "/c/Users/ESPRIEAETHER/Desktop/esprieaether"
path = os.path.join(BASE, "src", "offline_mode.py")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the broken get_dashboard_html method
old_method = '''    def get_dashboard_html(self) -> str:
        """Generate HTML dashboard for offline status."""
        status = self.get_local_status()
        offline = self.offline_mode

        return f"""\n<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>☀️ EsprieAether — Anti-Offline Mode</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #e0e0e0; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #1a1a2e; border-radius: 12px; margin-bottom: 20px; }}
        .header h1 {{ color: #ffdd44; }}
        .status-box {{ background: #1a1a2e; border: 2px solid #48c774; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
        .status-box h2 {{ color: #48c774; margin-bottom: 10px; }}
        .status-box .badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; background: #48c774; color: #0a0a1a; font-weight: bold; font-size: 14px; }}
        .card {{ background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
        .card h2 {{ color: #ffdd44; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat {{ text-align: center; padding: 15px; background: #2a2a3e; border-radius: 8px; }}
        .stat .value {{ font-size: 28px; font-weight: bold; color: #48c774; }}
        .stat .label {{ font-size: 12px; color: #888; }}
        .provider {{ margin-bottom: 15px; }}
        .provider h4 {{ color: #ffdd44; }}
        .provider .state {{ font-size: 12px; color: #888; }}
        .btn {{ background: #ffdd44; color: #0a0a1a; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; }}
        .footer {{ text-align: center; color: #666; padding: 20px; }}
        .offline-badge {{ background: #ff4444; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-left: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>☀️ EsprieAether — Anti-Offline Mode</h1>
            <p>لن يعمل أي ميزة في النظام بدون الإنترنت</p>
        </div>
        <div style="text-align: right;">
            <span class="badge" id="status-badge">● Local-First</span>
            <span class="offline-badge" id="offline-badge" style="display: {'block' if offline else 'none'}">وضع العزل 🇲🇦</span>
        </div>
    </div>

    <div class="status-box">
        <h2>🔒 الوضع المحلي - Anti-Offline</h2>
        <p style="font-size: 14px;">
            {% if all_local_online %}
                <span style="color: #48c774;">✅ كل الخدمات المحلية تعمل بشكل صحيح</span>
            {% else %}
                <span style="color: #ffdd44;">⚠️ بعض الخدمات غير متاحة</span>
            {% endif %}
        </p>
    </div>

    <div class="stats">
        <div class="card">
            <div class="stat"><div class="value" id="local-status">—</div><div class="label">الوضع المحلي</div></div>
            <div class="stat"><div class="value" id="local-status-text">قيد الفحص</div><div class="label">خدمات المحلية</div></div>
        </div>
    </div>

    <div class="card">
        <h2>🧠 الخدمات المحلية</h2>
        <div class="provider">
            <h4>🌐 Ollama (qwen2.5:3b)</h4>
            <p class="state" id="ollama-state">فحص...</p>
        </div>
        <div class="provider">
            <h4>🧠 Colibri (qwen3-coder-30b)</h4>
            <p class="state" id="colibri-state">فحص...</p>
        </div>
    </div>

    <div class="footer">
        <p>✅ نظام العمل بلا انقطاق - Always Works Offline</p>
        <p>📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""'''

new_method = '''    def get_dashboard_html(self) -> str:
        """Generate HTML dashboard for offline status."""
        if not FLASK_AVAILABLE:
            return ""

        status = self.get_local_status()
        offline = self.offline_mode

        # Build status messages
        if status.get("all_local_online"):
            online_text = '<span style="color: #48c774;">✅ كل الخدمات المحلية تعمل بشكل صحيح</span>'
        else:
            online_text = '<span style="color: #ffdd44;">⚠️ بعض الخدمات غير متاحة</span>'

        ollama_state = (
            '<span style="color: #48c774;">✅ متصل</span>'
            if self.services["ollama-local"]["status"] == "online"
            else '<span style="color: #ff4444;">❌ غير متصل</span>'
        )
        colibri_state = (
            '<span style="color: #48c774;">✅ متصل</span>'
            if self.services["colibri-local"]["status"] == "online"
            else '<span style="color: #ff4444;">❌ غير متصل</span>'
        )

        # Count available resources
        provider_count = len(self.config.get("providers", {})) if hasattr(self, 'config') else 0
        agent_count = len(self.config.get("agents", {})) if hasattr(self, 'config') else 0
        skill_count = len(self.config.get("skills", {})) if hasattr(self, 'config') else 0

        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>☀️ EsprieAether — Anti-Offline Mode</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #e0e0e0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #1a1a2e; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { color: #ffdd44; }
        .status-box { background: #1a1a2e; border: 2px solid #48c774; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .status-box h2 { color: #48c774; margin-bottom: 10px; }
        .card { background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #ffdd44; margin-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat { text-align: center; padding: 15px; background: #2a2a3e; border-radius: 8px; }
        .stat .value { font-size: 28px; font-weight: bold; color: #48c774; }
        .stat .label { font-size: 12px; color: #888; }
        .provider { margin-bottom: 15px; }
        .provider h4 { color: #ffdd44; }
        .provider .state { font-size: 12px; color: #888; }
        .footer { text-align: center; color: #666; padding: 20px; }
        .offline-badge { background: #ff4444; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-left: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>☀️ EsprieAether — Anti-Offline Mode</h1>
            <p>لن يعمل أي ميزة في النظام بدون الإنترنت</p>
        </div>
        <div style="text-align: right;">
            <span class="badge" id="status-badge">● Local-First</span>
            <span class="offline-badge" id="offline-badge" style="display: block;">وضع العزل 🇲🇦</span>
        </div>
    </div>

    <div class="status-box">
        <h2>🔒 الوضع المحلي - Anti-Offline</h2>
        <p style="font-size: 14px;">
            {online_text}
        </p>
    </div>

    <div class="stats">
        <div class="card">
            <div class="stat"><div class="value">{providers}</div><div class="label">AI Providers</div></div>
            <div class="stat"><div class="value">{agents}</div><div class="label">Agents</div></div>
            <div class="stat"><div class="value">{skills}</div><div class="label">Skills</div></div>
        </div>
    </div>

    <div class="card">
        <h2>🧠 الخدمات المحلية</h2>
        <div class="provider">
            <h4>🌐 Ollama (qwen2.5:3b)</h4>
            <p class="state" style="color: {ollama_color};">{ollama_state}</p>
        </div>
        <div class="provider">
            <h4>🧠 Colibri (qwen3-coder-30b)</h4>
            <p class="state" style="color: {colibri_color};">{colibri_state}</p>
        </div>
    </div>

    <div class="footer">
        <p>✅ نظام العمل بلا انقطاق - Always Works Offline</p>
        <p>📅 التاريخ: {date}</p>
    </div>
</body>
</html>"""

        html = html.format(
            online_text=online_text,
            providers=provider_count,
            agents=agent_count,
            skills=skill_count,
            ollama_color="#48c774",
            ollama_state=ollama_state,
            colibri_color="#48c774",
            colibri_state=colibri_state,
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        return html'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Old method not found!")
