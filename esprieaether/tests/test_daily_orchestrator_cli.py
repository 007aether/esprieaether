"""J125 — TDD : résumé CLI de l'ordonnanceur sûr sur console cp1252."""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import daily_orchestrator  # noqa: E402


class DailyOrchestratorCliTest(unittest.TestCase):
    def test_main_supporte_un_flux_cp1252(self) -> None:
        report = {
            "status": "live_verified",
            "tasks": [{"id": "doctor", "status": "live_verified"}],
        }
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        with patch.object(daily_orchestrator, "run_due", return_value={"ran": False, "report": report}), \
                redirect_stdout(stream):
            daily_orchestrator.main(Path("."))
        stream.flush()
        text = raw.getvalue().decode("utf-8", errors="replace")
        self.assertIn("live_verified", text)


if __name__ == "__main__":
    unittest.main()
