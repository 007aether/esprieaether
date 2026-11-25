#!/usr/bin/env python3
"""
KIT BUILDER - وحدة البناء المتكاملة (Complete Construction Kit)
--------------------------------------------------------------
هذه الوحدة تربط كل الـ deliverables من الدورة الشاملة في وحدة واحدة تعمل.

المكونات:
  1. Knowledge Router  ← روبوت ربط المعرفة
  2. Test Suite        ← اختبارات الربوت
  3. Skill Tracker     ← تتبيل مهارات الاعتماد
  4. Weekly Report     ← تقارير الأسبوع
  5. Knowledge Blueprint ← واجهة المعرفة (UI)
  6. Knowledge Interface ← واجهة المعرفة (API)

الاستخدام:
  python kit_builder.py run        # تشغيل الكل
  python kit_builder.py test       # تشغيل الاختبارات فقط
  python kit_builder.py link       # ربط المعرفة بالنظام
  python kit_builder.py report     # تقرير الأسبوع
  python kit_builder.py serve      # تشغيل الواجهة
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

# Colors
class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


class KitBuilder:
    """وحدة البناء المتكاملة."""

    def __init__(self):
        self.results = {}
        self.success_count = 0
        self.fail_count = 0

    def step(self, name):
        """طباعة خطوة."""
        print(f"\n{'═' * 60}")
        print(f"  {C.CYAN}▶ {name}{C.RESET}")
        print(f"{'═' * 60}")

    def ok(self, msg):
        print(f"  {C.GREEN}✅ {msg}{C.RESET}")

    def fail(self, msg):
        print(f"  {C.RED}❌ {msg}{C.RESET}")

    def warn(self, msg):
        print(f"  {C.YELLOW}⚠️  {msg}{C.RESET}")

    def run(self):
        """تشغيل وحدة البناء المتكاملة."""
        print(f"\n{'═' * 60}")
        print(f"  {C.MAGENTA}🚀 KIT BUILDER - وحدة البناء المتكاملة")
        print(f"  System: EsprieAether Agent-Network")
        print(f"{C.RESET}")

        # 1. Tests
        self.step("1. Test Suite")
        if self._run_tests():
            self.success_count += 1
        else:
            self.fail_count += 1

        # 2. Link Knowledge
        self.step("2. Link Knowledge")
        if self._run_link():
            self.success_count += 1
        else:
            self.fail_count += 1

        # 3. Track Skills
        self.step("3. Track Skills")
        if self._run_track():
            self.success_count += 1
        else:
            self.fail_count += 1

        # 4. Weekly Report
        self.step("4. Weekly Report")
        if self._run_report():
            self.success_count += 1
        else:
            self.fail_count += 1

        # 5. Knowledge Blueprint
        self.step("5. Knowledge Blueprint")
        if self._run_blueprint():
            self.success_count += 1
        else:
            self.fail_count += 1

        # 6. Knowledge Interface
        self.step("6. Knowledge Interface")
        if self._run_interface():
            self.success_count += 1
        else:
            self.fail_count += 1

        # Summary
        self.step("7. Summary")
        print(f"\n  {C.BLUE}📦 Tests passed: {self.success_count}/{self.success_count + self.fail_count}{C.RESET}")
        if self.fail_count > 0:
            print(f"  {C.RED}❌ Failed: {self.fail_count}{C.RESET}")
        else:
            print(f"  {C.GREEN}✅ All passed{C.RESET}")

        return self.fail_count == 0

    def _run_tests(self):
        """تشغيل الاختبارات."""
        import subprocess
        # BASE_DIR هو src/، فنتأكد من مسار الاختبار الصحيح
        test_script = str(BASE_DIR / "test_knowledge_router.py")
        result = subprocess.run(
            [sys.executable, test_script],
            cwd=BASE_DIR.parent, capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        if "10/10" in output:
            self.ok("All 10 tests passed")
            return True
        else:
            self.fail("Some tests failed")
            self.warn(output[:200])
            return False

    def _run_link(self):
        """ربط المعرفة بالنظام."""
        try:
            sys.path.insert(0, str(SRC_DIR))
            import knowledge_router as kr
            kr.run()
            self.ok("Knowledge linked to agent mesh")
            return True
        except Exception as e:
            self.fail(f"Link failed: {e}")
            return False

    def _run_track(self):
        """تتبيل المهارات."""
        try:
            sys.path.insert(0, str(SRC_DIR))
            import skill_tracker as st
            # للاشياء السريعة، نستخدم الدوال المباشرة
            skills = st.load_skills()
            if skills:
                self.ok(f"Loaded {len(skills)} skills")
                # نسجل واحدة كمثال
                st.track_skill(skills[0].get("name", "unknown"), "usage",
                              f"Linked via kit builder")
                self.ok("Skill tracked successfully")
                return True
            else:
                self.warn("No skills found")
                return False
        except Exception as e:
            self.fail(f"Track failed: {e}")
            return False

    def _run_report(self):
        """تقرير الأسبوع."""
        try:
            sys.path.insert(0, str(SRC_DIR))
            import weekly_report_robot as wrr
            wrr.generate_report()
            self.ok("Weekly report generated")
            return True
        except Exception as e:
            self.fail(f"Report failed: {e}")
            return False

    def _run_blueprint(self):
        """واجهة المعرفة."""
        try:
            sys.path.insert(0, str(SRC_DIR))
            import knowledge_blueprint as kb
            self.ok("Knowledge blueprint loaded")
            return True
        except Exception as e:
            self.fail(f"Blueprint failed: {e}")
            return False

    def _run_interface(self):
        """واجهة المعرفة API."""
        try:
            sys.path.insert(0, str(SRC_DIR))
            import knowledge_interface as ki
            self.ok("Knowledge API loaded")
            return True
        except Exception as e:
            self.fail(f"API failed: {e}")
            return False


def main():
    """النقطة الرئيسية."""
    import argparse
    parser = argparse.ArgumentParser(description="Kit Builder - Complete Construction Kit")
    parser.add_argument("action", choices=["run", "test", "link", "report"], nargs="?", default="run",
                        help="Action to perform: run (all), test, link, report (default: run)")
    args = parser.parse_args()

    kit = KitBuilder()

    if args.action == "test":
        kit._run_tests()
        kit._run_link()
        kit._run_track()
    elif args.action == "link":
        kit._run_link()
    elif args.action == "report":
        kit._run_report()
    else:
        kit.run()

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  {C.MAGENTA}📦 KIT BUILDER COMPLETE")
    print(f"  Tests: {kit.success_count}/{kit.success_count + kit.fail_count} passed")
    print(f"{C.RESET}")

    if kit.fail_count > 0:
        print(f"  {C.RED}❌ Some items failed. Check output above.{C.RESET}")
        return 1
    else:
        print(f"  {C.GREEN}✅ All items completed successfully{C.RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
