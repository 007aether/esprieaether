#!/usr/bin/env python3
"""J94 — exploration GitHub en lecture seule, derrière ``policy_gate``.

Une seule sortie réseau est possible : l'API publique ``api.github.com``.
Aucun jeton, fichier d'environnement ou secret n'est lu ni écrit. Les tests
injectent un ``fetcher`` : aucun réseau n'est alors utilisé.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import policy_gate

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = BASE_DIR / "state"
REPORT_NAME = "github_scout_report.json"

API_HOST = "api.github.com"
API_BASE = "https://" + API_HOST
SEARCH_PATH = "/search/repositories"
DEFAULT_QUERIES = (
    "ai agent framework",
    "local llm",
    "self improving agent",
    "voice assistant local",
)
PER_PAGE = 100
MAX_PAGES = 10
TARGET = 1000
SAMPLE_SIZE = 20
DESC_LIMIT = 200
TIMEOUT = 10
RATE_DELAY = 7
RETRY_DELAY = 31
MAX_ATTEMPTS = 3

_SECRET = re.compile(
    r"(?i)\b(?:api[_-]?key|token|password|secret)\b\s*[:=]\s*[\"']?[^\s\"',;]+[\"']?"
)
_URL = re.compile(r"https?://[^\s<>\"']+")
_SPACES = re.compile(r"\s+")


def _scrub(value: object) -> str:
    """Nettoie une valeur avant tout stockage : ni secret, ni URL à requête."""
    text = str(value if value is not None else "")

    def _trim_url(match: re.Match) -> str:
        return match.group(0).split("?", 1)[0].split("#", 1)[0]

    text = _URL.sub(_trim_url, text)
    text = _SECRET.sub("[redacted]", text)
    return _SPACES.sub(" ", text).strip()


def _clean(value: object, limit: int) -> str:
    return _scrub(value)[:limit]


def _bump(counter: dict, key: object) -> None:
    name = _clean(key, 80)
    if name:
        counter[name] = counter.get(name, 0) + 1


def _top_counts(counter: dict, limit: int = 10) -> dict:
    ordered = sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
    return dict(ordered[:limit])


def allowed(url: str) -> dict:
    """Décision publique du gate, resserrée sur l'hôte exact de l'API GitHub."""
    decision = policy_gate.check_url(url, action="research", internet=True)
    result = decision.to_dict()
    try:
        parsed = urllib.parse.urlparse(str(url or ""))
        host = (parsed.hostname or "").lower()
    except ValueError:
        parsed = None
        host = ""

    strict_host = bool(
        parsed is not None
        and parsed.scheme == "https"
        and host == API_HOST
        and parsed.port is None
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
    )
    if decision.allowed and not strict_host:
        result["allowed"] = False
        result["reason"] = "host_not_allowed"
    return result


def _default_fetcher(query, page, per_page=PER_PAGE, *, opener=None, sleeper=None) -> dict:
    """Fetcher réel : contrôle de sortie, espacement et reprises sur 403/429."""
    params = urllib.parse.urlencode(
        {"q": query, "per_page": per_page, "page": page}
    )
    url = API_BASE + SEARCH_PATH + "?" + params
    decision = allowed(url)
    if not decision.get("allowed"):
        raise ValueError("github_api_not_allowed")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "esprieaether-github-scout/1.0",
        },
    )
    open_url = opener or urllib.request.urlopen
    sleep = sleeper or time.sleep
    payload = None
    retried = False
    for attempt in range(MAX_ATTEMPTS):
        try:
            with open_url(request, timeout=TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429) or attempt == MAX_ATTEMPTS - 1:
                raise
            retried = True
            sleep(RETRY_DELAY)
    if not retried:
        sleep(RATE_DELAY)
    if not isinstance(payload, dict):
        return {"items": []}
    return payload


def harvest(fetcher, limit=TARGET, queries=None) -> dict:
    """Collecte jusqu'à ``limit`` dépôts uniques, sans jamais dépasser 10 pages.

    ``fetcher(query, page, per_page)`` renvoie un dict de style GitHub avec
    ``items``. Aucun résultat n'est accepté sans ce contrat explicite.
    """
    fetcher = fetcher if fetcher is not None else _default_fetcher
    selected = [_clean(query, 120) for query in (queries or DEFAULT_QUERIES)]
    selected = [query for query in selected if query]
    try:
        cap = int(limit)
    except (TypeError, ValueError):
        cap = TARGET
    cap = max(0, min(cap, TARGET))

    seen = set()
    collected = []
    topics = {}
    languages = {}

    for query in selected:
        if len(seen) >= cap:
            break
        for page in range(1, MAX_PAGES + 1):
            if len(seen) >= cap:
                break
            try:
                payload = fetcher(query, page, PER_PAGE)
            except Exception:
                break
            if not isinstance(payload, dict):
                break
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                break

            for item in items:
                if len(seen) >= cap:
                    break
                if not isinstance(item, dict):
                    continue
                full_name = _clean(item.get("full_name"), 200)
                key = full_name.lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                collected.append({
                    "name": full_name,
                    "description": _clean(item.get("description"), DESC_LIMIT),
                })
                raw_topics = item.get("topics")
                if isinstance(raw_topics, (list, tuple)):
                    for topic in raw_topics:
                        _bump(topics, topic)
                _bump(languages, item.get("language"))

    digest = hashlib.sha256("\n".join(sorted(seen)).encode("utf-8")).hexdigest()[:16]
    status = "live_verified" if collected else "no_data_source"
    next_step = (
        "مراجعة العينات محلياً وتغذية خطة التعلّم بدون أي اتصال إضافي."
        if collected
        else "لا توجد بيانات من GitHub؛ أعد المحاولة لاحقاً."
    )
    return {
        "ok": bool(collected),
        "status": status,
        "checked_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "target": API_BASE,
        "scanned": len(collected),
        "queries": selected,
        "topics": _top_counts(topics),
        "languages": _top_counts(languages),
        "sample": collected[:SAMPLE_SIZE],
        "next": next_step,
        "digest": digest,
    }


def run(state_dir=DEFAULT_STATE_DIR, fetcher=None, limit=TARGET) -> dict:
    """Lance la collecte et écrit ``state/github_scout_report.json``."""
    report = harvest(fetcher, limit=limit)
    path = Path(state_dir) / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(_scrub(payload) + "\n", encoding="utf-8")
    return report


def _say(text: str) -> None:
    """طباعة عربية آمنة على كونسول Windows بترميز غير UTF-8."""
    stream = sys.stdout
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        try:
            buffer.write((text + "\n").encode("utf-8"))
            buffer.flush()
            return
        except Exception:
            pass
    try:
        stream.write(text + "\n")
    except UnicodeEncodeError:
        stream.write(text.encode("ascii", "backslashreplace") + "\n")


def main() -> None:
    report = run()
    _say("فحص GitHub: " + str(report["scanned"]) + " مستودع، الحالة: " + report["status"])
    _say("التقرير: " + str(DEFAULT_STATE_DIR / REPORT_NAME))


if __name__ == "__main__":
    main()


__all__ = ["DEFAULT_STATE_DIR", "allowed", "harvest", "run"]
