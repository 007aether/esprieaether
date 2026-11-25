import os
import json
import hashlib

FORMATS = {
    "txt":   {"ext": [".txt"],          "mime": "text/plain",              "cat": "text"},
    "md":    {"ext": [".md", ".markdown"], "mime": "text/markdown",       "cat": "text"},
    "html":  {"ext": [".html", ".htm"],  "mime": "text/html",              "cat": "text"},
    "rtf":   {"ext": [".rtf"],           "mime": "text/rtf",               "cat": "text"},
    "csv":   {"ext": [".csv"],           "mime": "text/csv",               "cat": "data"},
    "tsv":   {"ext": [".tsv", ".tab"],   "mime": "text/tab-separated-values", "cat": "data"},
    "xlsx":  {"ext": [".xlsx", ".xls"],  "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "cat": "data"},
    "ods":   {"ext": [".ods"],           "mime": "application/vnd.oasis.opendocument.spreadsheet", "cat": "data"},
    "json":  {"ext": [".json"],          "mime": "application/json",       "cat": "data"},
    "xml":   {"ext": [".xml"],           "mime": "application/xml",        "cat": "data"},
    "yaml":  {"ext": [".yaml", ".yml"],  "mime": "application/x-yaml",     "cat": "data"},
    "toml":  {"ext": [".toml"],          "mime": "application/toml",       "cat": "data"},
    "ini":   {"ext": [".ini", ".cfg", ".conf"], "mime": "text/x-config",  "cat": "data"},
    "py":    {"ext": [".py"],            "mime": "text/x-python",          "cat": "code"},
    "js":    {"ext": [".js"],            "mime": "application/javascript", "cat": "code"},
    "css":   {"ext": [".css"],           "mime": "text/css",               "cat": "code"},
    "jpg":   {"ext": [".jpg", ".jpeg"],  "mime": "image/jpeg",             "cat": "image"},
    "png":   {"ext": [".png"],           "mime": "image/png",              "cat": "image"},
    "webp":  {"ext": [".webp"],          "mime": "image/webp",             "cat": "image"},
    "bmp":   {"ext": [".bmp"],           "mime": "image/bmp",              "cat": "image"},
    "gif":   {"ext": [".gif"],           "mime": "image/gif",              "cat": "image"},
    "tiff":  {"ext": [".tiff", ".tif"],  "mime": "image/tiff",             "cat": "image"},
    "ico":   {"ext": [".ico"],           "mime": "image/x-icon",           "cat": "image"},
    "svg":   {"ext": [".svg"],           "mime": "image/svg+xml",          "cat": "image"},
    "pdf":   {"ext": [".pdf"],           "mime": "application/pdf",        "cat": "document"},
    "docx":  {"ext": [".docx"],          "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "cat": "document"},
    "odt":   {"ext": [".odt"],           "mime": "application/vnd.oasis.opendocument.text", "cat": "document"},
    "epub":  {"ext": [".epub"],          "mime": "application/epub+zip",   "cat": "document"},
    "zip":   {"ext": [".zip"],           "mime": "application/zip",        "cat": "archive"},
    "tar":   {"ext": [".tar"],           "mime": "application/x-tar",      "cat": "archive"},
    "gz":    {"ext": [".gz", ".gzip"],   "mime": "application/gzip",       "cat": "archive"},
    "bz2":   {"ext": [".bz2"],           "mime": "application/x-bzip2",    "cat": "archive"},
    "xz":    {"ext": [".xz"],            "mime": "application/x-xz",       "cat": "archive"},
    "sqlite":{"ext": [".sqlite", ".sqlite3", ".db"], "mime": "application/vnd.sqlite3", "cat": "database"},
    "mp3":   {"ext": [".mp3"],           "mime": "audio/mpeg",             "cat": "audio"},
    "wav":   {"ext": [".wav"],           "mime": "audio/wav",              "cat": "audio"},
    "ogg":   {"ext": [".ogg", ".opus"],  "mime": "audio/ogg",              "cat": "audio"},
    "flac":  {"ext": [".flac"],          "mime": "audio/flac",             "cat": "audio"},
    "m4a":   {"ext": [".m4a", ".aac"],   "mime": "audio/mp4",              "cat": "audio"},
    "mp4":   {"ext": [".mp4", ".m4v"],   "mime": "video/mp4",              "cat": "video"},
    "mkv":   {"ext": [".mkv"],           "mime": "video/x-matroska",       "cat": "video"},
    "webm":  {"ext": [".webm"],          "mime": "video/webm",             "cat": "video"},
    "mov":   {"ext": [".mov"],           "mime": "video/quicktime",        "cat": "video"},
    "avi":   {"ext": [".avi"],           "mime": "video/x-msvideo",        "cat": "video"},
    "log":   {"ext": [".log"],           "mime": "text/plain",             "cat": "text"},
    "cfg":   {"ext": [".cfg", ".conf"],  "mime": "text/x-config",          "cat": "text"},
    "env":   {"ext": [".env"],           "mime": "text/plain",             "cat": "text"},
}

MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",
    b"BM": "bmp",
    b"%PDF": "pdf",
    b"PK\x03\x04": "zip",
    b"PK\x03\x04\x14\x00\x06\x00": "docx",
    b"PK\x03\x04\x14\x00\x08\x08": "xlsx",
    b"\x1f\x8b\x08": "gz",
    b"BZh": "bz2",
    b"\xfd7zXZ\x00": "xz",
    b"ustar": "tar",
    b"<?xml": "xml",
    b"<html": "html",
    b"#!": "script",
    b"{\n": "json",
    b"[\n": "json",
    b"PK\x03\x04 \x00": "epub",
    b"SQLite format 3\x00": "sqlite",
    b"ID3": "audio",
    b"\xff\xfb": "audio",
    b"\xff\xf3": "audio",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".ico"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".log", ".py", ".js", ".css", ".rtf"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".gzip", ".bz2", ".xz"}
DATA_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".ods", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".odt", ".epub", ".rtf"}


def detect_format_by_ext(filepath):
    _, ext = os.path.splitext(filepath.lower())
    for fmt, info in FORMATS.items():
        if ext in info["ext"]:
            return fmt
    return None


def detect_format_by_magic(filepath, bytes_to_read=256):
    try:
        with open(filepath, "rb") as f:
            head = f.read(bytes_to_read)
    except Exception:
        return None
    for magic, fmt in MAGIC_BYTES.items():
        if head[:len(magic)] == magic:
            return fmt
    if b"<?xml" in head[:100] or (b"<" in head[:100] and b">" in head[:200]):
        return "xml"
    if b"<html" in head[:200] or b"<!DOCTYPE html" in head[:200]:
        return "html"
    try:
        head.decode("utf-8").strip()
        return "txt"
    except Exception:
        return None


def detect_format(filepath):
    ext_fmt = detect_format_by_ext(filepath)
    if ext_fmt and FORMATS[ext_fmt]["cat"] in ("audio", "video"):
        # Containers like RIFF/ID3 are ambiguous (wav vs webp); the extension wins.
        return ext_fmt
    fmt = detect_format_by_magic(filepath)
    if fmt in ("zip",):
        ext_fmt = detect_format_by_ext(filepath)
        if ext_fmt in ("docx", "xlsx", "epub"):
            return ext_fmt
    if fmt in ("txt", "xml", "html", None):
        # Content sniffing is only a generic guess for text; trust the extension.
        return detect_format_by_ext(filepath) or fmt or "bin"
    return fmt


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def ensure_output_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def get_output_path(input_path, output_ext):
    base = os.path.splitext(input_path)[0]
    return base + output_ext


def compute_hash(filepath, algo="sha256"):
    h = hashlib.new(algo)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_category(filepath):
    fmt = detect_format(filepath)
    if fmt and fmt in FORMATS:
        return FORMATS[fmt]["cat"]
    return "binary"


def is_text_file(filepath, sample_size=8192):
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
        chunk.decode("utf-8")
        return True
    except Exception:
        return False


def detect_encoding(filepath):
    try:
        import chardet
        with open(filepath, "rb") as f:
            raw = f.read(10000)
        result = chardet.detect(raw)
        return result.get("encoding", "utf-8") or "utf-8"
    except ImportError:
        return "utf-8"
