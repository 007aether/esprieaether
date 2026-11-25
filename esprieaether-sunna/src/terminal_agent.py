"""Terminal agent — run shell commands from Telegram."""
import subprocess, shlex, os, platform
from pathlib import Path

# whitelist: only allow safe prefixes
SAFE_PREFIXES = (
    "ls", "dir", "cat", "head", "tail", "echo", "pwd", "whoami", "date",
    "uptime", "df", "free", "ps", "top", "env", "git status", "git log",
    "git diff", "curl", "ping", "nslookup", "dig", "hostname", "uname",
    "python --version", "node --version", "ollama list", "ollama ps",
)

MAX_OUTPUT = 2000  # chars

def _safe(command: str) -> bool:
    """Only allow whitelisted safe commands."""
    cmd = command.strip().lower()
    return any(cmd.startswith(p) for p in SAFE_PREFIXES)

def run_command(command: str, timeout: int = 30) -> dict:
    """Run a whitelisted shell command."""
    if not _safe(command):
        return {
            "ok": False,
            "error": "Command not allowed",
            "stdout": f"Whitelist: {', '.join(SAFE_PREFIXES[:5])}...",
        }

    try:
        # run in project root
        cwd = str(Path(__file__).parent.parent)
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        # truncate
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + "\n... (truncated)"
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": out,
            "stderr": err,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1:
        r = run_command(" ".join(sys.argv[1:]))
        print(json.dumps(r, ensure_ascii=False, indent=2))
