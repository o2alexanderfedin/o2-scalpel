"""Cross-artifact lock: PROGRESS.md §70 must reflect SHIP."""
from __future__ import annotations
from pathlib import Path

PROGRESS = Path("docs/superpowers/plans/spike-results/PROGRESS.md").read_text("utf-8")


def test_progress_md_marks_2026_04_24_row_superseded() -> None:
    # Append-only ledger: original row must remain, prefixed as superseded.
    assert "**Superseded by 2026-04-26 row below**" in PROGRESS
    assert "pylsp-mypy is dropped from the MVP active Python LSP set" in PROGRESS


def test_progress_md_records_ship_outcome_with_rerun_measurements() -> None:
    assert "pylsp-mypy is shipped in the MVP active Python LSP set" in PROGRESS
    assert "stale_rate 0.00%" in PROGRESS
    assert "p95 2.668s" in PROGRESS


def test_progress_md_quick_reference_row_reads_ship() -> None:
    assert "| P5a | B (ship pylsp-mypy with documented warning)" in PROGRESS
