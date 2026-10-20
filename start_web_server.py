import sys
import os

# Ensure src is in path BEFORE importing web_interface
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.web_interface import app

print("=== Starting fresh web server ===")
print("App routes:", [str(r) for r in app.url_map.iter_rules()])
app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
