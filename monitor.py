import psutil
import time
import sqlite3

# إعداد قاعدة البيانات لتخزين البيانات
conn = sqlite3.connect('system_monitor.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS metrics (
        timestamp DATETIME,
        cpu_percent REAL,
        memory_percent REAL
    )
''')
conn.commit()

try:
    while True:
        # جلب بيانات حقيقية من النظام
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # تخزين البيانات في قاعدة البيانات
        cursor.execute('INSERT INTO metrics VALUES (?, ?, ?)', (timestamp, cpu, memory))
        conn.commit()

        print(f"[{timestamp}] CPU: {cpu}% | RAM: {memory}%")

        # انتظار 10 ثواني قبل القراءة القادمة
        time.sleep(10)

except KeyboardInterrupt:
    print("تم إيقاف المراقبة.")
    conn.close()
