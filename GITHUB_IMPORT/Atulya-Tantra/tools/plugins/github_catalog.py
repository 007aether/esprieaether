"""J182 — cataleg local, en lecture seule, de 50 projets AI/tatwir pris sur GitHub.

Les réponses viennent d'un fichier JSON versionné, jamais d'un appel réseau au
moment de la conversation. Aucune affirmation de fonctionnement « live » n'est
ajoutée : le catalogue porte la date de collecte et les champs renvoyés par
l'API GitHub. Les questions d'état restent réservées à web_intent/_STATUS.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_LOCAL_SRC = Path(__file__).resolve().parents[4] / "esprieaether" / "src"
if str(_LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_SRC))

from pc_gateway import _scrub  # noqa: E402 — même nettoyage que la passerelle PC

_CATALOG = Path(__file__).with_name("github_catalog.json")

_LIST = re.compile(
    r"^(?:عطيني|أعطيني|جيب|أجيب|هات|اعرض|أعرض|ليست|شنو)\s+"
    r"(?:لي\s+)?(?:المشاريع|مشاريع)"
    r"(?:\s+(?:اللي\s+)?جبت(?:ها|هم|يهم)?)?"
    r"(?:\s+ديال\s+الـ?50)?\s*[.!?؟]?$",
    re.I,
)
_DETAIL = re.compile(
    r"^(?:تفاصيل|فصّل|فصل|اشرح|اشرحو|شرح|detail|describe)\s+"
    r"(?:لي\s+)?(?:المشروع|مشروع|repo|repository)?\s*"
    r"([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?|\d{1,2})\s*[.!?؟]?$",
    re.I,
)
_WHAT_DETAIL = re.compile(
    r"^(?:شنو|وشنو|ما هو)\s+(?:المشروع|مشروع)?\s*"
    r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*[.!?؟]?$",
    re.I,
)
_SEARCH = re.compile(
    r"^(?:مشاريع|جيب مشاريع|شنو مشاريع|ابحث|ابحثي|search)\s+"
    r"(?:في|على|عن|بخصوص|ديال|with|for|about)\s+(.{2,80}?)\s*[.!?؟]?$",
    re.I,
)
_COUNT = re.compile(
    r"^(?:بشحال|شحال من|كم)\s+مشروع\s+"
    r"(?:جبت|عندك|كاين|في الكاتالوج|فالكاتالوج)\s*[.!?؟]?$",
    re.I,
)
_UNIFIED = re.compile(
    r"^(?:(?:شنو|أي)\s+(?:المشروع|مشروع)\s+(?:اللي\s+)?كيجمع\s+كلشي"
    r"|.*\bijema(?:3|33)\s+kolechi\b.*"
    r"|unified\s+project(?:\s+for\s+esprieaether)?)\s*[.!?؟]?$",
    re.I | re.S,
)
_UNIFIED_PICK = "affaan-m/ECC"
_UNIFIED_WHY = (
    "كيجمع المهارات (skills)، والردود السريعة (instincts)، والذاكرة (memory)، "
    "والأمان (security): يعني نفس طبقات أتوليا المحلية فمشروع واحد. "
    "هادي توصية محلية مبنية على وصف المستودع فالكاتالوج، "
    "ما كتعنيش إنّا نزّلنا الكود ولا إنو شغّال عندنا دابا."
)


@dataclass(frozen=True)
class CatalogIntent:
    kind: str
    target: str


def match_intent(text: str) -> CatalogIntent | None:
    value = " ".join(str(text or "").strip().split())
    if not value:
        return None
    if _COUNT.fullmatch(value):
        return CatalogIntent("count", "")
    if _UNIFIED.fullmatch(value):
        return CatalogIntent("unified", "")
    if _LIST.fullmatch(value):
        return CatalogIntent("list", "")
    if match := _DETAIL.fullmatch(value):
        return CatalogIntent("detail", _scrub(match.group(1)).strip())
    if match := _WHAT_DETAIL.fullmatch(value):
        return CatalogIntent("detail", _scrub(match.group(1)).strip())
    if match := _SEARCH.fullmatch(value):
        return CatalogIntent("search", _scrub(match.group(1)).strip())
    return None


def _read(path: Path | None) -> dict:
    target = Path(path) if path is not None else _CATALOG
    data = json.loads(target.read_text(encoding="utf-8"))
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        raise ValueError("catalogue local vide ou invalide")
    return data


def _snapshot(data: dict) -> str:
    return str(data.get("collectedAt") or "")[:10]


def _find(data: dict, target: str) -> dict | None:
    key = target.lower()
    projects = data["projects"]
    if key.isdigit():
        number = int(key)
        return next((p for p in projects if p.get("rank") == number), None)
    return next(
        (p for p in projects if str(p.get("full_name", "")).lower() == key
         or str(p.get("name", "")).lower() == key),
        None,
    )


def _detail_text(project: dict, snapshot: str) -> str:
    desc = _scrub(str(project.get("description") or ""))[:600] or "-"
    topics = ", ".join(str(t) for t in project.get("topics", [])[:12]) or "-"
    return (
        "{rank:02d}. {full_name} — ★{stars:,} — forks {forks:,} — {language} — {license}\n"
        "الوصف: {desc}\n"
        "المواضيع: {topics}\n"
        "تاريخ النشر: {created} — آخر push: {pushed}\n"
        "الرابط: {url}\n"
        "ملاحظة: هادي لقطة من GitHub فـ{snapshot}، وما كنأكدش إن المشروع باقي شغّال دابا."
    ).format(
        rank=int(project.get("rank") or 0),
        full_name=_scrub(str(project.get("full_name") or "")),
        stars=int(project.get("stars") or 0),
        forks=int(project.get("forks") or 0),
        language=_scrub(str(project.get("language") or "-")) or "-",
        license=_scrub(str(project.get("license") or "-")) or "-",
        desc=desc,
        topics=_scrub(topics),
        created=str(project.get("created_at") or "")[:10] or "-",
        pushed=str(project.get("pushed_at") or "")[:10] or "-",
        url=_scrub(str(project.get("url") or "")),
        snapshot=snapshot or "تاريخ غير مسجّل",
    )


def execute_intent(intent: CatalogIntent, catalog_path: Path | None = None) -> str:
    """نصّ صادق من الملف المحلي غير، بلا وصول للشبكة ولا ادّعاء حالة حية."""
    try:
        data = _read(catalog_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return "الكاتالوج المحلي غير متوفر دابا. ما عنديش معلومات مؤكدة منو."

    projects = data["projects"]
    snapshot = _snapshot(data)
    prefix = f"لقطة GitHub محلية فـ{snapshot or 'تاريخ غير مسجّل'}، بلا تحقق من الحالة الحية دابا.\n"

    if intent.kind == "count":
        return prefix + f"عندي {len(projects)} مشروع AI وتطوير فالكاتالوج المحلي."

    if intent.kind == "unified":
        project = _find(data, _UNIFIED_PICK)
        if project is None:
            return prefix + "ما لقيتش المشروع المختار فالكاتالوج المحلي."
        return (
            prefix
            + f"المشروع اللي كيجمع كلشي، واللي كنخصّصو لـEsprieaether هو {_UNIFIED_PICK}. "
            + _UNIFIED_WHY
            + "\nقول «تفاصيل المشروع 2» باش تشوف الوصف والرخصة والرابط."
        )

    if intent.kind == "list":
        lines = [
            "{rank:02d}. {full_name} — ★{stars:,} — {language}".format(
                rank=int(p.get("rank") or 0),
                full_name=_scrub(str(p.get("full_name") or "")),
                stars=int(p.get("stars") or 0),
                language=_scrub(str(p.get("language") or "-")) or "-",
            )
            for p in projects
        ]
        return (
            prefix
            + f"ها كامل {len(projects)} المشاريع اللي جبتها من GitHub:\n"
            + "\n".join(lines)
            + "\nقول «تفاصيل <اسم المشروع>» باش تعطيك الوصف والرخصة والمواضيع والرابط."
        )

    if intent.kind == "detail":
        project = _find(data, intent.target)
        if project is None:
            return prefix + f"ما لقيتش مشروع باسم «{_scrub(intent.target)[:80]}» فالكاتالوج المحلي."
        return prefix + _detail_text(project, snapshot)

    if intent.kind == "search":
        needle = intent.target.lower()
        hits = []
        for project in projects:
            haystack = " ".join(
                [
                    str(project.get("full_name") or ""),
                    str(project.get("description") or ""),
                    str(project.get("language") or ""),
                    " ".join(str(t) for t in project.get("topics") or []),
                ]
            ).lower()
            if needle in haystack:
                hits.append(project)
        if not hits:
            return prefix + f"ما لقيتش مشروع يطابق «{_scrub(intent.target)[:80]}» فالكاتالوج المحلي."
        shown = hits[:12]
        lines = [
            "{rank:02d}. {full_name} — ★{stars:,} — {desc}".format(
                rank=int(p.get("rank") or 0),
                full_name=_scrub(str(p.get("full_name") or "")),
                stars=int(p.get("stars") or 0),
                desc=_scrub(str(p.get("description") or "-"))[:110] or "-",
            )
            for p in shown
        ]
        suffix = "" if len(hits) <= 12 else f"\n(و{len(hits) - 12} آخرين مازالين فالكاتالوج)."
        return prefix + f"لقيت {len(hits)} مشروع يطابق «{_scrub(intent.target)[:80]}»:\n" + "\n".join(lines) + suffix

    return prefix + "ما فهمتش السؤال. قول «عطيني المشاريع» ولا «تفاصيل <اسم المشروع>»."
