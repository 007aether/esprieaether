import psutil, sqlite3, time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "aether.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS system_metrics
                 (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  cpu_percent REAL,
                  ram_percent REAL)''')
    conn.commit()
    return conn

def run_daemon():
    conn = init_db()
    c = conn.cursor()
    try:
        while True:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            c.execute("INSERT INTO system_metrics (cpu_percent, ram_percent) VALUES (?, ?)", (cpu, ram))
            conn.commit()
            time.sleep(10)
    except:
        pass
    finally:
        conn.close()

if __name__ == "__main__":
    run_daemon()
