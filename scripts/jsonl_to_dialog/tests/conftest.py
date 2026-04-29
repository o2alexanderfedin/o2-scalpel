"""Make `scripts.jsonl_to_dialog.renderer` importable when pytest is run from
the repo root without an installed package.

Adds the repo root to sys.path so `from scripts.jsonl_to_dialog.renderer import …`
resolves regardless of pytest's rootdir detection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
