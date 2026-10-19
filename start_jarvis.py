#!/usr/bin/env python3
"""Start JARVIS OSINT backend on port 8000"""
import sys
import os

# Add the backend directory to path
backend_dir = r"C:\Users\ESPRIEAETHER\AppData\Local\Temp\JARVIS_repo\backend"
repo_dir = r"C:\Users\ESPRIEAETHER\AppData\Local\Temp\JARVIS_repo"

sys.path.insert(0, backend_dir)
sys.path.insert(0, repo_dir)

# Set environment variable for the Python executable
import subprocess
import time

print("Starting JARVIS API...")
print(f"Python: {sys.executable}")
print(f"Working dir: {os.getcwd()}")

# Run the main.py file
cmd = [
    sys.executable,
    r"C:\Users\ESPRIEAETHER\AppData\Local\Temp\JARVIS_repo\backend\main.py"
]

proc = subprocess.Popen(
    cmd,
    stdout=open(r"C:\Users\ESPRIEAETHER\Desktop\esprieaether\jarvis_output.log", "w"),
    stderr=subprocess.STDOUT,
    cwd=repo_dir
)

print(f"JARVIS started with PID: {proc.pid}")
time.sleep(10)

# Check if it's still running
if proc.poll() is None:
    print("JARVIS is running...")
    import urllib.request
    try:
        response = urllib.request.urlopen("http://localhost:8000/", timeout=5)
        print(f"HTTP Response: {response.status}")
    except Exception as e:
        print(f"Connection check: {e}")
else:
    print(f"JARVIS exited with code: {proc.returncode}")
    print("Check log file for details")

print("Done.")
