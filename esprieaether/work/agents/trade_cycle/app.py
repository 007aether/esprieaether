from flask import Flask, jsonify, send_file
import sqlite3

app = Flask(__name__)

@app.route('/api/status')
def status():
    conn = sqlite3.connect('work/data/trade_cycle.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cycle_runs')
    cycle_runs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM research WHERE source='coingecko'")
    research = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM feedback')
    feedback = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM trades')
    trades = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(SUM(pnl), 0) FROM ledger')
    ledger_total = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(pnl) FROM trades')
    profit_total = cur.fetchone()[0] or 0
    conn.close()
    return jsonify({
        'cycle_runs': cycle_runs,
        'research': research,
        'feedback': feedback,
        'trades': trades,
        'ledger_total': ledger_total,
        'profit_total': profit_total
    })

@app.route('/api/trades')
def trades_api():
    conn = sqlite3.connect('work/data/trade_cycle.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT symbol, side, size, price, pnl, status, created_at FROM trades ORDER BY id DESC LIMIT 20')
    rows = cur.fetchall()
    conn.close()
    return jsonify({'trades': [dict(r) for r in rows]})

@app.route('/')
def index():
    return send_file('realtime_status.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
