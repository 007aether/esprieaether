import os
from pathlib import Path

def generate_custom_tool(tool_type="security_scanner"):
    lab_dir = Path("src/lab")
    lab_dir.mkdir(parents=True, exist_ok=True)
    
    if tool_type == "security_scanner":
        tool_code = """import socket

def scan_local_ports():
    print("[+] 🛡️ [Lab Tool] Running local security port scan...")
    ports = [22, 80, 443, 8080]
    results = {}
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        res = s.connect_ex(('127.0.0.1', port))
        results[port] = "Open" if res == 0 else "Closed/Filtered"
        s.close()
    print(f"[+] Scan Results: {results}")
    return results

if __name__ == '__main__':
    scan_local_ports()
"""
        filename = lab_dir / "port_scanner_utility.py"
        with open(filename, "w") as f:
            f.write(tool_code)
        return f"تم ابتكر أداة فحص المنافذ الجديدة بنجاح في: {filename}"
    
    return "نوع الأداة غير معروف"

if __name__ == "__main__":
    print(generate_custom_tool("security_scanner"))
