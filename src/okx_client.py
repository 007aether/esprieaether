#!/usr/bin/env python3
"""
okx_client.py — EsprieAether × OKX connector (sovereign money layer)

SAFETY: this client deliberately refuses to sign withdrawal or transfer
requests. Only read + trade permissions are used — even if the key on
OKX still carries them, we never build the URL.

Auth: HMAC-SHA256 signature (OKX v5 standard).
Base: https://www.okx.com  (live)  — use sandbox via OKX_SANDBOX=1
"""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("OKX_API_KEY")
SECRET = os.getenv("OKX_SECRET_KEY")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")
SANDBOX = os.getenv("OKX_SANDBOX", "0") == "1"
BASE = "https://www.okx.com" if not SANDBOX else "https://www.okx.com"  # same host; x-simulated-trading flag

# Endpoints we will NEVER touch, regardless of key permissions
FORBIDDEN = ("withdrawal", "transfer", "sub-account/transfer", "asset/transfer")


class OKXError(Exception):
    pass


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _sign(timestamp: str, method: str, path: str, body: str = "") -> str:
    msg = timestamp + method + path + body
    mac = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def _headers(method: str, path: str, body: str = "") -> dict:
    ts = _ts()
    return {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": _sign(ts, method, path, body),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json",
        **({"x-simulated-trading": "1"} if SANDBOX else {}),
    }


def request(method: str, path: str, params: dict = None, body: dict = None):
    """Signed OKX request. Refuses forbidden endpoints."""
    low = path.lower()
    for bad in FORBIDDEN:
        if bad in low:
            raise OKXError(f"refusing to call forbidden endpoint: {path}")

    query = ""
    if params:
        query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
    body_str = json.dumps(body) if body else ""

    url = BASE + path + query
    r = requests.request(
        method,
        url,
        headers=_headers(method, path + query, body_str),
        data=body_str or None,
        timeout=15,
    )
    data = r.json()
    if data.get("code") not in (0, "0"):
        raise OKXError(f"OKX {data.get('code')}: {data.get('msg')}")
    return data.get("data", data)


# ── Read helpers ──

def balance() -> list:
    return request("GET", "/api/v5/account/balance")


def ticker(inst_id: str) -> dict:
    d = request("GET", "/api/v5/market/ticker", params={"instId": inst_id})
    return d[0] if d else {}


def price(inst_id: str) -> float:
    return float(ticker(inst_id).get("last", 0))


def candles(inst_id: str, bar: str = "1H", limit: int = 100) -> list:
    return request("GET", "/api/v5/market/candles", params={"instId": inst_id, "bar": bar, "limit": str(limit)})


def orders_pending(inst_id: str = None) -> list:
    params = {"instType": "SPOT"}
    if inst_id:
        params["instId"] = inst_id
    return request("GET", "/api/v5/trade/orders-pending", params=params)


# ── Trade helpers (spot only, no leverage) ──

def place_spot_order(inst_id: str, side: str, sz: str, px: str = None, ord_type: str = "limit"):
    """side: buy|sell. sz in base ccy. ord_type: limit|market."""
    body = {"instId": inst_id, "tdMode": "cash", "side": side, "ordType": ord_type, "sz": sz}
    if ord_type == "limit" and px:
        body["px"] = px
    return request("POST", "/api/v5/trade/order", body=body)


def cancel_order(inst_id: str, ord_id: str):
    return request("POST", "/api/v5/trade/cancel-order", body={"instId": inst_id, "ordId": ord_id})


if __name__ == "__main__":
    print(f"OKX client — sandbox={SANDBOX} key_set={bool(API_KEY)}")
    try:
        b = balance()
        total_eq = b[0]["totalEq"] if b else "?"
        print(f"  total equity: {total_eq} USD")
    except OKXError as e:
        print(f"  balance error: {e}")
    try:
        print(f"  BTC-USDT last: {price('BTC-USDT')}")
    except OKXError as e:
        print(f"  price error: {e}")
