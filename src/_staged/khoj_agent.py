"""
This module implements a lightweight autonomous data‑gathering agent for the
EsprieAether system, inspired by the concepts from khoj‑ai/khoj.

في هذا الوحدات يتم تنفيذ مختلف الأنشطة التي يطلبها  نظام
"EsprieAether" من الوكيل المستقل، مع الالتزام بالاشتراطات التالية:
- لا يُصنع أي اتصال شبكة غير مبرمج يحدد عنوانه ضمن ثوابت الوحدات.
- لا تُحفظ أو تُنقل تفاصيل حساسة، ولا تُجرى عمليات مدمرة على الجهاز.
- تم الاعتماد على مكتبات الجايثون القياسية فقط، لتفادي المتطلبات البرمجية الخارجية.
- يُراعى كفاءة التوثيق والتعليق على الشيفرة لضمان سهولة الصيانة.
"""

import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: تردد التقاط البيانات بالدقائق. يحدد الفاصل الزمني للعمليات أوجادة
INTERVAL_MIN: int = 15

#: العلامات التي تصف الوكيل والوحدة، تُستعمل للفلترة أو التصنيف
TAGS: List[str] = [
    "esprit",        # نمط (Esprie) – تعريف الوكيل
    "aether",        # البيئة (Aether) – منشئ الواجهة
    "khoj",          # إشارة إلى لايف ريسورس
    "autonomous",    # ليعبر عن العميل الذكي
]

#: عنوان URL (أو غيرها) الذي قد يُستعمل لاحقًا لرفع البيانات إلى الخادم
# انتبه: هذه متغير ثابت لتجنب استدعاء الشبكة دون عنوان محدد مسبقاً.
COLLECTION_ENDPOINT: str = "https://example.com/api/collect"

# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def gather() -> Dict[str, str]:
    """
    Collect system diagnostic information that can be used by the EsprieAether
    autonomous agent.  The function intentionally gathers only basic,
    non‑sensitive data such as platform details, Python version, and
    environment variables.

    Returns
    -------
    dict
        A dictionary containing the following keys:
            - ``timestamp``: ISO‑8601 UTC timestamp of data collection.
            - ``os``: Name of the operating system.
            - ``platform``: Detailed platform identifier.
            - ``python_version``: The Python interpreter version.
            - ``tags``: The module's :data:`TAGS` constant.
            - ``environment``: A dictionary of selected environment variables
              that are considered safe to expose.

    Notes
    -----
    * No network operations are performed; the emerging data simply
      stays in memory.  The :data:`COLLECTION_ENDPOINT` constant
      exists only as a placeholder to illustrate where an endpoint might
      be used in a fuller implementation.

    * The function is deliberately conservative: it only copies environment
      variables that match a whitelist pattern to avoid leaking secrets.
    """
    # --- Core system info ------------------------------------------- #
    timestamp = datetime.now(timezone.utc).isoformat()
    os_name = os.name
    platform_info = platform.platform()
    py_version = sys.version.split()[0]  # Just the version number

    # --- Environment variables ------------------------------------- #
    # Whitelist for safe env variables; expands to avoid accidental leaks.
    safe_env_prefixes = ("HOME", "USER", "PATH", "PYTHONPATH")
    env_filtered: Dict[str, str] = {
        k: v for k, v in os.environ.items()
        if any(k.startswith(prefix) for prefix in safe_env_prefixes)
    }

    # --- Assemble data ---------------------------------------------- #
    data = {
        "timestamp": timestamp,
        "os": os_name,
        "platform": platform_info,
        "python_version": py_version,
        "tags": ",".join(TAGS),
        "environment": env_filtered,
    }

    return data

def main() -> int:
    """
    Entry point for manual testing.  It simply calls :func:`gather`,
    prints the resulting dictionary, and exits with status code 0.
    """
    info = gather()
    # Format output neatly
    for key, value in sorted(info.items()):
        if key == "environment":
            print(f"{key}:")
            for env_k, env_v in sorted(value.items()):
                print(f"  {env_k}={env_v}")
        else:
            print(f"{key} = {value}")
    return 0

# --------------------------------------------------------------------------- #
# Self-test (executed only when run as a script)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    sys.exit(main())