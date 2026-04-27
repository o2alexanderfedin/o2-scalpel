# Leaf 02 — rust-analyzer Position Validation Helper

> **STATUS: SHIPPED 2026-04-26** — see `stage-v0.2.0-followups-complete` tag (parent + submodule). Cross-reference: `docs/gap-analysis/WHAT-REMAINS.md` §4 line 105 + `docs/superpowers/plans/stage-1h-results/PROGRESS.md` §86.
>
> **Implementation deviations from this plan** (recorded post-shipment):
> - `whole_file_range` conftest fixture shipped DUAL-MODE rather than single-mode (parametrized via `indirect=True` OR backwards-compat fallback). Spec compliance review approved this; subsequent review I3 reverted it to single-mode (see commit `8b7e8aac`).
> - Adapter test uses `RustAnalyzer.__new__()` + `patch.object` to mock `super().request_code_actions` instead of integration-style booted RA test (faster + verifies preflight without LSP round-trip).

**Goal.** Ship `compute_file_range(path) -> (start, end)` so the 16 deferred Rust integration tests stop duplicating end-of-file coordinate math, and rust-analyzer's strict out-of-range rejection is centrally validated. Closes WHAT-REMAINS.md §4 line 103 and the Stage 1H follow-up at `stage-1h-results/PROGRESS.md:86`.

**Architecture.** The existing `whole_file_range` conftest fixture (`vendor/serena/test/integration/conftest.py:185`) is hard-coded for a single Python sample (`del whole_file_range  # unused on Rust path` in `test_smoke_rust_codeaction.py:43`). We move the math into a pure helper next to the rust-analyzer adapter so it can be imported by Rust integration tests and by the adapter itself for pre-flight position validation.

**Tech Stack.** Python 3.13, pytest, hypothesis (already in dev deps). Reference rust-analyzer adapter at `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py`.

**Source spec.** `stage-1h-results/PROGRESS.md:86` ("compute_file_range(path) -> (start, end) helper to remove duplication across the 16 deferred Rust tests").

**Author.** AI Hive(R).

## File Structure

| Path | Action | Approx LoC |
|------|--------|------------|
| `vendor/serena/src/solidlsp/util/file_range.py` | new — pure helper | ~60 |
| `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py` | edit — preflight validation in `request_code_actions` | ~15 |
| `vendor/serena/test/solidlsp/util/test_file_range.py` | new — unit tests | ~140 |
| `vendor/serena/test/integration/conftest.py` | edit — `whole_file_range` delegates to helper | ~5 |

## Tasks

### Task 1 — Failing unit tests for `compute_file_range`

Create `vendor/serena/test/solidlsp/util/test_file_range.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from solidlsp.util.file_range import compute_file_range


def test_empty_file_returns_zero_zero(tmp_path: Path) -> None:
    p = tmp_path / "empty.rs"
    p.write_text("", encoding="utf-8")
    start, end = compute_file_range(p)
    assert start == {"line": 0, "character": 0}
    assert end == {"line": 0, "character": 0}


def test_single_line_no_trailing_newline(tmp_path: Path) -> None:
    p = tmp_path / "one.rs"
    p.write_text("fn main() {}", encoding="utf-8")
    start, end = compute_file_range(p)
    assert start == {"line": 0, "character": 0}
    assert end == {"line": 0, "character": 12}


def test_multiline_with_trailing_newline(tmp_path: Path) -> None:
    p = tmp_path / "two.rs"
    p.write_text("fn a() {}\nfn b() {}\n", encoding="utf-8")
    start, end = compute_file_range(p)
    assert end == {"line": 2, "character": 0}


def test_crlf_line_endings(tmp_path: Path) -> None:
    p = tmp_path / "crlf.rs"
    p.write_bytes(b"a\r\nb\r\n")
    _, end = compute_file_range(p)
    # rust-analyzer treats LF as line break per LSP §3.17 PositionEncoding;
    # CRLF counts as one line break too.
    assert end == {"line": 2, "character": 0}


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compute_file_range(tmp_path / "nope.rs")
```

Run `uv run pytest vendor/serena/test/solidlsp/util/test_file_range.py -x` — confirm `ModuleNotFoundError`. Stage test only.

### Task 2 — Implement `compute_file_range`

Create `vendor/serena/src/solidlsp/util/file_range.py`:

```python
"""LSP-compliant whole-file range computation for position-strict servers
like rust-analyzer (which rejects out-of-range positions per LSP §3.17).
"""
from __future__ import annotations

from pathlib import Path

LSPPosition = dict[str, int]


def compute_file_range(path: Path) -> tuple[LSPPosition, LSPPosition]:
    """Return (start, end) LSP positions covering the entire file.

    Encoding follows LSP default (UTF-16); for ASCII-only fixtures this is
    identical to UTF-8 character counts. CRLF is treated as one line
    terminator.
    """
    text = path.read_text(encoding="utf-8")
    if not text:
        return ({"line": 0, "character": 0}, {"line": 0, "character": 0})

    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    last_index = len(lines) - 1
    last_char = len(lines[-1])
    return (
        {"line": 0, "character": 0},
        {"line": last_index, "character": last_char},
    )
```

Run `uv run pytest vendor/serena/test/solidlsp/util/test_file_range.py -x` — five green. Commit `feat(stage-v0.2.0-followup-02a): compute_file_range LSP helper`.

### Task 3 — Failing adapter test for preflight rejection

Append to `vendor/serena/test/solidlsp/rust/test_rust_analyzer_detection.py`:

```python
import pytest

from solidlsp.language_servers.rust_analyzer import RustAnalyzer


def test_request_code_actions_rejects_out_of_range_position(
    rust_analyzer_booted,
    calcrs_root,
):
    bad_end = {"line": 9_999_999, "character": 0}
    with pytest.raises(ValueError, match="out of range"):
        rust_analyzer_booted.request_code_actions(
            file=str(calcrs_root / "src" / "lib.rs"),
            range_start={"line": 0, "character": 0},
            range_end=bad_end,
        )
```

Run — confirm failure (no preflight check). Stage only.

### Task 4 — Wire preflight validation into the adapter

Edit `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py`, locate `request_code_actions` (line ≈729 in `ls.py` base; the rust adapter overrides at the same name). Add at top:

```python
from solidlsp.util.file_range import compute_file_range

def request_code_actions(self, file, range_start, range_end, *args, **kwargs):
    _, eof = compute_file_range(Path(file))
    if (range_end["line"], range_end["character"]) > (eof["line"], eof["character"]):
        raise ValueError(
            f"position {range_end} out of range for {file} (eof={eof})"
        )
    return super().request_code_actions(file, range_start, range_end, *args, **kwargs)
```

Run `uv run pytest vendor/serena/test/solidlsp/rust/test_rust_analyzer_detection.py -x` — green. Commit `feat(stage-v0.2.0-followup-02b): rust-analyzer preflight position validation`.

### Task 5 — Migrate conftest fixture to delegate

Edit `vendor/serena/test/integration/conftest.py:185`:

```python
@pytest.fixture
def whole_file_range(request):
    from solidlsp.util.file_range import compute_file_range
    target = request.param if hasattr(request, "param") else None
    if target is None:
        pytest.skip("whole_file_range requires parametrized file path")
    return compute_file_range(Path(target))
```

Re-run the smoke tests `uv run pytest vendor/serena/test/integration/test_smoke_python_codeaction.py vendor/serena/test/integration/test_smoke_rust_codeaction.py -x` — green. Commit `refactor(stage-v0.2.0-followup-02c): conftest whole_file_range uses helper`.

## Self-Review Checklist

- [ ] Helper covers empty / single-line / multi-line / CRLF / missing.
- [ ] Adapter raises ValueError before sending to rust-analyzer (no LSP round-trip on bad input).
- [ ] No regressions in existing smoke tests.
- [ ] No emoji, sizes-only, author = AI Hive(R).
