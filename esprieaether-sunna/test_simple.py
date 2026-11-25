
from flask import Flask
app = Flask(__name__)
@app.route('/')
def index():
    return 'Hello World'
@app.route('/executor')
def executor():
    return 'EXECUTOR PAGE'
@app.route('/api/executor')
def api_executor():
    return {'status': 'ok'}
@app.route('/health')
def health():
    return 'OK'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
