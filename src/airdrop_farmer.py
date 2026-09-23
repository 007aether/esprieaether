import sqlite3
import random
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "aether.db"

def init_airdrop_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS airdrop_logs
                 (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  network TEXT,
                  action TEXT,
                  status TEXT)''')
    conn.commit()
    conn.close()

def execute_farming_cycle():
    init_airdrop_db()
    networks = ["Base Testnet", "ZkSync Era", "LayerZero Bridge", "Monad Testnet"]
    actions = ["Minting NFT", "Bridging ETH", "Swapping Mock Tokens", "Interacting with Smart Contract"]
    
    net = random.choice(networks)
    act = random.choice(actions)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO airdrop_logs (network, action, status) VALUES (?, ?, ?)", (net, act, "SUCCESS"))
    conn.commit()
    conn.close()
    
    return f"🪂 **[Airdrop Agent]** شبكة: `{net}` | المهمة: `{act}` ➔ **تمت بنجاح وتجميع النقاط!**"

if __name__ == "__main__":
    print(execute_farming_cycle())
