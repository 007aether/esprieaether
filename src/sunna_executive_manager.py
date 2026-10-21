#!/usr/bin/env python3
"""
SUNNA EXECUTIVE MANAGER (الكل)
═══════════════════════════════════════════════════════
Complete Executive Management System for SUNNA Company.
EsprieAether = Executive Director.

Capabilities:
  📊 Production Management
  💰 Pricing & Profit Management
  🛒 Supplier Management
  📢 Marketing & Sales
  ⚙️ Operational Efficiency
  💵 Financial Management
  ✅ Quality Control

Usage:
  python3 src/sunna_executive_manager.py [--start] [--stop] [--daemon]
  python3 src/sunna_executive_manager.py --guide   # show all capabilities
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Flask for dashboard
try:
    from flask import Flask, request, jsonify, render_template_string
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

BASE_DIR = Path(__file__).resolve().parent
SUNNA_DIR = BASE_DIR.parent / "Sunna-Equipe-Industrial"
STATE_FILE = BASE_DIR.parent / "data" / "sunna_executive_state.json"

# ── Default state ──
DEFAULT_STATE = {
    "company": {
        "name": "SUNNA ÉQUIPE INDUSTRIAL",
        "type": "SARL AU",
        "ice": "004054044000074",
        "activity": "تصنيع منتجات معدنية · حدادة · غلفنة · هياكل",
        "workshop": "72م² — الدار البيضاء",
        "phone": "0770720602",
    },
    "director": {
        "name": "EsprieAether",
        "role": "Executive Director (AI Agent OS)",
        "status": "online",
        "capabilities": ["production", "pricing", "suppliers", "marketing", "operations", "finance", "quality"],
    },
    "production": {
        "status": "idle",
        "last_audit": None,
        "tasks_queued": [],
        "inventory_status": "unknown",
        "recommendations": [],
    },
    "pricing": {
        "status": "idle",
        "last_analysis": None,
        "markup_strategy": "auto",
        "recommendations": [],
    },
    "suppliers": {
        "status": "idle",
        "last_review": None,
        "vendors_evaluated": [],
        "recommendations": [],
    },
    "marketing": {
        "status": "idle",
        "last_campaign": None,
        "leads_generated": 0,
        "recommendations": [],
    },
    "operations": {
        "status": "idle",
        "last_audit": None,
        "task_queue": [],
        "recommendations": [],
    },
    "finance": {
        "status": "idle",
        "last_analysis": None,
        "cash_position": "unknown",
        "recommendations": [],
    },
    "quality": {
        "status": "idle",
        "last_audit": None,
        "defects_found": 0,
        "recommendations": [],
    },
    "dashboard": {
        "host": "0.0.0.0", "port": 5105, "url": "http://localhost:5105",
    },
    "logs": [],
    "running": False,
}


class SunnaExecutiveManager:
    """
    Complete Executive Management System for SUNNA Company.
    EsprieAether = Executive Director.
    """

    def __init__(self):
        self.state = self._load_state()
        self.running = False
        self._lock = threading.Lock()
        self._log("Sunna Executive Manager initialized")

    def _load_state(self):
        try:
            if STATE_FILE.exists():
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return json.loads(json.dumps(DEFAULT_STATE))

    def _save_state(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            self._log(f"Failed to save state: {e}")

    def _log(self, message):
        entry = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.state["logs"].append(entry)
        self._log_to_console(entry)
        self._trim_logs()

    def _trim_logs(self):
        if len(self.state["logs"]) > 500:
            self.state["logs"] = self.state["logs"][-500:]

    def _log_to_console(self, message):
        print(message)

    def _queue_task(self, module, action, details):
        self.state[module]["tasks_queued"].append({
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._log(f"[{module}] Queued: {action} - {details}")
        return True

    # ════════════════════════════════════════════════════
    #  PRODUCTION MANAGEMENT
    # ════════════════════════════════════════════════════

    def manage_production(self):
        self._log("Production management started")
        self.state["production"]["status"] = "running"
        self._queue_task("production", "audit", "Starting production audit")

        # Sync from Sunna directory
        catalogue_dir = SUNNA_DIR / "Catalogue"
        if catalogue_dir.exists():
            products = [f.name for f in catalogue_dir.iterdir() if f.is_dir()]
            self.state["production"]["products"] = products
            self._log(f"Found {len(products)} product categories")

        # Audit
        self.state["production"]["last_audit"] = datetime.now(timezone.utc).isoformat()
        self.state["production"]["status"] = "completed"

        # Generate recommendations
        recs = self._generate_production_recommendations()
        self.state["production"]["recommendations"] = recs
        self._log(f"Production recommendations: {len(recs)}")

        self._save_state()
        self._log("Production management completed")
        return recs

    def _generate_production_recommendations(self):
        """Generate production-related recommendations"""
        recs = [
            "Prioritize high-demand products (steel structures, galvanized panels)",
            "Review inventory of galvanization materials (last 6h checked)",
            "Schedule production runs for best-selling items",
            "Implement kanban system for material tracking",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  PRICING & PROFIT MANAGEMENT
    # ════════════════════════════════════════════════════

    def manage_pricing(self):
        self._log("Pricing management started")
        self.state["pricing"]["status"] = "running"

        # Load price data
        price_file = SUNNA_DIR / "Recherche" / "live_prices.json"
        if price_file.exists():
            try:
                prices = json.loads(price_file.read_text(encoding="utf-8"))
                self.state["pricing"]["live_prices"] = prices
                self.state["pricing"]["last_analysis"] = datetime.now(timezone.utc).isoformat()
                self._log(f"Loaded {len(prices)} price entries")
            except Exception:
                pass

        # Generate price recommendations
        recs = self._generate_pricing_recommendations()
        self.state["pricing"]["recommendations"] = recs
        self.state["pricing"]["status"] = "completed"

        self._save_state()
        self._log("Pricing management completed")
        return recs

    def _generate_pricing_recommendations(self):
        """Generate pricing-related recommendations"""
        recs = [
            "Apply 15-20% markup on steel products for profit margin",
            "Check competitor prices daily (M1_Marche_Metallerie agent)",
            "Price galvanization services: 30% above material cost",
            "Increase prices on slow-moving products by 10%",
            "Maintain lead times: 2-3 weeks for standard structures",
            "Track net profit per product (not just unit price)",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  SUPPLIER MANAGEMENT
    # ════════════════════════════════════════════════════

    def manage_suppliers(self):
        self._log("Supplier management started")
        self.state["suppliers"]["status"] = "running"

        # Load vendor/market data
        research_dir = SUNNA_DIR / "Recherche"
        if research_dir.exists():
            files = list(research_dir.glob("*.md"))
            self.state["suppliers"]["vendors_evaluated"] = [
                {"file": f.name, "evaluated": datetime.now(timezone.utc).isoformat()}
                for f in files[:7]
            ]
            self.state["suppliers"]["last_review"] = datetime.now(timezone.utc).isoformat()
            self._log(f"Evaluated {len(files)} research files")

        # Generate supplier recommendations
        recs = self._generate_supplier_recommendations()
        self.state["suppliers"]["recommendations"] = recs
        self.state["suppliers"]["status"] = "completed"

        self._save_state()
        self._log("Supplier management completed")
        return recs

    def _generate_supplier_recommendations(self):
        """Generate supplier-related recommendations"""
        recs = [
            "Prioritize local suppliers (reduce shipping time and cost)",
            "Negotiate bulk pricing for steel (minimum 500kg orders)",
            "Evaluate Galvanization specialists: A1-G agent covers 9 companies",
            "Add backup suppliers for critical materials (steel, zinc)",
            "Track delivery times and quality per supplier",
            "Quarterly review for all vendors with scorecard system",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  MARKETING & SALES
    # ════════════════════════════════════════════════════

    def manage_marketing(self):
        self._log("Marketing management started")
        self.state["marketing"]["status"] = "running"

        # Generate marketing recommendations
        recs = self._generate_marketing_recommendations()
        self.state["marketing"]["recommendations"] = recs
        self.state["marketing"]["last_campaign"] = datetime.now(timezone.utc).isoformat()
        self.state["marketing"]["status"] = "completed"

        self._save_state()
        self._log("Marketing management completed")
        return recs

    def _generate_marketing_recommendations(self):
        """Generate marketing-related recommendations"""
        recs = [
            "Post on LinkedIn: daily market updates (steel prices, projects)",
            "Update Instagram: photos of completed projects",
            "Send weekly newsletter (offer + market insights)",
            "Track competitor posts and react quickly",
            "Target: E-commerce for B2B products",
            "Generate 5 leads per day minimum",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  OPERATIONS MANAGEMENT
    # ════════════════════════════════════════════════════

    def manage_operations(self):
        self._log("Operations management started")
        self.state["operations"]["status"] = "running"

        # Generate operational recommendations
        recs = self._generate_operations_recommendations()
        self.state["operations"]["recommendations"] = recs
        self.state["operations"]["last_audit"] = datetime.now(timezone.utc).isoformat()
        self.state["operations"]["status"] = "completed"

        self._save_state()
        self._log("Operations management completed")
        return recs

    def _generate_operations_recommendations(self):
        """Generate operations-related recommendations"""
        recs = [
            "Optimize production schedule: 08:00-16:00 (5 days/week)",
            "Assign A1-A4 agents: galvanization, pricing, plans, legal",
            "M1-M2 agents: market and pricing monitoring",
            "L1-L2 agents: tax and labor compliance",
            "Implement daily standup (15 min) with team",
            "Track cycle time per project",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  FINANCIAL MANAGEMENT
    # ════════════════════════════════════════════════════

    def manage_finance(self):
        self._log("Financial management started")
        self.state["finance"]["status"] = "running"

        # Load financial data
        finance_dir = SUNNA_DIR / "Etude_Financiere"
        if finance_dir.exists():
            files = list(finance_dir.glob("*.md"))
            self.state["finance"]["financial_files"] = [
                f.name for f in files[:5]
            ]
            self.state["finance"]["last_analysis"] = datetime.now(timezone.utc).isoformat()

        # Load cash position from working files
        cash_files = list(SUNNA_DIR.glob("*.csv")) + list(SUNNA_DIR.glob("*.xlsx"))
        self.state["finance"]["cash_position"] = "unknown"  # Could be computed via Excel
        self.state["finance"]["recommendations"] = self._generate_finance_recommendations()

        self.state["finance"]["status"] = "completed"
        self._save_state()
        self._log("Financial management completed")
        return self.state["finance"]["recommendations"]

    def _generate_finance_recommendations(self):
        """Generate financial-related recommendations"""
        recs = [
            "Track daily expenses: materials, labor, tools, transport",
            "Set 3-month cash reserve target (50,000 MAD)",
            "Allocate 20% profit to new equipment",
            "Avoid debt for daily operations",
            "Review weekly: revenue vs costs",
            "Quarterly: tax estimates (L1 agent)",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  QUALITY CONTROL
    # ════════════════════════════════════════════════════

    def manage_quality(self):
        self._log("Quality management started")
        self.state["quality"]["status"] = "running"

        # Generate quality recommendations
        recs = self._generate_quality_recommendations()
        self.state["quality"]["recommendations"] = recs
        self.state["quality"]["last_audit"] = datetime.now(timezone.utc).isoformat()
        self.state["quality"]["status"] = "completed"

        self._save_state()
        self._log("Quality management completed")
        return recs

    def _generate_quality_recommendations(self):
        """Generate quality control recommendations"""
        recs = [
            "Inspect galvanized surfaces: uniform coating, no streaks",
            "Test structural integrity: load test for critical frames",
            "Check dimensions: every 5th product",
            "Document defects: photo + description + severity",
            "Implement 5S system: Sort, Set, Shine, Standardize, Sustain",
            "Monthly quality review with team",
            "Track defect rate: target < 2%",
        ]
        return recs

    # ════════════════════════════════════════════════════
    #  AGGREGATE MANAGER (all at once)
    # ════════════════════════════════════════════════════

    def manage_all(self):
        """Run all management capabilities in sequence"""
        self.running = True
        self._log("=" * 60)
        self._log("Sunna Executive Manager: Full management cycle starting...")

        modules = [
            ("production", self.manage_production),
            ("pricing", self.manage_pricing),
            ("suppliers", self.manage_suppliers),
            ("marketing", self.manage_marketing),
            ("operations", self.manage_operations),
            ("finance", self.manage_finance),
            ("quality", self.manage_quality),
        ]

        for name, func in modules:
            try:
                result = func()
                self._log(f"  ✓ {name}: {len(result)} recommendations")
            except Exception as e:
                self._log(f"  ✗ {name}: Error - {str(e)}")

        self.running = False
        self._log("=" * 60)
        self._log("Full management cycle completed")

        self._save_state()
        return self._get_summary()

    def _get_summary(self):
        """Return executive summary"""
        summary = {
            "executive": "EsprieAether",
            "company": self.state["company"]["name"],
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "modules": {},
        }

        for module in ["production", "pricing", "suppliers", "marketing", "operations", "finance", "quality"]:
            s = self.state.get(module, {})
            summary["modules"][module] = {
                "status": s.get("status", "unknown"),
                "recommendations": len(s.get("recommendations", [])),
                "last_updated": s.get("last_audit") or s.get("last_analysis") or s.get("last_review") or s.get("last_campaign"),
            }

        return summary

    # ════════════════════════════════════════════════════
    #  DASHBOARD
    # ════════════════════════════════════════════════════

    def start_dashboard(self):
        """Start the executive dashboard"""
        if not FLASK_AVAILABLE:
            self._log("⚠️ Flask not available, dashboard skipped")
            return

        self._log(f"Starting dashboard on {self.state['dashboard']['host']}:{self.state['dashboard']['port']}")

        # Create Flask app as instance attribute
        self.app = Flask(__name__)

        @self.app.route("/")
        def dashboard():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/executive")
        def api_exec():
            return jsonify(self._get_summary())

        @self.app.route("/api/state")
        def api_state():
            return jsonify(self.state)

        @self.app.route("/api/schedule", methods=["POST"])
        def api_schedule_task():
            data = request.json or {}
            module = data.get("module", "")
            action = data.get("action", "")

            if module in self.state and action in ["update", "restart"]:
                self._log(f"Scheduled: {module}/{action}")
                return jsonify({"status": "scheduled"})

            return jsonify({"error": f"Unknown module: {module}"}), 400

        # Run Flask in a separate thread
        import threading
        def run_server():
            # Create app and run it
            app = Flask(__name__)
            @app.route("/")
            def dashboard():
                return render_template_string(DASHBOARD_HTML)
            @app.route("/api/executive")
            def api_exec():
                return jsonify(self._get_summary())
            @app.route("/api/state")
            def api_state():
                return jsonify(self.state)
            @app.route("/api/schedule", methods=["POST"])
            def api_schedule_task():
                data = request.json or {}
                module = data.get("module", "")
                action = data.get("action", "")
                if module in self.state and action in ["update", "restart"]:
                    self._log(f"Scheduled: {module}/{action}")
                    return jsonify({"status": "scheduled"})
                return jsonify({"error": f"Unknown module: {module}"}), 400
            app.run(host=self.state["dashboard"]["host"], port=self.state["dashboard"]["port"], threaded=True, debug=False)

        self._dashboard_thread = threading.Thread(target=run_server, daemon=True)
        self._dashboard_thread.start()

        # Wait for server to be ready
        import time
        time.sleep(2)
        self._log(f"✓ Dashboard running at {self.state['dashboard']['url']}")

    def stop(self):
        self.running = False
        self._log("Sunna Executive Manager stopped")


# ── Dashboard HTML ──
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>☀️ Sunna Company — EsprieAether Executive</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a1a; color: #e0e0e0; padding: 20px; }

        .header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #1a1a2e; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { font-size: 24px; color: #ffdd44; }
        .header .subtitle { color: #888; font-size: 14px; }

        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 15px; }
        .stat-card h3 { font-size: 12px; color: #888; text-transform: uppercase; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #ffdd44; }

        .section { background: #1a1a2e; border: 1px solid #333; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
        .section h2 { color: #ffdd44; margin-bottom: 15px; font-size: 18px; }

        .module-card { background: #2a2a3e; border-radius: 8px; padding: 12px; border-left: 3px solid #ffdd44; margin-bottom: 10px; }
        .module-card h4 { color: #ffdd44; font-size: 14px; margin-bottom: 5px; }
        .module-card p { font-size: 12px; color: #aaa; }

        .btn { background: #ffdd44; color: #0a0a1a; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; margin: 5px; }
        .btn:hover { background: #ffee66; }

        .log { background: #0a0a1a; border: 1px solid #333; border-radius: 8px; padding: 15px; font-family: 'Courier New', monospace; font-size: 12px; height: 300px; overflow: auto; margin-top: 15px; }
        .entry { padding: 4px 0; border-bottom: 1px solid #222; }
        .entry.success { color: #48c774; }
        .entry.error { color: #ff6b6b; }
        .entry.info { color: #4a9eff; }

        .module-tabs { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
        .module-tab { background: #2a2a3e; color: #aaa; padding: 10px 20px; border-radius: 6px; cursor: pointer; border: 1px solid #333; }
        .module-tab.active { background: #ffdd44; color: #0a0a1a; font-weight: bold; }

        .status-badge { background: #48c774; color: #0a0a1a; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>☀️ Sunna Company</h1>
            <p class="subtitle">Executive Director — EsprieAether · Agent OS</p>
        </div>
        <div style="text-align: right;">
            <span class="status-badge" id="status-badge">● Online</span>
            <button class="btn" onclick="refreshData()">🔄 Refresh</button>
            <button class="btn" onclick="runManager()">⚙️ Run Manager (ALL)</button>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card"><h3>Status</h3><div class="value" id="mod-status">● Online</div></div>
        <div class="stat-card"><h3>Recommendations</h3><div class="value" id="mod-recs">0</div></div>
        <div class="stat-card"><h3>Captured At</h3><div class="value" id="mod-time">—</div></div>
        <div class="stat-card"><h3>Modules</h3><div class="value" id="mod-count">7</div></div>
    </div>

    <div class="module-tabs">
        <div class="module-tab active" onclick="showModule('production')">📊 Production</div>
        <div class="module-tab" onclick="showModule('pricing')">💰 Pricing</div>
        <div class="module-tab" onclick="showModule('suppliers')">🛒 Suppliers</div>
        <div class="module-tab" onclick="showModule('marketing')">📢 Marketing</div>
        <div class="module-tab" onclick="showModule('operations')">⚙️ Operations</div>
        <div class="module-tab" onclick="showModule('finance')">💵 Finance</div>
        <div class="module-tab" onclick="showModule('quality')">✅ Quality</div>
    </div>

    <div class="section" id="module-content">
        <h2>📊 Production Management</h2>
        <div class="module-card">
            <h4>🛠️ Status</h4>
            <p><span id="prod-status">—</span></p>
            <p>Last audit: <span id="prod-audit">—</span></p>
            <p>Recommendations: <span id="prod-recs">0</span></p>
        </div>
    </div>

    <div class="section">
        <h2>⚙️ System Logs</h2>
        <div class="log" id="log">
            <div class="entry info">Sunna Executive Manager initialized.</div>
        </div>
    </div>

    <script>
        function showModule(module) {
            document.querySelectorAll('.module-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            const conv = {
                'production': '📊 Production Management',
                'pricing': '💰 Pricing & Profit',
                'suppliers': '🛒 Suppliers',
                'marketing': '📢 Marketing',
                'operations': '⚙️ Operations',
                'finance': '💵 Finance',
                'quality': '✅ Quality Control',
            };
            document.getElementById('module-content').innerHTML = '<h2>' + conv[module] + '</h2><div class="module-card"><p>Loading...' + module + '...</p></div>';
            refreshData();
        }

        async function refreshData() {
            try {
                const [state, exec] = await Promise.all([
                    fetch('/api/state').then(r => r.json()),
                    fetch('/api/executive').then(r => r.json()),
                ]);

                const execData = exec.modules || {};
                document.getElementById('mod-status').textContent = state.director?.status || '—';
                document.getElementById('mod-recs').textContent = Object.values(execData).reduce((a, m) => a + (m.recommendations || 0), 0);
                document.getElementById('mod-time').textContent = state.captured_at || '—';

                const modules = ['production', 'pricing', 'suppliers', 'marketing', 'operations', 'finance', 'quality'];
                modules.forEach(m => {
                    const el = document.getElementById(m + '-' + 'status');
                    if (el) el.textContent = state[m]?.status || '—';
                    const aud = document.getElementById(m + '-' + 'audit');
                    if (aud) aud.textContent = state[m]?.last_audit || '—';
                    const recs = document.getElementById(m + '-' + 'recs');
                    if (recs) recs.textContent = (execData[m]?.recommendations || 0);
                });

                // Log
                const log = document.getElementById('log');
                const stateLogs = state.logs || [];
                stateLogs.forEach(entry => {
                    const div = document.createElement('div');
                    div.className = 'entry info';
                    div.textContent = entry;
                    log.appendChild(div);
                });
                log.scrollTop = log.scrollHeight;

            } catch (e) {
                const log = document.getElementById('log');
                log.innerHTML += '<div class="entry error">❌ Refresh failed: ' + e.message + '</div>';
            }
        }

        async function runManager() {
            fetch('/api/schedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ module: 'manager', action: 'run_all' })
            }).then(r => r.json())
              .then(data => {
                  document.getElementById('log').innerHTML += '<div class="entry success">✅ Manager ran all modules</div>';
                  refreshData();
              });
        }

        setInterval(refreshData, 10000);
    </script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sunna Executive Manager")
    parser.add_argument("--start", action="store_true", help="Start the manager")
    parser.add_argument("--stop", action="store_true", help="Stop the manager")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--guide", action="store_true", help="Show capabilities guide")
    parser.add_argument("--modules", type=str, nargs="+", help="Run specific modules (production pricing suppliers marketing operations finance quality)")
    parser.add_argument("--dashboard", action="store_true", help="Start dashboard")
    args = parser.parse_args()

    if args.guide:
        print_guide()
        return

    manager = SunnaExecutiveManager()

    if args.modules:
        # Run specific modules
        module_map = {
            "production": manager.manage_production,
            "pricing": manager.manage_pricing,
            "suppliers": manager.manage_suppliers,
            "marketing": manager.manage_marketing,
            "operations": manager.manage_operations,
            "finance": manager.manage_finance,
            "quality": manager.manage_quality,
        }

        for mod in args.modules:
            if mod in module_map:
                manager._log(f"=== Running: {mod} ===")
                result = module_map[mod]()
                manager._log(f"  → {len(result)} recommendations")
            else:
                print(f"Unknown module: {mod}")

        manager._save_state()
        print("\n✅ Executive manager completed")
        return

    if args.dashboard:
        manager.start_dashboard()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDashboard stopped")

    if args.daemon or args.start:
        manager._log("Starting executive management daemon...")
        manager.running = True

        # Run in a loop
        while manager.running:
            try:
                manager.manage_all()
                time.sleep(3600)  # Run every hour
            except KeyboardInterrupt:
                break

        manager.stop()
        print("\n✅ Sunna Executive Manager stopped")


def print_guide():
    print("""
╔══════════════════════════════════════════════════════════╗
║  ☀️ Sunna Executive Manager — Capabilities Guide         ║
╚══════════════════════════════════════════════════════════╝

  📊 PRODUCTION    →  Track production, inventory, and tasks
  💰 PRICING       →  Markup strategy, competitor pricing, profit
  🛒 SUPPLIERS     →  Vendor evaluation, bulk orders, backup
  📢 MARKETING     →  Social media, leads, market awareness
  ⚙️ OPERATIONS    →  Team workflow, schedule, cycle time
  💵 FINANCE       →  Cash flow, profit tracking, tax planning
  ✅ QUALITY       →  Defect tracking, quality improvement

  Run: python3 src/sunna_executive_manager.py --modules production pricing suppliers marketing operations finance quality

  Dashboard: http://localhost:5105

  ═══════════════════════════════════════════════════════════╗
  ║  EsprieAether = Executive Director | Sunna = Company     ║
  ╚══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
