# Leaf L-G7-C — `transaction_commit` real-disk + `expand_macro` / `verify_after_refactor` real-disk + spike-test rewrites

**Goal.** Two distinct chunks in one leaf:

1. **Real-disk tests for the 3 remaining zero-coverage facades** that are too cross-cutting for G7-A or G7-B:
   - `scalpel_transaction_commit` — multi-step transaction with checkpoint/rollback. Acid test: each per-step `RefactorResult` reports a real on-disk effect.
   - `scalpel_expand_macro` — informational LSP query, real-LSP test asserts the returned expansion text matches a known-output fixture.
   - `scalpel_verify_after_refactor` — composite query, real-LSP test asserts runnable/flycheck counts are non-zero on a known fixture.

2. **Rewrites of 7 mock-only spike tests** to acid-test discipline:
   - `test_stage_2a_t2_split_file.py` — already partially mock-only; rewrite the rust path to use real `Path.read_text()` (gated by rust-analyzer-on-PATH skip).
   - `test_stage_2a_t3_extract.py`, `test_stage_2a_t4_inline.py`, `test_stage_2a_t5_rename.py`, `test_stage_2a_t6_imports_organize.py`
   - `test_stage_3_t1_rust_wave_a.py`, `test_stage_3_t4_python_wave_a.py`

The rewrite pattern: keep the existing dispatch-shape assertion AND add a `Path.read_text()` post-apply assertion. The mock-only path stays as a fast unit-level guard; the real-disk path is added as a sibling test (`test_<name>_real_disk`) gated on the LSP binary.

**Spec § Test discipline gaps (lines 157-174):** "the mock-only tests assert dispatch shape only; they cannot catch the discards." This leaf retrofits the discipline.

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/test/integration/test_v1_5_g7c_transaction_real_disk.py` | NEW — 3 real-disk tests for the cross-cutting facades | ~200 |
| `vendor/serena/test/spikes/test_stage_2a_t2_split_file.py` | extend — add real-disk sibling test | ~80 |
| `vendor/serena/test/spikes/test_stage_2a_t3_extract.py` | extend | ~80 |
| `vendor/serena/test/spikes/test_stage_2a_t4_inline.py` | extend | ~80 |
| `vendor/serena/test/spikes/test_stage_2a_t5_rename.py` | extend | ~80 |
| `vendor/serena/test/spikes/test_stage_2a_t6_imports_organize.py` | extend | ~80 |
| `vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py` | extend | ~80 |
| `vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py` | extend | ~80 |

## TDD — failing tests first

**Transaction commit real-disk pattern:**

```python
@pytest.mark.skipif(
    shutil.which("rust-analyzer") is None,
    reason="rust-analyzer not on PATH",
)
def test_transaction_commit_two_step_real_disk(rust_workspace, ra_lsp):
    src = rust_workspace / "lib.rs"
    before = src.read_text()

    # Compose a transaction: change_visibility + tidy_structure.
    runtime = ScalpelRuntime.instance()
    txn_store = runtime.transaction_store()
    raw_id = txn_store.new()
    txn_store.add_step(raw_id, {
        "tool": "scalpel_change_visibility",
        "args": {"file": str(src),
                 "position": {"line": 0, "character": 0},
                 "target_visibility": "pub_crate",
                 "language": "rust"},
    })
    txn_store.add_step(raw_id, {
        "tool": "scalpel_tidy_structure",
        "args": {"file": str(src), "scope": "file", "language": "rust"},
    })

    tool = ScalpelTransactionCommitTool.__new__(ScalpelTransactionCommitTool)
    out = tool.apply(transaction_id=f"txn_{raw_id}")
    payload = json.loads(out)
    assert all(step["applied"] for step in payload["per_step"])
    after = src.read_text()
    assert "pub(crate)" in after
    assert after != before
```

**Spike-test rewrite pattern (sibling test addition):**

```python
# In test_stage_2a_t3_extract.py — add at the bottom:

@pytest.mark.skipif(
    shutil.which("rust-analyzer") is None,
    reason="rust-analyzer not on PATH",
)
def test_extract_function_real_disk(extract_workspace, ra_lsp):
    """Acid-test sibling to the existing mock-only suite."""
    src = extract_workspace / "lib.rs"
    before = src.read_text()
    tool = _make_tool(extract_workspace)
    out = tool.apply(
        file=str(src),
        range={"start": {"line": ..., "character": ...},
               "end":   {"line": ..., "character": ...}},
        target="function",
        new_name="sum_three",
        language="rust",
    )
    payload = json.loads(out)
    assert payload["applied"] is True
    after = src.read_text()
    assert "fn sum_three" in after
    assert after != before
```

The 7 spike-test extensions follow the same template — add a sibling `_real_disk` test, leave the mock-only test in place as a fast unit-level guard.

## Implementation steps

1. **Add the 3 transaction-commit / expand_macro / verify real-disk tests** to a new file `test_v1_5_g7c_transaction_real_disk.py`.
2. **Extend each of the 7 spike-test files** with a sibling `_real_disk` test gated on the relevant binary.
3. **Run the full test suite** with rust-analyzer / pylsp / ruff on PATH; verify all 10 new tests PASS, all existing tests unchanged.
4. **Submodule pyright clean** on the touched files.

## Verification

```bash
uv run pytest vendor/serena/test/integration/test_v1_5_g7c_transaction_real_disk.py \
                vendor/serena/test/spikes/test_stage_2a_t2_split_file.py \
                vendor/serena/test/spikes/test_stage_2a_t3_extract.py \
                vendor/serena/test/spikes/test_stage_2a_t4_inline.py \
                vendor/serena/test/spikes/test_stage_2a_t5_rename.py \
                vendor/serena/test/spikes/test_stage_2a_t6_imports_organize.py \
                vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py \
                vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py -x

uv run pyright vendor/serena/test/integration/test_v1_5_g7c_transaction_real_disk.py
```

**Atomic commit:**

```
test(facades): real-disk discipline retrofit + transaction commit acid tests (G7-C)

Adds Path.read_text() post-apply discipline to:
  - 3 cross-cutting facades (transaction_commit, expand_macro,
    verify_after_refactor)
  - 7 mock-only spike tests (stage_2a_t2/3/4/5/6, stage_3_t1/t4) via
    sibling _real_disk tests gated on LSP binary presence.

Existing mock-only tests stay as fast unit-level guards.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** transaction-commit's compose-store layer has setup ceremony that varies between sessions. Mitigation: existing transaction-commit unit test (`test_stage_2a_t7_transaction_commit.py`) provides the boilerplate; copy its pattern.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G7-A and L-G7-B (the patterns and fixtures established there are reused; running this leaf before A/B duplicates fixture work).
- **Soft:** L-G2 (`expand_macro` and `verify_after_refactor` honor `dry_run` only after G2 lands; tests assert dry_run path here).
- **Soft:** L-G3a (split_file rust path is asserted real-disk only after G3a lands).
- **Blocks:** none — terminal milestone-discipline leaf.

---

**Author:** AI Hive®.
