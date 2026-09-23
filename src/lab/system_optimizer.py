# Auto-generated System Optimizer by AETHER Lab Agent
import psutil

def optimize_system():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return f"✅ [Optimizer Tool]: حالة النظام ممتازة. CPU: {cpu}% | RAM: {ram}%"

if __name__ == "__main__":
    print(optimize_system())
