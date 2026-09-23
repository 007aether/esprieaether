import os
import json
from pathlib import Path
from eth_account import Account

# تمكين ميزات الحسابات غير المدققة بطريقة صحيحة وآمنة
Account.enable_unaudited_hdwallet_features()

WALLET_FILE = Path.home() / "AETHER_V8" / "aether_wallet.json"

def create_wallet():
    try:
        if WALLET_FILE.exists():
            with open(WALLET_FILE, "r") as f:
                data = json.load(f)
                return data
        
        # إنشاء محفظة إيثريوم حقيقية جديدة
        account, mnemonic = Account.create_with_mnemonic()
        wallet_data = {
            "address": account.address,
            "private_key": account.key.hex(),
            "mnemonic": mnemonic
        }
        
        WALLET_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WALLET_FILE, "w") as f:
            json.dump(wallet_data, f, indent=4)
            
        return wallet_data
    except Exception as e:
        # محفظة احتياطية في حال فشل التوليد العشوائي
        return {"address": "0xRealAetherCoreFallbackAddress007", "error": str(e)}

def get_existing_wallet():
    return create_wallet()
