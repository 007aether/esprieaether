import os
from eth_account import Account
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
WALLET_FILE = BASE_DIR / "aether_wallet.json"

def create_wallet():
    # تفعيل ميزة توليد الحسابات العشوائية في الإيثريوم/EVM
    Account.enable_unaudited_hwtng()
    account = Account.create()
    
    wallet_data = {
        "address": account.address,
        "private_key": account.key.hex()
    }
    
    # حفظ المحفظة محلياً في ملف آمن خاص بالروبوت
    with open(WALLET_FILE, "w") as f:
        json.dump(wallet_data, f, indent=4)
        
    return wallet_data

def get_existing_wallet():
    if WALLET_FILE.exists():
        with open(WALLET_FILE, "r") as f:
            return json.load(f)
    else:
        return create_wallet()
