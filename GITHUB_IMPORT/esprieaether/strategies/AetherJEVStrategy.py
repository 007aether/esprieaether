# AetherJEVStrategy — freqtrade strategy that asks the JEV brain for the call
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path.home() / "Desktop" / "esprieaether" / "src"))

from freqtrade.strategy import IStrategy  # noqa: E402
from pandas import DataFrame  # noqa: E402

ROUTER = "http://127.0.0.1:11435/decide"


class AetherJEVStrategy(IStrategy):
    """
    Every candle close, ask JEV: buy / sell / hold.
    JEV sees last 20 closes + the current position, returns a typed decision
    with a confidence. We act only above min_confidence.
    """

    timeframe = "1h"
    minimal_roi = {"0": 0.04}
    stoploss = -0.04
    trailing_stop = True
    process_only_new_candles = True
    startup_candle_count = 20
    can_short = False

    min_confidence = 0.60

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def _ask_jev(self, closes: list) -> tuple[str, float]:
        state = {
            "closes": [round(c, 2) for c in closes],
            "pair": metadata_pair,
        }
        questions = {
            "action": {
                "type": "choice",
                "instructions": "Based on the last 20 closes, what spot action now?",
                "criteria": {
                    "buy": "Momentum + structure favour buying",
                    "sell": "Momentum + structure favour selling",
                    "hold": "No clear edge",
                },
            }
        }
        try:
            r = requests.post(ROUTER, json={"state": state, "questions": questions}, timeout=25)
            ans = r.json().get("answers", {}).get("action", {})
            return ans.get("choice", "hold"), ans.get("confidence", 0.0)
        except Exception:
            return "hold", 0.0

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        metadata_pair = metadata["pair"]
        df = dataframe.copy()
        df["enter_long"] = 0
        for i in range(self.startup_candle_count, len(df)):
            closes = df["close"].iloc[i - self.startup_candle_count:i].tolist()
            action, conf = self._ask_jev(closes)
            if action == "buy" and conf >= self.min_confidence:
                df.iloc[i, df.columns.get_loc("enter_long")] = 1
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        metadata_pair = metadata["pair"]
        df = dataframe.copy()
        df["exit_long"] = 0
        for i in range(self.startup_candle_count, len(df)):
            closes = df["close"].iloc[i - self.startup_candle_count:i].tolist()
            action, conf = self._ask_jev(closes)
            if action == "sell" and conf >= self.min_confidence:
                df.iloc[i, df.columns.get_loc("exit_long")] = 1
        return df
