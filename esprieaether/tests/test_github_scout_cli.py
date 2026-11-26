"""J124 — TDD : la sortie CLI de la veille GitHub survit à un console cp1252."""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import github_scout  # noqa: E402


class GithubScoutCliTest(unittest.TestCase):
    def test_main_ecrit_un_resume_sans_erreur_dencodage(self) -> None:
        report = {"scanned": 1000, "status": "live_verified"}
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with patch.object(github_scout, "run", return_value=report), \
                redirect_stdout(stream):
            github_scout.main()
        stream.flush()
        text = raw.getvalue().decode("utf-8", errors="replace")
        self.assertIn("1000", text)
        self.assertIn("live_verified", text)


if __name__ == "__main__":
    unittest.main()
