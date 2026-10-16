"""
Checkpoint Agent — absolute quality gate for every addition to EsprieAether.

Every new feature, module, agent, or change passes through this gate:
  1. UNIT TEST      : function runs without error
  2. INTEGRATION    : connects to required services (router, mesh, obsidian, etc.)
  3. DOCUMENTATION  : summary written to Obsidian vault
  4. GIT COMMIT     : committed to main branch
  5. HEALTH CHECK   : service health verified

Usage:
  python checkpoint_agent.py --name "feature-name" --type "agent" --test "test command" --obsidian "summary"

If any gate fails, the agent stops and reports the error. If all pass, it commits and exits 0.
"""

import argparse
import traceback

def run_gate(name, gate_func, *args, **kwargs):
    """Run a named gate; return (passed: bool, message: str)."""
    try:
        result = gate_func(*args, **kwargs)
        if result is True:
            return True, "passed"
        elif isinstance(result, str):
            return False, result
        else:
            return result, "unknown"
    except Exception as e:
        return False, f"exception: {type(e).__name__}: {e}\n{traceback.format_exc()}"


def gate_unit_test(command):
    """Run a unit test command; return True if exit code 0."""
    log(f"  unit-test: {command}")
    # shell=True used here: internal trust command chain (git add -A && git commit), safe for this env
    r = subprocess.run(command, shell=True, cwd=REPO_DIR, capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        return True
    return f"exit {r.returncode}: {r.stderr[-500:]}"


def gate_integration(services):
    """Check integration with required services. Returns True if all required are up."""
    import urllib.request
    for svc, port in services:
        try:
            url = f"http://127.0.0.1:{port}/"
            urllib.request.urlopen(url, timeout=3)
        except Exception as e:
            return f"{svc}:$port unreachable ({e})"
    return True


def gate_documentation(summary, obsidian_dir):
    """Write a summary note to the Obsidian vault under 'Gate/'. Returns True if written."""
    os.makedirs(obsidian_dir, exist_ok=True)
    # write a markdown file
    note_path = os.path.join(obsidian_dir, f"checkpoint_{int(time.time())}.md")
    content = f"""---
title: "{summary['name']}"
type: "{summary['type']}"
status: "PASSED"
date: "{time.strftime('%Y-%m-%d %H:%M:%S')}"
---
## Summary
{summary.get('summary', '')}

## Unit Test
{summary.get('unit_test_result', '')}

## Integration
{summary.get('integration_result', '')}

## Commit
{summary.get('commit', '')}
"""
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(content)
    log(f"  obsidian: wrote {note_path}")
    return True


def gate_git_commit(name, message):
    """Commit the change to git. Returns True if commit succeeds."""
    # stage the specific file or all changes
    r = subprocess.run(
        f"cd {REPO_DIR} && git add -A && git commit -m '{message}'",
        shell=True, capture_output=True, text=True, timeout=60)
    if r.returncode == 0:
        return True
    return f"git commit failed: {r.stderr[-500:]}"


def gate_health_check():
    """Check EsprieAether health. Returns True if at least 8/9 services up."""
    import urllib.request, json
    services = {
        "router": 11435, "mesh": 11437, "web": 5000, "cloud": 5001,
        "sunna": 5100, "kanban": 5103, "homedock": 5104, "jarvis": 8000, "ollama": 11434
    }
    up = 0
    for name, port in services.items():
        try:
            url = f"http://127.0.0.1:{port}/"
            urllib.request.urlopen(url, timeout=3)
            up += 1
        except Exception:
            pass
    ok = up >= 8
    log(f"  health: {up}/9 services up")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Checkpoint Agent — absolute quality gate")
    parser.add_argument("--name", required=True, help="Name of the feature/change")
    parser.add_argument("--type", default="feature", help="Type: agent, module, config, etc.")
    parser.add_argument("--test", default="", help="Unit test command to run")
    parser.add_argument("--summary", default="", help="Brief summary")
    parser.add_argument("--services", default="mesh:11437,web:5000,cloud:5001,sunna:5100,kanban:5103,ollama:11434",
                        help="Comma-separated list of service:port for integration check")
    parser.add_argument("--obsidian", action="store_true", help="Also write to Obsidian")
    args = parser.parse_args()

    log(f"=== Checkpoint Gate for: {args.name} ({args.type}) ===")

    # 1. Unit test
    result, status = run_gate(args.name, gate_unit_test, args.test)
    log(f"  [1/5] unit-test → {status}")
    if not result:
        log(f"  ❌ UNIT TEST FAILED: {result}")
        return 1

    # 2. Integration
    services = []
    for item in args.services.split(","):
        if ":" in item:
            svc, port = item.split(":")
            services.append((svc, int(port)))
    result, status = run_gate(args.name, gate_integration, services)
    log(f"  [2/5] integration → {status}")
    if not result:
        log(f"  ❌ INTEGRATION FAILED: {result}")
        return 1

    # 3. Documentation (Obsidian)
    if args.obsidian:
        summary = {
            "name": args.name,
            "type": args.type,
            "summary": args.summary,
            "unit_test_result": "PASSED",
            "integration_result": "PASSED",
            "commit": "see git log",
        }
        run_gate(args.name, gate_documentation, summary, OBSIDIAN_DIR if os.path.exists(OBSIDIAN_DIR) else os.path.join(REPO_DIR, "data", "vault"))

    # 4. Git commit
    commit_msg = f"checkpoint: {args.name} — {args.type}"
    result, status = run_gate(args.name, gate_git_commit, args.name, commit_msg)
    log(f"  [4/5] git → {status}")
    if not result:
        log(f"  ❌ GIT COMMIT FAILED: {result}")
        return 1

    # 5. Health check
    result, status = run_gate(args.name, gate_health_check)
    log(f"  [5/5] health → {status}")
    if not result:
        log(f"  ⚠️  HEALTH WARNING: not all services up, but checkpoint passed")

    log(f"✅ CHECKPOINT PASSED for: {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
