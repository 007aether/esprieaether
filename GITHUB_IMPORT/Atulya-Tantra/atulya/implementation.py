"""Owner-visible implementation record; contains engineering state, never credentials."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from atulya.settings import PROJECT_ROOT

VERIFY_TTL_DAYS = 7
LIVE_STATES = {"live_verified", "partially_live_verified"}


def _parse_stamp(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def implementation_status(root=PROJECT_ROOT, now=None):
    """Les statuts live périment : une preuve ancienne n'est plus une preuve."""
    path = root / "docs" / "implementation-status.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"updated": "", "scope": "Implementation record is unavailable.",
                "items": [], "fresh": False, "verifiedAt": None, "expiresAt": None,
                "ttlDays": VERIFY_TTL_DAYS}
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    stamp = _parse_stamp(data.get("updated"))
    ttl = timedelta(days=VERIFY_TTL_DAYS)
    fresh = stamp is not None and timedelta(0) <= moment - stamp <= ttl
    data["verifiedAt"] = stamp.isoformat() if stamp else None
    data["expiresAt"] = (stamp + ttl).isoformat() if stamp else None
    data["ttlDays"] = VERIFY_TTL_DAYS
    data["fresh"] = fresh
    for item in data.get("items", []):
        if not isinstance(item, dict) or item.get("status") not in LIVE_STATES:
            continue
        item["verifiedAt"] = data["verifiedAt"]
        item["expiresAt"] = data["expiresAt"]
        if not fresh:
            item["status"] = "implemented_unverified"
            item["next"] = "Preuve périmée : " + str(item.get("next") or "retester localement")
    return data


async def implementation_tool(_args, ctx):
    if ctx is None or ctx.user_id != "admin":
        return "Only the owner can inspect implementation progress."
    return json.dumps(await asyncio.to_thread(implementation_status), ensure_ascii=False)


def register_implementation_routes(app, auth_store):
    @app.get("/api/implementation")
    async def status(request: Request):
        if not await asyncio.to_thread(auth_store.is_admin, str(request.state.user_id)):
            raise HTTPException(403, "Implementation progress is for the owner.")
        return await asyncio.to_thread(implementation_status)
