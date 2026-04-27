"""CHANGELOG must document the P5a cold-daemon caveat per outcome B."""
from __future__ import annotations

from pathlib import Path

CHANGELOG = Path("CHANGELOG.md").read_text(encoding="utf-8")


def test_changelog_has_unreleased_section() -> None:
    assert "## [Unreleased]" in CHANGELOG


def test_changelog_documents_pylsp_mypy_cold_start_caveat() -> None:
    assert "pylsp-mypy" in CHANGELOG
    assert "live_mode: false" in CHANGELOG
    assert "dmypy: true" in CHANGELOG
    assert "first didSave after long idle" in CHANGELOG
