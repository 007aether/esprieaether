#!/usr/bin/env python3
"""
obsidian_graph_web.py — render the Obsidian vault as a live web page
(served by web_interface.py at /obsidian + a standalone graph.html).

Parses [[wiki-links]] from every note in the vault → vis-network graph.
"""

import json
import os
import re
from pathlib import Path

VAULT = Path(os.getenv("OBSIDIAN_VAULT_DIR", str(Path(os.path.expanduser("~")) / "ObsidianVault" / "EsprieAether")))
OUT_HTML = VAULT / "graph.html"
# Bibliothèque embarquée : le graphe doit s'afficher sans accès à un CDN externe.
VENDOR_JS = Path(__file__).resolve().parent / "vendor" / "vis-network.min.js"

# category colors
COLORS = {
    "service": "#22d3ee",     # cyan
    "bot": "#a78bfa",         # violet
    "agent": "#818cf8",       # indigo
    "integration": "#34d399", # green
    "sunna": "#f59e0b",       # amber (Sunna)
    "brain": "#f472b6",       # pink
    "infra": "#f87171",       # red
    "docs": "#eab308",        # yellow
    "meta": "#94a3b8",        # slate
    "api": "#60a5fa",         # blue
    "web": "#fb923c",         # orange
}


def _vault_files():
    """Toutes les notes réelles, y compris _Index, sans fichiers de travail."""
    if not VAULT.exists():
        return []
    return [f for f in VAULT.rglob("*.md") if ".graphify" not in str(f)]


def _note_index():
    """(fichiers, par stem, fonction d'identifiant) — jamais deux notes avec le même id."""
    files = _vault_files()
    by_stem = {}
    for f in files:
        by_stem.setdefault(f.stem, []).append(f)

    def note_id(path):
        candidates = by_stem[path.stem]
        if len(candidates) == 1:
            return path.stem
        parent = path.relative_to(VAULT).parent.as_posix()
        return f"{parent}/{path.stem}" if parent != "." else path.stem

    ids = {f: note_id(f) for f in files}
    return files, by_stem, ids


def resolve_link(link, source, by_stem, ids):
    """Résout un [[wiki-link]] vers une note existante ; None si le lien est mort."""
    link = link.strip().replace("\\", "/")
    if not link:
        return None
    if "/" in link:
        target = link[:-3] if link.endswith(".md") else link
        for path, ident in ids.items():
            rel = path.relative_to(VAULT).with_suffix("").as_posix()
            if rel.lower() == target.lower():
                return ident
        link = target.rsplit("/", 1)[-1]
    candidates = by_stem.get(link) or by_stem.get(link.rstrip(".md")) or []
    if not candidates:
        return None
    if len(candidates) == 1:
        return ids[candidates[0]]
    same_folder = [c for c in candidates if c.parent == source.parent]
    return ids[(same_folder or sorted(candidates))[0]]


# Les noms génériques (email, orchestrator, REA…) existent dans plusieurs
# dossiers. On garde la note la plus structurante et on préfixe les autres par
# leur dossier : aucun contenu n'est inventé, seul le nom change.
CATEGORY_PRIORITY = ("services", "brains", "integrations", "agents", "sunna", "meta")


def deduplicate_note_names():
    """Renomme les notes en doublon et réécrit tous les liens affectés."""
    files, by_stem, ids = _note_index()
    renames, id_map, primary_map = {}, {}, {}

    def priority(path):
        parts = path.relative_to(VAULT).parts
        category = parts[0].lower() if len(parts) > 1 else ""
        rank = (CATEGORY_PRIORITY.index(category)
                if category in CATEGORY_PRIORITY else len(CATEGORY_PRIORITY))
        return rank, str(path).lower()

    for stem, paths in by_stem.items():
        if len(paths) < 2:
            continue
        primary = min(paths, key=priority)
        primary_map[stem] = ids[primary]
        for path in paths:
            if path == primary:
                continue
            folder = path.parent.name
            stem_new = f"{folder}-{stem}"
            counter = 2
            while (path.with_name(f"{stem_new}.md").exists()
                   and path.with_name(f"{stem_new}.md") != path):
                stem_new = f"{folder}-{stem}-{counter}"
                counter += 1
            target = path.with_name(f"{stem_new}.md")
            renames[path] = target
            id_map[ids[path]] = stem_new

    stats = {"renamed": len(renames)}
    if not renames:
        stats.update({"duplicates": 0, "files": len(files)})
        return stats

    for path in files:
        original = path.read_text(encoding="utf-8", errors="ignore")

        def replace(match):
            raw = match.group(1)
            alias = match.group(2) or ""
            resolved = resolve_link(raw, path, by_stem, ids)
            if raw in primary_map:
                resolved = primary_map[raw]
            target = id_map.get(resolved, resolved or raw)
            suffix = f"|{alias}" if alias else ""
            return f"[[{target}{suffix}]]"

        fixed = re.sub(r"\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]", replace, original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")

    for old, new in renames.items():
        old.rename(new)

    files_after, by_after, _ = _note_index()
    stats["duplicates"] = sum(1 for group in by_after.values() if len(group) > 1)
    stats["files"] = len(files_after)
    return stats


def parse_vault():
    """Return (nodes, edges) — liens morts ignorés, noms dupliqués distingués par dossier."""
    files, by_stem, ids = _note_index()
    nodes, edges, seen = {}, [], set()
    for f in files:
        parts = f.relative_to(VAULT).parts
        cat = parts[0].lower() if len(parts) > 1 else "meta"
        ident = ids[f]
        nodes[ident] = {"id": ident, "label": ident, "group": cat, "size": 12}
        text = f.read_text(encoding="utf-8", errors="ignore")
        for raw in re.findall(r"\[\[([^\]|#]+)", text):
            to = resolve_link(raw, f, by_stem, ids)
            if to is None or to == ident or (ident, to) in seen:
                continue
            seen.add((ident, to))
            edges.append({"from": ident, "to": to})
    # degree sizing
    from collections import Counter
    deg = Counter()
    for e in edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1
    for n in nodes.values():
        n["value"] = min(40, 10 + deg.get(n["id"], 0) * 3)
    return list(nodes.values()), edges


def repair_wiki_links():
    """Réécrit les liens morts/ambiguus en identifiants réels ; ne supprime aucune note."""
    files, by_stem, ids = _note_index()
    stats = {"notes": len(files), "rewritten": 0, "removed": 0}
    canonical = set(ids.values())
    for f in files:
        original = f.read_text(encoding="utf-8", errors="ignore")

        def replace(match):
            raw = match.group(1)
            target = resolve_link(raw, f, by_stem, ids)
            alias = match.group(2) or ""
            suffix = f"|{alias}" if alias else ""
            if target is None:
                stats["removed"] += 1
                return ""
            if target != raw:
                stats["rewritten"] += 1
            return f"[[{target}{suffix}]]"

        fixed = re.sub(r"\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]", replace, original)
        if fixed != original:
            f.write_text(fixed, encoding="utf-8")
    stats["notes_after"] = len(_note_index()[0])
    stats["canonical_ids"] = len(canonical)
    return stats


def _vis_script() -> str:
    """Bibliothèque locale uniquement : aucun CDN, même en secours."""
    if VENDOR_JS.exists():
        js = VENDOR_JS.read_text(encoding="utf-8", errors="ignore")
        return "<script>\n" + js + "\n</script>"
    return "<script>/* vis-network local absent : rendu hors-ligne indisponible */</script>"


def render_html(nodes, edges):
    groups = {k: {"color": v} for k, v in COLORS.items()}
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧠 EsprieAether — Knowledge Graph</title>
{_vis_script()}
<style>
 body{{background:#0b1120;color:#e2e8f0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0}}
 header{{padding:14px 20px;border-bottom:1px solid #1e293b;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
 h1{{font-size:17px;margin:0;font-weight:600}}
 .stat{{font-size:12px;color:#94a3b8}} .stat b{{color:#22d3ee}}
 #legend{{display:flex;gap:10px;flex-wrap:wrap;padding:10px 20px;font-size:11px}}
 .lg{{display:flex;align-items:center;gap:5px}} .dot{{width:9px;height:9px;border-radius:50%}}
 #net{{width:100%;height:calc(100vh - 92px);background:#0b1120}}
 #tip{{position:fixed;left:12px;bottom:12px;font-size:11px;color:#64748b}}
</style></head><body>
<header><h1>🧠 EsprieAether — Knowledge Graph</h1>
 <span class="stat">📝 <b>{len(nodes)}</b> notes</span>
 <span class="stat">🔗 <b>{len(edges)}</b> links</span>
 <span class="stat">~ObsidianVault/EsprieAether</span></header>
<div id="legend">{''.join(f'<span class="lg"><span class="dot" style="background:{c}"></span>{k}</span>' for k,c in COLORS.items())}</div>
<div id="net"></div><div id="tip">drag to pan · scroll to zoom · click a node</div>
<script>
const nodes=new vis.DataSet({json.dumps(nodes)});
const edges=new vis.DataSet({json.dumps(edges)}.map(e=>({{from:e.from,to:e.to,color:{{color:'#334155',highlight:'#22d3ee'}},width:1}})));
const net=new vis.Network(document.getElementById('net'),{{nodes,edges}},{{
  nodes:{{shape:'dot',font:{{color:'#cbd5e1',size:11}},borderWidth:1.5}},
  edges:{{smooth:{{type:'continuous'}},hoverWidth:1.8}},
  physics:{{stabilization:true,barnesHut:{{gravitationalConstant:-9000,springLength:130}}}},
  groups:{json.dumps(groups)}
}});
net.on('click',p=>{{if(p.nodes.length){{const n=nodes.get(p.nodes[0]);net.selectNodes([n.id]);}}}});
</script></body></html>"""


def main(repair=False, dedupe=False):
    if not VAULT.exists():
        print(f"ERROR vault not found: {VAULT} - run obsidian_vault_builder.py first")
        return
    if dedupe:
        stats = deduplicate_note_names()
        print(f"OK dedupe: {stats['renamed']} notes renommées, "
              f"{stats['duplicates']} groupes doublons restants")
    if repair:
        stats = repair_wiki_links()
        print(f"OK repair: {stats['rewritten']} liens réécrits, {stats['removed']} liens morts retirés")
    nodes, edges = parse_vault()
    OUT_HTML.write_text(render_html(nodes, edges), encoding="utf-8")
    print(f"OK graph.html: {OUT_HTML}")
    print(f"   {len(nodes)} nodes / {len(edges)} edges")
    from collections import Counter
    cats = Counter(n["group"] for n in nodes)
    for c, n in cats.most_common():
        print(f"   {c}: {n}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true", help="réécrit les liens morts/ambiguus")
    parser.add_argument("--dedupe", action="store_true", help="renomme les notes en doublon")
    args = parser.parse_args()
    main(repair=args.repair, dedupe=args.dedupe)
