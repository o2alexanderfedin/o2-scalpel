# Leaf 02 — T4–T6: 3 calcpy Sub-Fixtures

**Goal:** Land the 3 calcpy sub-fixtures the v0.1.0 cut deferred — `calcpy_circular`, `calcpy_dataclasses`, `calcpy_notebooks` — atop the existing `vendor/serena/test/fixtures/calcpy/core.py` skeleton (which T3-min shipped) and alongside the `calcpy_namespace/` sub-fixture which was deferred not shipped. Each sub-fixture is its own pip-installable package with its own `pyproject.toml` and `expected/baseline.txt` so per-fixture isolation matches the original plan's "every sub-fixture has its own pyproject.toml so `pip install -e .` works without leaking deps cross-fixture" rule.

**Architecture:** Three independent Python packages. `calcpy_circular` exercises the lazy-import-trap detection path (extract_function strategy must NOT promote the lazy import to top-level). `calcpy_dataclasses` exercises the inline strategy across 5 `@dataclass` declarations with one extracted to a sub-module. `calcpy_notebooks` exercises the organize-imports flow with a `.ipynb` companion file the strategy detects and warns about without rewriting cells.

**Tech stack:** Python ≥3.11, pydantic v2 at fixture boundaries, pytest, hatchling-built packages. Each fixture roots at `vendor/serena/test/fixtures/<name>/` and is invocable from either the repo root or `vendor/serena/`.

**Source spec:** original Stage 1H plan §File structure F33–F35 (lines 123–125) and §Tasks 4–6 (lines 2959–3471).

**Original Stage 1H tasks:** **T4** (`calcpy_circular`), **T5** (`calcpy_dataclasses`), **T6** (`calcpy_notebooks`). All three deferred per `stage-1h-results/PROGRESS.md:16–18`.

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/fixtures/`) | Change | LoC | Responsibility |
|---|---|---|---|
| `calcpy_circular/pyproject.toml` | New | ~20 | hatchling package manifest |
| `calcpy_circular/__init__.py` | New | ~10 | re-export `from .a import compute` |
| `calcpy_circular/a.py` | New | ~25 | top-level fn that lazy-imports `b` inside the body |
| `calcpy_circular/b.py` | New | ~25 | top-level fn that lazy-imports `a` inside the body |
| `calcpy_circular/tests/test_circular.py` | New | ~25 | round-trip test that fails if either lazy import is promoted to top-level |
| `calcpy_circular/expected/baseline.txt` | New | ~5 | frozen `pytest -q` output |
| `calcpy_dataclasses/pyproject.toml` | New | ~20 | manifest |
| `calcpy_dataclasses/__init__.py` | New | ~15 | re-exports |
| `calcpy_dataclasses/models.py` | New | ~120 | 4 `@dataclass` declarations + 1 nested |
| `calcpy_dataclasses/sub/__init__.py` | New | ~5 | namespace marker |
| `calcpy_dataclasses/sub/extracted.py` | New | ~30 | the 5th dataclass already extracted (target shape) |
| `calcpy_dataclasses/tests/test_dc.py` | New | ~50 | byte-equality of dataclass `__repr__` pre/post inline-flow |
| `calcpy_dataclasses/expected/baseline.txt` | New | ~5 | frozen baseline |
| `calcpy_notebooks/pyproject.toml` | New | ~20 | manifest with `nbformat` dep |
| `calcpy_notebooks/src/calcpy_min.py` | New | ~60 | small calculator-shaped module + import block ruff would reorder |
| `calcpy_notebooks/notebooks/explore.ipynb` | New | ~30 | minimal `nbformat==4.5`-shaped JSON; 2 code cells, 1 markdown cell |
| `calcpy_notebooks/tests/test_nb.py` | New | ~40 | asserts notebook bytes unchanged after running organize-imports on `src/calcpy_min.py` |
| `calcpy_notebooks/expected/baseline.txt` | New | ~5 | frozen baseline |

**LoC total:** ~510 raw + ~20 wiring = **~530**. The original-spec budget envelope is ~1,500 — the slack reserved for additional sub-fixture richness (extra dataclass variants, multi-cell notebook scenarios, deeper circular-import patterns) that the implementer may add during execution if needed.

## Tasks

### Task 1 — `calcpy_circular` sub-fixture (canonical pattern, full TDD cycle)

- [ ] **Step 1: Write failing pytest membership test**

Create `vendor/serena/test/fixtures/calcpy_circular/tests/test_circular.py`:

```python
"""Lazy-import-trap fixture. The test passes if a.compute() and b.echo()
both work despite a→b and b→a circular references; it fails if either
import has been promoted from function-body scope to module-top-level."""
from __future__ import annotations
import importlib
import pytest


def test_a_calls_b_lazily() -> None:
    a = importlib.import_module("calcpy_circular.a")
    assert a.compute(7) == 14  # a.compute calls b.double internally


def test_b_calls_a_lazily() -> None:
    b = importlib.import_module("calcpy_circular.b")
    assert b.echo("hi") == "echo:hi"


def test_no_top_level_cross_import() -> None:
    """If a refactor promoted the lazy import, this would ImportError on first import."""
    import importlib, sys
    for mod in ("calcpy_circular", "calcpy_circular.a", "calcpy_circular.b"):
        sys.modules.pop(mod, None)
    importlib.import_module("calcpy_circular.a")  # must not raise
    importlib.import_module("calcpy_circular.b")  # must not raise
```

Run: `cd vendor/serena/test/fixtures/calcpy_circular && python -m pytest tests/ -q`
Expected: **FAIL** — `ModuleNotFoundError: No module named 'calcpy_circular'`.

- [ ] **Step 2: Create `pyproject.toml`**

Create `vendor/serena/test/fixtures/calcpy_circular/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "calcpy-circular-fixture"
version = "0.0.0"
requires-python = ">=3.11"
description = "Stage 1H sub-fixture for circular-import-trap detection."

[tool.hatch.build.targets.wheel]
packages = ["calcpy_circular"]
```

- [ ] **Step 3: Create `calcpy_circular/__init__.py`**

Create `vendor/serena/test/fixtures/calcpy_circular/__init__.py`:

```python
"""calcpy_circular — circular-import-trap fixture for Stage 1H T4."""
from __future__ import annotations

__all__ = ["a", "b"]
```

- [ ] **Step 4: Create the lazy-import bodies**

Create `vendor/serena/test/fixtures/calcpy_circular/a.py`:

```python
"""Module a — calls b lazily to avoid circular-import ImportError."""
from __future__ import annotations


def compute(x: int) -> int:
    """Doubles via b.double (lazy import keeps the ref out of module scope)."""
    from calcpy_circular import b  # NOTE: lazy. DO NOT promote to top-level.
    return b.double(x)


def echo_local(s: str) -> str:
    return f"a:{s}"
```

Create `vendor/serena/test/fixtures/calcpy_circular/b.py`:

```python
"""Module b — calls a lazily to avoid circular-import ImportError."""
from __future__ import annotations


def double(n: int) -> int:
    return n * 2


def echo(s: str) -> str:
    """Delegates to a.echo_local (lazy import keeps the ref out of module scope)."""
    from calcpy_circular import a  # NOTE: lazy. DO NOT promote to top-level.
    return f"echo:{a.echo_local(s).split(':', 1)[1]}"
```

- [ ] **Step 5: Run test — green**

Run: `cd vendor/serena/test/fixtures/calcpy_circular && python -m pytest tests/ -q`
Expected: `3 passed`.

- [ ] **Step 6: Freeze baseline + commit**

Run:
```bash
cd vendor/serena/test/fixtures/calcpy_circular
mkdir -p expected
python -m pytest tests/ -q | tee expected/baseline.txt
```

Then:
```bash
cd vendor/serena
git add test/fixtures/calcpy_circular
git commit -m "fixtures(stage-1h): add calcpy_circular sub-fixture (T4)

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Task 2 — `calcpy_dataclasses` sub-fixture

Apply Task 1's 6-step cycle. Specifics:

**Test (`tests/test_dc.py`):**
```python
"""Five dataclasses; one already extracted to sub/extracted.py.
The inline-flow integration test (leaf 04 T19) asserts repr equality
pre/post inlining one of the four root dataclasses into a synthetic call site."""
from __future__ import annotations
from calcpy_dataclasses import models
from calcpy_dataclasses.sub import extracted


def test_root_dataclasses_count() -> None:
    import dataclasses
    cls_list = [c for c in vars(models).values() if dataclasses.is_dataclass(c)]
    assert len(cls_list) == 4


def test_extracted_dataclass_present() -> None:
    import dataclasses
    assert dataclasses.is_dataclass(extracted.Money)


def test_repr_contract() -> None:
    p = models.Point(1, 2)
    assert repr(p) == "Point(x=1, y=2)"
    m = extracted.Money(amount=10, currency="USD")
    assert repr(m) == "Money(amount=10, currency='USD')"
```

**`models.py`:** four `@dataclass` declarations — `Point(x: int, y: int)`, `User(id: int, name: str, email: str)`, `Order(id: int, total: int, items: tuple[str, ...])`, `Box(width: int, height: int, depth: int)`. Each has `__post_init__` validating non-negative numerics. One nested `Box` instance built in a module-level `DEFAULT_BOX = Box(...)` constant.

**`sub/extracted.py`:** the fifth dataclass — `Money(amount: int, currency: str)` with `__post_init__` validating `currency` length == 3.

### Task 3 — `calcpy_notebooks` sub-fixture

Apply Task 1's 6-step cycle. Specifics:

**Test (`tests/test_nb.py`):**
```python
"""calcpy_notebooks fixture: organize-imports applies to .py only,
.ipynb cell content must be byte-stable post-flow."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_notebook_is_valid_nbformat() -> None:
    payload = json.loads((ROOT / "notebooks" / "explore.ipynb").read_text())
    assert payload["nbformat"] == 4
    assert payload["nbformat_minor"] == 5
    assert len(payload["cells"]) == 3


def test_calcpy_min_module_imports_present() -> None:
    src = (ROOT / "src" / "calcpy_min.py").read_text()
    assert "import math" in src
    assert "from typing" in src


def test_baseline_notebook_hash() -> None:
    """Captured at fixture freeze; integration test re-checks post-flow."""
    h = hashlib.sha256((ROOT / "notebooks" / "explore.ipynb").read_bytes()).hexdigest()
    assert len(h) == 64  # sentinel — leaf 04 captures the actual hash
```

**`src/calcpy_min.py`:** ~60 LoC small calculator with imports deliberately out of canonical order (`from typing import Optional`, `import math`, `import os` — two of the three are unused so ruff `F401` fires).

**`notebooks/explore.ipynb`:** minimal `nbformat==4.5` JSON: cell 0 = markdown `# explore`, cell 1 = code `from calcpy_min import add; print(add(1,2))`, cell 2 = code with empty source. `metadata.kernelspec` set to a python3 entry. Use `nbformat.v4.new_notebook()` to generate; commit the resulting JSON byte-stable.

### Self-review

- [ ] **Spec coverage:** F33, F34, F35 each map to a task. F32 (`calcpy_namespace`) is already on disk per T3-min — confirmed by `vendor/serena/test/fixtures/calcpy_namespace/` listing.
- [ ] **Placeholder scan:** Task 1 has full code; Tasks 2–3 have full test code + content shape descriptions complete enough for the implementer to write `models.py` / `extracted.py` / `calcpy_min.py` / `explore.ipynb` directly.
- [ ] **Type consistency:** every fixture name in the LoC table matches the path used in the test file imports (`calcpy_circular`, `calcpy_dataclasses`, `calcpy_notebooks`).
- [ ] **Convention compliance:** each sub-fixture has its own `pyproject.toml`, `expected/baseline.txt`, and `tests/`.
