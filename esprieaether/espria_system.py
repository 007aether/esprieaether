"""EspriaAether system gateway — O4 auth, O8 KPI, O20 LLM router, O11 GitHub readiness.

Run: .venv\\Scripts\\python.exe -m uvicorn espria_system:app --host 127.0.0.1 --port 5001
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

STATE_DIR = Path(os.getenv("ESPRIA_STATE_DIR", BASE_DIR / "state")).resolve()
STATE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STATE_DIR / "auth.db"

# Sources documentaires locales pour les rôles sans source vérifiée.
# Un fichier déposé ici devient une source réelle ; sinon l'agent répond
# explicitement `no_data_source` au lieu d'inventer une réponse.
SOURCES_ROOT = Path(os.getenv("AGENT_SOURCES_DIR", BASE_DIR / "data" / "sources")).resolve()
AGENT_SOURCE_DIRS = {
    "A4": SOURCES_ROOT / "legal",
    "L1": SOURCES_ROOT / "fiscal",
    "L2": SOURCES_ROOT / "travail",
}


def _source_files(agent_id: str) -> list[Path]:
    directory = AGENT_SOURCE_DIRS.get(agent_id)
    if not directory or not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and not p.name.startswith(("_", "README", "."))
    )

FREELLMAPI_BASE = os.getenv("FREE_LLM_BASE_URL", "http://127.0.0.1:31415").rstrip("/")
FREELLMAPI_MODEL = os.getenv("FREELLMAPI_MODEL", "gemini-flash-lite")
REQUEST_TIMEOUT = float(os.getenv("FREELLMAPI_TIMEOUT", "90"))

# Routeur des modèles GGUF locaux (llama.cpp) : aucune clé, loopback uniquement.
LOCAL_BRAIN_BASE = os.getenv("LOCAL_BRAIN_API_BASE", "http://127.0.0.1:31416/v1").rstrip("/")
LOCAL_BRAIN_MODEL = os.getenv("LOCAL_BRAIN_MODEL", "dolphin3")
LOCAL_BRAIN_PREFER = os.getenv("LOCAL_BRAIN_PREFER", "1") == "1"


def _load_llm_key() -> str:
    """Clé locale : variable d'environnement OU state/freellmapi.key (jamais .env)."""
    configured = os.getenv("FREELLMAPI_KEY")
    if configured:
        return configured
    key_file = STATE_DIR / "freellmapi.key"
    return key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else ""


FREELLMAPI_KEY = _load_llm_key()


def _record_share(consumer: str, model: str | None, ok: bool) -> None:
    """Trace locale de la part de requêtes FreeLLMAPI, sans secret ni contenu."""
    try:
        from src import freellm_share
        freellm_share.record(consumer, model, ok)
    except Exception:
        pass


def _load_secret() -> str:
    configured = os.getenv("WEB_SECRET_KEY")
    if configured:
        return configured
    key_file = STATE_DIR / "secret.key"
    if key_file.is_file():
        return key_file.read_text(encoding="utf-8").strip()
    value = secrets.token_urlsafe(48)
    key_file.write_text(value, encoding="utf-8")
    return value


SECRET_KEY = _load_secret()


# ── Database ──────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    conn = get_db()
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE NOT NULL,
                   email TEXT UNIQUE,
                   password_hash TEXT NOT NULL,
                   role TEXT NOT NULL DEFAULT 'user',
                   created_at TEXT NOT NULL,
                   is_active INTEGER NOT NULL DEFAULT 1
               )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS kpis (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   metric TEXT NOT NULL,
                   value REAL NOT NULL,
                   updated_at TEXT NOT NULL,
                   window TEXT
               )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS modules (
                   id TEXT PRIMARY KEY,
                   name TEXT NOT NULL,
                   status TEXT NOT NULL,
                   version TEXT,
                   installed_at TEXT
               )"""
        )
        modules = [
            ("o4-auth", "Authentication", "active", "1.0"),
            ("o8-kpi", "KPI store", "active", "1.0"),
            ("o20-llm-router", "LLM router (FreeLLMAPI API)", "active" if FREELLMAPI_KEY else "needs_key", "2.0"),
            ("o11-github", "GitHub push readiness", "needs_private_key", "1.0"),
        ]
        for module_id, name, status, version in modules:
            cur.execute(
                "INSERT OR IGNORE INTO modules (id, name, status, version, installed_at) VALUES (?, ?, ?, ?, ?)",
                (module_id, name, status, version, datetime.now().isoformat()),
            )


# ── Auth helpers (O4) ─────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    salt = secrets.token_bytes(32)
    derived = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100_000)
    return "pbkdf2_sha256$100000$" + base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(derived).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        algorithm, iterations, salt_b64, derived_b64 = hashed.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), base64.b64decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(derived, base64.b64decode(derived_b64))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + 120 * 60,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def llm_provider_name() -> str:
    """Vrai chemin de routage : local d'abord, FreeLLMAPI ensuite."""
    if llm._local_available():
        return "local-brain"
    return "freellmapi-api" if llm.api_key else "needs_key"


def get_current_user(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], SECRET_KEY, algorithms=["HS256"])
        return {
            "id": int(payload["sub"]),
            "username": payload["username"],
            "role": payload["role"],
        }
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


# ── O4 : politique d'accès à la production (désactivée par défaut) ─────────────
PRODUCTION_ACCESS_ENABLED = os.getenv("ESPRIA_PRODUCTION_ACCESS", "0") == "1"
PRODUCTION_ROLE = os.getenv("ESPRIA_PRODUCTION_ROLE", "admin")


# ── O8 : catalogue KPI métier (dérivé du contrat DashboardState réel) ──────────
BUSINESS_KPIS = [
    {"metric": "g_rate", "label": "Taux de galvanisation", "source": "dashboard.fields.g-rate", "unit": "%"},
    {"metric": "g_cons", "label": "Consommation", "source": "dashboard.fields.g-cons", "unit": ""},
    {"metric": "g_over", "label": "Dépassement", "source": "dashboard.fields.g-over", "unit": ""},
    {"metric": "g_margin", "label": "Marge", "source": "dashboard.fields.g-margin", "unit": ""},
    {"metric": "products_count", "label": "Nombre de produits", "source": "dashboard.products", "unit": "count"},
    {"metric": "todo_open", "label": "Tâches ouvertes", "source": "dashboard.todo", "unit": "count"},
    {"metric": "tasks_done", "label": "Tâches terminées (observé)", "source": "kpi_store", "unit": "count"},
    {"metric": "cpu", "label": "CPU (observé)", "source": "kpi_store", "unit": "%"},
]


# ── LLM router (O20) ──────────────────────────────────────────────────────────
class LLMProviderError(Exception):
    pass


class EspriaLLM:
    """Client OpenAI-compatible : cerveaux GGUF locaux d'abord, FreeLLMAPI ensuite."""

    def __init__(self, api_key: str = FREELLMAPI_KEY, base_url: str = FREELLMAPI_BASE,
                 model: str = FREELLMAPI_MODEL, local_base_url: str = LOCAL_BRAIN_BASE,
                 local_model: str = LOCAL_BRAIN_MODEL, local_enabled: bool = LOCAL_BRAIN_PREFER):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = REQUEST_TIMEOUT
        self.local_base_url = local_base_url
        self.local_model = local_model
        self.local_enabled = local_enabled

    def _local_available(self) -> bool:
        if not self.local_enabled:
            return False
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.local_base_url}/models")
                return response.status_code == 200 and bool(response.json().get("data"))
        except Exception:
            return False

    def _post_local(self, payload: dict):
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(
                f"{self.local_base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
            )

    def _post(self, payload: dict):
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )

    def complete(self, prompt: str, model: str | None = None, system: str | None = None, max_tokens: int = 512) -> dict:
        result = {
            "text": "",
            "model": model or self.model,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "status": "success",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # 1. Cerveau local : prioritaire, sans clé, sans quitter la machine.
        if self._local_available():
            try:
                response = self._post_local(
                    {
                        "model": model or self.local_model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                    }
                )
                response.raise_for_status()
                data = response.json()
                result["text"] = data["choices"][0]["message"]["content"]
                result["model"] = data.get("model", result["model"])
                result["usage"] = data.get("usage", result["usage"])
                result["routed_via"] = "local-brain"
                return result
            except Exception as exc:
                result["local_error"] = type(exc).__name__

        # 2. Passerelle FreeLLMAPI (clé locale, jamais écrite dans .env).
        if not self.api_key:
            result.update(status="no_api_key", text="Clé FreeLLMAPI absente (variable FREELLMAPI_KEY).")
            return result
        freellm_payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        try:
            response = self._post(freellm_payload)
            response.raise_for_status()
            data = response.json()
            result["text"] = data["choices"][0]["message"]["content"]
            result["model"] = data.get("model", result["model"])
            result["usage"] = data.get("usage", result["usage"])
            result["routed_via"] = data.get("_routed_via")
            _record_share("atulya", freellm_payload["model"], True)
        except Exception as exc:
            _record_share("atulya", freellm_payload["model"], False)
            result.update(status="error", text=f"[LLM error: {type(exc).__name__}]")
        return result


llm = EspriaLLM()


# ── Request models ────────────────────────────────────────────────────────────
class SignupReq(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginReq(BaseModel):
    username: str
    password: str


class KpiRecord(BaseModel):
    metric: str
    value: float
    window: str = "realtime"


class ChatReq(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=128)
    system: str | None = Field(default=None, max_length=4000)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 7200
    user: dict


app = FastAPI(title="EspriaAether", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.post("/signup")
async def signup(req: SignupReq) -> TokenOut:
    try:
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (req.username, req.email, hash_password(req.password), "user", datetime.now().isoformat()),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur ou email déjà utilisé") from exc
    return TokenOut(
        access_token=create_token(user_id, req.username, "user"),
        user={
            "id": user_id,
            "username": req.username,
            "email": req.email,
            "role": "user",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
        },
    )


@app.post("/login")
async def login(req: LoginReq) -> TokenOut:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (req.username,))
        user = cur.fetchone()
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["id"], user["username"], user["role"])
    return TokenOut(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "is_active": True,
            "created_at": user["created_at"],
        },
    )


@app.get("/me")
async def me(authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(authorization)
    return {"id": user["id"], "username": user["username"], "email": None, "role": user["role"], "is_active": True, "created_at": ""}


@app.post("/token")
async def token_endpoint(username: str, password: str) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
        user = cur.fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_token(user["id"], user["username"], user["role"]),
        "token_type": "bearer",
        "expires_in": 7200,
        "user": {"id": user["id"], "username": user["username"], "role": user["role"]},
    }


# ── KPI routes (O8) ───────────────────────────────────────────────────────────
def _record_kpi(metric: str, value: float, window: str) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO kpis (metric, value, updated_at, window) VALUES (?, ?, ?, ?)",
            (metric, value, datetime.now().isoformat(), window),
        )
    return {"status": "recorded", "metric": metric, "value": value}


@app.post("/kpi")
async def record_kpi(payload: KpiRecord) -> dict:
    return _record_kpi(payload.metric, payload.value, payload.window)


@app.post("/kpi/{metric}")
async def record_kpi_path(metric: str, value: float, window: str = "realtime") -> dict:
    return _record_kpi(metric, value, window)


@app.get("/kpi/all")
async def get_all_kpis() -> list[dict]:
    return _all_kpis()


@app.get("/kpi/catalogue")
async def kpi_catalogue() -> dict:
    return {"catalogue": BUSINESS_KPIS, "count": len(BUSINESS_KPIS)}


@app.get("/kpi/from-dashboard")
async def kpi_from_dashboard() -> dict:
    """Valeurs réellement présentes dans le DashboardState — aucune estimation."""
    try:
        state = _dashboard_state()
    except Exception as exc:
        return {"status": "source_error", "source": DASHBOARD_STATE_URL, "message": str(exc)[:160], "values": {}}
    fields = state.get("fields", {})
    values = {
        key: fields.get(field)
        for key, field in (
            ("g_rate", "g-rate"), ("g_cons", "g-cons"),
            ("g_over", "g-over"), ("g_margin", "g-margin"),
        )
    }
    values["products_count"] = len(state.get("products", []))
    values["todo_open"] = sum(1 for done in state.get("todo", {}).values() if not done)
    return {"status": "ok", "source": DASHBOARD_STATE_URL, "values": values}


@app.get("/kpi/{metric}")
async def get_kpi(metric: str) -> dict:
    with db_cursor() as cur:
        cur.execute(
            "SELECT SUM(value) AS total, AVG(value) AS avg, COUNT(*) AS count FROM kpis WHERE metric = ?",
            (metric,),
        )
        row = cur.fetchone()
    if not row or row["total"] is None:
        return {"metric": metric, "total": 0, "avg": 0, "count": 0}
    return {"metric": metric, "total": round(row["total"], 4), "avg": round(row["avg"], 4), "count": row["count"]}


@app.get("/access/policy")
async def access_policy() -> dict:
    return {
        "signup_forced_role": "user",
        "role_escalation": "impossible",
        "production_enabled": PRODUCTION_ACCESS_ENABLED,
        "production_role_required": PRODUCTION_ROLE,
        "message": "Accès production fermé tant que ESPRIA_PRODUCTION_ACCESS=1 n'est pas explicitement positionné.",
    }


@app.get("/production/status")
async def production_status(authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(authorization)
    if not PRODUCTION_ACCESS_ENABLED or user["role"] != PRODUCTION_ROLE:
        raise HTTPException(status_code=403, detail="Accès production non autorisé")
    return {"status": "ok", "role": user["role"], "production": True}


# ── LLM routes (O20) ──────────────────────────────────────────────────────────
@app.post("/chat/completions")
async def chat_completions(req: ChatReq) -> dict:
    return llm.complete(req.prompt, model=req.model, system=req.system, max_tokens=req.max_tokens)


@app.get("/llm/status")
async def llm_status() -> dict:
    local_ok = llm._local_available()
    return {
        "provider": "local-brain" if local_ok else "freellmapi-api",
        "base_url": llm.base_url,
        "model": llm.model,
        "api_key_configured": bool(llm.api_key),
        "status": "ready" if (local_ok or llm.api_key) else "needs_key",
        "local_brain": {
            "preferred": llm.local_enabled,
            "available": local_ok,
            "base_url": llm.local_base_url,
            "model": llm.local_model,
        },
    }


# ── GitHub readiness (O11 — no push without key and target) ───────────────────
@app.get("/github/push-status")
async def github_push_status() -> dict:
    return {
        "push_performed": False,
        "private_key_available": False,
        "target_repo_configured": bool(os.getenv("GITHUB_REPO")),
        "message": "Aucun push effectué : clé privée et dépôt cible explicites requis.",
    }


# ── Agents (rôles déclarés dans les notes Obsidian) ───────────────────────────
DASHBOARD_STATE_URL = os.getenv("DASHBOARD_STATE_URL", "http://127.0.0.1:5100/api/dashboard/state")

AGENTS = {
    "A1": "Galvanisation",
    "A2": "Prix",
    "A3": "Plans",
    "A4": "Legal",
    "M1": "M1_Marche_Metallerie",
    "L1": "Fiscalité",
    "L2": "Travail",
    "director": "EsprieAether — Directeur exécutif",
}

# Rôle + travail concret de chaque agent. Les agents documentaires ne produisent
# aucune affirmation juridique/fiscale/sociale sans fichier vérifié déposé.
AGENT_DUTIES = {
    "A1": ("Suivre la galvanisation réelle du dashboard et signaler les écarts.", "system"),
    "A2": ("Contrôler les prix et la marge à partir des champs du dashboard.", "system"),
    "A3": ("Suivre les plans et tâches ouvertes du dashboard.", "system"),
    "A4": ("Examiner les contrats et documents juridiques déposés localement.", "documents"),
    "M1": ("Suivre la marche métallerie : produits et inventaire réels.", "system"),
    "L1": ("Vérifier les pièces fiscales déposées localement, sans inventer de barème.", "documents"),
    "L2": ("Vérifier les documents de travail déposés localement, sans inventer de règle.", "documents"),
    "director": ("Consolider l'état réel des agents, services et KPI du système.", "system"),
}


def _dashboard_state() -> dict:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(DASHBOARD_STATE_URL)
        response.raise_for_status()
        return response.json()["state"]


def _all_kpis() -> list[dict]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT metric, SUM(value) AS total, AVG(value) AS avg, COUNT(*) AS count "
            "FROM kpis GROUP BY metric ORDER BY MAX(updated_at) DESC LIMIT 20"
        )
        rows = cur.fetchall()
    return [
        {
            "metric": row["metric"],
            "total": round(row["total"], 4) if row["total"] else 0,
            "avg": round(row["avg"], 4) if row["avg"] else 0,
            "count": row["count"],
        }
        for row in rows
    ]


@app.get("/agents")
async def list_agents() -> list[dict]:
    return [
        {"id": agent_id, "role": role, "mission": AGENT_DUTIES[agent_id][0]}
        for agent_id, role in AGENTS.items()
    ]


@app.get("/agents/{agent_id}/run")
async def run_agent(agent_id: str) -> dict:
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail="Agent inconnu")
    if agent_id in AGENT_SOURCE_DIRS:
        directory = AGENT_SOURCE_DIRS[agent_id]
        files = _source_files(agent_id)
        if not files:
            return {
                "agent": agent_id,
                "role": AGENTS[agent_id],
                "duty": AGENT_DUTIES[agent_id][0],
                "status": "no_data_source",
                "source": str(directory),
                "summary": {},
                "work": {
                    "checked_dir": str(directory),
                    "files_found": 0,
                    "next_action": f"Déposer un fichier vérifié dans {directory}.",
                },
                "message": f"Aucun document source vérifié. Déposer un fichier dans {directory}.",
            }
        excerpts = []
        for path in files[:5]:
            excerpts.append({
                "file": path.name,
                "text": path.read_text(encoding="utf-8", errors="ignore")[:600],
            })
        return {
            "agent": agent_id,
            "role": AGENTS[agent_id],
            "duty": AGENT_DUTIES[agent_id][0],
            "status": "ok",
            "source": str(directory),
            "summary": {"documents": len(files), "excerpts": excerpts},
            "work": {"checked_dir": str(directory), "files_found": len(files)},
            "message": "Source documentaire locale lue telle quelle ; aucune interprétation automatique.",
        }
    try:
        state = _dashboard_state()
    except Exception as exc:
        return {
            "agent": agent_id,
            "role": AGENTS[agent_id],
            "duty": AGENT_DUTIES[agent_id][0],
            "status": "source_error",
            "source": DASHBOARD_STATE_URL,
            "summary": {},
            "work": {"scope": "system", "source": DASHBOARD_STATE_URL},
            "message": f"Source indisponible ({type(exc).__name__}).",
        }

    fields = state.get("fields", {})
    products = state.get("products", [])
    inventory = state.get("inventory", [])
    todo = state.get("todo", [])
    # DashboardState.todo est un objet (contract.mjs) ; accepter aussi la vieille liste.
    if isinstance(todo, dict):
        todo_items = [{"id": key, "done": value} for key, value in todo.items()]
    elif isinstance(todo, list):
        todo_items = todo
    else:
        todo_items = []
    if agent_id == "A2":
        summary = {"g_rate": fields.get("g-rate"), "g_cons": fields.get("g-cons"), "g_margin": fields.get("g-margin")}
    elif agent_id == "A3":
        summary = {"todo_count": len(todo_items), "items": todo_items[:10]}
    elif agent_id == "A1":
        summary = {"f_a": fields.get("f-a"), "fields_count": len(fields)}
    elif agent_id == "M1":
        summary = {"products_count": len(products), "inventory_count": len(inventory)}
    else:
        summary = {
            "agents_total": len(AGENTS),
            "fields_count": len(fields),
            "products_count": len(products),
            "inventory_count": len(inventory),
            "todo_count": len(todo_items),
            "kpis": _all_kpis(),
            "llm_provider": llm_provider_name(),
        }
    return {
        "agent": agent_id,
        "role": AGENTS[agent_id],
        "duty": AGENT_DUTIES[agent_id][0],
        "status": "ok",
        "source": DASHBOARD_STATE_URL,
        "summary": summary,
        "work": {"scope": "system", "source": DASHBOARD_STATE_URL},
    }


@app.get("/")
async def root() -> dict:
    return {
        "name": "EspriaAether",
        "version": "1.0.0",
        "status": "running",
        "modules": {
            "o20_llm_router": f"active ({llm_provider_name()})" if (llm._local_available() or llm.api_key) else "needs_key",
            "o4_auth": "active (JWT)",
            "o8_kpi": "active (SQLite)",
            "o11_github": "ready (private key required)",
        },
        "docs": "/docs",
    }
