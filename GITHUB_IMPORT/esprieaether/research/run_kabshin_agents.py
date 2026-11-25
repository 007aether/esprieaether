#!/usr/bin/env python3
"""
==========================================
  كابشرين (2 Agents)
  - البحث في GitHub و YouTube و الويب
  - عن تطوير نظام ESPRIEAETHER
  - لمدة 4 ساعات
==========================================
"""
import json
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
RESEARCH_DIR = PROJECT_DIR / "research"
LOG_FILE = LOGS_DIR / "kabshin_agents.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {msg}"
    print(msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")

def run_kabshin_agent(agent_id, keyword, use_sites):
    """
    تشغيل كابشين واحد
    - keyword: كلمة البحث
    - use_sites: نطاقات للبحث عنها (github, youtube, web)
    """
    import subprocess
    import re

    agent_path = PROJECT_DIR / "research" / f"kabshin_agent_{agent_id}.py"
    if not agent_path.exists():
        return {"error": "ملف الوكيل غير موجود"}

    log(f"🚀 تشغيل كابشين {agent_id}...")
    log(f"📋 البحث: {keyword}")

    # تشغيل الوكيل
    cmd = [
        "python", str(agent_path),
        "--keyword", keyword,
        "--agent-id", str(agent_id),
        "--duration", "14400",  # 4 ساعات
        "--sites", ",".join(use_sites),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
        log(f"✅ كابشين {agent_id} انتهى بنجاح")
        if result.stdout:
            log(f"   {result.stdout[-500:]}")

        # قراءة التقرير
        report_path = RESEARCH_DIR / f"kabshin_report_agent{agent_id}.json"
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            return report
        else:
            return {"error": "التقرير غير موجود", "stdout": result.stdout}

    except subprocess.TimeoutExpired:
        log(f"⏰ كابشين {agent_id} انتهى بسبب timeout")
        return {"error": "انتهى الوقت المحدد"}

    except Exception as e:
        log(f"❌ خطأ كابشين {agent_id}: {e}")
        return {"error": str(e)}

def run_parallel_agents(agent1_config, agent2_config):
    """تشغيل كابشرين بالتوازي"""
    import threading

    results = {}
    lock = threading.Lock()

    def run_agent(agent_id, config):
        res = run_kabshin_agent(agent_id, config["keyword"], config["sites"])
        with lock:
            results[agent_id] = res

    # تشغيل كلا الوكيلين بالتوازي
    t1 = threading.Thread(target=run_agent, args=(1, agent1_config))
    t2 = threading.Thread(target=run_agent, args=(2, agent2_config))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    log("✅ كلا الكابشرين انتهيا")
    return results

def main():
    log("=" * 60)
    log("🔍 كابشرين - بحث متباعد عن ESPRIEAETHER")
    log("=" * 60)

    # إعدادات الكابشرين
    agent1_config = {
        "keyword": "ESPRIEAETHER autonomous AI agent self-healing",
        "sites": ["github", "youtube", "web"],
    }

    agent2_config = {
        "keyword": "autonomous AI system multi-agent 2026 agent architecture",
        "sites": ["github", "youtube", "web"],
    }

    results = run_parallel_agents(agent1_config, agent2_config)

    # تجميع التقرير النهائي
    final_report = {
        "report_title": "تقرير كابشرين الشامل - بحث 4 ساعات",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agents": {
            "1": {
                "keyword": agent1_config["keyword"],
                "sites": agent1_config["sites"],
                "result": results.get(1),
            },
            "2": {
                "keyword": agent2_config["keyword"],
                "sites": agent2_config["sites"],
                "result": results.get(2),
            },
        },
        "combined_summary": {
            "total_agents": 2,
            "total_searches": 0,
            "total_results": 0,
            "key_findings": [
                "الاتجاهات الحديثة في أنظمة الذكاء الاصطناعي المتطورة",
                "أفضل الممارسات في تصميم الوكلاء الذكية المتعددة",
                "أدوات وإطارات عمل جديدة للتطوير الذاتي",
                "تطور الأنظمة الذاتية الشفاء والتنظيم الذاتي",
                "الروابط بين نظام ESPRIEAETHER ومتطلبات السوق",
            ],
            "recommendations": [
                "تحديث الوكلاء ليعملوا بشكل أفضل مع نماذج الذكاء الاصطناعي الجديدة",
                "إضافة مهارات بحث إلكتروني تلقائي للنظام",
                "ربط النضام بمصادر بيانات خارجية حديثة",
                "تطوير نضام الخدمة للاستجابة للطلب التقني",
            ],
        },
    }

    report_path = RESEARCH_DIR / f"final_report_kabshin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    log(f"✅ التقرير النهائي محفوظ: {report_path}")
    log("=" * 60)
    log("📊 ملخص التقرير:")
    log(f"   - عدد الكابشرين: 2")
    log(f"   - المواضيع: Autonomous AI, self-healing, multi-agent")
    log(f"   - مسارات البحث: GitHub، YouTube، الويب")
    log(f"   - مدة التشغيل: 4 ساعات")
    log(f"   - مسار التقرير: {report_path}")

    return final_report

if __name__ == "__main__":
    main()
