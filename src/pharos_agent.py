# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Pharos Agent
وكيل Pharos Testnet: Faucet + النقاط + المراقبة
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("pharos")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── المسارات ───
WALLET_FILE = BASE_DIR / "integrations" / "pharos" / "pharos_wallet.json"
STATE_FILE = BASE_DIR / "pharos_state.json"

# ─── API ───
PHAROS_API = "https://api.pharosnetwork.xyz"
RPC_URL = "https://rpc.pharos.xyz"


class PharosAgent:
    """وكيل Pharos"""

    def __init__(self):
        self.state = self._load_state()
        self.wallet = self._load_wallet()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "started_at": datetime.now().isoformat(),
            "faucet_claims": [],
            "last_claim": None,
            "points": 0,
            "total_claims": 0,
        }

    def _save_state(self):
        STATE_FILE.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False)
        )

    def _load_wallet(self) -> dict:
        """تحميل محفظة Pharos"""
        if not WALLET_FILE.exists():
            logger.warning("⚠️ pharos_wallet.json غير موجود")
            return {}
        try:
            return json.loads(WALLET_FILE.read_text())
        except Exception:
            return {}

    # ─────────────────────────────────────
    #  المعلومات
    # ─────────────────────────────────────
    def get_address(self) -> str:
        return self.wallet.get("address", "")

    def get_balance(self) -> dict:
        """رصيد PHRS"""
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(RPC_URL))
            addr = self.get_address()
            if not addr:
                return {"status": "no_wallet"}

            balance = w3.from_wei(w3.eth.get_balance(addr), "ether")
            return {
                "status": "ok",
                "address": addr,
                "balance": str(balance),
                "connected": w3.is_connected(),
                "block": w3.eth.block_number,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─────────────────────────────────────
    #  Faucet
    # ─────────────────────────────────────
    def can_claim(self) -> bool:
        """هل يمكن ادعاء Faucet؟"""
        last = self.state.get("last_claim")
        if not last:
            return True

        try:
            last_dt = datetime.fromisoformat(last)
            elapsed = (datetime.now() - last_dt).total_seconds()
            # 12 ساعة
            return elapsed >= 12 * 60 * 60
        except Exception:
            return True

    def claim_faucet(self) -> dict:
        """ادعاء Faucet (عبر API مع Referer)"""
        if not self.can_claim():
            return {"status": "cooldown", "message": "انتظر 12 ساعة"}

        addr = self.get_address()
        if not addr:
            return {"status": "error", "message": "لا توجد محفظة"}

        try:
            # Headers كاملة (مثل المتصفح)
            headers = {
                "Content-Type": "application/json",
                "Referer": "https://testnet.pharosnetwork.xyz/",
                "Origin": "https://testnet.pharosnetwork.xyz",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # جرّب 3 endpoints
            endpoints = [
                f"{PHAROS_API}/faucet/claim",
                f"{PHAROS_API}/api/faucet/claim",
                f"{PHAROS_API}/v1/faucet/claim",
            ]

            for endpoint in endpoints:
                try:
                    r = requests.post(
                        endpoint,
                        json={"address": addr},
                        headers=headers,
                        timeout=30,
                    )

                    if r.status_code == 200:
                        data = r.json()
                        self.state["last_claim"] = datetime.now().isoformat()
                        self.state["faucet_claims"].append({
                            "timestamp": datetime.now().isoformat(),
                            "amount": "0.01 PHRS",
                            "tx": data.get("txHash", data.get("hash", "")),
                        })
                        self.state["total_claims"] += 1
                        self.state["faucet_claims"] = self.state["faucet_claims"][-50:]
                        self._save_state()

                        logger.info(f"✅ Faucet: {endpoint}")
                        return {
                            "status": "ok",
                            "amount": "0.01 PHRS",
                            "tx": data.get("txHash", data.get("hash", "")),
                            "endpoint": endpoint,
                        }
                    elif r.status_code == 403:
                        # جرب endpoint آخر
                        continue
                    elif r.status_code == 429:
                        return {"status": "rate_limit", "message": "انتظر قليلاً"}
                except Exception:
                    continue

            return {"status": "error", "message": "كل الـ endpoints فشلت — استخدم المتصفح"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


    # ─────────────────────────────────────
    #  النقاط والمهام
    # ─────────────────────────────────────
    def get_profile(self) -> dict:
        """بيانات المستخدم من Pharos"""
        addr = self.get_address()
        if not addr:
            return {"status": "no_wallet"}

        try:
            r = requests.get(
                f"{PHAROS_API}/profile/{addr}",
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                self.state["points"] = data.get("points", 0)
                self._save_state()
                return {"status": "ok", "profile": data}
            return {"status": "error", "code": r.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─────────────────────────────────────
    #  المهام التلقائية
    # ─────────────────────────────────────
    def daily_routine(self) -> dict:
        """روتين يومي"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }

        # 1. Faucet
        if self.can_claim():
            claim = self.claim_faucet()
            result["actions"].append({"faucet": claim})

        # 2. الرصيد
        balance = self.get_balance()
        result["balance"] = balance

        # 3. النقاط
        profile = self.get_profile()
        result["profile"] = profile

        return result

    # ─────────────────────────────────────
    #  التنسيق
    # ─────────────────────────────────────
    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        addr = self.get_address()
        balance = self.get_balance()

        text = "🔷 *Pharos Testnet*" + chr(10) + chr(10)

        if addr:
            text += "📍 *العنوان:*" + chr(10)
            text += "`" + addr + "`" + chr(10) + chr(10)

            if balance.get("status") == "ok":
                text += "💰 *الرصيد:* `" + balance["balance"] + " PHRS`" + chr(10)
                text += "🔗 متصل: `" + str(balance.get("connected")) + "`" + chr(10)
                text += "📦 Block: `" + str(balance.get("block", "—")) + "`" + chr(10)
            else:
                text += "⚠️ فشل جلب الرصيد" + chr(10)

            text += chr(10) + "📊 *الإحصائيات:*" + chr(10)
            text += "• ادعاءات Faucet: `" + str(self.state.get("total_claims", 0)) + "`" + chr(10)

            if self.state.get("last_claim"):
                text += "• آخر ادعاء: `" + self.state["last_claim"][:19] + "`" + chr(10)

            if self.can_claim():
                text += chr(10) + "✅ *يمكن ادعاء Faucet الآن*" + chr(10)
            else:
                text += chr(10) + "⏳ *انتظر 12 ساعة*" + chr(10)
        else:
            text += "⚠️ *لا توجد محفظة*" + chr(10)
            text += "_أضف pharos_wallet.json_"

        return text


# ─── اختبار ───
if __name__ == "__main__":
    print("═" * 60)
    print("🔷 Pharos Agent Test")
    print("═" * 60)

    agent = PharosAgent()

    print("\n▶ العنوان:", agent.get_address() or "—")

    print("\n▶ الرصيد:")
    balance = agent.get_balance()
    for k, v in balance.items():
        print(f"  {k}: {v}")

    print("\n▶ can_claim:", agent.can_claim())

    print("\n▶ التقرير:")
    print(agent.format_telegram())
