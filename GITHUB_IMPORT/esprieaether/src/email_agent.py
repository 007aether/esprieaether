"""
⚡ EsprieAether - Email Agent
وكيل إرسال التقارير بالبريد
"""
import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", SMTP_USER)

logger = logging.getLogger("email_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class EmailAgent:
    """وكيل إرسال التقارير بالبريد"""

    def __init__(self):
        self.host = SMTP_HOST
        self.port = SMTP_PORT
        self.user = SMTP_USER
        self.password = SMTP_PASSWORD
        self.to = EMAIL_TO

    def is_configured(self) -> bool:
        return bool(self.user and self.password and self.to)

    def send_email(self, subject: str, body: str, html: str = None) -> dict:
        """إرسال بريد"""
        if not self.is_configured():
            logger.error("⚠️ SMTP غير مُعدّ في .env")
            return {"status": "error", "message": "SMTP غير مُعدّ"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = self.to

            msg.attach(MIMEText(body, "plain", "utf-8"))
            if html:
                msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            logger.info(f"✅ بريد أُرسل إلى {self.to}")
            return {"status": "ok", "to": self.to}
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ كلمة مرور SMTP خاطئة")
            return {"status": "error", "message": "كلمة مرور خاطئة"}
        except Exception as e:
            logger.error(f"❌ فشل إرسال البريد: {e}")
            return {"status": "error", "message": str(e)}

    def build_weekly_report(self) -> tuple:
        """بناء تقرير أسبوعي"""
        # جلب البيانات
        from airdrop_agent import AirdropAgent
        airdrop = AirdropAgent()

        # Airdrops
        recent_airdrops = airdrop.get_recent(10)
        airdrop_total = airdrop.count()

        # الحالة
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # نص عادي
        text = f"""
╔══════════════════════════════════════╗
║   ⚡ ESPRIEAETHER - تقرير أسبوعي      ║
╚══════════════════════════════════════╝

📅 التاريخ: {now}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 الإيردروبات
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 الإجمالي: {airdrop_total} إيردروب

أحدث 10:
"""
        for i, item in enumerate(recent_airdrops, 1):
            text += f"{i}. {item['title'][:80]}\n   {item['link']}\n\n"

        text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 الروابط السريعة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Dashboard: http://localhost:5000
• Airdrops:  http://localhost:5000/airdrops
• Telegram:  @Esprieaether_bot
• GitHub:    https://github.com/007aether/esprieaether

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تم إنشاؤه تلقائياً بواسطة EsprieAether
"""

        # HTML
        html = f"""
<html dir="rtl">
<head>
<style>
body {{ font-family: Arial, sans-serif; background: #0a0e1a; color: #e4e8f1; padding: 20px; }}
.container {{ max-width: 700px; margin: auto; background: #1a2030; padding: 30px; border-radius: 12px; }}
h1 {{ color: #00d9ff; }}
h2 {{ color: #a855f7; border-bottom: 2px solid #2a3142; padding-bottom: 8px; }}
.item {{ padding: 12px; margin: 8px 0; background: #131826; border-radius: 8px; border-right: 3px solid #00d9ff; }}
.item a {{ color: #00d9ff; text-decoration: none; }}
.stat {{ font-size: 36px; color: #00d9ff; font-weight: bold; }}
.footer {{ margin-top: 30px; color: #8892a6; font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <h1>⚡ ESPRIEAETHER</h1>
  <p>تقرير أسبوعي — {now}</p>

  <h2>📡 الإيردروبات</h2>
  <div class="stat">{airdrop_total}</div>
  <p>إيردروب في القاعدة</p>

  <h2>أحدث 10</h2>
"""
        for i, item in enumerate(recent_airdrops, 1):
            html += f'<div class="item"><b>{i}.</b> <a href="{item["link"]}">{item["title"][:100]}</a></div>'

        html += f"""
  <h2>🔗 الروابط السريعة</h2>
  <div class="item">🌐 <a href="http://localhost:5000">Dashboard</a></div>
  <div class="item">📡 <a href="http://localhost:5000/airdrops">Airdrops</a></div>
  <div class="item">💬 <a href="https://t.me/Esprieaether_bot">Telegram Bot</a></div>
  <div class="item">🔄 <a href="https://github.com/007aether/esprieaether">GitHub</a></div>

  <div class="footer">
    تم إنشاؤه تلقائياً بواسطة EsprieAether — {now}
  </div>
</div>
</body>
</html>
"""
        return text, html

    def send_weekly_report(self) -> dict:
        """إرسال التقرير الأسبوعي"""
        text, html = self.build_weekly_report()
        subject = f"⚡ EsprieAether — تقرير أسبوعي ({datetime.now().strftime('%Y-%m-%d')})"
        return self.send_email(subject, text, html)


if __name__ == "__main__":
    print("═" * 60)
    print("⚡ Email Agent Test")
    print("═" * 60)

    agent = EmailAgent()

    if not agent.is_configured():
        print("❌ SMTP غير مُعدّ")
        print("أضف SMTP_USER و SMTP_PASSWORD إلى .env")
        exit(1)

    print(f"📧 From: {agent.user}")
    print(f"📧 To: {agent.to}")
    print()

    result = agent.send_weekly_report()
    print(f"✅ النتيجة: {result}")
