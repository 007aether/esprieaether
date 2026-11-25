"""File manager — list/read/write/delete files from Telegram."""
import os, shutil, mimetypes
from pathlib import Path

# root = project dir
ROOT = str(Path(__file__).parent.parent)

def _safe_path(p: str) -> bool:
    """Prevent path traversal outside ROOT."""
    target = os.path.normpath(os.path.join(ROOT, p.lstrip("/")))
    return target.startswith(ROOT)

def list_dir(path: str = ".") -> dict:
    """List directory contents."""
    if not _safe_path(path):
        return {"ok": False, "error": "Path outside project root"}
    target = os.path.join(ROOT, path.lstrip("/"))
    if not os.path.isdir(target):
        return {"ok": False, "error": "Not a directory"}
    items = []
    for name in sorted(os.listdir(target)):
        full = os.path.join(target, name)
        is_dir = os.path.isdir(full)
        try:
            size = 0 if is_dir else os.path.getsize(full)
        except OSError:
            size = 0
        items.append({"name": name, "type": "dir" if is_dir else "file", "size": size})
    return {"ok": True, "path": path, "items": items}

def read_file(path: str, max_chars: int = 3000) -> dict:
    """Read a text file (truncated)."""
    if not _safe_path(path):
        return {"ok": False, "error": "Path outside project root"}
    target = os.path.join(ROOT, path.lstrip("/"))
    if not os.path.isfile(target):
        return {"ok": False, "error": "Not a file"}
    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        truncated = os.path.getsize(target) > max_chars
        return {
            "ok": True, "path": path, "content": content,
            "size": os.path.getsize(target), "truncated": truncated,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def write_file(path: str, content: str) -> dict:
    """Write text content to a file."""
    if not _safe_path(path):
        return {"ok": False, "error": "Path outside project root"}
    target = os.path.join(ROOT, path.lstrip("/"))
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path, "bytes": len(content)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def delete_file(path: str) -> dict:
    """Delete a file (not a directory)."""
    if not _safe_path(path):
        return {"ok": False, "error": "Path outside project root"}
    target = os.path.join(ROOT, path.lstrip("/"))
    if not os.path.isfile(target):
        return {"ok": False, "error": "Not a file"}
    try:
        os.remove(target)
        return {"ok": True, "deleted": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import json, sys
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "list":
        r = list_dir(sys.argv[2] if len(sys.argv) > 2 else ".")
    elif action == "read" and len(sys.argv) > 2:
        r = read_file(sys.argv[2])
    elif action == "write" and len(sys.argv) > 3:
        r = write_file(sys.argv[2], sys.argv[3])
    elif action == "delete" and len(sys.argv) > 2:
        r = delete_file(sys.argv[2])
    else:
        r = {"error": "usage: file_manager.py <list|read|write|delete> [path] [content]"}
    print(json.dumps(r, ensure_ascii=False, indent=2))
