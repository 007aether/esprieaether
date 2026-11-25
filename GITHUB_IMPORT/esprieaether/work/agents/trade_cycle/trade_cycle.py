"""Trade Cycle — module entry point for ESPRIEAETHER

ضع هذا الملف بجانب /src/agents/ أو أضف المسار المطلوب، أو استدعِ loop.run_once().
مثال:
    from work.agents.trade_cycle.loop import run_once
    run_once()
"""

import os
import sys
from pathlib import Path

# المهيكل الحالي
BASE = Path(__file__).resolve().parent.parent
TC = BASE / "work" / "agents" / "trade_cycle"
sys.path.insert(0, str(TC))

from loop import run_once, run_once as loop_run_once  # noqa: E402

__all__ = ["run_once", "TC_DIR"]
