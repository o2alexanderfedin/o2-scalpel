# Python Playground — o2-scalpel E2E fixture workspace

This is the baseline Python project used by the o2-scalpel Python E2E
test suite (v1.3-C+).

> **DO NOT hand-edit these source files without updating the E2E
> assertions.** The test suite asserts on specific symbol names, line
> ranges, and file paths that match the baseline exactly. If you change
> the baseline, update the corresponding test in
> `vendor/serena/test/e2e/test_e2e_playground_python.py` in the same
> commit.
>
> The E2E suite refactors a **clone** of this directory (via
> `playground_python_root` fixture), never this source-controlled copy.

---

## Packages

| Package | Purpose |
|---------|---------|
| `src/calc/` | Minimal expression parser + evaluator. Split-file, rename, extract, and import-organize targets live here. |
| `src/lints/` | Lint-pattern helpers. Inline target lives here. |

---

## Facade targets at a glance

| Facade | File | Symbol / location |
|--------|------|-------------------|
| `scalpel_split_file` | `src/calc/ast.py` | multi-class module `Expr`, `Num`, `Add` → split into sibling files |
| `scalpel_rename_symbol` | `src/calc/parser.py` | `parse_expr` → `parse_expression` |
| `scalpel_extract` | `src/calc/eval.py` | `a + b` expression inside `evaluate` → helper `add_values` |
| `scalpel_inline` | `src/lints/core.py` | `sum_helper` (single call site in `report`) → inlined away |
| `scalpel_imports_organize` | `src/calc/eval.py` | disorganized imports → sorted/organized |

---

## Quickstart

```bash
# From the playground/python/ directory:
python -m pytest tests/
```

The baseline tests must pass on the unmodified source.

---

## How the E2E suite uses this workspace

1. The pytest fixture `playground_python_root` calls `shutil.copytree` to
   clone the entire workspace into `pytest`'s `tmp_path` directory.
   `__pycache__/`, `.venv/`, and `.pytest_cache/` are stripped post-copy
   to prevent stale bytecode from influencing LSP analysis.

2. The test invokes a facade (e.g. `scalpel_rename`) against the
   **clone** — never against this source-controlled directory.

3. After the refactor, the test asserts that files changed, that the
   applied payload carries `"applied": true`, and optionally runs
   `python -m pytest tests/` in the clone to confirm the package still
   passes.
