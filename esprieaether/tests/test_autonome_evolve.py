"""J152 — TDD : le compteur de cycles n'avance qu'une fois par cycle."""

import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


class AutonomeEvolveTest(unittest.TestCase):
    def test_cycle_counter_increments_once(self) -> None:
        source = (SRC / "autonome_evolve.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('state["current_cycle"] += 1'), 1)

    def test_auto_dev_is_called_after_green_report(self) -> None:
        source = (SRC / "autonome_evolve.py").read_text(encoding="utf-8")
        self.assertIn("auto_dev.maybe_commit_push()", source)
        self.assertLess(source.index("generate_report()"), source.index("auto_dev.maybe_commit_push()"))

    def test_every_file_open_declares_utf8(self) -> None:
        # Le daemon écrit du français/arabe : sans encoding explicite, Windows
        # utilise cp1252 et le cycle meurt avec UnicodeEncodeError.
        source = (SRC / "autonome_evolve.py").read_text(encoding="utf-8")
        opens = re.findall(r"(?<!\w)open\([^)]*\)", source)
        self.assertTrue(opens)
        self.assertTrue(all("encoding=" in item for item in opens),
                        [item for item in opens if "encoding=" not in item])


if __name__ == "__main__":
    unittest.main()
