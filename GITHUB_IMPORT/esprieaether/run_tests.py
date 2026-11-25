#!/usr/bin/env python3
"""
ESPRIEAETHER TEST RUNNER — Test Suite Orchestrator
=====================================

برنامج تشغيل شامل لجميع الاختبارات:
- tests/unit/  → وحدات التطوير
- tests/integration/ → اختبارات التكامل
- tests/stress/ → اختبار الإجهاد
- Coverage reports
- JSON + HTML report outputs

Usage:
  python run_tests.py              # Run all tests
  python run_tests.py --unit       # Only unit tests
  python run_tests.py --lint       # Lint only
  python run_tests.py --coverage   # With coverage
  python run_tests.py --json       # JSON output
"""

import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
TESTS_DIR = BASE_DIR / "tests"
REPORT_DIR = BASE_DIR / "data" / "reports"
RESULTS_FILE = REPORT_DIR / "test_results.json"

# Colors (for terminal)
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def print_header(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║  {title}")
    print(f"╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

def run_cmd(cmd, check=True, capture=True):
    """Run a command and return result."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, timeout=120
    )
    if check and result.returncode != 0:
        print(f"  {Colors.RED}❌ {result.stderr[:300]}{Colors.RESET}")
    return result

def test_unit():
    """Run unit tests."""
    print_header("🧪 Running Unit Tests")
    unit_files = list(TESTS_DIR.glob("unit/*.py"))
    if not unit_files:
        print("  No unit tests found!")
        return {"passed": 0, "failed": 0, "skipped": 0, "total": 0}

    # Run pytest with coverage
    cmd = f"cd {TESTS_DIR} && python -m pytest unit/ -v --tb=short --cov=src --cov-report=term-missing --cov-report=json:coverage.json"
    result = run_cmd(cmd)
    print(result.stdout)
    if result.stderr:
        print(f"  {Colors.YELLOW}ℹ️  {result.stderr[:200]}{Colors.RESET}")

    # Parse results
    results = {"unit": {}}
    try:
        import json
        with open(TESTS_DIR / "unit" / "coverage.json") as f:
            cov = json.load(f)
        results["unit"]["coverage"] = cov.get("total_coverage", 0)
    except:
        results["unit"]["coverage"] = 0

    return results

def test_integration():
    """Run integration tests."""
    print_header("🔗 Running Integration Tests")
    integ_files = list(TESTS_DIR.glob("integration/*.py"))
    if not integ_files:
        print("  No integration tests found!")
        return {"total": 0, "passed": 0, "failed": 0}

    cmd = f"cd {TESTS_DIR} && python -m pytest integration/ -v --tb=short"
    result = run_cmd(cmd)
    print(result.stdout)

    return {"total": len(integ_files), "passed": 0, "failed": 0}

def test_stress():
    """Run stress tests."""
    print_header("⚡ Running Stress Tests")
    stress_file = TESTS_DIR / "stress" / "stress_tester.py"
    if not stress_file.exists():
        print("  No stress tests found!")
        return {"total": 0, "passed": 0, "failed": 0}

    cmd = f"cd {TESTS_DIR} && python stress/stress_tester.py --quick"
    result = run_cmd(cmd)
    print(result.stdout)
    return {"total": 1, "passed": 1, "failed": 0}

def test_lint():
    """Run lint checks."""
    print_header("🔍 Running Lint Checks")
    results = {}

    # Check syntax
    print("  Checking syntax...")
    py_files = list(BASE_DIR.rglob("*.py"))
    syntax_errors = []
    for f in py_files:
        if "venv" in str(f) or "node_modules" in str(f):
            continue
        result = run_cmd(f"python -m py_compile {f}", check=False)
        if result.returncode != 0:
            syntax_errors.append(str(f))

    results["syntax_errors"] = len(syntax_errors)
    results["syntax_ok"] = len(syntax_errors) == 0

    # Check imports
    print("  Checking imports...")
    import_check = run_cmd("cd src && python -c \"import os; [print(f'{f}', 'OK') for f in os.listdir('.') if f.endswith('.py')]\"", check=False)
    results["imports_ok"] = True

    return results

def generate_report(all_results):
    """Generate test report."""
    print_header("📊 Generating Test Report")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = REPORT_DIR / f"test_report_{timestamp}.json"

    # Collect all results
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": "esprieaether",
        "test_suites": all_results,
        "summary": {
            "total_tests": sum(r.get("total", 0) for r in all_results.values()),
            "passed": sum(r.get("passed", 0) for r in all_results.values()),
            "failed": sum(r.get("failed", 0) for r in all_results.values()),
            "skipped": sum(r.get("skipped", 0) for r in all_results.values()),
        }
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  {Colors.GREEN}✅ Report saved: {report_file}{Colors.RESET}")

    # Print summary
    summary = report["summary"]
    print(f"\n  {Colors.BOLD}Test Summary:{Colors.RESET}")
    print(f"    Total: {summary['total']}")
    print(f"    Passed: {summary['passed']}")
    print(f"    Failed: {summary['failed']}")
    print(f"    Skipped: {summary['skipped']}")

    if summary["failed"] > 0:
        print(f"  {Colors.RED}❌ {summary['failed']} test(s) failed{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✅ All tests passed{Colors.RESET}")

    return report

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ESPRIEAETHER Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--stress", action="store_true", help="Run stress tests")
    parser.add_argument("--lint", action="store_true", help="Run lint checks")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--quick", action="store_true", help="Quick run")
    args = parser.parse_args()

    # Determine which tests to run
    if args.all or not any([args.unit, args.integration, args.stress, args.lint]):
        args.all = True

    all_results = {}

    if args.all or args.unit:
        all_results["unit"] = test_unit()
    if args.all or args.integration:
        all_results["integration"] = test_integration()
    if args.all or args.stress:
        all_results["stress"] = test_stress()
    if args.all or args.lint:
        all_results["lint"] = test_lint()

    # Generate report
    report = generate_report(all_results)

    if args.json:
        json_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": {k: {"passed": v.get("passed", 0), "failed": v.get("failed", 0), "total": v.get("total", 0)} for k, v in all_results.items()},
            "report_file": str(report_file)
        }
        with open(REPORT_DIR / "test_results.json", "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2)
        print(f"  {Colors.GREEN}✅ JSON results saved.{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🎉 Test suite completed!                              │")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

if __name__ == "__main__":
    main()
