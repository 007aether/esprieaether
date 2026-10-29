"""
⚡ EsprieAether - Airdrop Agent
وكيل مراقبة الإيردروبات من مصادر RSS
"""
import os
import json
import logging
import requests
import xml.etree.ElementTree as ET
import defusedxml.ElementTree as DEFUSED_ET
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

logger = logging.getLogger("airdrop_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

RSS_FEEDS = [
    "https://airdrops.io/feed/",
    "https://airdropalert.com/feed/",
    "https://airdropalert.com/feed/?post_type=airdrop",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
    "https://cryptopotato.com/feed/",
    "https://u.today/rss",
    "https://news.bitcoin.com/feed/",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://www.newsbtc.com/feed/",
    "https://cryptoslate.com/feed/",
    "https://beincrypto.com/feed/",
    "https://www.gemini.com/feed/",
    "https://blog.ethereum.org/feed.xml",
]

AIRDROP_DB = BASE_DIR / "airdrops.json"


class AirdropAgent:
    """وكيل مراقبة الإيردروبات"""

    def __init__(self):
        self.feeds = RSS_FEEDS

    def fetch_feed(self, url: str) -> list:
        """حصول على تغذية RSS مع معالجة خطأ متقدمة"""
        try:
            r = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; EsprieAether/1.0)"
            })
            r.raise_for_status()

            # Handle content encoding safely
            content = r.content
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('latin-1')
                except UnicodeDecodeError:
                    logger.warning(f"⚠️ {url}: Encoding مشكل، تخطي")
                    return []

            root = DEFUSED_ET.fromstring(text)
            items = []

            for item in root.findall(".//item")[:20]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()

                if title and link:
                    items.append({
                        "title": title,
                        "link": link,
                        "date": pub_date,
                        "source": url,
                        "fetched_at": datetime.now().isoformat(),
                    })

            logger.info(f"✅ {url}: {len(items)} عنصر")
            return items
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ {url}: وقت استجابة متوقف (Timeout)")
            return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"🚫 {url}: محظور (403 Forbidden) - مصدر مBLOCKED")
            elif e.response.status_code == 404:
                logger.warning(f"🔍 {url}: غير موجود (404 Not Found)")
            else:
                logger.warning(f"⚠️ {url}: خطأ HTTP {e.response.status_code}")
            return []
        except requests.exceptions.ConnectionError as e:
            if "SSL" in str(e) or "ssl" in str(e):
                logger.warning(f"🔒 {url}: خطأ SSL ({e})")
            else:
                logger.warning(f"🔌 {url}: مشكلة في الاتصال ({e})")
            return []
        except Exception as e:
            logger.warning(f"⚠️ {url}: {type(e).__name__}: {e}")
            return []

    def fetch_all(self) -> list:
        all_items = []
        for feed in self.feeds:
            all_items.extend(self.fetch_feed(feed))
        return all_items

    def save_airdrops(self, items: list) -> int:
        existing = []
        if AIRDROP_DB.exists():
            try:
                existing = json.loads(AIRDROP_DB.read_text())
            except Exception:
                pass

        existing_links = {x["link"] for x in existing}
        new_items = [x for x in items if x["link"] not in existing_links]

        all_items = (new_items + existing)[:500]
        AIRDROP_DB.write_text(json.dumps(all_items, ensure_ascii=False, indent=2))

        return len(new_items)

    def get_recent(self, limit: int = 5) -> list:
        if not AIRDROP_DB.exists():
            return []
        try:
            items = json.loads(AIRDROP_DB.read_text())
            return items[:limit]
        except Exception:
            return []

    def count(self) -> int:
        if not AIRDROP_DB.exists():
            return 0
        try:
            return len(json.loads(AIRDROP_DB.read_text()))
        except Exception:
            return 0

    def format_telegram(self, limit: int = 5) -> str:
        recent = self.get_recent(limit)
        if not recent:
            return "📭 لا توجد إيردروبات جديدة"

        text = f"📡 *أحدث الإيردروبات* ({self.count()} إجمالي)\n\n"
        for i, item in enumerate(recent, 1):
            title = item["title"][:80]
            text += f"{i}. [{title}]({item['link']})\n\n"
        return text


if __name__ == "__main__":
    print("═" * 60)
    print("⚡ Airdrop Agent Test")
    print("═" * 60)

    agent = AirdropAgent()
    items = agent.fetch_all()

    print(f"\n✅ تم جلب {len(items)} عنصر")
    new = agent.save_airdrops(items)
    print(f"✅ {new} عنصر جديد تم حفظه")

    print("\n▶ أحدث 5:")
    for i, item in enumerate(agent.get_recent(5), 1):
        print(f"  {i}. {item['title'][:70]}")
