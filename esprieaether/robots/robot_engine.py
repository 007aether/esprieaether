#!/usr/bin/env python3
"""
ESPRIEAETHER ROBOT ENGINE
محرك تنفيذ الروبوتات — scheduler + task queue + role handlers.

كل robot عندو role (وظيفة). المحرك كيربط الـ role بـ handler حقيقي،
وكيديرها ف loop مستمر (idle → active → done → idle).

الواجهة:
  engine = RobotEngine()
  engine.run_once()      # دورة واحدة (كل robots)
  engine.start()         # loop مستمر (thread)
  engine.get_stats()     # حالة كل robot
"""

import os
import re
import sys
import time
import json
import hashlib
import shutil
import sqlite3
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# ─── Paths ───
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

from policy_gate import check_url  # noqa: E402

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")
PRODUCTION_DB = DB  # repère pour activer le journal uniquement en production
LOG_FILE = BASE_DIR / "robot_engine.log"

# Cibles des gardiens (chemins locaux uniquement, aucun secret lu ou affiché).
ROOT_DIR = BASE_DIR.parent
PY_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"
NODE_EXE = ROOT_DIR / ".tools" / "node-v26.13.1" / "node.exe"
GIT_EXE = ROOT_DIR / ".tools" / "git" / "cmd" / "git.exe"
ENV_PATH = BASE_DIR / ".env"
ENV_SHA256 = "DE9449DD1DB4F3A7EAE2C78B887E280981503D4D0B76BFF70105D5CA9FE27A7E"
VAULT_DIR = Path.home() / "ObsidianVault" / "EsprieAether"
PROJECT_MAP = Path(r"C:\Users\aether\Documents\Projet par défaut\PROJECT_MAP.md")
REPORT_DIR = BASE_DIR / "state"

# ── J52/J53 : autorité locale et journal d'exécution ──────────────────────
# Configuré par configure_authority(). Sans configuration, le comportement
# historique des robots reste inchangé (aucune régression).
_RUN_STORE = None
_AUTH_MODE = None
_LEDGER_EXPORT = None


def configure_authority(ledger_path=None, export_path=None, mode="full_local"):
    """Active la politique et le journal pour tous les robots du process."""
    global _RUN_STORE, _AUTH_MODE, _LEDGER_EXPORT
    src = str(BASE_DIR / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from policy_gate import AuthorityMode  # import différé : évite le cycle d'import
    from run_store import RunStore
    _AUTH_MODE = mode if isinstance(mode, AuthorityMode) else AuthorityMode(mode)
    _RUN_STORE = RunStore(ledger_path or (REPORT_DIR / "run_ledger.db"))
    _LEDGER_EXPORT = export_path or (REPORT_DIR / "run_ledger.json")
    _RUN_STORE.export_json(_LEDGER_EXPORT)
    return _RUN_STORE


def _authority_decide(role, mode=None):
    from policy_gate import decide
    return decide(role, mode=mode or _AUTH_MODE)

# Services locaux réellement démarrés, vérifiés par le robot de surveillance.
LOCAL_SERVICES = (
    ("jarvis", 5000, "/api/health"),
    ("gateway", 5001, "/agents"),
    ("dashboard", 5100, "/api/dashboard/state"),
    ("dsh_bridge", 5101, "/health"),
    ("homedock", 5104, "/health"),
    ("ai_router", 11435, "/health"),
    ("orchestrator", 11436, "/health"),
    ("agent_mesh", 11437, "/health"),
    ("llm_gateway", 31415, "/health"),
    ("local_brain", 31416, "/health"),
)

# Ces deux services sont volontairement hors du démarrage automatique :
# dsh_bridge appartient à son propre processus, llm_gateway (FreeLLMAPI) est manuel.
MANUAL_LOCAL_SERVICES = ("dsh_bridge", "llm_gateway")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("robot-engine")


# ═══════════════════════════════════════════════════════════════
#  DB Schema
# ═══════════════════════════════════════════════════════════════

def init_engine_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robot_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            action TEXT,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            started_at DATETIME,
            completed_at DATETIME
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robot_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            role TEXT,
            status TEXT,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS robots (
            id TEXT PRIMARY KEY,
            name TEXT,
            system TEXT,
            role TEXT,
            status TEXT DEFAULT 'idle',
            tasks_completed INTEGER DEFAULT 0,
            last_active DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO robots (id, name, system, role, status) VALUES (?,?,?,?,?)",
        ("SYS_01", "SERVICE_SENTINEL", "monitoring", "service_health", "active"),
    )
    for seed in (
        ("SYS_02", "QUALITY_GUARDIAN", "monitoring", "quality_guard", "active"),
        ("SYS_03", "VAULT_GUARDIAN", "monitoring", "vault_guard", "active"),
        ("SYS_04", "BACKLOG_SCOUT", "monitoring", "backlog_scout", "active"),
        ("SYS_05", "AGENT_AUDIT_MIRROR", "monitoring", "agent_audit", "active"),
    ):
        conn.execute(
            "INSERT OR IGNORE INTO robots (id, name, system, role, status) VALUES (?,?,?,?,?)",
            seed,
        )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
#  Role Handlers
# ═══════════════════════════════════════════════════════════════

def _get_robot_info(robot_id: str) -> dict:
    conn = sqlite3.connect(DB)
    r = conn.execute("SELECT id, name, system, role, status FROM robots WHERE id=?", (robot_id,)).fetchone()
    conn.close()
    return {"id": r[0], "name": r[1], "system": r[2], "role": r[3], "status": r[4]} if r else {}


def h_health_check(robot_id: str) -> dict:
    """فحص صحة النظام"""
    try:
        import psutil
        return {
            "ok": True,
            "summary": f"cpu={psutil.cpu_percent()}% mem={psutil.virtual_memory().percent}% disk={psutil.disk_usage('/').percent}%",
        }
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_service_health(robot_id: str) -> dict:
    """Vérifie les endpoints locaux réels et signale ceux qui sont down."""
    import urllib.request

    up, down = [], []
    for name, port, path in LOCAL_SERVICES:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=8
            ) as resp:
                if 200 <= resp.status < 500:
                    up.append(name)
                else:
                    down.append(name)
        except Exception:
            down.append(name)
    expected_down = [name for name in down if name in MANUAL_LOCAL_SERVICES]
    unexpected_down = [name for name in down if name not in MANUAL_LOCAL_SERVICES]
    return {
        "ok": not unexpected_down,
        "summary": f"up={len(up)}/{len(LOCAL_SERVICES)} down={','.join(down) or 'none'}",
        "detail": {
            "up": up,
            "down": down,
            "expected_down": expected_down,
            "unexpected_down": unexpected_down,
        },
    }


def h_log_scan(robot_id: str) -> dict:
    """فحص السجلات للأخطاء"""
    try:
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT COUNT(*) FROM robot_results WHERE status='error'").fetchone()
        conn.close()
        return {"ok": True, "summary": f"robot_errors={rows[0]}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_ai_think(robot_id: str) -> dict:
    """فكر محلي فقط: :31416 (Dolphin) ← :31415 (FreeLLMAPI) ← Ollama :11434."""
    import urllib.request

    messages = [
        {"role": "system", "content": "أنت JARVIS، مساعد EsprieAether. أجب باختصار."},
        {"role": "user", "content": "قل OK فقط"},
    ]

    def _chat(base: str, model: str, body: dict, headers: dict = None, timeout: int = 60) -> str:
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(
            base, data=json.dumps(body).encode("utf-8"), headers=h, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return str((data.get("choices") or [{}])[0].get("message", {}).get("content")
                   or data.get("message", {}).get("content") or "").strip()

    # 1) local brain :31416 — Dolphin 3.0 uncensored, بلا مفتاح
    try:
        base = os.getenv("LOCAL_BRAIN_API_BASE", "http://127.0.0.1:31416").rstrip("/")
        model = os.getenv("LOCAL_BRAIN_MODEL", "dolphin3")
        text = _chat(f"{base}/v1/chat/completions", model,
                     {"model": model, "messages": messages, "max_tokens": 64})
        if text:
            return {"ok": True, "summary": f"engine=local-brain:{model} reply={text[:40]}"}
    except Exception:
        pass

    # 2) FreeLLMAPI :31415 — كلشي محلي، الموديل الأساسي uncensored
    try:
        from src.espria_system import FREELLMAPI_BASE, FREELLMAPI_MODEL, FREELLMAPI_KEY
        text = _chat(f"{FREELLMAPI_BASE}/v1/chat/completions", FREELLMAPI_MODEL,
                     {"model": FREELLMAPI_MODEL, "messages": messages, "max_tokens": 64},
                     {"Authorization": f"Bearer {FREELLMAPI_KEY}"} if FREELLMAPI_KEY else None)
        if text:
            return {"ok": True, "summary": f"engine=freellmapi:{FREELLMAPI_MODEL} reply={text[:40]}"}
    except Exception:
        pass

    # 3) Ollama مباشر — كيخدم غير كيكون شغال، بلا سحابة
    try:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        text = _chat(f"{host}/api/chat", model,
                     {"model": model, "messages": messages, "stream": False})
        if text:
            return {"ok": True, "summary": f"engine=ollama:{model} reply={text[:40]}"}
    except Exception as e:
        return {"ok": False, "summary": f"no_local_engine: {str(e)[:60]}"}
    return {"ok": False, "summary": "no_local_engine: empty_reply"}


def h_git_status(robot_id: str) -> dict:
    """حالة git — يستعمل git المحلي إذا ما كاينش فـ PATH."""
    try:
        import subprocess
        git_exe = shutil.which("git") or (str(GIT_EXE) if GIT_EXE.exists() else "git")
        r = subprocess.run(
            [git_exe, "status", "--porcelain"],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=10
        )
        changes = len([l for l in (r.stdout or "").splitlines() if l.strip()])
        return {"ok": True, "summary": f"pending_changes={changes}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_stats(robot_id: str) -> dict:
    """إحصائيات عامة"""
    try:
        conn = sqlite3.connect(DB)
        total = conn.execute("SELECT COUNT(*) FROM robots").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM robot_results WHERE status='ok'").fetchone()[0]
        conn.close()
        return {"ok": True, "summary": f"robots={total} completed={done}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)}


def h_news_scan(robot_id: str) -> dict:
    """EXT_04 NEWS_SCANNER — فحص الأخبار (RSS)"""
    try:
        from scanners.news_scanner import NewsScanner
        ns = NewsScanner()
        ns.scan_all()  # كيمسح كل الـ RSS feeds
        return {"ok": True, "summary": "news scan done"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_market_scan(robot_id: str) -> dict:
    """EXT_02 CRYPTO_TRADER / EXT_03 STOCK_ANALYZER — أسعار السوق"""
    try:
        from src.market_watcher import MarketWatcher
        mw = MarketWatcher()
        prices = mw.fetch_prices()  # dict
        return {"ok": True, "summary": f"coins={len(prices) if isinstance(prices, dict) else 0}"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_embed(robot_id: str) -> dict:
    """AI_05 EMBEDDER — embedding عبر المحرك المحلي"""
    try:
        import urllib.request
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        payload = json.dumps({"model": model, "prompt": "test embedding"}).encode()
        req = urllib.request.Request(
            f"{host}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        emb = data.get("embedding", [])
        if emb:
            return {"ok": True, "summary": f"embed_dim={len(emb)}"}
        # Ollama شغال بلا embeddings — fallback (ماشي error)
        return {"ok": True, "summary": "embed unavailable (server no --embeddings)"}
    except urllib.error.HTTPError as e:
        # الموديل ما يدعمش embeddings — نعتبره "idle" ماشي error
        return {"ok": True, "summary": f"embed unsupported (model, http {e.code})"}
    except urllib.error.URLError:
        # Ollama est volontairement arrêté : ce n'est pas une erreur du robot.
        return {"ok": True, "summary": "embed indisponible (Ollama arrêté volontairement)"}
    except Exception as e:
        return {"ok": False, "summary": str(e)[:100]}


def h_noop(robot_id: str) -> dict:
    """robots بدون handler حقيقي"""
    return {"ok": True, "summary": "idle (no handler)"}


def h_knowledge(robot_id: str) -> dict:
    """روبوت المعرفة — يربط ذاكرة الش안건 بالنظام (mesh + tasks)."""
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        import knowledge_router as kr
        result = kr.run()
        return {"ok": True, "summary": f"knowledge_router done={result}"}
    except Exception as e:
        return {"ok": False, "summary": f"knowledge_router error: {str(e)[:120]}"}


def h_hexstrike(robot_id: str) -> dict:
    """IMM robots — فحص أمني عبر HexStrike AI (port 8888)"""
    try:
        import urllib.request
        host = os.getenv("HEXSTRIKE_HOST", "http://127.0.0.1:8888")
        gate = check_url(f"{host}/health")
        if not gate.allowed:
            return {"ok": False, "summary": f"egress_blocked:{gate.reason}"}
        # ping HexStrike server
        req = urllib.request.Request(f"{host}/health")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        status = data.get("status", "unknown")
        return {"ok": True, "summary": f"hexstrike={status}"}
    except Exception as e:
        # HexStrike offline — graceful (ماشي error)
        return {"ok": True, "summary": f"hexstrike offline ({str(e)[:40]})"}


# ═══════════════════════════════════════════════════════════════
#  Gardiens SYS_02 → SYS_04 (qualité, vault, backlog)
# ═══════════════════════════════════════════════════════════════

def _sha256(path: Path) -> str:
    """Empreinte SHA256 en majuscules — le contenu du fichier n'est jamais lu."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _run_checked_command(cmd: list, cwd: Path, timeout: int) -> tuple:
    """Exécute une commande locale et renvoie (code_retour, sortie)."""
    proc = subprocess.run(
        [str(x) for x in cmd], cwd=str(cwd), capture_output=True,
        text=True, timeout=timeout, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _parse_python_tests(output: str) -> tuple:
    match = re.search(r"Ran (\d+) tests?", output)
    ran = int(match.group(1)) if match else 0
    return ran, ran > 0 and bool(re.search(r"^OK(?:\s|$)", output, re.M))


def _parse_node_tests(output: str) -> tuple:
    passed = re.search(r"pass (\d+)", output)
    failed = re.search(r"fail (\d+)", output)
    return (int(passed.group(1)) if passed else 0,
            int(failed.group(1)) if failed else -1)


def _vault_checks(vault: Path = None) -> dict:
    """Vérifie les faits déjà corrigés : JARVIS :5000, lien local-brain, pas de CDN."""
    vault = Path(vault) if vault is not None else VAULT_DIR
    checks = {}
    try:
        text = (vault / "Services" / "jarvis.md").read_text(encoding="utf-8")
        checks["jarvis_port_5000"] = "Port **5000**" in text
        checks["jarvis_verified"] = "✅ Vérifié" in text
        checks["jarvis_links_brain"] = "[[local-brain]]" in text
    except OSError:
        checks.update(jarvis_port_5000=False, jarvis_verified=False,
                      jarvis_links_brain=False)
    try:
        html = (vault / "graph.html").read_text(encoding="utf-8")
        checks["graph_local_brain"] = '"local-brain"' in html
        checks["graph_jarvis_brain_edge"] = (
            '"from": "jarvis", "to": "local-brain"' in html
        )
        checks["graph_no_cdn"] = not re.search(
            r"""<script[^>]*\bsrc=["']https?://""", html, re.I
        )
        nodes = re.search(r"const nodes=new vis\.DataSet\(\[(.*?)\]\);", html, re.S)
        edges = re.search(r"const edges=new vis\.DataSet\(\[(.*?)\]\);", html, re.S)
        checks["nodes"] = nodes.group(1).count('"id":') if nodes else 0
        checks["edges"] = edges.group(1).count('"from":') if edges else 0
    except OSError:
        checks.update(graph_local_brain=False, graph_jarvis_brain_edge=False,
                      graph_no_cdn=False, nodes=0, edges=0)
    checks["ok"] = all(v for v in checks.values() if isinstance(v, bool))
    return checks


def _write_report(filename: str, payload: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _parse_backlog(text: str) -> list:
    """Extrait les lignes O*-n ouvertes/en cours sans inventer de décision."""
    items = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        match = re.match(r"^\|\s*(O\d+)\s*\|", line)
        if match and ("Ouvert" in line or "En cours" in line):
            items.append({"id": match.group(1), "detail": line.strip()[:240]})
    return items


def _parse_milestones(text: str, limit: int = 20) -> list:
    """Extrait les lignes J* du journal d'audit, bornées, sans LLM ni réseau."""
    items = []
    for line in text.splitlines():
        match = re.match(r"^\|\s*(J\d+(?:-[a-z])?)\s*\|", line)
        if match:
            items.append({"id": match.group(1), "detail": line.strip()[:240]})
    return items[-limit:]


def h_quality_guard(robot_id: str) -> dict:
    """SYS_02 — tests, empreinte .env, endpoints et graphe : un seul verdict."""
    checks, detail = {}, {"checked_at": datetime.now().isoformat()}

    try:
        code, output = _run_checked_command(
            [PY_EXE, "-m", "unittest", "discover", "-s", "tests"], BASE_DIR, 240
        )
        ran, ok = _parse_python_tests(output)
        checks["python"] = ok and code == 0
        detail["python"] = {"ran": ran, "ok": ok, "returncode": code}
    except Exception as exc:
        checks["python"] = False
        detail["python"] = {"error": str(exc)[:160]}

    try:
        code, output = _run_checked_command(
            [NODE_EXE, "--test", "tests/dashboard.test.mjs"], ROOT_DIR, 180
        )
        passed, failed = _parse_node_tests(output)
        checks["dashboard"] = passed > 0 and failed == 0 and code == 0
        detail["dashboard"] = {"passed": passed, "failed": failed, "returncode": code}
    except Exception as exc:
        checks["dashboard"] = False
        detail["dashboard"] = {"error": str(exc)[:160]}

    env_ok = ENV_PATH.exists() and _sha256(ENV_PATH) == ENV_SHA256
    checks["env"] = env_ok
    detail["env"] = {"hash_matches": env_ok}

    health = h_service_health(robot_id)
    checks["endpoints"] = bool(health.get("ok"))
    detail["endpoints"] = health.get("summary")

    vault = _vault_checks()
    checks["graph"] = vault["ok"]
    detail["graph"] = vault
    detail["checks"] = checks
    _write_report("quality_guard_report.json", detail)

    ran = detail["python"].get("ran", 0)
    passed = detail["dashboard"].get("passed", 0)
    summary = (
        f"py={ran}/{ran if checks['python'] else 0} "
        f"dash={passed}/{passed if checks['dashboard'] else 0} "
        f"env={'ok' if checks['env'] else 'KO'} "
        f"endpoints={'ok' if checks['endpoints'] else 'KO'} "
        f"graph={'ok' if checks['graph'] else 'KO'}"
    )
    return {"ok": all(checks.values()), "summary": summary}


def h_vault_guard(robot_id: str) -> dict:
    """SYS_03 — JARVIS reste connecté aux cerveaux dans le vault Obsidian."""
    checks = _vault_checks()
    _write_report("vault_guard_report.json", {
        "checked_at": datetime.now().isoformat(), "checks": checks,
    })
    summary = (
        f"jarvis5000={int(checks['jarvis_port_5000'])} "
        f"link={int(checks['jarvis_links_brain'])} "
        f"nodes={checks.get('nodes', 0)} edges={checks.get('edges', 0)} "
        f"cdn_free={int(checks['graph_no_cdn'])}"
    )
    return {"ok": checks["ok"], "summary": summary}


def _has_real_source(directory: Path) -> bool:
    """Même règle que espria_system._source_files : les _modèles/README ne comptent pas."""
    if not directory.is_dir():
        return False
    return any(
        p.is_file() and not p.name.startswith(("_", "README", "."))
        for p in directory.iterdir()
    )


def h_backlog_scout(robot_id: str) -> dict:
    """SYS_04 — inventaire honnête des points ouverts, sans rien inventer."""
    try:
        text = PROJECT_MAP.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "summary": f"PROJECT_MAP introuvable: {str(exc)[:80]}"}

    items = _parse_backlog(text)
    sources = BASE_DIR / "data" / "sources"
    missing = [
        name for name in ("legal", "fiscal", "travail")
        if not _has_real_source(sources / name)
    ]
    _write_report("backlog_scout_report.json", {
        "checked_at": datetime.now().isoformat(),
        "items": items,
        "missing_sources": missing,
    })
    summary = (
        f"open={len(items)} ids={','.join(i['id'] for i in items) or 'none'} "
        f"no_data_source={','.join(missing) or 'none'}"
    )
    return {"ok": True, "summary": summary}


def h_agent_audit(robot_id: str) -> dict:
    """SYS_05 — miroir local du journal J* de PROJECT_MAP, jamais deLLM ni réseau."""
    checked_at = datetime.now().isoformat()
    try:
        text = PROJECT_MAP.read_text(encoding="utf-8")[-1_000_000:]
    except OSError:
        _write_report("agent_audit_report.json", {
            "checked_at": checked_at,
            "available": False,
            "reason": "no_data_source",
            "items": [],
        })
        return {"ok": False, "summary": "no_data_source=project_map"}

    items = _parse_milestones(text)
    latest = items[-1]["id"] if items else "none"
    _write_report("agent_audit_report.json", {
        "checked_at": checked_at,
        "available": True,
        "source": "PROJECT_MAP.md",
        "latest": latest,
        "items": items,
    })
    return {
        "ok": True,
        "summary": f"milestones={len(items)} latest={latest} source=project_map",
    }


# role → handler mapping
ROLE_HANDLERS: dict = {
    # Immune / monitoring
    "defense": h_hexstrike,        # IMM robots → HexStrike
    "cleanup": h_log_scan,
    "filter": h_log_scan,
    "monitoring": h_health_check,
    "perf": h_health_check,
    "service_health": h_service_health,
    # Gardiens locaux (SYS_02 → SYS_05)
    "quality_guard": h_quality_guard,
    "vault_guard": h_vault_guard,
    "backlog_scout": h_backlog_scout,
    "agent_audit": h_agent_audit,
    # Analysis / reports
    "logs": h_log_scan,
    "analysis": h_log_scan,
    "reports": h_stats,
    # Knowledge
    "knowledge": h_knowledge,
    # AI
    "hermes_bridge": h_ai_think,
    "prompt_craft": h_ai_think,
    "decision_making": h_ai_think,
    "quick_response": h_ai_think,
    "model_eval": h_ai_think,
    "knowledge_base": h_ai_think,
    # Embeddings
    "embeddings": h_embed,
    # Backup / storage
    "backup": h_git_status,
    "buffer": h_git_status,
    # External (real handlers now)
    "news": h_news_scan,
    "trading": h_market_scan,
    "stocks": h_market_scan,
    # Meta
    "schedule": h_stats,
    "optimize": h_stats,
}


# ═══════════════════════════════════════════════════════════════
#  Robot Engine
# ═══════════════════════════════════════════════════════════════

class RobotEngine:
    def __init__(self, interval: float = 30.0):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.cycles = 0
        init_engine_db()
        # J52/J53 : en production, chaque robot passe par la politique et le
        # journal terminal. Les tests avec DB temporaire gardent le comportement
        # historique (aucune régression, aucun fichier d'état parasite).
        if (str(DB) == str(PRODUCTION_DB)
                and os.environ.get("SUNNAVOK_JARVIS_AUTHORITY", "1") != "0"
                and (_RUN_STORE is None or not _RUN_STORE.path.exists())):
            try:
                configure_authority()
            except Exception:
                pass  # le journal reste optionnel : il ne doit jamais arrêter un robot

    # ─── DB helpers ───

    def _set_status(self, robot_id: str, status: str):
        conn = sqlite3.connect(DB)
        conn.execute(
            "UPDATE robots SET status=?, last_active=? WHERE id=?",
            (status, datetime.now().isoformat(), robot_id),
        )
        conn.commit()
        conn.close()

    def _record_result(self, robot_id: str, role: str, status: str, summary: str):
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT INTO robot_results (robot_id, role, status, summary) VALUES (?,?,?,?)",
            (robot_id, role, status, summary[:500]),
        )
        if status == "ok":
            conn.execute(
                "UPDATE robots SET tasks_completed = tasks_completed + 1 WHERE id=?",
                (robot_id,),
            )
        conn.commit()
        conn.close()

    # ─── Execution ───

    def run_robot(self, robot_id: str, keep_active: bool = False) -> dict:
        """ينفّذ robot واحد حسب الـ role.
        keep_active=True: يحافظ status='active' من بعد (للـ loop)."""
        info = _get_robot_info(robot_id)
        if not info:
            return {"robot_id": robot_id, "status": "error", "summary": "unknown robot"}

        role = info["role"]
        handler = ROLE_HANDLERS.get(role, h_noop)

        run_id = None
        if _RUN_STORE is not None:
            # Le rôle est l'identité du robot (28 handlers + rôles no-op), pas une
            # action à autoriser. Le gate porte sur la classe d'action générique.
            decision = _authority_decide("run_robot", _AUTH_MODE)
            if not decision.allowed:
                status = "error"
                summary = f"authority_denied:{decision.reason}"
                _RUN_STORE.record(
                    role, actor=robot_id, status="failed", detail=summary,
                    mode=getattr(_AUTH_MODE, "value", str(_AUTH_MODE)),
                    tainted=bool(decision.tainted),
                )
                self._record_result(robot_id, role, status, summary)
                self._set_status(robot_id, "active" if keep_active else "idle")
                return {"robot_id": robot_id, "name": info["name"], "role": role,
                        "status": status, "summary": summary}
            run_id = _RUN_STORE.record(
                role, actor=robot_id, status="running",
                mode=getattr(_AUTH_MODE, "value", str(_AUTH_MODE)),
                tainted=bool(decision.tainted),
            )

        self._set_status(robot_id, "active")
        try:
            result = handler(robot_id)
            status = "ok" if result.get("ok") else "error"
            summary = result.get("summary", "")
        except Exception as e:
            status = "error"
            summary = str(e)[:200]

        if run_id is not None:
            try:
                _RUN_STORE.update(run_id, "succeeded" if status == "ok" else "failed",
                                  detail=summary[:200])
                if _LEDGER_EXPORT:
                    _RUN_STORE.export_json(_LEDGER_EXPORT)
            except Exception:
                pass  # le journal ne doit jamais faire échouer un robot

        self._record_result(robot_id, role, status, summary)
        # loop: نرجعو active باش يدوز ف الدورة الجاية
        # manual: نرجعو idle
        self._set_status(robot_id, "active" if keep_active else "idle")
        return {"robot_id": robot_id, "name": info["name"], "role": role, "status": status, "summary": summary}

    def run_once(self, system: str = None) -> dict:
        """دورة واحدة — كل robots (أو نظام واحد)"""
        conn = sqlite3.connect(DB)
        if system:
            rows = conn.execute("SELECT id, role FROM robots WHERE system=?", (system,)).fetchall()
        else:
            rows = conn.execute("SELECT id, role FROM robots").fetchall()
        conn.close()

        results = []
        for robot_id, role in rows:
            results.append(self.run_robot(robot_id))

        self.cycles += 1
        ok = sum(1 for r in results if r["status"] == "ok")
        err = sum(1 for r in results if r["status"] == "error")
        logger.info(f"cycle #{self.cycles}: {len(results)} robots, {ok} ok, {err} error")
        return {"cycle": self.cycles, "total": len(results), "ok": ok, "error": err, "results": results}

    def run_active(self) -> dict:
        """غير robots المفعّلين (status='active') — يحافظ active للدورة الجاية"""
        if _RUN_STORE is not None:
            try:
                _RUN_STORE.reap_stale()  # aucune tâche ne reste 'running' indéfiniment
                _RUN_STORE.export_json(_LEDGER_EXPORT)
            except Exception:
                pass
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT id, role FROM robots WHERE status='active'").fetchall()
        conn.close()
        results = []
        for robot_id, role in rows:
            results.append(self.run_robot(robot_id, keep_active=True))
        if results:
            self.cycles += 1
            logger.info(f"cycle #{self.cycles}: {len(results)} active robots ran")
        return {"cycle": self.cycles, "ran": len(results), "results": results}

    # ─── Activation ───

    def activate(self, robot_id: str = None, system: str = None):
        conn = sqlite3.connect(DB)
        if robot_id:
            conn.execute("UPDATE robots SET status='active' WHERE id=?", (robot_id,))
        elif system:
            conn.execute("UPDATE robots SET status='active' WHERE system=?", (system,))
        conn.commit()
        conn.close()

    def deactivate(self, robot_id: str = None, system: str = None):
        conn = sqlite3.connect(DB)
        if robot_id:
            conn.execute("UPDATE robots SET status='idle' WHERE id=?", (robot_id,))
        elif system:
            conn.execute("UPDATE robots SET status='idle' WHERE system=?", (system,))
        conn.commit()
        conn.close()

    def activate_all(self):
        """Active tous les robots (demande explicite de l'opérateur)."""
        conn = sqlite3.connect(DB)
        conn.execute("UPDATE robots SET status='active'")
        conn.commit()
        conn.close()

    def deactivate_all(self):
        conn = sqlite3.connect(DB)
        conn.execute("UPDATE robots SET status='idle'")
        conn.commit()
        conn.close()

    # ─── Loop ───

    def _loop(self):
        logger.info(f"robot engine loop started (interval={self.interval}s)")
        while not self._stop.is_set():
            try:
                self.run_active()
            except Exception as e:
                logger.error(f"loop error: {e}")
            self._stop.wait(self.interval)
        logger.info("robot engine loop stopped")

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ─── Stats ───

    def get_stats(self) -> dict:
        conn = sqlite3.connect(DB)
        by_status = dict(conn.execute("SELECT status, COUNT(*) FROM robots GROUP BY status").fetchall())
        results = dict(conn.execute("SELECT status, COUNT(*) FROM robot_results GROUP BY status").fetchall())
        recent = conn.execute(
            "SELECT robot_id, role, status, summary, created_at FROM robot_results ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        return {
            "cycles": self.cycles,
            "robots_by_status": by_status,
            "results_by_status": results,
            "recent": [
                {"robot_id": r[0], "role": r[1], "status": r[2], "summary": r[3], "at": r[4]}
                for r in recent
            ],
        }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="run one cycle")
    p.add_argument("--system", default=None, help="filter by system")
    p.add_argument("--activate", default=None, help="activate system")
    p.add_argument("--deactivate-all", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--loop", action="store_true")
    args = p.parse_args()

    eng = RobotEngine()

    if args.activate:
        eng.activate(system=args.activate)
        print(f"activated system: {args.activate}")
    elif args.deactivate_all:
        eng.deactivate_all()
        print("all robots deactivated")
    elif args.stats:
        print(json.dumps(eng.get_stats(), ensure_ascii=False, indent=2))
    elif args.once:
        print(json.dumps(eng.run_once(system=args.system), ensure_ascii=False, indent=2))
    elif args.loop:
        try:
            eng.start()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            eng.stop()
    else:
        p.print_help()
