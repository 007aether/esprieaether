# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Telegram Bot Controller
بوت تيليغرام لل(full) Control النظام
"""
import os
import sys
import json
import subprocess
import logging
import requests
from datetime import datetime
from cloud_fallback import CloudFallback
from ask_agent import AskAgent
from complex_executor import ComplexExecutor
from memory_layer import SemanticMemory
from smart_alerts import SmartAlerts
from log_analyzer import LogAnalyzer
from auto_apply import AutoApply
from market_watcher import MarketWatcher
from daily_digest import DailyDigest
from bandwidth_agent import BandwidthAgent
from pharos_agent import PharosAgent
from self_evolve import SelfEvolve
from pathlib import Path

# مسار المشروع
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv

from jarvis_bridge import JarvisBridge

from vpn_agent import VPNAgent
from airdrop_agent import AirdropAgent

# ─── الإعدادات ───
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
AETHER_ID = os.getenv("AETHER_ID", "007aether")

# ─── Logger ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("aether-bot")

# ─── JARVIS ───
jarvis = JarvisBridge()
cloud = CloudFallback()
ask_agent = AskAgent()
executor = ComplexExecutor()
memory = SemanticMemory()
alerts = SmartAlerts()
analyzer = LogAnalyzer()
auto_apply = AutoApply()
market = MarketWatcher()
digest = DailyDigest()
bandwidth = BandwidthAgent()
pharos = PharosAgent()
evolve = SelfEvolve()

vpn = VPNAgent()
airdrop = AirdropAgent()

# ─── معالجة الأخطاء المتحدة للاتصال بالخادم ───
def connect(server_url: str, timeout: int = 30) -> requests.Response:
    """
    الاتصال بالخادم بـ timeout من 30 ثانية مع معالجة أخطاء متحدة.
    """
    try:
        logger.info(f"Attempting to connect to {server_url} with timeout {timeout}s")
        response = requests.get(server_url, timeout=timeout)
        response.raise_for_status()
        logger.info(f"Successfully connected to {server_url}")
        return response
    except requests.exceptions.Timeout as e:
        logger.error(f"Connection timeout after {timeout}s: {e}")
        raise ConnectionError(f"Timeout connecting to {server_url}") from e
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to {server_url}: {e}")
        raise ConnectionError(f"Failed to connect to {server_url}") from e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error from {server_url}: {e}")
        raise ConnectionError(f"HTTP error: {e}") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"General request error: {e}")
        raise ConnectionError(f"Request failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during connection: {e}")
        raise ConnectionError(f"Unexpected error: {e}") from e

# مثال على استخدام دالة connect (يمكن حذفها أو تعديلها حسب الحاجة)
# try:
#     response = connect("http://example.com/api")
# except ConnectionError as e:
#     logger.critical(f"Connection failed: {e}")