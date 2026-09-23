from flask import Flask, render_template_string, jsonify, request
import psutil
import sqlite3
from pathlib import Path
from jarvis_bridge import query_open_jarvis
from security_agent import activate_stealth_and_defense
from airdrop_farmer import execute_farming_cycle

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>EsprieAether - Jarvis Web Command Center</title>
    <style>
        body { background-color: #030712; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 20px; }
        h1 { text-align: center; text-shadow: 0 0 15px #00ffcc; font-size: 28px; }
        .container { display: flex; gap: 20px; margin-top: 20px; flex-wrap: wrap; }
        .panel { background: #0f172a; border: 1px solid #00ffcc; padding: 20px; border-radius: 12px; flex: 1; min-width: 300px; box-shadow: 0 0 20px rgba(0,255,204,0.15); }
        .chat-box { height: 350px; overflow-y: scroll; border: 1px solid #1e293b; padding: 15px; background: #020617; border-radius: 8px; margin-bottom: 15px; font-size: 14px; line-height: 1.6; }
        .chat-input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 12px; background: #020617; border: 1px solid #00ffcc; color: #fff; border-radius: 6px; font-family: monospace; }
        button { padding: 12px 20px; background: #00ffcc; color: #030712; border: none; font-weight: bold; border-radius: 6px; cursor: pointer; transition: 0.3s; }
        button:hover { background: #00b388; box-shadow: 0 0 10px #00ffcc; }
        .metric { font-size: 16px; margin: 15px 0; padding: 10px; background: #020617; border-right: 4px solid #00ffcc; border-radius: 4px; }
        .badge { display: inline-block; padding: 4px 8px; background: #065f46; color: #34d399; border-radius: 4px; font-size: 12px; }
        .quick-actions { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        .quick-btn { padding: 8px 12px; background: #1e293b; color: #00ffcc; border: 1px solid #00ffcc; border-radius: 4px; cursor: pointer; font-size: 12px; }
        .quick-btn:hover { background: #00ffcc; color: #030712; }
    </style>
</head>
<body>
    <h1>⚡ ESPRIEAETHER - JARVIS COMMAND CENTER ⚡</h1>
    <div class="container">
        <!-- لوحة التحكم الحية -->
        <div class="panel">
            <h2>📊 مراقبة النظام والدرع الأمني</h2>
            <div class="metric" id="cpu">CPU Usage: جاري التحميل...</div>
            <div class="metric" id="ram">RAM Usage: جاري التحميل...</div>
            <div class="metric">الهوية النشطة: <code>007aether@gmail.com</code></div>
            <div class="metric">حالة الأمان: <span class="badge">🟢 مخفي ومحمي (Stealth Mode)</span></div>
            <div class="metric">الخدمة الخلفية: <span class="badge">🟢 تعمل 24/24</span></div>
            
            <h3 style="margin-top: 25px;">⚡ إجراءات سريعة</h3>
            <div class="quick-actions">
                <button class="quick-btn" onclick="triggerAction('farm')">🪂 صيد الأيردروبات</button>
                <button class="quick-btn" onclick="triggerAction('security')">🛡️ فحص الأمان</button>
                <button class="quick-btn" onclick="triggerAction('status')">📊 تحديث الحالة</button>
            </div>
        </div>

        <!-- نافذة الدردشة مع Jarvis -->
        <div class="panel" style="flex: 2;">
            <h2>💬 محادثة Jarvis المباشرة</h2>
            <div class="chat-box" id="chatHistory">
                <div><strong>EsprieAether Jarvis:</strong> أهلاً بك يا سيدي. أنا جاهز، مدمج مع محرك OpenJarvis، وأدير قلعتك السيبرانية 24/24. كيف أساعدك اليوم؟</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="userInput" placeholder="اطرح سؤالك أو أمرك على Jarvis..." onkeydown="if(event.key==='Enter') sendMsg()">
                <button onclick="sendMsg()">إرسال</button>
            </div>
        </div>
    </div>

    <script>
        function updateMetrics() {
            fetch('/metrics')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('cpu').innerText = 'CPU Usage: ' + data.cpu + '%';
                    document.getElementById('ram').innerText = 'RAM Usage: ' + data.ram + '%';
                });
        }
        setInterval(updateMetrics, 3000);

        function sendMsg() {
            let input = document.getElementById('userInput');
            let chat = document.getElementById('chatHistory');
            let txt = input.value.trim();
            if(!txt) return;

            chat.innerHTML += `<div style="margin: 8px 0;"><strong>أنت:</strong> ${txt}</div>`;
            input.value = '';
            chat.scrollTop = chat.scrollHeight;

            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: txt})
            })
            .then(res => res.json())
            .then(data => {
                chat.innerHTML += `<div style="margin: 8px 0; color: #34d399;"><strong>Jarvis:</strong> ${data.reply}</div>`;
                chat.scrollTop = chat.scrollHeight;
            });
        }

        function triggerAction(action) {
            let chat = document.getElementById('chatHistory');
            chat.innerHTML += `<div style="margin: 8px 0; color: #fbbf24;"><strong>[نظام]:</strong> جاري تنفيذ أمر (${action})...</div>`;
            
            fetch('/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action})
            })
            .then(res => res.json())
            .then(data => {
                chat.innerHTML += `<div style="margin: 8px 0; color: #34d399;"><strong>Jarvis:</strong> ${data.result}</div>`;
                chat.scrollTop = chat.scrollHeight;
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/metrics')
def metrics():
    return jsonify({
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    msg = data.get('message', '')
    reply = query_open_jarvis(msg)
    return jsonify({"reply": reply})

@app.route('/action', methods=['POST'])
def action():
    data = request.json
    act = data.get('action', '')
    
    if act == 'farm':
        res = execute_farming_cycle()
    elif act == 'security':
        res = activate_stealth_and_defense()
    else:
        res = f"النظام يعمل بكفاءة تامة. استهلاك المعالج: {psutil.cpu_percent()}%"
        
    return jsonify({"result": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
