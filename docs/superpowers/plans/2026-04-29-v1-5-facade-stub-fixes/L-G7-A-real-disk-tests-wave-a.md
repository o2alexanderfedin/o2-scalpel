# Leaf L-G7-A — Real-disk test wave A (10 Rust facades)

**Goal.** Add ≥1 real-disk-mutation test (acid-test discipline: `Path.read_text()` post-apply) for each of 10 Rust ergonomic facades that today have ZERO real-disk coverage. Spec § Test discipline gaps (lines 157-174) enumerates the 21 zero-coverage facades; this leaf covers the Rust half.

**Facades covered (10):**

| # | Facade | Test fixture base |
|---|---|---|
| 1 | `scalpel_change_visibility` | `calcrs/visibility_companion` |
| 2 | `scalpel_change_return_type` | `calcrs/return_type_companion` |
| 3 | `scalpel_convert_module_layout` | `calcrs/module_layout_companion` |
| 4 | `scalpel_tidy_structure` | `calcrs/tidy_companion` |
| 5 | `scalpel_change_type_shape` | `calcrs/type_shape_companion` |
| 6 | `scalpel_complete_match_arms` | `calcrs/match_arms_companion` |
| 7 | `scalpel_extract_lifetime` | `calcrs/extract_lifetime_companion` |
| 8 | `scalpel_expand_glob_imports` | `calcrs/glob_imports_companion` |
| 9 | `scalpel_generate_trait_impl_scaffold` | `calcrs/trait_impl_companion` |
| 10 | `scalpel_generate_member` | `calcrs/generate_member_companion` |

**Test pattern (acid-test compliant):**

```python
@pytest.mark.skipif(
    shutil.which("rust-analyzer") is None,
    reason="rust-analyzer not on PATH",
)
def test_<facade>_real_disk_mutation(<workspace>, ra_lsp, assert_workspace_edit_round_trip):
    src = <workspace> / "lib.rs"
    before = src.read_text()
    tool = _make_tool(<workspace>)
    out = tool.apply(file=str(src), <args>, language="rust")
    payload = json.loads(out)
    assert payload["applied"] is True
    after = src.read_text()
    assert after != before, "facade reported applied=True but file unchanged"
    assert <facade-specific assertion on `after`>
```

**Source spec.** § Test discipline gaps (lines 157-174).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/test/integration/test_v1_5_g7a_rust_real_disk.py` | NEW — 10 tests, one per facade | ~600 |
| `vendor/serena/test/integration/calcrs/<companion>/Cargo.toml` × 10 | NEW — minimal companion crates as fixtures | ~30 each (10 × 30 ≈ 300) |
| `vendor/serena/test/integration/calcrs/<companion>/src/lib.rs` × 10 | NEW — minimal source the facade can act on | ~20 each (10 × 20 ≈ 200) |
| `vendor/serena/test/integration/conftest.py` | extend — 10 new `@pytest.fixture` workspace builders if not derivable from existing patterns | ~80 |

## TDD — failing tests first

Each of the 10 tests follows the pattern above. The leaf is the largest by LoC (≈600 test LoC + 500 fixture LoC ≈ 1100 total) and is the largest concentration of real-LSP work in the milestone.

**Sample (one of ten — `scalpel_change_visibility`):**

```python
@pytest.mark.skipif(
    shutil.which("rust-analyzer") is None,
    reason="rust-analyzer not on PATH",
)
def test_change_visibility_real_disk_pub_crate(
    visibility_workspace,
    ra_lsp,
    assert_workspace_edit_round_trip,
):
    src = visibility_workspace / "src" / "lib.rs"
    before = src.read_text()
    assert "pub(crate)" not in before  # precondition

    tool = ScalpelChangeVisibilityTool.__new__(ScalpelChangeVisibilityTool)
    tool.get_project_root = lambda: str(visibility_workspace)
    out = tool.apply(
        file=str(src),
        position={"line": 0, "character": 4},  # cursor on `fn`
        target_visibility="pub_crate",
        language="rust",
    )
    payload = json.loads(out)
    assert payload["applied"] is True
    after = src.read_text()
    assert "pub(crate)" in after
    assert after != before
```

The leaf creates an analogous test for each of the 10 facades, gating each on `shutil.which("rust-analyzer")` so the suite skips cleanly on partial dev hosts.

**Fixture approach:** Each companion crate is a 2-file scaffold (`Cargo.toml` + `src/lib.rs`). Where possible, reuse the existing `calcrs_workspace` fixture pattern from `conftest.py:78`. Where not, add a session-scoped fixture per companion.

## Implementation steps

1. **For each of the 10 facades:**
   a. Add the companion-crate fixture under `test/integration/calcrs/<companion>/` (or extend `calcrs_workspace` with a second scaffold path).
   b. Add a `@pytest.fixture` builder in `conftest.py` that copies the companion to `tmp_path` so each test gets a writable scratch copy.
   c. Add the test body following the pattern above.
   d. Run the test once with `--lf` to confirm RED → GREEN locally before committing.

2. **Skip discipline:** Each test gates on the relevant binary (`rust-analyzer` for all 10). On a partial host, the suite skips cleanly with a clear reason — never fails for missing infrastructure.

3. **Submodule pyright clean** on the touched files. Pyright over the test suite is a regression-protection step.

## Verification

```bash
# Full G7-A pass:
uv run pytest vendor/serena/test/integration/test_v1_5_g7a_rust_real_disk.py -x

# Skip-clean on partial host:
PATH=/usr/bin uv run pytest vendor/serena/test/integration/test_v1_5_g7a_rust_real_disk.py
# Expected: 10 SKIP with "rust-analyzer not on PATH" — no FAILs.

uv run pyright vendor/serena/test/integration/test_v1_5_g7a_rust_real_disk.py
```

**Atomic commit:**

```
test(facades-rust): real-disk mutation tests for 10 Rust facades (G7-A)

Acid-test discipline: every test reads the file post-apply with
Path.read_text() and asserts specific content. Closes the zero-coverage
gap for change_visibility, change_return_type, convert_module_layout,
tidy_structure, change_type_shape, complete_match_arms, extract_lifetime,
expand_glob_imports, generate_trait_impl_scaffold, generate_member.

Tests skip cleanly when rust-analyzer is not on PATH.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** rust-analyzer's per-version output can vary; test assertions tied too tightly to RA's specific newText risk flakes. Mitigation: assertions check for substring presence (`"pub(crate)" in after`), not exact equality.
- **Risk:** large LoC concentrated in one leaf. Mitigation: the leaf is a single coherent commit because the 10 tests share fixture infrastructure; splitting risks duplicating fixture code.
- **Rollback:** revert single commit; the 10 facades return to their zero-coverage state — but the fix leaves landed prior remain in tree.

## Dependencies

- **Hard:** L-G1 + L-G4-1, L-G4-2, L-G4-3, L-G4-4 + L-G6 (the facades' fixes must be in tree so the tests can validate the fixed behavior).
- **Soft:** L-G3b (resource-op support — needed for `convert_module_layout` if it emits `RenameFile`).
- **Blocks:** none — terminal regression discipline for this language.

---

**Author:** AI Hive®.
