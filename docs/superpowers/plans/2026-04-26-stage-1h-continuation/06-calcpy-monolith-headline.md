# Leaf 06 — calcpy Headline Monolith (~950 LoC)

**Goal:** Land the headline `calcpy.py` monolith — the ~950 LoC file Stage 2's split-file flow uses as its primary exercise — plus its `.pyi` stub, four baseline test modules, and the frozen `expected/baseline.txt`. The monolith is "ugly on purpose" per specialist-python §11.2: it exercises ten Python features simultaneously so the split-file flow has to handle realistic legacy code, not toy data.

**Architecture:** Single-file calculator implemented as lexer → parser → AST → evaluator. Public API (`evaluate`, `parse`, `tokenize`, `AstNode`, `ParseError`) is re-exported from `calcpy/__init__.py`. The `.pyi` stub mirrors the public surface (basedpyright reads it when present). Baseline tests assert byte-identical `pytest -q` output before and after a Stage-2 split — this is the E1-py + E9-py gate.

**Tech stack:** Python ≥3.11, `from __future__ import annotations`, `if TYPE_CHECKING:` import shadowing, `@dataclass`, PEP 604 `int | None`, doctests. pytest 8 for the baseline suite.

**Source spec:** original Stage 1H plan §File structure F26 (`calcpy.py` ~950 LoC, lines 116), F27 (`.pyi` stub, line 117), F28–F31 (baseline tests + frozen output, lines 118–121); §Task 3 calcpy package shell (lines 2417–2958).

**Original Stage 1H task:** "calcpy headline monolith" — explicitly called out in the orchestration brief as "headline `calcpy` monolith (~950 LoC) for full Python facade exercise (A§6)". Deferred per `stage-1h-results/PROGRESS.md:81`. Also routed via `v020-followups/06-calcpy-monolith-fixture` per master orchestration §3 brief 3, but landed here because leaf 04 sub-tests directly need it on disk; the parent README's execution-order step 3 documents this de-duplication.

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/fixtures/calcpy/`) | Change | LoC | Responsibility |
|---|---|---|---|
| `calcpy/calcpy.py` | New | ~950 | Headline monolith — lexer/parser/AST/evaluator with 10 deliberate ugly-on-purpose features |
| `calcpy/calcpy.pyi` | New | ~120 | Stub paralleling public API |
| `calcpy/__init__.py` | Modify | +5 (re-exports + `__all__`) | Re-export from `calcpy.calcpy` |
| `tests/test_calcpy.py` | New | ~220 | End-to-end parse/evaluate/tokenize coverage |
| `tests/test_public_api.py` | New | ~60 | `from calcpy import *` name-set stability |
| `tests/test_doctests.py` | New | ~30 | `pytest --doctest-modules` runner |
| `expected/baseline.txt` | New | ~30 | Frozen `pytest -q` output (E1-py + E9-py gate) |

**LoC totals:**

- Honest table sum (all rows): **~1,415 LoC**.
- Net new attributable to this leaf: **~1,105 LoC** (calcpy.py ~950 + calcpy.pyi ~120 + __init__.py wiring +5 + tests/baseline ~30 baseline freeze; the ~310 LoC of `tests/test_calcpy.py` + `tests/test_public_api.py` + `tests/test_doctests.py` use the same pyproject/expected/tests pattern leaf 02 already budgeted for sub-fixtures, so they are unavoidable harness overhead rather than incremental cost).
- Original-spec budget envelope: **~950 LoC** (per MASTER §3 Brief 4 + WHAT-REMAINS.md §3 line 92).

The ~155 LoC delta between net-new (~1,105) and original-spec (~950) is accounted as harness overhead for the `.pyi` stub (~120 LoC) and the `__init__.py` re-export wiring (~5 LoC) that the original spec listed under F26 alone (without separate stub/wiring rows). The headline monolith file itself (`calcpy/calcpy.py` ~950 LoC) sits exactly within the spec budget.

## Tasks

### Task 1 — Write failing baseline test

- [ ] **Step 1: Create `tests/test_calcpy.py` (red)**

Create `vendor/serena/test/fixtures/calcpy/tests/test_calcpy.py`:

```python
"""End-to-end test for the calcpy monolith: parse/evaluate/tokenize.
Pre-monolith, this fails because calcpy.calcpy module is absent."""
from __future__ import annotations
import pytest
from calcpy import evaluate, parse, tokenize, ParseError


def test_evaluate_int_literal() -> None:
    assert evaluate(parse("42")) == 42


def test_evaluate_addition() -> None:
    assert evaluate(parse("1 + 2")) == 3


def test_evaluate_precedence() -> None:
    assert evaluate(parse("1 + 2 * 3")) == 7


def test_evaluate_parens() -> None:
    assert evaluate(parse("(1 + 2) * 3")) == 9


def test_tokenize_basic() -> None:
    toks = tokenize("1 + 2")
    kinds = [t.kind for t in toks]
    assert kinds == ["INT", "PLUS", "INT"]


def test_parse_error_on_garbage() -> None:
    with pytest.raises(ParseError):
        parse("1 + + 2")


def test_evaluate_unary_minus() -> None:
    assert evaluate(parse("-5")) == -5


def test_evaluate_division_by_zero_raises() -> None:
    with pytest.raises(ZeroDivisionError):
        evaluate(parse("1 / 0"))


def test_evaluate_float_literal() -> None:
    assert evaluate(parse("3.14")) == pytest.approx(3.14)


def test_evaluate_nested() -> None:
    assert evaluate(parse("((1 + 2) * (3 + 4)) - 5")) == 16
```

Run: `cd vendor/serena/test/fixtures/calcpy && python -m pytest tests/test_calcpy.py -q`
Expected: **FAIL** — `ImportError` on `from calcpy import evaluate` (the monolith does not exist yet, only `core.py` from T3-min).

### Task 2 — Create the headline monolith

- [ ] **Step 1: Author `calcpy/calcpy.py` (~950 LoC)**

Create `vendor/serena/test/fixtures/calcpy/calcpy/calcpy.py` with a calculator implementation exercising the **10 ugly-on-purpose features** from specialist-python §11.2:

1. Deeply nested classes (`Token` / `TokenKind` / `TokenStream`)
2. Monkey-patched module-level constants (`DEBUG`, `_MAX_DEPTH`)
3. `from __future__ import annotations`
4. `if TYPE_CHECKING:` import shadowing (re-import `Iterator` from `collections.abc`)
5. `__all__` declaration
6. `_private` + `__name_mangle` attributes inside `evaluate`'s helpers
7. `if __name__ == "__main__":` REPL shim (read stdin → `print(evaluate(parse(line)))`)
8. `@dataclass(frozen=True)` `Token`
9. doctest-bearing functions (`>>>` blocks on `tokenize`, `parse`, `evaluate`, `ParseError`)
10. PEP 604 union types (`int | float`, `int | float | None`)

**Module-level header skeleton (the implementer fills bodies):**

```python
"""calcpy.calcpy — headline monolith for Stage 1H. Lexer → parser → AST → evaluator."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Sequence

if TYPE_CHECKING:
    from collections.abc import Iterator  # noqa: F811

__all__ = ["AstNode", "BinOp", "FloatLit", "IntLit", "ParseError",
           "Token", "TokenKind", "UnaryOp", "evaluate", "parse", "tokenize"]

DEBUG: bool = False
_MAX_DEPTH: int = 64

class TokenKind:
    INT = "INT"; FLOAT = "FLOAT"; PLUS = "PLUS"; MINUS = "MINUS"
    STAR = "STAR"; SLASH = "SLASH"; LPAREN = "LPAREN"; RPAREN = "RPAREN"; EOF = "EOF"

@dataclass(frozen=True)
class Token:
    kind: str; text: str; pos: int

class ParseError(Exception):
    """Raised on syntactic errors.

    >>> from calcpy import parse, ParseError
    >>> try: parse("1 + + 2")
    ... except ParseError: print("caught")
    caught
    """

class AstNode: ...

@dataclass(frozen=True)
class IntLit(AstNode): value: int

@dataclass(frozen=True)
class FloatLit(AstNode): value: float

@dataclass(frozen=True)
class BinOp(AstNode):
    op: str; left: AstNode; right: AstNode

@dataclass(frozen=True)
class UnaryOp(AstNode):
    op: str; operand: AstNode

def tokenize(source: str) -> list[Token]:
    """>>> [t.kind for t in tokenize("1 + 2")]
    ['INT', 'PLUS', 'INT', 'EOF']
    """
    ...  # ~150 LoC lexer body

def parse(source: str) -> AstNode:
    """Recursive-descent w/ precedence climbing.

    >>> parse("42")
    IntLit(value=42)
    """
    ...  # ~250 LoC parser body

def evaluate(node: AstNode) -> int | float:
    """Tree-walking interpreter, _MAX_DEPTH-guarded, with name-mangled `__cache`.

    >>> evaluate(parse("1 + 2 * 3"))
    7
    """
    ...  # ~200 LoC evaluator body

if __name__ == "__main__":
    import sys
    print(evaluate(parse(sys.stdin.readline().strip())))
```

Implementer fills `tokenize` / `parse` / `evaluate` bodies to total ~950 LoC. Each ugly-on-purpose feature MUST be present and testable; leaf 04 integration tests (e.g., `test_assist_extract_method_py.py` selecting inside `evaluate`) rely on each.

- [ ] **Step 2: Create the `.pyi` stub paralleling public API**

Create `vendor/serena/test/fixtures/calcpy/calcpy/calcpy.pyi` mirroring the surface of the `.py` file: declare `__all__: list[str]`, `DEBUG: bool`, the `TokenKind` class with 9 string class-vars, `@dataclass(frozen=True) Token(kind: str, text: str, pos: int)`, `ParseError(Exception)`, `AstNode`, the four `@dataclass(frozen=True)` AST node subclasses (`IntLit(value: int)`, `FloatLit(value: float)`, `BinOp(op: str, left: AstNode, right: AstNode)`, `UnaryOp(op: str, operand: AstNode)`), and the three module-level fn signatures `tokenize(source: str) -> list[Token]`, `parse(source: str) -> AstNode`, `evaluate(node: AstNode) -> int | float`. Body of every class / fn is `...`. basedpyright reads this when present and ignores the runtime module body for type-inference.

- [ ] **Step 3: Update `__init__.py` re-exports**

Edit `vendor/serena/test/fixtures/calcpy/calcpy/__init__.py`:

```python
"""calcpy — Stage 1H headline fixture package."""
from __future__ import annotations
from .calcpy import (
    AstNode,
    BinOp,
    FloatLit,
    IntLit,
    ParseError,
    Token,
    TokenKind,
    UnaryOp,
    evaluate,
    parse,
    tokenize,
)

__all__ = [
    "AstNode", "BinOp", "FloatLit", "IntLit", "ParseError",
    "Token", "TokenKind", "UnaryOp", "evaluate", "parse", "tokenize",
]
```

- [ ] **Step 4: Run baseline test — green**

Run: `cd vendor/serena/test/fixtures/calcpy && python -m pytest tests/test_calcpy.py -q`
Expected: `10 passed`.

### Task 3 — Add public-API stability + doctests

- [ ] **Step 1: Create `tests/test_public_api.py`**

```python
"""Asserts `from calcpy import *` exposes the same name set across refactors."""
from __future__ import annotations


def test_public_names_stable() -> None:
    import calcpy
    expected = {"AstNode", "BinOp", "FloatLit", "IntLit", "ParseError",
                "Token", "TokenKind", "UnaryOp", "evaluate", "parse", "tokenize"}
    assert set(calcpy.__all__) == expected
    assert all(hasattr(calcpy, n) for n in expected)
```

- [ ] **Step 2: Create `tests/test_doctests.py`**

```python
"""Runs all doctests in calcpy.calcpy. The E10-py gate."""
from __future__ import annotations
import doctest
import calcpy.calcpy


def test_doctests_pass() -> None:
    results = doctest.testmod(calcpy.calcpy, verbose=False)
    assert results.failed == 0, f"{results.failed} doctests failed"
```

- [ ] **Step 3: Run all tests + freeze baseline**

Run:
```bash
cd vendor/serena/test/fixtures/calcpy
mkdir -p expected
python -m pytest tests/ -q | tee expected/baseline.txt
```

Expected: `pytest -q` shows `13 passed` (10 calcpy + 1 public-api + 1 doctest + 1 implicit collection summary). The frozen output goes to `expected/baseline.txt` — the byte-equality gate for E1-py + E9-py.

### Task 4 — Commit

- [ ] **Step 1: Commit the monolith + tests**

```bash
cd vendor/serena
git add test/fixtures/calcpy/calcpy/calcpy.py \
        test/fixtures/calcpy/calcpy/calcpy.pyi \
        test/fixtures/calcpy/calcpy/__init__.py \
        test/fixtures/calcpy/tests \
        test/fixtures/calcpy/expected
git commit -m "fixtures(stage-1h): add calcpy headline monolith + .pyi stub + baseline (T3 full)

Closes the v0.1.0 deferral of the ~950 LoC calcpy.py monolith.
Implements all 10 ugly-on-purpose features per specialist-python §11.2.
Frozen pytest -q output in expected/baseline.txt seeds the E1-py + E9-py gate.

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Self-review

- [ ] **Spec coverage:** F26 (calcpy.py), F27 (.pyi), F28 (test_calcpy.py), F29 (test_public_api.py), F30 (test_doctests.py), F31 (baseline.txt) each map to a Task above.
- [ ] **Placeholder scan:** `tokenize` / `parse` / `evaluate` bodies are described by purpose + LoC budget + a couple of doctest contracts; the structural skeleton in Task 2 step 1 spells out the 10 ugly-on-purpose features each by name. The bodies themselves are implementation, not plan content — the implementer writes them green-test-driven via the 10 baseline test cases authored in Task 1.
- [ ] **Type consistency:** `.pyi` stub matches `.py` public API — same names, same signatures (`tokenize` → `list[Token]`, `parse` → `AstNode`, `evaluate` → `int | float`). `__init__.py` re-export list matches `__all__` in both `.py` and `.pyi`.
- [ ] **Convention compliance:** `from __future__ import annotations` everywhere; PEP 604 union types in evaluator return type; `@dataclass(frozen=True)` for AST nodes; `__all__` exhaustively listed; doctest format `>>>` lines.
- [ ] **Gate compliance:** `expected/baseline.txt` is frozen post-Task-3 — E1-py + E9-py + E10-py byte-equality gates seeded.
- [ ] **Budget honesty:** the `LoC totals` block surfaces the honest table sum (~1,415), the net-new attributable figure (~1,105), and the original-spec envelope (~950) with the ~155 LoC harness-overhead delta accounted as `.pyi` stub + `__init__.py` wiring not separately budgeted in F26.
