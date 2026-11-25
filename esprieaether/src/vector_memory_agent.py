#!/usr/bin/env python3
"""
vector_memory_agent.py — semantic memory with embeddings (SQLite + Ollama)

WHAT: A real semantic memory layer: every fact/decision/insight the system
produces is embedded and stored in SQLite, and `recall(query)` returns the
most semantically similar entries — so the mesh agents, the autonomous loop,
and Telegram can all remember context across sessions.

WHY: the existing memory_layer keeps key→value dicts with a keyword overlap
"recall_similar" — no vectors, no real similarity, and it pointed at the dead
~/AETHER_V8 path. This replaces it: SQLite (stdlib) + Ollama embeddings when
available, with a deterministic hash-based fallback so it works offline.

EMBEDDINGS: tries Ollama's /api/embeddings (nomic-embed-text if pulled),
falls back to a 256-dim character-ngram hash vector. Both give cosine
similarity; the fallback is weaker but always available.

OUTPUT: data/vector_memory.db (SQLite, FTS + embedding blobs)
"""

import hashlib
import json
import logging
import math
import os
import sqlite3
import struct
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    pass

DB_FILE = BASE_DIR / "data" / "vector_memory.db"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

logger = logging.getLogger("vector_memory")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

DIM = 256  # fallback hash-vector dimension


# ── Embeddings ──

def ollama_embed(text, model=EMBED_MODEL, timeout=15):
    """Embed via Ollama. Returns list[float] or None."""
    payload = json.dumps({"model": model, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        emb = data.get("embedding")
        if emb and isinstance(emb, list):
            return emb
    except Exception:
        return None
    return None


def hash_embed(text, dim=DIM):
    """Deterministic char-ngram hash vector — the offline fallback."""
    text = text.lower().strip()
    vec = [0.0] * dim
    # unigrams + bigrams
    tokens = text.split()
    grams = list(text) + tokens + [a + b for a, b in zip(text, text[1:])]
    for g in grams:
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(text):
    """Ollama when available, else hash fallback. Returns (vector, source)."""
    v = ollama_embed(text)
    if v:
        return v, "ollama"
    return hash_embed(text), "hash"


def cosine(a, b):
    """Cosine similarity between two equal-length vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def pack_vector(vec):
    return struct.pack(f"{len(vec)}f", *vec)


def unpack_vector(blob):
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


# ── SQLite store ──

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,           -- fact | decision | insight | event | task
    source TEXT,                  -- agent name / telegram / loop
    text TEXT NOT NULL,
    embedding BLOB,
    importance REAL DEFAULT 0.5,
    tags TEXT
);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(ts);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, content='memories', content_rowid='id');
"""


class VectorMemory:
    def __init__(self, db_path=DB_FILE):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def remember(self, text, kind="fact", source="system", importance=0.5, tags=None):
        """Store one memory with its embedding."""
        vec, emb_source = embed(text)
        ts = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "INSERT INTO memories (ts, kind, source, text, embedding, importance, tags) VALUES (?,?,?,?,?,?,?)",
            (ts, kind, source, text, pack_vector(vec), importance, json.dumps(tags or [])),
        )
        self.conn.execute(
            "INSERT INTO memories_fts (rowid, text) VALUES (?, ?)",
            (cur.lastrowid, text),
        )
        self.conn.commit()
        return {"id": cur.lastrowid, "ts": ts, "embed_source": emb_source, "kind": kind}

    def recall(self, query, limit=5, kind=None, min_score=0.0):
        """Semantic recall: cosine over stored vectors (+ FTS boost)."""
        qvec, _ = embed(query)
        where = "WHERE kind = ?" if kind else ""
        params = (kind,) if kind else ()
        rows = self.conn.execute(
            f"SELECT id, ts, kind, source, text, embedding, importance FROM memories {where}",
            params,
        ).fetchall()

        # FTS keyword hits get a small boost
        fts_ids = set()
        try:
            fts = self.conn.execute(
                "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? LIMIT 20",
                (query.replace('"', ' '),),
            ).fetchall()
            fts_ids = {r[0] for r in fts}
        except Exception:
            pass

        scored = []
        for rid, ts, k, source, text, blob, importance in rows:
            vec = unpack_vector(blob)
            score = cosine(qvec, vec)
            if rid in fts_ids:
                score += 0.15
            score += importance * 0.1
            if score >= min_score:
                scored.append({
                    "id": rid, "ts": ts, "kind": k, "source": source,
                    "text": text, "score": round(score, 4),
                })
        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_kind = self.conn.execute(
            "SELECT kind, COUNT(*) FROM memories GROUP BY kind"
        ).fetchall()
        return {
            "total": total,
            "by_kind": {k: n for k, n in by_kind},
            "db_size_kb": round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0,
        }

    def recent(self, limit=10):
        rows = self.conn.execute(
            "SELECT id, ts, kind, source, text FROM memories ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"id": r[0], "ts": r[1], "kind": r[2], "source": r[3], "text": r[4]} for r in rows]

    def format_telegram(self, query=None, limit=5):
        if query:
            items = self.recall(query, limit=limit)
            if not items:
                return f"🧠 ما كاين حتى ذكرى قريبة من: {query}"
            lines = [f"🧠 *ذكرى* — «{query}»\n"]
            for it in items:
                lines.append(f"`{it['score']:.2f}` [{it['kind']}] {it['text'][:80]}")
            return "\n".join(lines)
        items = self.recent(limit=limit)
        lines = ["🧠 *آخر الذكريات*\n"]
        for it in items:
            lines.append(f"[{it['kind']}] {it['text'][:80]}")
        return "\n".join(lines)

    def close(self):
        self.conn.close()


# ── CLI / helpers ──

def remember_many(items):
    """Batch remember. items: list of dicts {text, kind, source, importance, tags}."""
    vm = VectorMemory()
    ids = [vm.remember(**i) for i in items]
    vm.close()
    return ids


def recall(query, limit=5, kind=None):
    vm = VectorMemory()
    res = vm.recall(query, limit=limit, kind=kind)
    vm.close()
    return res


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--remember", help="text to remember")
    ap.add_argument("--kind", default="fact")
    ap.add_argument("--source", default="cli")
    ap.add_argument("--importance", type=float, default=0.5)
    ap.add_argument("--recall", help="semantic query")
    ap.add_argument("--recent", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    vm = VectorMemory()

    if args.remember:
        r = vm.remember(args.remember, kind=args.kind, source=args.source, importance=args.importance)
        print(f"✅ remembered id={r['id']} ({r['embed_source']})")
    elif args.recall:
        for it in vm.recall(args.recall, limit=5):
            print(f"  {it['score']:.3f} [{it['kind']}] {it['text'][:90]}")
    elif args.recent:
        for it in vm.recent(limit=10):
            print(f"  [{it['kind']}] {it['text'][:90]}")
    elif args.stats:
        print(json.dumps(vm.stats(), ensure_ascii=False, indent=2))
    else:
        print("vector_memory_agent — use --remember / --recall / --recent / --stats")

    vm.close()


if __name__ == "__main__":
    main()
