#!/usr/bin/env python3
"""
KnowledgeBase Agent - مقالة وتوثيق النظام
إضافة مصادر وروابط جديدة
"""

import os, json, sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
DB_PATH = BASE_DIR / "work" / "data" / "knowledge.db"

class KnowledgeBaseAgent:
    def __init__(self):
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                category TEXT,
                source_url TEXT,
                created_at TEXT,
                updated_at TEXT,
                views INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT,
                description TEXT,
                category TEXT,
                created_at TEXT,
                status TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_article(self, title, content, category="general"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO articles (title, content, category, source_url, created_at, updated_at, views)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (title, content, category, None, datetime.now().isoformat(),
              datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def add_link(self, title, url, description="", category="general"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO links (title, url, description, category, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, url, description, category, datetime.now().isoformat(), "active"))
        conn.commit()
        conn.close()

    def get_links(self, category=None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if category:
            cur.execute("SELECT * FROM links WHERE category=? ORDER BY id DESC", (category,))
        else:
            cur.execute("SELECT * FROM links WHERE status='active' ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "url": r[2], "description": r[3],
                 "category": r[4], "created_at": r[5], "status": r[6]} for r in rows]

    def get_articles(self, category=None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if category:
            cur.execute("SELECT * FROM articles WHERE category=? ORDER BY id DESC", (category,))
        else:
            cur.execute("SELECT * FROM articles ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "content": r[2], "category": r[3],
                 "source_url": r[4], "created_at": r[5], "updated_at": r[6], "views": r[7]} for r in rows]

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        articles = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM links WHERE status='active'")
        links = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM articles WHERE views > 0")
        viewed_articles = cur.fetchone()[0]
        conn.close()
        return {"articles": articles, "links": links, "viewed_articles": viewed_articles}

    def add_known_sources(self):
        self.add_article(
            title="نظام ESPRIEAETHER - نظرة عامة",
            content="نظام ESPRIEAETHER هو نظام ذكاء اصطناعي محلي كامل التوليد يتكون من:"
            " • JARVIS (الرأس الذكاء الاصطناعي)"
            " • Agent OS (نظام الوكلاء المتعددين)"
            " • trade_cycle (دورة التداول الآلية)"
            " • self_heal_daemon (الإصلاح التلقائي)"
            " • Knowledge Base (مجموعة المعرفة والوثائق)"
            " • Telegram bot (المكالمات والمراسلات)",
            category="overview"
        )

        self.add_article(
            title="خوارزمية تداول النظام",
            content="نظام التداول يعمل على ثلاث مراحل رئيسية:"
            " 1. البحث (Research): جمع البيانات من CoinGecko"
            " 2. التحليل (Risk Decisions): تقييم المخاطر"
            " 3. التنفيذ (Trading): تنفيذ الصفقات"
            "الخوارزمية قابلة للتطوير والتحسين المستمر.",
            category="trading"
        )

        self.add_link(
            title="CoinGecko API",
            url="https://www.coingecko.com/api",
            description="بوابة البيانات المالية الرئيسية",
            category="research"
        )
        self.add_link(
            title="OKX API",
            url="https://www.okx.com/docs",
            description="مكتبة واجهة برمجة التطبيقات",
            category="trading"
        )
        self.add_link(
            title="GitHub - EsprieAether",
            url="https://github.com/007aether/esprieaether",
            description="مستودع المصدر",
            category="development"
        )
        self.add_link(
            title="Ollama - نماذج محلية",
            url="https://ollama.ai/",
            description="نماذج ذكاء اصطناعي محلية",
            category="ai"
        )
        self.add_link(
            title="Colibri Router",
            url="http://127.0.0.1:8000",
            description="خادم Qwen3-Coder-30B المحلي",
            category="ai"
        )
        self.add_link(
            title="AgenticSeek Documentation",
            url="https://github.com/007aether/esprieaether/tree/main/src/agenticseek",
            description="توثيق وكلاء الـ AgenticSeek",
            category="documentation"
        )
        self.add_link(
            title="Sunna Integration",
            url="https://github.com/007aether/esprieaether/tree/main/src/sunna_api.py",
            description="تكامل Sunna التجاري",
            category="integration"
        )
        stats = self.get_stats()
        print(f"   📚 KnowledgeBase: {stats['articles']} مقالات، {stats['links']} روابط")
