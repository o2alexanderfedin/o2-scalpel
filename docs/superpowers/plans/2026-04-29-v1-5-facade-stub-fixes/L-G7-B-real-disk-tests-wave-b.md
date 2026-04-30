# Leaf L-G7-B — Real-disk test wave B (10 Python facades)

**Goal.** Mirror image of L-G7-A for the 10 Python facades that today have ZERO real-disk coverage. Each gets ≥1 acid-test (`Path.read_text()` post-apply with content assertion). Spec § Test discipline gaps.

**Facades covered (10):**

| # | Facade | LSP server | Test fixture base |
|---|---|---|---|
| 1 | `scalpel_inline` | pylsp-rope | `calcpy/inline_companion` |
| 2 | `scalpel_imports_organize` | pylsp-rope + ruff | `calcpy/imports_companion` |
| 3 | `scalpel_convert_to_method_object` | pylsp-rope | `calcpy/method_obj_companion` |
| 4 | `scalpel_local_to_field` | pylsp-rope | `calcpy/local_to_field_companion` |
| 5 | `scalpel_use_function` | pylsp-rope | `calcpy/use_fn_companion` |
| 6 | `scalpel_introduce_parameter` | pylsp-rope | `calcpy/intro_param_companion` |
| 7 | `scalpel_generate_from_undefined` | pylsp-rope | `calcpy/gen_undef_companion` |
| 8 | `scalpel_auto_import_specialized` | pylsp-rope | `calcpy/auto_import_companion` |
| 9 | `scalpel_fix_lints` | ruff | `calcpy/fix_lints_companion` |
| 10 | `scalpel_ignore_diagnostic` | ruff / basedpyright | `calcpy/ignore_diag_companion` |

**Test pattern:** identical structure to L-G7-A but skipped on `pylsp` / `ruff` / `basedpyright` PATH absence (whichever the facade requires).

**Source spec.** § Test discipline gaps (lines 157-174).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/test/integration/test_v1_5_g7b_python_real_disk.py` | NEW — 10 tests | ~600 |
| `vendor/serena/test/integration/calcpy/<companion>/main.py` × 10 | NEW — minimal source | ~15 each (10 × 15 = 150) |
| `vendor/serena/test/integration/conftest.py` | extend with 10 workspace fixtures | ~80 |

## TDD — failing tests first

Sample (one of ten — `scalpel_fix_lints`):

```python
@pytest.mark.skipif(
    shutil.which("ruff") is None,
    reason="ruff not on PATH",
)
def test_fix_lints_real_disk_dedups_imports(
    fix_lints_workspace,
    ruff_lsp,
):
    src = fix_lints_workspace / "main.py"
    before = src.read_text()
    assert before.count("import os") == 2  # precondition: dup

    tool = ScalpelFixLintsTool.__new__(ScalpelFixLintsTool)
    tool.get_project_root = lambda: str(fix_lints_workspace)
    out = tool.apply(file=str(src), rules=["I001"], language="python")
    payload = json.loads(out)
    assert payload["applied"] is True
    after = src.read_text()
    assert after.count("import os") == 1
    assert after != before
```

Sample (one of ten — `scalpel_imports_organize` with `remove_unused=True` only):

```python
@pytest.mark.skipif(
    shutil.which("pylsp") is None or shutil.which("ruff") is None,
    reason="pylsp + ruff required",
)
def test_imports_organize_remove_unused_only(
    imports_workspace, pylsp_lsp, ruff_lsp,
):
    src = imports_workspace / "main.py"
    before = src.read_text()
    assert "import json" in before  # precondition: unused

    tool = ScalpelImportsOrganizeTool.__new__(ScalpelImportsOrganizeTool)
    tool.get_project_root = lambda: str(imports_workspace)
    out = tool.apply(
        files=[str(src)],
        add_missing=False, remove_unused=True, reorder=False,
        language="python",
    )
    payload = json.loads(out)
    assert payload["applied"] is True
    after = src.read_text()
    assert "import json" not in after
    # add_missing=False, reorder=False → other imports' order preserved
    sys_idx = after.index("import sys")
    os_idx = after.index("import os")
    assert before.index("import sys") < before.index("import os")
    assert sys_idx < os_idx  # order unchanged
```

The remaining 8 follow the same shape with facade-specific assertions.

## Implementation steps

1. **For each of the 10 facades:** create companion fixture, fixture builder, and test body following the L-G7-A pattern. The Python facades require fewer file-system scaffolds (no `Cargo.toml`); each is just a `main.py`.

2. **Skip discipline per server:**
   - rope-only (4 facades): skip on `pylsp` absence.
   - ruff-only (1): skip on `ruff` absence.
   - mixed (5): skip if any required server is absent.

3. **Submodule pyright clean** on the new test file.

## Verification

```bash
uv run pytest vendor/serena/test/integration/test_v1_5_g7b_python_real_disk.py -x

# Skip-clean on partial host:
PATH=/usr/bin uv run pytest vendor/serena/test/integration/test_v1_5_g7b_python_real_disk.py
# Expected: 10 SKIP with the corresponding "X not on PATH" reason.

uv run pyright vendor/serena/test/integration/test_v1_5_g7b_python_real_disk.py
```

**Atomic commit:**

```
test(facades-python): real-disk mutation tests for 10 Python facades (G7-B)

Closes the zero-coverage gap for inline, imports_organize,
convert_to_method_object, local_to_field, use_function,
introduce_parameter, generate_from_undefined, auto_import_specialized,
fix_lints, ignore_diagnostic.

Tests skip cleanly when pylsp / ruff / basedpyright are absent.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** rope's behavior varies with caller intent encoding; test assertions need to match what rope actually emits, not an idealized output. Mitigation: ran each test once locally before committing per the L-G7-A precedent.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1 + L-G4-5 .. L-G4-10 + L-G6 (Python-touching fix leaves must be in tree).
- **Soft:** L-G3b (for facades emitting resource ops).
- **Blocks:** none — terminal regression discipline for this language.

---

**Author:** AI Hive®.
