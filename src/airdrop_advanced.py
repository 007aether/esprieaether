"""Airdrop Scanner متقدم — بديل HarvestKit"""
import os, json, logging, requests
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("airdrop_advanced")
DATA_FILE = Path.home() / "AETHER_V8" / "airdrops_advanced.json"

SOURCES = {
    "airdrops_io": "https://airdrops.io/feed/",
    "airdropalert": "https://airdropalert.com/feed/",
}

NETWORKS = [
    "pharos", "somnia", "linea", "scroll", "zksync",
    "starknet", "base", "arbitrum", "optimism", "manta", "blast",
]

class AirdropScanner:
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        if DATA_FILE.exists():
            try:
                return json.loads(DATA_FILE.read_text())
            except Exception:
                pass
        return {"scans": []}
    
    def _save(self):
        DATA_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def scan(self):
        results = {}
        for name, url in SOURCES.items():
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "AETHER/1.0"})
                if r.status_code == 200:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(r.text)
                    items = [{"title": item.find("title").text}
                             for item in root.findall(".//item")[:10]
                             if item.find("title") is not None]
                    results[name] = items
                    logger.info(f"✅ {name}: {len(items)}")
            except Exception as e:
                logger.error(f"❌ {name}: {e}")
        
        scan = {"timestamp": datetime.now().isoformat(), "results": results}
        self.data["scans"].append(scan)
        self.data["scans"] = self.data["scans"][-20:]
        self._save()
        return scan

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    s = AirdropScanner()
    result = s.scan()
    for src, items in result["results"].items():
        print(f"\n📡 {src}: {len(items)} عنصر")
        for i in items[:5]:
            print(f"  • {i['title'][:70]}")
