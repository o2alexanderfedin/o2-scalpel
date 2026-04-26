# P3a - basedpyright==1.39.3 green-bar baseline

**Pin:** `basedpyright==1.39.3` ([Q3 resolution](../../design/mvp/open-questions/q3-basedpyright-pinning.md))

**Errors (total):** 2  |  **Warnings (total):** 2
**Errors (excluding `_pep_syntax.py`):** 1  |  **Warnings (excl.):** 1
**Intentional-fixture diagnostics:** 2

**Sample diagnostics (first 3):**

```
[
  {
    "severity": "warning",
    "file": "__init__.py",
    "rule": "reportUnusedFunction",
    "message": "Function \"_private_helper\" is not accessed"
  },
  {
    "severity": "error",
    "file": "__init__.py",
    "rule": "reportAssignmentType",
    "message": "Type \"None\" is not assignable to declared type \"int\"\n\u00a0\u00a0\"None\" is not assignable to \"int\""
  },
  {
    "severity": "warning",
    "file": "_pep_syntax.py",
    "rule": "reportUnusedVariable",
    "message": "Variable \"eg\" is not accessed"
  }
]
```

**Version reported:**
- CLI (`basedpyright --version`): `basedpyright 1.39.3`
- JSON report (`report.version`): `1.39.3`

**`_pep_syntax.py` decision:** basedpyright 1.39.3 has no `--exclude` CLI flag
(verified via `--help`). The P3 fixture `_pep_syntax.py` contains an
intentional semantic violation (`return` inside `except*`). Rather than ship
a `pyrightconfig.json` to exclude one file, this spike runs the full seed
root and PARTITIONS diagnostics; errors outside `_pep_syntax.py` define the
green-bar baseline.

**Decision:** BASELINE ISSUE: 1 unexpected error(s) outside _pep_syntax.py.

**Re-run scope (Stage 1H):** full calcpy suite + sub-fixtures, same partitioning rule.
