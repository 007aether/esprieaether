import sys
from pathlib import Path
from flask import Flask, request, jsonify
sys.path.insert(0, str(Path(__file__).parent.parent))
from inference_router import ask

app = Flask(__name__)
API_KEYS = {"test_key_123": {"plan": "basic", "quota": 100, "used": 0}}

@app.route("/api/v1/task", methods=["POST"])
def run_task():
    api_key = request.headers.get("X-API-Key")
    client = API_KEYS.get(api_key)
    if not client:
        return jsonify({"error": "مفتاح غير صحيح"}), 401
    if client["used"] >= client["quota"]:
        return jsonify({"error": "الحصة انتهت"}), 429
    data = request.json or {}
    task = data.get("task")
    if not task:
        return jsonify({"error": "لا توجد مهمة"}), 400
    result = ask(task)
    client["used"] += 1
    return jsonify({"result": result, "used": client["used"], "total": client["quota"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
