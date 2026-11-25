"""Password vault — encrypted secrets storage (Fernet)."""
import os, json, base64
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# vault file location
VAULT_DIR = os.path.join(str(Path(__file__).parent.parent.parent), "ESPRIEAETHER", "data")
VAULT_FILE = os.path.join(VAULT_DIR, "vault.json")
KEY_FILE = os.path.join(VAULT_DIR, "vault.key")

def _get_key() -> bytes:
    """Get or create encryption key (32 url-safe base64 bytes)."""
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography not installed (uv pip install cryptography)")
    os.makedirs(VAULT_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    # generate new key (Fernet key = 32 url-safe base64 bytes)
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def _crypt():
    return Fernet(_get_key())

def _load() -> dict:
    if not os.path.exists(VAULT_FILE):
        return {}
    with open(VAULT_FILE, "r") as f:
        return json.load(f)

def _save(data: dict):
    with open(VAULT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def store(name: str, value: str) -> dict:
    """Encrypt and store a secret."""
    try:
        f = _crypt()
        token = f.encrypt(value.encode()).decode()
        data = _load()
        data[name] = token
        _save(data)
        return {"ok": True, "stored": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def retrieve(name: str) -> dict:
    """Decrypt and retrieve a secret."""
    try:
        data = _load()
        if name not in data:
            return {"ok": False, "error": "Not found"}
        f = _crypt()
        value = f.decrypt(data[name].encode()).decode()
        return {"ok": True, "name": name, "value": value}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def list_secrets() -> dict:
    """List stored secret names (not values)."""
    data = _load()
    return {"ok": True, "count": len(data), "names": list(data.keys())}

def delete_secret(name: str) -> dict:
    data = _load()
    if name in data:
        del data[name]
        _save(data)
        return {"ok": True, "deleted": name}
    return {"ok": False, "error": "Not found"}

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "store" and len(sys.argv) > 3:
        r = store(sys.argv[2], sys.argv[3])
    elif action == "get" and len(sys.argv) > 2:
        r = retrieve(sys.argv[2])
    elif action == "delete" and len(sys.argv) > 2:
        r = delete_secret(sys.argv[2])
    else:
        r = list_secrets()
    print(json.dumps(r, ensure_ascii=False, indent=2))
