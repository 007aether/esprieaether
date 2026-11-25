"""App lookup must accept the localized Start-menu names present on this host."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from tools.plugins.system import actions

CALCULATOR_APPID = "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"


class FindAppTest(unittest.TestCase):
    @patch.object(actions, "_app_entries", return_value={"calculatrice": CALCULATOR_APPID})
    def test_french_calculator_name_matches_english_request(self, _entries) -> None:
        self.assertEqual(actions.find_app("Calculator"), ("calculatrice", CALCULATOR_APPID))

    @patch.object(actions, "_app_entries", return_value={"calculatrice": CALCULATOR_APPID})
    def test_unrelated_app_is_still_missing(self, _entries) -> None:
        self.assertIsNone(actions.find_app("Notepad"))

    @patch.object(actions.subprocess, "run")
    def test_windows_start_apps_decodes_utf8_names(self, run) -> None:
        run.return_value.stdout = json.dumps(
            [{"Name": "Calculatrice", "AppID": CALCULATOR_APPID},
             {"Name": "Éditeur de texte", "AppID": "Fake.Editor"}], ensure_ascii=False)
        actions._START_APPS = (0.0, {})
        try:
            apps = actions._windows_start_apps()
        finally:
            actions._START_APPS = (0.0, {})
        self.assertEqual(apps.get("calculatrice"), CALCULATOR_APPID)
        self.assertEqual(run.call_args.kwargs.get("encoding"), "utf-8")


if __name__ == "__main__":
    unittest.main()
