#!/usr/bin/env python3
"""ESPRIEAETHER v1.0"""

import os, sys
from datetime import datetime
from colorama import Fore, Style, init

BASE = os.path.expanduser("~/ESPRIEAETHER")
sys.path.insert(0, BASE)

import ollama
from kanban.kanban_engine import KanbanEngine
from code.cloud_code import CloudCode

init(autoreset=True)
MODEL = "hermes3:latest"

kanban = KanbanEngine()
cc = CloudCode()


def banner():
    print(Fore.CYAN + "=" * 70)
    print(Fore.CYAN + "  🛡️  ESPRIEAETHER v1.0")
    print(Fore.CYAN + "  🧠  Hermes 3 + Super Kanban + Cloud Code")
    print(Fore.CYAN + "=" * 70)
    print(Fore.YELLOW + "  📋 KANBAN:  board | add <task> | run <id>")
    print(Fore.YELLOW + "  💻 CODE:    code <prompt> | cat <file> | ls | exec <file>")
    print(Fore.YELLOW + "  ⚙️  SYSTEM:  agents | status | clear | exit")
    print(Fore.CYAN + "=" * 70 + "\n")


def chat(prompt):
    try:
        start = datetime.now()
        r = ollama.chat(model=MODEL, messages=[
            {"role": "system", "content": "You are ESPRIEAETHER. JARVIS-style, helpful."},
            {"role": "user", "content": prompt}
        ])
        return r['message']['content'], (datetime.now() - start).total_seconds()
    except Exception as e:
        return f"Error: {e}", 0


def main():
    banner()
    while True:
        try:
            ui = input(Fore.GREEN + "ESPRIEAETHER > " + Style.RESET_ALL).strip()
            if not ui:
                continue
            cmd = ui.lower()
            if cmd in ['exit', 'quit', 'q']:
                print(Fore.CYAN + "\n👋 Bye.\n"); break
            if cmd == "clear":
                os.system("clear"); banner(); continue
            if cmd == "board":
                kanban.print_board(); continue
            if cmd.startswith("add "):
                tid = kanban.add_task(ui[4:].strip())
                print(Fore.GREEN + f"✅ Task [{tid}] added\n"); continue
            if cmd.startswith("run "):
                try:
                    tid = int(ui[4:].strip())
                    task = kanban.get_task(tid)
                    if task:
                        kanban.move_task(tid, "doing")
                        print(f"🚀 Running: {task[3]}")
                        r, t = chat(task[3])
                        kanban.complete_task(tid, r)
                        print(Fore.GREEN + f"✅ Done in {t:.2f}s\n")
                    else:
                        print(Fore.RED + f"❌ Task {tid} not found\n")
                except ValueError:
                    print(Fore.RED + "Usage: run <id>\n")
                continue
            if cmd.startswith("code "):
                code = cc.generate_code(ui[5:].strip())
                if code:
                    print(Fore.CYAN + "\n" + code + "\n")
                continue
            if cmd == "ls":
                for f, s in cc.list_files():
                    print(Fore.WHITE + f"  • {f} ({s} bytes)")
                print(); continue
            if cmd.startswith("cat "):
                c = cc.read_file(ui[4:].strip())
                print(Fore.WHITE + (c if c else "❌ Not found") + "\n"); continue
            if cmd.startswith("exec "):
                r = cc.execute(ui[5:].strip())
                if "error" in r:
                    print(Fore.RED + f"❌ {r['error']}\n")
                else:
                    print(Fore.CYAN + f"📤 {r.get('stdout', '')}")
                    if r.get('stderr'):
                        print(Fore.RED + f"📥 {r['stderr']}")
                    print(Fore.WHITE + f"🚪 Exit: {r.get('exit_code')}\n")
                continue
            if cmd == "agents":
                print(Fore.CYAN + "\n🤖 Agents:\n")
                for a in kanban.list_agents():
                    print(Fore.GREEN + f"  • {a[1]} [{a[2]}] — {a[3]}\n")
                continue
            if cmd == "status":
                todo = len(kanban.list_tasks("todo"))
                doing = len(kanban.list_tasks("doing"))
                done = len(kanban.list_tasks("done"))
                print(Fore.CYAN + f"\n📊 Tasks: TODO:{todo} DOING:{doing} DONE:{done}\n")
                continue
            print(Fore.YELLOW + "⏳ Thinking...\n")
            r, t = chat(ui)
            print(Fore.CYAN + "🤖 ESPRIEAETHER:")
            print(Fore.WHITE + r)
            print(Fore.WHITE + f"\n⏱️  {t:.2f}s\n" + "-" * 70 + "\n")
        except KeyboardInterrupt:
            print(Fore.CYAN + "\n\n👋 Interrupted.\n"); break
        except Exception as e:
            print(Fore.RED + f"❌ {e}\n")


if __name__ == "__main__":
    main()

# ============ FUSION COMMANDS ============
# Add at top of file:
# from robots.robots_system import RobotsSystem
# from scanners.security_scanner import SecurityScanner

# Add in main loop:
# if cmd == "robots":
#     robots = RobotsSystem()
#     robots.print_robots()
#     continue
# if cmd == "scan":
#     scanner = SecurityScanner()
#     scanner.scan_directory()
#     continue
