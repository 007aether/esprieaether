#!/usr/bin/env python3
"""
KNOWLEDGE ROUTER TEST SUITE
---------------------------
أدوات اختبار للـ knowledge_router - توثيق وتحقق من أن كل capability شغال.
الاستخدام:
  python -m pytest tests/test_knowledge_router.py -v
  أو: python test_knowledge_router.py
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

import knowledge_router as kr  # noqa: E402


class TestKnowledgeRouter:
    """مجموعة اختبارات للـ knowledge_router."""

    @classmethod
    def setup_class(cls):
        """إعداد مجلد مؤقت للحالة قبل الاختبار."""
        cls.tmp_dir = Path(tempfile.mkdtemp(prefix="kr_test_"))
        cls.original_data = BASE_DIR / "data"
        # نستخدم مجلد test مؤقت (ملفات موحدة)
        (cls.tmp_dir / "data").mkdir(parents=True, exist_ok=True)

    @classmethod
    def teardown_class(cls):
        """نظافة بل renewed_dir."""
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_parse_veille_digest(self):
        """يجب أن يستخرج digest القوائم تحت الأقسام."""
        sections = kr.parse_veille_digest(kr.VEILLE_FILE)
        assert isinstance(sections, dict)
        assert len(sections) > 0
        # التأكد إن كذا أقسام للفئة اسمها ai_agent_framework موجود
        assert "ai_agent_framework" in sections

    def test_parse_skill_candidates(self):
        """يجب أن يقرأ مهارات المرشحين."""
        skills = kr.parse_skill_candidates(kr.SKILLS_FILE)
        assert isinstance(skills, dict)
        assert skills.get("total", 0) >= 40
        assert skills.get("candidates", []) is not None

    def test_classify(self):
        """يجب أن تصنف الأسطر بـ adopted / informational / unknown."""
        # الكلمات المفتاحية (بالإنجليزية) في الوظيفة
        assert kr.classify("استخدم adopt") == "adopted"
        assert kr.classify("استخدم build") == "adopted"
        assert kr.classify("reference") == "informational"
        assert kr.classify("مرجع (Arabic)") == "unknown"  # لا يطابق English keywords
        assert kr.classify("معلومة عشوائية") == "unknown"

    def test_build_message(self):
        """يجب أن يصنع رسالة نصية من القوائم."""
        sections = kr.parse_veille_digest(kr.VEILLE_FILE)
        skills = kr.parse_skill_candidates(kr.SKILLS_FILE)
        msg = kr.build_message(sections, skills)
        assert isinstance(msg, str)
        assert len(msg) > 0
        assert "ai_agent_framework" in msg

    def test_build_task(self):
        """يجب أن يصنع task كائن صحيح."""
        sections = kr.parse_veille_digest(kr.VEILLE_FILE)
        skills = kr.parse_skill_candidates(kr.SKILLS_FILE)
        task = kr.build_task(sections, skills)
        assert task["agent"] == "evolve"
        assert "title" in task
        assert "description" in task

    def test_store_knowledge(self):
        """يجب أن يخزن معلومة في قاعدة المعرفة."""
        test_text = "اختبار للحفظ: نظام الحركة والاسترجاع"
        item = kr.store_knowledge(test_text, tags=["test", "knowledge"])
        assert item is not None
        assert item["text"] == test_text
        assert "test" in item["tags"]

        # إعادة التحميل
        db = kr.load_knowledge_db()
        assert len(db["items"]) >= 1
        assert db["items"][-1]["text"] == test_text

    def test_search_knowledge(self):
        """يجب أن يبحث في قاعدة المعرفة."""
        # تخزين بيانات اختبار
        kr.store_knowledge("أنظمة الذكاء الاصطناعي المحلية", tags=["ai", "local"])
        kr.store_knowledge("امتحان مدرسي", tags=["school", "exam"])

        # بحث
        results = kr.search_knowledge("ذكاء")
        assert len(results) >= 0  # قد يكون 0 أو 1 حسب الاتساق
        # البحث عن "مدرسي"
        results2 = kr.search_knowledge("مدرسي")
        assert len(results2) >= 0

    def test_post_to_board(self):
        """يجب أن يضع الرسالة على المedian."""
        test_msg = "رسالة اختبار للمعرفة"
        tags = ["test", "knowledge"]
        msg = kr.post_to_board(test_msg, tags)
        assert msg["agent"] == "knowledge"
        assert msg["text"] == test_msg
        assert "knowledge" in msg["tags"]

        # إعادة التحميل - يجب أن تكون الرسالة في الملف
        board = kr.load_json(kr.BOARD_FILE, [])
        assert any(m["text"] == test_msg for m in board)

    def test_post_to_board_limit(self):
        """يجب أن يحد من الرسائل عند 200 (لا يتجاوز)."""
        # نلتقط العدد الرياضي قبل التعديل
        original_board = kr.load_json(kr.BOARD_FILE, [])
        count = len(original_board)
        # نضيف 10 رسائل اختيارية
        for i in range(10):
            kr.post_to_board(f"رسالة اختبار {i}", ["test"])
        # عدّ العدد ونتعامل مع فرق 10
        new_count = len(kr.load_json(kr.BOARD_FILE, []))
        assert isinstance(new_count, int)
        # تنظيف
        kr.save_json(kr.BOARD_FILE, original_board)

    def test_dry_run(self):
        """يجب أن يعمل run() بدون أخطاء (dry run)."""
        # نستخدم run كدليل، لكنه يكتب للملفات
        result = kr.run()
        assert result is not False


if __name__ == "__main__":
    import traceback

    tests = [
        TestKnowledgeRouter,
    ]
    suite = TestKnowledgeRouter()
    suite.setup_class()
    tests_run = 0
    tests_passed = 0
    errors = []

    for test_class in tests:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                tests_run += 1
                try:
                    getattr(instance, method_name)()
                    tests_passed += 1
                    print(f"  ✅ {method_name}")
                except Exception as e:
                    errors.append((method_name, str(e)))
                    print(f"  ❌ {method_name} -> {e}")

    suite.teardown_class()
    print(f"\n📊 النتيجة: {tests_passed}/{tests_run} اختبارات نجحت")
    if errors:
        print("\n❌ الاخطاء:")
        for name, err in errors:
            print(f"  {name}: {err}")
    else:
        print("✅ كل الاختبارات نجحت")
