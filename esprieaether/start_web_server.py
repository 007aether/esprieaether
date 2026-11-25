import sys
import os

# Ensure src is in path BEFORE importing web_interface
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.web_interface import app

print("=== Starting fresh web server ===")
print("App routes:", [str(r) for r in app.url_map.iter_rules()])
host = os.getenv("WEB_HOST", "127.0.0.1")
port = int(os.getenv("WEB_PORT", "5000"))
app.run(host=host, port=port, debug=False, use_reloader=False)
