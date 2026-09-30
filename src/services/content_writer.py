import sys
from pathlib import Path
from flask import Flask, request, jsonify
sys.path.insert(0, str(Path(__file__).parent.parent))
from inference_router import ask

app = Flask(__name__)

SERVICES = {
    "article": {"price": 20, "words": 1000},
    "blog_post": {"price": 10, "words": 500},
    "product_review": {"price": 15, "words": 800},
}

@app.route("/api/content/write", methods=["POST"])
def write_content():
    data = request.json or {}
    topic = data.get("topic")
    if not topic:
        return jsonify({"error": "الموضوع مطلوب"}), 400
    service_type = data.get("type", "article")
    spec = SERVICES.get(service_type, SERVICES["article"])
    prompt = f"اكتب {service_type} احترافي عن: {topic}\nالطول: {spec['words']} كلمة"
    content = ask(prompt)
    return jsonify({"content": content, "words": len(content.split()), "price": spec["price"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
