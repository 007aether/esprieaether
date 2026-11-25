#!/usr/bin/env python3
"""
OKX Balance Agent - ربط البيانات الحقيقية من حساب OKX
يمكن استخدام هذه الفئة لجلب رصيد الحساب الفعلي
"""

import os, json, sqlite3, base64, hashlib, hmac, pathlib
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

# Load .env file
_env_path = pathlib.Path(__file__).parent.parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)

BASE_DIR = Path(__file__).parent.parent.parent.parent

BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "work" / "data" / "trade_cycle.db"

class OKXBalanceAgent:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.api_key = os.getenv("OKX_API_KEY", "6fa1cfec-b853-402b-838f-1329c5163555")
        self.secret_key = os.getenv("OKX_SECRET_KEY", "9318A560C3A34A2C0FC763222E769D17")
        self.passphrase = os.getenv("OKX_PASS", "0.0.0.0")
        self.base_url = "https://www.okx.com/api/v5"

    def _sign(self, payload=""):
            """إنشاء التوقيع لـ OKX API حسب المواصفات الرسمية"""
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            # OKX: message = timestamp + method + request_path + query_string + body
            method = "GET"
            path = "/api/v5/account/balance"
            message = f"{timestamp}{method}{path}{payload}"
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
            return base64.b64encode(signature).decode('utf-8'), timestamp

    def fetch_balance(self):
        """جلب رصيد الحساب من OKX"""
        sign, timestamp = self._sign("")
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sign,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}/account/balance?ccy=USDT"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"   ⚠️  خطأ في جلب الرصيد: {e}")
            return {"error": str(e)}

    def update_ledger(self, data):
        """تحديث السجلات مع البيانات الجديدة"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if isinstance(data, dict) and "error" not in data:
            # تحديث الرصيد في الجدول
            for balance in data.get("data", []):
                symbol = balance.get("ccy", "USDT")
                balance_usd = float(balance.get("bal", 0))
                # تحديث أو إضافة في الجدول
                cur.execute("""
                    INSERT INTO ledger (symbol, balance_usd, source, updated_at, status)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        balance_usd=excluded.balance_usd,
                        source=excluded.source,
                        updated_at=excluded.updated_at,
                        status=excluded.status
                """, (symbol, balance_usd, "okx", datetime.now().isoformat(), "active"))
            conn.commit()
        conn.close()

    def get_balance(self):
        """الحصول على الرصيد الحالي"""
        data = self.fetch_balance()
        if isinstance(data, dict) and "error" not in data:
            balances = {}
            for item in data.get("data", []):
                symbol = item.get("ccy", "USDT")
                balance = float(item.get("bal", 0))
                balances[symbol] = balance
            return balances
        return {}
