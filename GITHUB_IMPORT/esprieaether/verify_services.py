# ESPRIEAETHER startup verification
# Python script to verify all services are online

import urllib.request

services = [
    ("JARVIS Web", "http://localhost:5000/"),
    ("Cloud Desktop (5001)", "http://localhost:5001/status"),
    ("Cloud Desktop (5173)", "http://localhost:5173/status"),
    ("Kanban (5103)", "http://localhost:5103/health"),
    ("Sunna Dashboard (5105)", "http://localhost:5105/health"),
    ("AI Router (11435)", "http://localhost:11435/health"),
    ("Orchestrator (11436)", "http://localhost:11436/health"),
    ("Agent Mesh (11437)", "http://localhost:11437/health"),
    ("Sunna API (5100)", "http://localhost:5100/health"),
]

all_ok = True
for name, url in services:
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        all_ok = False

print()
if all_ok:
    print("ALL SERVICES ONLINE")
else:
    print("SOME SERVICES DOWN")
