"""J86: pont local et muet vers le convertisseur hors ligne vendored.

Aucun appel réseau, aucun raccourci, aucune commande d'exécution arbitraire :
on appelle uniquement le module Python installé dans le dossier du projet.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "GITHUB_IMPORT" / "Atulya-All-File-Converter"
_PY = VENDOR / ".venv" / "Scripts" / "python.exe"
if not _PY.exists():
    _PY = VENDOR / ".venv" / "bin" / "python"
PYTHON = _PY

VAULT = Path("C:/Users/aether/ObsidianVault/EsprieAether")
ALLOWED_ROOTS = tuple(
    path.resolve() for path in (ROOT, Path(tempfile.gettempdir()), VAULT)
    if path.exists()
)


def available() -> bool:
    """Le convertisseur est installé localement, rien n'est promis de plus."""
    return PYTHON.exists() and (VENDOR / "atulya_all_file_converter").is_dir()


def _inside(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in ALLOWED_ROOTS)


def convert_file(source: str | Path, target: str | Path) -> dict:
    """Convertit un fichier local ; jamais de téléversement ni de commande open."""
    result = {
        "available": available(), "ok": False, "code": "",
        "source": str(source), "target": str(target),
        "stdout": "", "stderr": "", "returncode": None,
    }
    if not result["available"]:
        result["code"] = "CONVERTER_MISSING"
        return result
    src, dst = Path(source), Path(target)
    if not _inside(src) or not _inside(dst):
        result["code"] = "PATH_REFUSED"
        return result
    if not src.is_file():
        result["code"] = "SOURCE_MISSING"
        return result
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(PYTHON), "-m", "atulya_all_file_converter", "convert",
           "-i", str(src.resolve()), "-o", str(dst.resolve())]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env.pop(key, None)
        env.pop(key.lower(), None)
    try:
        done = subprocess.run(cmd, cwd=str(VENDOR), env=env, capture_output=True,
                              text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        result["code"] = "CONVERT_FAILED"
        result["stderr"] = str(error)
        return result
    result["stdout"] = (done.stdout or "").strip()[-2000:]
    result["stderr"] = (done.stderr or "").strip()[-2000:]
    result["returncode"] = done.returncode
    result["ok"] = done.returncode == 0
    result["code"] = "OK" if result["ok"] else "CONVERT_FAILED"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Conversion locale hors ligne")
    parser.add_argument("--check", action="store_true", help="Afficher la disponibilité")
    parser.add_argument("--source")
    parser.add_argument("--target")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps({"available": available()}, ensure_ascii=False))
        return 0
    if not args.source or not args.target:
        parser.error("--source et --target sont requis (ou --check)")
    result = convert_file(args.source, args.target)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
