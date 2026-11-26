"""J114 — agent d'apprentissage local : il retient des actions réelles de l'utilisateur.

L'agent ne parle à aucun réseau, n'ouvre aucun secret et ne propose aucune
exécution : il transforme les journaux déjà présents en leçons publiques,
puis les range dans ``learning_memory.jsonl`` et ``learning_selfcheck.json``.
Toute décision d'autorité passe par ``policy_gate`` en mode ``full_local``
avec ``internet=False`` ; les actions effectives sont refusées ici.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

from policy_gate import AuthorityMode, decide
from run_store import redact

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = BASE_DIR / "state"
MAX_LESSONS = 200
PUBLIC_LESSONS = 10

LEARN_ACTIONS = frozenset({
    "learn", "inspect", "read", "list", "get", "status", "check",
    "analyze", "audit", "monitor", "test",
})

_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)"
    r"(\s*[=:]\s*)([\"']?)([^\s,;\"'}\]]{2,})([\"']?)"
)
_JSON_SECRET_KEY = re.compile(
    r"(?i)([\"'](?:api[_-]?key|token|password|secret|authorization|bearer)[\"'])"
    r"(\s*:\s*)([\"'])([^\"']*)([\"'])"
)


def _scrub(value: object) -> str:
    """Masque les secrets avant toute persistence ; ne garde pas l'original."""
    text = redact(str(value or ""))
    text = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    text = _JSON_SECRET_KEY.sub(lambda m: f"{m.group(1)}{m.group(2)}\"<redacted>\"", text)
    return text[:400]


def allowed(action: str = "learn", *, path: Optional[str] = None,
            host: Optional[str] = None, internet: bool = False) -> Dict[str, object]:
    """Décision publique : aucun journal n'est touché ici."""
    name = str(action or "").strip().lower()
    if name not in LEARN_ACTIONS:
        return {
            "action": name, "allowed": False,
            "mode": AuthorityMode.FULL_LOCAL.value,
            "reason": "not_allowed_for_learning", "tainted": False,
            "requires_confirmation": False,
        }
    decision = decide(
        name, path=path, host=host, mode=AuthorityMode.FULL_LOCAL,
        internet=False, source="learning_agent",
    )
    payload = decision.to_dict()
    payload["internet"] = False  # périmètre J114 : aucun appel réseau, quel que soit l'appelant
    return payload


def _read_json(path: Path) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        return json.loads(raw) if raw.strip() else None
    except (ValueError, TypeError):
        return None


def _read_jsonl(path: Path, limit: int = 500) -> Iterable[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    rows = []
    for line in raw.splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _lesson(kind: str, source: str, detail: object) -> Dict[str, object]:
    return {
        "kind": str(kind),
        "source": str(source),
        "detail": _scrub(detail),
        "learnedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _ledger_lessons(state: Path) -> List[dict]:
    data = _read_json(state / "run_ledger.json")
    if not isinstance(data, dict):
        return []
    lessons = []
    for run in (data.get("runs") or [])[:50]:
        if not isinstance(run, dict):
            continue
        action = _scrub(run.get("action"))
        status = _scrub(run.get("status"))
        if status == "succeeded":
            lessons.append(_lesson("reinforce", "run_ledger.json",
                                   f"action={action} a réussi ; garder cette approche"))
        elif status in {"failed", "timed_out"}:
            detail = _scrub(run.get("detail"))
            suffix = f" ; détail={detail}" if detail else ""
            lessons.append(_lesson("avoid", "run_ledger.json",
                                   f"action={action} a échoué ({status}) ; "
                                   f"revérifier avant de répéter{suffix}"))
    stats = data.get("stats") or {}
    if isinstance(stats, dict) and stats:
        lessons.append(_lesson("trend", "run_ledger.json",
                               f"total={stats.get('total')} succeeded={stats.get('succeeded')} "
                               f"failed={stats.get('failed')}"))
    return lessons


def _approval_lessons(state: Path) -> List[dict]:
    lessons = []
    for row in _read_jsonl(state / "action_audit.jsonl"):
        transition = row.get("transition") or f"{row.get('from', '')}->{row.get('to', '')}"
        if "approved" in str(transition) or "executed" in str(transition):
            lessons.append(_lesson("consent", "action_audit.jsonl",
                                   f"id={row.get('id', '')} transition={transition} ; "
                                   "demander une nouvelle validation avant chaque action"))
        elif "denied" in str(transition):
            lessons.append(_lesson("avoid", "action_audit.jsonl",
                                   f"id={row.get('id', '')} refusé par l'utilisateur ; "
                                   "ne pas représenter telle quelle"))
    return lessons


def _voice_lessons(state: Path) -> List[dict]:
    lessons = []
    for row in _read_jsonl(state / "voice_inbox.jsonl"):
        if row.get("reason") == "barge_in":
            lessons.append(_lesson("interrupt", "voice_inbox.jsonl",
                                   "l'utilisateur a coupé la parole ; répondre plus court"))
        elif row.get("ok") is True and row.get("spoken") is True:
            lessons.append(_lesson("reinforce", "voice_inbox.jsonl",
                                   f"voix locale comprise ({_scrub(row.get('language'))})"))
    return lessons


def _error_lessons(state: Path) -> List[dict]:
    lessons = []
    for row in _read_jsonl(state / "brain_errors.jsonl"):
        lessons.append(_lesson("error", "brain_errors.jsonl",
                               f"source={_scrub(row.get('source'))} "
                               f"erreur={_scrub(row.get('error') or row.get('message'))}"))
    return lessons


def _request_lessons(state: Path) -> List[dict]:
    data = _read_json(state / "action_requests.json")
    if not isinstance(data, list):
        return []
    lessons = []
    for row in data[:50]:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "")
        if status in {"executed", "approved_once"}:
            lessons.append(_lesson("consent", "action_requests.json",
                                   f"action={_scrub(row.get('action'))} status={status}"))
        elif status == "denied":
            lessons.append(_lesson("avoid", "action_requests.json",
                                   f"action={_scrub(row.get('action'))} refusée"))
    return lessons


def _source_lessons(state: Path) -> List[dict]:
    lessons = []
    for row in _read_jsonl(state / "sources_intake.jsonl"):
        lessons.append(_lesson("source", "sources_intake.jsonl",
                               f"catégorie={_scrub(row.get('category'))} "
                               f"fichier={_scrub(row.get('sourceName'))}"))
    wake = _read_json(state / "wake_selfcheck.json")
    if isinstance(wake, dict) and wake.get("ok") is True:
        lessons.append(_lesson("wake", "wake_selfcheck.json",
                               f"détecteur local prêt ({_scrub(wake.get('model'))})"))
    return lessons


def _count(value: object) -> int:
    """Convertit un comptage en entier sans jamais lever d'exception."""
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _scout_lessons(state: Path) -> List[dict]:
    """Retient les sujets et langages vus dans la veille GitHub (lecture seule)."""
    report = _read_json(state / "github_scout_report.json")
    if not isinstance(report, dict) or report.get("ok") is not True:
        return []
    lessons = []
    scanned = _scrub(report.get("scanned"))
    if scanned and scanned != "0":
        lessons.append(_lesson("scout", "github_scout_report.json",
                               f"projets examinés={scanned} en lecture seule"))
    for key in ("topics", "languages"):
        values = report.get(key)
        label = key[:-1]
        if isinstance(values, dict):
            # Le rapport réel stocke des comptages ; on retient le top 3.
            ranked = sorted(
                ((_scrub(name), _scrub(count)) for name, count in values.items()),
                key=lambda pair: (-_count(pair[1]), pair[0]),
            )[:3]
            for name, count in ranked:
                if name and count and count != "0":
                    lessons.append(_lesson("scout", "github_scout_report.json",
                                           f"{label}={name}:{count}"))
        elif isinstance(values, list):
            for value in values[:3]:
                text = _scrub(value)
                if text:
                    lessons.append(_lesson("scout", "github_scout_report.json",
                                           f"{label}={text}"))
    return lessons


def _week_lessons(state: Path) -> List[dict]:
    """Retient la fenêtre de 7 jours de la veille GitHub, sans aucun appel réseau."""
    report = _read_json(state / "github_week_report.json")
    if not isinstance(report, dict) or report.get("errors"):
        return []
    items = report.get("items")
    if not isinstance(items, list):
        return []
    since = _scrub(report.get("since"))
    if not since and not _scrub(report.get("digest")):
        return []
    lessons = []
    if since:
        lessons.append(_lesson("week", "github_week_report.json",
                               f"fenêtre depuis={since} dépôts={len(items)}"))
    for key, label in (("latestCreated", "plus récent"), ("latestPushed", "dernier push")):
        entry = report.get(key)
        if not isinstance(entry, dict):
            continue
        name = _scrub(entry.get("name"))
        primary = "pushedAt" if key == "latestPushed" else "createdAt"
        secondary = "createdAt" if key == "latestPushed" else "pushedAt"
        moment = _scrub(entry.get(primary) or entry.get(secondary))
        if name:
            lessons.append(_lesson("week", "github_week_report.json",
                                   f"{label}={name} à={moment}"))
    ranked = sorted(
        (item for item in items if isinstance(item, dict)),
        key=lambda item: str(item.get("createdAt") or ""),
        reverse=True,
    )[:3]
    for item in ranked:
        name = _scrub(item.get("name"))
        created = _scrub(item.get("createdAt"))
        if name:
            lessons.append(_lesson("week", "github_week_report.json",
                                   f"dépôt={name} créé={created}"))
    return lessons


def _vault_lesson(vault_dir: Union[str, Path]) -> tuple[Optional[str], List[dict]]:
    try:
        from vault_memory import VaultMemory
        hits = VaultMemory(Path(vault_dir)).query(
            "préférences utilisateur réponses courtes darija", limit=3)
    except Exception:
        return None, []
    if not hits:
        return None, []
    top = str(hits[0].get("path") or "")
    return top, [_lesson("preference", "vault_memory", f"note={top} pertinence={hits[0].get('score')}")]


def _store_lessons(path: Path, lessons: List[dict]) -> List[dict]:
    previous = []
    seen = set()
    for row in _read_jsonl(path, limit=MAX_LESSONS):
        key = (row.get("kind"), row.get("source"), row.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        previous.append(row)
    for row in lessons:
        key = (row.get("kind"), row.get("source"), row.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        previous.append(row)
    kept = previous[-MAX_LESSONS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept),
                   encoding="utf-8")
    os.replace(tmp, path)
    return kept


def learn(state_dir: Union[str, Path] = DEFAULT_STATE_DIR, *,
          vault_dir: Optional[Union[str, Path]] = None) -> Dict[str, object]:
    """Observe les journaux locaux, en tire des leçons et écrit une preuve publique."""
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    decision = allowed("learn", path=str(state / "learning_selfcheck.json"))
    if not decision["allowed"]:
        return {
            "ok": False, "status": "not_available", "engine": "local_only",
            "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "learnedCount": 0, "sources": [], "lessons": [], "policy": decision,
        }

    lessons: List[dict] = []
    sources: List[str] = []
    for path, builder in (
        ("run_ledger.json", _ledger_lessons),
        ("action_audit.jsonl", _approval_lessons),
        ("voice_inbox.jsonl", _voice_lessons),
        ("brain_errors.jsonl", _error_lessons),
        ("action_requests.json", _request_lessons),
        ("sources_intake.jsonl", _source_lessons),
        ("github_scout_report.json", _scout_lessons),
        ("github_week_report.json", _week_lessons),
    ):
        if (state / path).exists():
            found = builder(state)
            if found:
                sources.append(path)
                lessons.extend(found)

    top_note = None
    if vault_dir:
        top_note, vault_lessons = _vault_lesson(vault_dir)
        if vault_lessons:
            sources.append("vault_memory")
            lessons.extend(vault_lessons)

    stored = _store_lessons(state / "learning_memory.jsonl", lessons)
    unique = []
    seen = set()
    for row in stored:
        key = (row.get("kind"), row.get("source"), row.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    ok = bool(unique)
    report = {
        "ok": ok,
        "status": "live_verified" if ok else "no_data_source",
        "engine": "local_only",
        "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "learnedCount": len(unique),
        "sources": sources,
        "lessons": unique[-PUBLIC_LESSONS:],
        "topNote": top_note,
        "policy": decision,
        "next": "Relancer après de nouvelles actions locales ; aucune exécution automatique.",
    }
    report_path = state / "learning_selfcheck.json"
    tmp = report_path.with_name(f"{report_path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, report_path)
    return report


def main() -> None:
    report = learn()
    print(json.dumps({key: report[key] for key in
                      ("status", "engine", "learnedCount", "sources", "topNote")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()


__all__ = ["MAX_LESSONS", "DEFAULT_STATE_DIR", "allowed", "learn"]
