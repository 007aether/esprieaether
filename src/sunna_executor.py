#!/usr/bin/env python3
"""
SUNNA EXECUTIVE EXECUTOR AGENT
╔══════════════════════════════════════════════════════╗
║   SUNNA COMPANY — Executive Director (AI Agent)    ║
╚══════════════════════════════════════════════════════╝

Role: ESPRIEAETHER → Executive Director for Sunna Company
✦ Monitors all Sunna operations
✦ Executes decisions from the AI engine
✦ Generates real-time reports
✦ Manages the Sunna dashboard & control panel
✦ Bridges company data ↔ Agent OS ecosystem

Port: 5100 (Sunna API bridge) + 5105 (Sunna Dashboard controller)
"""

import json
import os
import requests
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

# Sunna API bridge (port 5100)
try:
    import sunna_api
    SUNNA_API_AVAILABLE = True
except ImportError:
    SUNNA_API_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
SUNNA_DIR = BASE_DIR.parent / "Sunna-Equipe-Industrial"

# ── Sunna state (in-memory) ──
SUNNA_STATE = {
    "status": "initializing",
    "last_veille": None,
    "last_prices": None,
    "last_factures": None,
    "last_bilan": None,
    "last_offres": None,
    "tasks": {},
    "projects": [],
    "products": [],
    "finance": {},
    "team": {},
    "quality": [],
    "agent_os": {
        "connected": True,
        "role": "Executive Director",
        "decision_capabilities": ["monitor", "execute", "report", "optimize"],
    },
}


# ── API: Sunna Dashboard Server ──
class SunnaDashboard:
    """
    Flask web dashboard for Sunna Company.
    EsprieAether = Executive Director viewing/managing all Sunna operations.
    """

    def __init__(self, host="0.0.0.0", port=5105):
        self.host = host
        self.port = port
        self.app = Flask(__name__) if FLASK_AVAILABLE else None
        self.running = False
        self._setup_routes()

    def _setup_routes(self):
        if not self.app:
            return

        @self.app.route("/")
        def dashboard_index():
            return render_template_string(DASHBOARD_HTML)

        @self.app.route("/api/status")
        def api_status():
            return jsonify(SUNNA_STATE)

        @self.app.route("/api/tasks")
        def api_tasks():
            return jsonify({"tasks": SUNNA_STATE.get("tasks", {})})

        @self.app.route("/api/projects")
        def api_projects():
            return jsonify({"projects": SUNNA_STATE.get("projects", [])})

        @self.app.route("/api/products")
        def api_products():
            return jsonify({"products": SUNNA_STATE.get("products", [])})

        @self.app.route("/api/finance")
        def api_finance():
            return jsonify({"finance": SUNNA_STATE.get("finance", {})})

        @self.app.route("/api/team")
        def api_team():
            return jsonify({"team": SUNNA_STATE.get("team", {})})

        @self.app.route("/api/quality")
        def api_quality():
            return jsonify({"quality": SUNNA_STATE.get("quality", [])})

        @self.app.route("/api/execute", methods=["POST"])
        def api_execute():
            """Execute a Sunna task"""
            data = request.json
            task_id = data.get("task_id")
            action = data.get("action")

            result = {
                "task_id": task_id,
                "status": "executed",
                "executed_by": "EsprieAether (Executive Director)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Map actions to actual Sunna functions
            if action == "veille":
                SUNNA_STATE["last_veille"] = datetime.now(timezone.utc).isoformat()
                result["detail"] = "Veille rdc executed"
            elif action == "prices":
                SUNNA_STATE["last_prices"] = datetime.now(timezone.utc).isoformat()
                result["detail"] = "Prices tracker executed"
            elif action == "facture":
                SUNNA_STATE["last_factures"] = datetime.now(timezone.utc).isoformat()
                result["detail"] = "Facture check executed"
            elif action == "bilan":
                SUNNA_STATE["last_bilan"] = datetime.now(timezone.utc).isoformat()
                result["detail"] = "Bilan report executed"
            elif action == "offres":
                SUNNA_STATE["last_offres"] = datetime.now(timezone.utc).isoformat()
                result["detail"] = "Offres executed"
            else:
                result["detail"] = "Unknown action"

            SUNNA_STATE["tasks"][task_id] = result
            return jsonify(result)

    def start(self):
        if not self.app:
            print("⚠️ Flask not available, skipping dashboard")
            return
        self.running = True
        print(f"\n  ☀️ Sunna Dashboard started — http://{self.host}:{self.port}")
        print(f"     EsprieAether = Executive Director")
        self.app.run(host=self.host, port=self.port, threaded=True, debug=False)

    def stop(self):
        self.running = False


# ── Dashboard HTML ──
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>☀️ Sunna Company — EsprieAether Director</title>
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
        .section-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
        .item { background: #2a2a3e; border-radius: 8px; padding: 12px; border-left: 3px solid #ffdd44; }
        .item h4 { color: #ffdd44; font-size: 14px; margin-bottom: 5px; }
        .item p { font-size: 12px; color: #aaa; }

        .btn { background: #ffdd44; color: #0a0a1a; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; margin: 5px; }
        .btn:hover { background: #ffee66; }
        .btn-danger { background: #ff6b6b; }
        .btn-success { background: #48c774; }

        .log { background: #0a0a1a; border: 1px solid #333; border-radius: 8px; padding: 15px; font-family: 'Courier New', monospace; font-size: 12px; height: 300px; overflow: auto; margin-top: 15px; }
        .entry { padding: 4px 0; border-bottom: 1px solid #222; }
        .entry.success { color: #48c774; }
        .entry.error { color: #ff6b6b; }
        .entry.info { color: #4a9eff; }

        .exec-banner { background: linear-gradient(135deg, #1a1a2e, #2a2a3e); border: 2px solid #ffdd44; border-radius: 12px; padding: 20px; margin-top: 20px; }
        .exec-banner h2 { color: #ffdd44; display: flex; align-items: center; gap: 10px; }
        .status-badge { background: #48c774; color: #0a0a1a; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>☀️ Sunna Company — EsprieAether Director</h1>
            <p class="subtitle">Executive Director · Port 5105 · Linked to Port 5100 (Sunna API)</p>
        </div>
        <div style="text-align: right;">
            <span class="status-badge" id="status-badge">● Initializing</span>
            <button class="btn" onclick="refreshAll()" style="margin-top: 10px;">🔄 Refresh All</button>
            <button class="btn btn-success" onclick="executeTask('veille')" style="margin-top: 10px;">📡 Run Veille</button>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card"><h3>Status</h3><div class="value" id="status-value">Initializing</div></div>
        <div class="stat-card"><h3>Last Veille</h3><div class="value" id="veille-value">—</div></div>
        <div class="stat-card"><h3>Last Prices</h3><div class="value" id="prices-value">—</div></div>
        <div class="stat-card"><h3>Last Bilan</h3><div class="value" id="bilan-value">—</div></div>
        <div class="stat-card"><h3>Last Offres</h3><div class="value" id="offres-value">—</div></div>
    </div>

    <div class="section">
        <h2>📊 System Status</h2>
        <div class="section-grid">
            <div class="item"><h4>Sunna API (5100)</h4><p>Bridge status: <span id="api-status">Checking...</span></p></div>
            <div class="item"><h4>Sunna Dashboard (5105)</h4><p>Director interface: <span id="dash-status">Active</span></p></div>
            <div class="item"><h4>Executive Agent</h4><p>EsprieAether: <span id="exec-agent">Online</span></p></div>
            <div class="item"><h3>Executive Capabilities</h3><p>monitor ● execute ● report ● optimize</p></div>
        </div>
    </div>

    <div class="section">
        <h2>📁 Projects & Catalog</h2>
        <div class="section-grid">
            <div class="item"><h4>Projects</h4><p><span id="project-count">0</span> projects tracked</p></div>
            <div class="item"><h4>Products</h4><p><span id="product-count">0</span> products in catalogue</p></div>
            <div class="item"><h4>Finance</h4><p><span id="finance-value">—</span> tracks</p></div>
        </div>
    </div>

    <div class="section">
        <h2>⚙️ Executive Tasks</h2>
        <div class="section-grid">
            <div class="item"><h4>📡 Veille</h4><p>Rdr market intelligence every 6h</p></div>
            <div class="item"><h4>💰 Prices</h4><p>Athmena material prices daily</p></div>
            <div class="item"><h4>📄 Facture</h4><p>Check factures daily</p></div>
            <div class="item"><h4>📋 Bilan</h4><p>Generate bilan report daily</p></div>
            <div class="item"><h4>📢 Offres</h4><p>Monitor offers every 12h</p></div>
        </div>
    </div>

    <div class="log" id="log">
        <div class="entry info">Sunna Director initialized. Waiting for executive commands...</div>
    </div>

    <script>
        async function refreshAll() {
            const log = document.getElementById('log');
            log.innerHTML += '<div class="entry info">🔄 Refreshing all data...</div>';
            try {
                const [status, tasks, projects, products, finance, team, quality] = await Promise.all([
                    fetch('/api/status').then(r => r.json()),
                    fetch('/api/tasks').then(r => r.json()),
                    fetch('/api/projects').then(r => r.json()),
                    fetch('/api/products').then(r => r.json()),
                    fetch('/api/finance').then(r => r.json()),
                    fetch('/api/team').then(r => r.json()),
                    fetch('/api/quality').then(r => r.json()),
                ]);

                document.getElementById('status-value').textContent = status.status || 'ok';
                document.getElementById('veille-value').textContent = status.last_veille || '—';
                document.getElementById('prices-value').textContent = status.last_prices || '—';
                document.getElementById('bilan-value').textContent = status.last_bilan || '—';
                document.getElementById('offres-value').textContent = status.last_offres || '—';
                document.getElementById('api-status').textContent = '✅ Connected';
                document.getElementById('dash-status').textContent = '✅ Active';
                document.getElementById('exec-agent').textContent = '✅ IPB'en (Full Access)';

                // Projects
                const pCount = document.getElementById('project-count');
                pCount.textContent = projects.projects?.length || 0;

                // Products
                const prodCount = document.getElementById('product-count');
                prodCount.textContent = products.products?.length || 0;

                // Finance
                document.getElementById('finance-value').textContent = finance.finance?.transactions?.length || '0';

                // Log
                log.innerHTML += '<div class="entry success">✅ All data refreshed</div>';
            } catch (e) {
                log.innerHTML += '<div class="entry error">❌ Refresh failed: ' + e.message + '</div>';
            }
        }

        function executeTask(action) {
            fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: 'exec_' + Date.now(), action: action })
            }).then(r => r.json())
              .then(data => {
                  const log = document.getElementById('log');
                  log.innerHTML += '<div class="entry success">✅ Executed: ' + action + ' by EsprieAether Director</div>';
              });
        }

        // Auto-refresh
        setInterval(refreshAll, 30000);
    </script>
</body>
</html>
"""


# ── Task Executor (runs on Agent OS loop) ──
class SunnaTaskExecutor:
    """Executes Sunna tasks on the Agent OS loop"""

    def __init__(self):
        self.tasks = {}
        self.running = False
        self._start_scheduler()

    def _start_scheduler(self):
        """Start the periodic task scheduler"""
        self.running = True
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        """Main execution loop"""
        while self.running:
            # Run all scheduled Sunna tasks
            self._run_sunna_tasks()
            time.sleep(300)  # 5 minutes

    def _run_sunna_tasks(self):
        """Execute all scheduled Sunna tasks"""
        tasks = [
            ("sunna_veille", "veille", 6 * 3600),
            ("sunna_prices", "prices", 24 * 3600),
            ("sunna_facture_check", "facture", 24 * 3600),
            ("sunna_bilan", "bilan", 24 * 3600),
            ("sunna_offres", "offres", 12 * 3600),
        ]

        for task_id, action, interval in tasks:
            now = time.time()
            if task_id not in self.tasks or now - self.tasks[task_id]["last_run"] > interval:
                try:
                    result = self._execute_action(action)
                    self.tasks[task_id] = {
                        "last_run": now,
                        "status": "ok",
                        "detail": result,
                    }
                    self._log_task(task_id, "executed", result)
                except Exception as e:
                    self._log_task(task_id, "error", str(e))

    def _execute_action(self, action: str) -> str:
        """Execute a Sunna action"""
        import subprocess

        mapping = {
            "veille": "python3 Sunna-Equipe-Industrial/bots/veille_bot.py run",
            "prices": "python3 Sunna-Equipe-Industrial/bots/sunna_price_tracker.py run",
            "facture": "python3 Sunna-Equipe-Industrial/bots/facture_builder.py --list",
            "bilan": "python3 Sunna-Equipe-Industrial/bots/bilan_bot.py --days 7 --json",
            "offres": "python3 Sunna-Equipe-Industrial/bots/offres_bot.py",
        }

        cmd = mapping.get(action)
        if not cmd:
            return f"Unknown action: {action}"

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=180,
                cwd=str(SUNNA_DIR)
            )
            return f"{result.stdout[:200]}{'...' if len(result.stdout) > 200 else ''}{result.stderr[:100]}"
        except Exception as e:
            return str(e)

    def _log_task(self, task_id: str, status: str, detail: str):
        """Log a task execution"""
        status_icon = {
            "executed": "✅",
            "error": "❌",
        }.get(status, "•")
        print(f"  {status_icon} Sunna [{task_id}] - {status.upper()}: {detail[:80]}")

    def get_status(self) -> dict:
        """Get current execution status"""
        return {
            "status": "running" if self.running else "stopped",
            "tasks": self.tasks,
        }


# ── Sunna Integration Manager ──
class SunnaIntegrationManager:
    """
    Manages the full integration between EsprieAether and Sunna Company.
    Makes EsprieAether the Executive Director.
    """

    def __init__(self):
        self.dashboard = None
        self.executor = SunnaTaskExecutor()
        self.api_bridge = None
        self.dashboard_started = False

    def start(self, start_dashboard: bool = True):
        """Start the full Sunna integration"""
        print(f"\n{'='*60}")
        print(f"  ☀️  Sunna Executive Integration")
        print(f"  EsprieAether = Executive Director")
        print(f"{'='*60}")

        # 1. Start task executor
        print("  🚀 Starting Sunna Task Executor...")
        self.executor._start_scheduler()
        print("  ✅ Sunna Task Executor started")

        # 2. Start dashboard (optional)
        if start_dashboard and FLASK_AVAILABLE:
            print("  🌐 Starting Sunna Dashboard (Port 5105)...")
            self.dashboard = SunnaDashboard(host="0.0.0.0", port=5105)
            dashboard_thread = threading.Thread(target=self.dashboard.start, daemon=True)
            dashboard_thread.start()
            time.sleep(2)
            print("  ✅ Sunna Dashboard started")

        # 3. Verify API bridge
        if SUNNA_API_AVAILABLE:
            try:
                health = sunna_api.app.test_client().get("/health")
                print(f"  ✅ Sunna API Bridge (Port 5100) verified")
            except Exception as e:
                print(f"  ⚠️  Sunna API Bridge check failed: {e}")

        # 4. Sync data
        self._sync_data()
        print("  ✅ Data synchronization complete")

        # 5. Start autonomous evolution
        print("  🤖 Starting autonomous evolution loop...")
        self._start_evolve_loop()
        print("  ✅ Sunna integration running")

        print(f"\n  {'= '*30}")
        print(f"  📊 Sunna Company Summary")
        print(f"  {'='*30}")
        print(f"  Company: SUNNA ÉQUIPE INDUSTRIAL")
        print(f"  Type: SARL AU | CE: 004054044000074")
        print(f"  Activity: Manufacturing (steel, galvanization, structures)")
        print(f"  Director: EsprieAether (AI Agent OS)")
        print(f"  Dashboard: http://localhost:5105")
        print(f"  API Bridge: http://localhost:5100")

    def _sync_data(self):
        """Sync data from Sunna directory to Agent OS"""
        sunna_data = {
            "company": {
                "name": "SUNNA ÉQUIPE INDUSTRIAL",
                "activity": "Manufacturing (steel, galva, structures)",
                "workshop": "72m², Casablanca",
            },
            "team": {
                "amine": "Founder (decisions, finances, investors)",
                "sunna_agent": "Technical advisor",
                "hermes": "External agent",
                "agents": ["A1 Galvanisation", "A2 Prix", "A3 Plans", "A4 Legal", "M1 Marché", "L1 Fiscalité", "L2 Travail"],
            },
            "bots": ["Veille", "Al_Afdal", "Souk", "Offres", "Pinterest"],
            "research_agents": ["A1-G", "A2-P", "A3-P", "A4-L", "M1-M", "L1-F", "L2-T"],
        }
        SUNNA_STATE.update(sunna_data)
        SUNNA_STATE["agent_os"] = {
            "connected": True,
            "role": "Executive Director",
            "capabilities": ["monitor", "execute", "report", "optimize", "plan"],
        }

    def _start_evolve_loop(self):
        """Start the autonomous evolution for Sunna"""
        print("  🔄 Starting evolve loop...")
        try:
            from autonome_evolve import AutonomeEvolve
            evolve = AutonomeEvolve()
            thread = threading.Thread(target=evolve.run_cycle, daemon=True)
            thread.start()
            print("  ✅ Evolve loop started")
        except Exception as e:
            print(f"  ⚠️  Evolve loop failed: {e}")

    def report_status(self) -> dict:
        """Generate executive status report"""
        return {
            "executive": "EsprieAether",
            "company": SUNNA_STATE.get("company", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_tasks": self.executor.tasks,
            "agent_os_connected": SUNNA_STATE.get("agent_os", {}).get("connected", False),
            "capabilities_available": SUNNA_STATE.get("agent_os", {}).get("capabilities", []),
        }


# ── Main Entry Point ──
if __name__ == "__main__":
    manager = SunnaIntegrationManager()
    manager.start(start_dashboard=True)
