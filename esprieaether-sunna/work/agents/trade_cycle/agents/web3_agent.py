#!/usr/bin/env python3
"""
Web3 Agent - دعم السلاسل البلوك تشين المتعددة
يدعم Ethereum و BSC و Polygon و Solana
يدعم OKX Wallet و Web3 wallets
"""

import os, json, sqlite3, hashlib, base64, hmac, time
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "work" / "data" / "trade_cycle.db"

class Web3Agent:
    """عرض البيانات من أسواق البلوك تشين"""

    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.okx_balance = OKXBalanceAgent()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS web3_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain TEXT,
                symbol TEXT,
                address TEXT,
                balance REAL,
                price REAL,
                market_data TEXT,
                timestamp TEXT,
                status TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallet_balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT,
                chain TEXT,
                balance_usd REAL,
                balance_token REAL,
                token_symbol TEXT,
                timestamp TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def get_supported_chains(self):
        """أعلى 30 عضواً في القائمة (إضافة RPC مخصص)"""
        return {
            "Ethereum": {"symbol": "ETH", "rpc": "https://rpc.ankr.com/eth"},
            "Binance Smart Chain": {"symbol": "BNB", "rpc": "https://bsc-dataseed.binance.org/"},
            "Polygon": {"symbol": "MATIC", "rpc": "https://polygon-rpc.com/"},
            "Solana": {"symbol": "SOL", "rpc": "https://api.mainnet-beta.solana.com"},
            "Moonbeam": {"symbol": "GLMR", "rpc": "https://rpc.api.moonbeam.network"},
            "Fantom": {"symbol": "FTM", "rpc": "https://rpc.ftm.tools/"},
            "Arbitrum": {"symbol": "ARB", "rpc": "https://arb1.arbitrum.io/rpc"},
            "Optimism": {"symbol": "OP", "rpc": "https://mainnet.optimism.io"},
            "Avalanche": {"symbol": "AVAX", "rpc": "https://api.avax.network/ext/bc/C/rpc"},
            "Base": {"symbol": "BASE", "rpc": "https://mainnet.base.org"},
            "Custom (Ankr MultiChain)": {
                "symbol": "MULTI",
                "rpc": "https://rpc.ankr.com/multichain/755844f5dc2213f1b7e93a00f208b661e2d271430a21f7d0b24607ae0dffbb70",
                "is_custom": True
            },
        }

    def get_chain_data(self, chain_name):
        """الحصول على البيانات من سلسلة معينة"""
        chains = self.get_supported_chains()
        if chain_name not in chains:
            return {"error": "Chain not supported"}

        chain_info = chains[chain_name]
        symbol = chain_info["symbol"]

        data = {
            "chain": chain_name,
            "symbol": symbol,
            "rpc": chain_info["rpc"],
            "timestamp": datetime.now().isoformat()
        }

        # جلب البيانات (سيتم ربطه بالواجهة الحقيقية لاحقاً)
        try:
            data["status"] = "connected"
            data["message"] = f"تم الاتصال بـ {chain_name}"
        except Exception as e:
            data["status"] = "error"
            data["error"] = str(e)

        return data

    def update_wallet_balance(self, wallet_address, chain="Ethereum"):
        """تحديث رصيد المحفظة"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO wallet_balance (wallet_address, chain, balance_usd, token_symbol, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (wallet_address, chain, 0.0, "USDT", datetime.now().isoformat(), "pending"))
        conn.commit()
        conn.close()

    def get_wallet_balance(self, wallet_address=None):
        """الحصول على رصيد المحفظة"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if wallet_address:
            cur.execute("""
                SELECT * FROM wallet_balance WHERE wallet_address=? ORDER BY id DESC LIMIT 1
            """, (wallet_address,))
        else:
            cur.execute("SELECT * FROM wallet_balance ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "wallet": r[1], "chain": r[2],
                 "balance_usd": r[3], "token": r[4], "timestamp": r[5], "status": r[6]} for r in rows]

    def generate_web3_report(self):
        """توليد تقرير البلوك تشين"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM web3_data ORDER BY id DESC LIMIT 50")
        rows = cur.fetchall()
        conn.close()
        return [{
            "id": r[0], "chain": r[1], "symbol": r[2],
            "address": r[3], "balance": r[4], "price": r[5],
            "data": r[6], "timestamp": r[7], "status": r[8]
        } for r in rows]
