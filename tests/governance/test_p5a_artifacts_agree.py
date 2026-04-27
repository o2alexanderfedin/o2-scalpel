"""Single integration assertion: all three P5a artifacts agree on SHIP."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "vendor" / "serena" / "src"))

from solidlsp.decisions.p5a_mypy import P5A_MYPY_DECISION  # noqa: E402

PROGRESS = (REPO_ROOT / "docs/superpowers/plans/spike-results/PROGRESS.md").read_text(
    encoding="utf-8"
)
PYLSP_SERVER = (
    REPO_ROOT / "vendor/serena/src/solidlsp/language_servers/pylsp_server.py"
).read_text(encoding="utf-8")


def test_decision_record_says_ship() -> None:
    assert P5A_MYPY_DECISION.outcome == "SHIP"


def test_progress_log_says_ship() -> None:
    assert "pylsp-mypy is shipped in the MVP active Python LSP set" in PROGRESS


def test_pylsp_server_consumes_decision_record() -> None:
    assert "P5A_MYPY_DECISION.pylsp_initialization_options" in PYLSP_SERVER
    assert '"pylsp_mypy": {"enabled": False}' not in PYLSP_SERVER
