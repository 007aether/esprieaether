import socket

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
