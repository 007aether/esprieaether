"""Mémoire locale du vault Obsidian — BM25 sans dépendance ni réseau.

Motif repris de khoj-ai/khoj et FelipeMachado25/jarvis : indexer les notes
markdown en texte brut et interroger localement. Aucun embedding cloud,
aucune base de données externe.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

TOKEN = re.compile(r"[\w\-]+", re.UNICODE)
K1 = 1.5
B = 0.75


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class VaultMemory:
    def __init__(self, vault_dir: Path):
        self.vault_dir = Path(vault_dir)
        self.docs: list[dict] = []
        self._index()

    def _index(self) -> None:
        if not self.vault_dir.is_dir():
            return
        for path in sorted(self.vault_dir.rglob("*.md")):
            if any(part.startswith(".") for part in path.relative_to(self.vault_dir).parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            tokens = _tokens(text)
            if not tokens:
                continue
            self.docs.append({
                "path": path.relative_to(self.vault_dir).as_posix(),
                "text": text,
                "tokens": tokens,
                "length": len(tokens),
            })
        self.avgdl = sum(d["length"] for d in self.docs) / len(self.docs) if self.docs else 0
        self.df: dict[str, int] = {}
        for doc in self.docs:
            for term in set(doc["tokens"]):
                self.df[term] = self.df.get(term, 0) + 1
        self.total = len(self.docs)

    @property
    def count(self) -> int:
        return self.total

    def _idf(self, term: str) -> float:
        freq = self.df.get(term, 0)
        return math.log(1 + (self.total - freq + 0.5) / (freq + 0.5))

    def query(self, text: str, limit: int = 5) -> list[dict]:
        terms = _tokens(text)
        if not terms or not self.docs:
            return []
        scores: list[dict] = []
        for doc in self.docs:
            lengths = doc["length"]
            denominator_base = K1 * (1 - B + B * lengths / self.avgdl) if self.avgdl else K1
            score = 0.0
            for term in terms:
                freq = doc["tokens"].count(term)
                if not freq:
                    continue
                score += self._idf(term) * (freq * (K1 + 1)) / (freq + denominator_base)
            if score > 0:
                scores.append({
                    "path": doc["path"],
                    "score": round(score, 4),
                    "snippet": doc["text"].replace("\n", " ").strip()[:240],
                })
        scores.sort(key=lambda hit: hit["score"], reverse=True)
        return scores[:limit]

    def evidence(self, query: str, limit: int = 5) -> dict:
        hits = self.query(query, limit=limit)
        return {
            "ok": bool(hits),
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "noteCount": self.count,
            "topPath": hits[0]["path"] if hits else None,
            "topScore": hits[0]["score"] if hits else 0,
            "engine": "local_bm25",
        }

    def write_evidence(self, path: Path, query: str, limit: int = 5) -> dict:
        proof = self.evidence(query, limit=limit)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return proof


if __name__ == "__main__":  # usage local : python vault_memory.py <vault> <requête>
    import sys

    if len(sys.argv) >= 3:
        memory = VaultMemory(Path(sys.argv[1]))
        for hit in memory.query(" ".join(sys.argv[2:])):
            print(f"{hit['score']}\t{hit['path']}")
