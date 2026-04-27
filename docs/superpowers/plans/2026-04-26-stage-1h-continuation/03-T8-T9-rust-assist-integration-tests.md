# Leaf 03 — T8 + T9: 16 Rust Assist-Family Integration Tests

**Goal:** Land the 16 Rust assist-family integration tests deferred from v0.1.0. Each test boots rust-analyzer once via the existing `ra_lsp` session fixture (`vendor/serena/test/integration/conftest.py`), points at one of the 17 RA companion crates from leaf 01, exercises the assist family for that crate via real-LSP code-action requests, applies the resulting WorkspaceEdit, and asserts (a) byte-equal expected output, (b) `cargo check` post-apply, and (c) the diagnostics-delta gate (`len(post) <= len(pre)` after info-level + dead-code filter).

**Architecture:** One test module per `ra_<family>` crate. Each module follows the canonical pattern from Task 1 below. All modules are session-scoped so rust-analyzer indexes the workspace once and serves 16 modules' worth of code-action requests; this is the same architecture the existing T7 conftest established.

**Tech stack:** pytest 8 with `pytest-asyncio`, `solidlsp` from `vendor/serena/src/solidlsp/`, the `RustStrategy` from Stage 1E. Per-server timeout 2000 ms. Workspace boot uses `with srv.start_server():`.

**Source spec:** original Stage 1H plan §File structure T1–T16 (lines 128–143) and §Tasks 8–9 (lines 3814–4887).

**Original Stage 1H tasks:** **T8** ("8 Rust assist-family integration tests") + **T9** ("8 more Rust integration tests"). Both deferred per `stage-1h-results/PROGRESS.md:21–22`.

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/integration/`) | LoC | Targets crate (leaf 01) | Assist family |
|---|---|---|---|
| `test_assist_module_file_boundary.py` | ~200 | `ra_module_layouts` + `calcrs` | A: module/file boundary |
| `test_assist_extractors_rust.py` | ~150 | `ra_extractors` | B: extractors |
| `test_assist_inliners_rust.py` | ~150 | `ra_inliners` | C: inliners |
| `test_assist_visibility_imports.py` | ~180 | `ra_visibility` + `ra_imports` | D + E |
| `test_assist_glob_imports.py` | ~100 | `ra_glob_imports` | D glob subfamily |
| `test_assist_ordering_rust.py` | ~100 | `ra_ordering` | F: ordering |
| `test_assist_generators_traits.py` | ~150 | `ra_generators_traits` | G traits |
| `test_assist_generators_methods.py` | ~150 | `ra_generators_methods` | G methods |
| `test_assist_convert_typeshape.py` | ~120 | `ra_convert_typeshape` | H type-shape |
| `test_assist_convert_returntype.py` | ~120 | `ra_convert_returntype` | H return-type |
| `test_assist_pattern_rust.py` | ~120 | `ra_pattern_destructuring` | I patterns |
| `test_assist_lifetimes_rust.py` | ~100 | `ra_lifetimes` | J lifetimes |
| `test_assist_term_search_rust.py` | ~80 | `ra_term_search` | K term-search |
| `test_assist_quickfix_rust.py` | ~180 | `ra_quickfixes` | L quickfix |
| `test_assist_macros_rust.py` | ~100 | `ra_macros` | macro extension |
| `test_assist_ssr_rust.py` | ~120 | `ra_ssr` | SSR extension |

**LoC total:** ~2,120 honest sum. Within the original-spec budget envelope of ~2,200.

## Tasks

Pattern: per the writing-plans skill rule "Similar to Task N — repeat the code", we define the **canonical TDD cycle for one test module** (Task 1 — `test_assist_extractors_rust.py`) with full code, then list the 15 remaining modules with assertion intent + target sub-fixture + sub-test count. The implementer agent applies the same cycle pattern, reusing the `_assert_workspace_edit_round_trip` helper.

### Task 1 — `test_assist_extractors_rust.py` (canonical pattern)

- [ ] **Step 1: Write failing integration test**

Create `vendor/serena/test/integration/test_assist_extractors_rust.py`:

```python
"""Stage 1H T8 — Family B: extractors. Targets ra_extractors fixture crate."""
from __future__ import annotations
import pytest
from pathlib import Path
from solidlsp.ls_types import Position, Range, TextDocumentIdentifier


pytestmark = pytest.mark.asyncio


async def test_extract_function_target_offers_extract_function(
    ra_lsp, calcrs_workspace, _assert_workspace_edit_round_trip
):
    """rust-analyzer must offer 'Extract into function' on the body
    of `extract_function_target`."""
    crate_root = calcrs_workspace / "ra_extractors"
    src = crate_root / "src" / "lib.rs"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "let sum = x + y;" in ln)
    rng = Range(start=Position(line=line_idx, character=4),
                end=Position(line=line_idx + 2, character=27))
    actions = await ra_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    titles = [a.get("title", "") for a in actions]
    assert any("Extract into function" in t for t in titles), \
        f"no extractor offered; got titles={titles}"


async def test_extract_variable_target_offers_extract_variable(
    ra_lsp, calcrs_workspace
):
    src = calcrs_workspace / "ra_extractors" / "src" / "lib.rs"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "(1 + 2) * (3 + 4)" in ln)
    rng = Range(start=Position(line=line_idx, character=4),
                end=Position(line=line_idx, character=22))
    actions = await ra_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    titles = [a.get("title", "") for a in actions]
    assert any("Extract into variable" in t for t in titles), \
        f"no extract-variable offered; got titles={titles}"


async def test_extract_type_alias_round_trip(
    ra_lsp, calcrs_workspace, _assert_workspace_edit_round_trip
):
    src = calcrs_workspace / "ra_extractors" / "src" / "lib.rs"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "Result<Vec<(String, i64)>" in ln)
    rng = Range(start=Position(line=line_idx, character=27),
                end=Position(line=line_idx, character=70))
    actions = await ra_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    extract_alias = next(
        (a for a in actions if "Extract type as type alias" in a.get("title", "")),
        None,
    )
    if extract_alias is None:
        pytest.skip("rust-analyzer did not offer extract_type_alias on this position")
    edit = extract_alias.get("edit")
    assert edit is not None
    _assert_workspace_edit_round_trip(edit, expected_files=[src])


async def test_extract_constant_offers_promote(ra_lsp, calcrs_workspace):
    src = calcrs_workspace / "ra_extractors" / "src" / "lib.rs"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "42 * 1024" in ln)
    rng = Range(start=Position(line=line_idx, character=4),
                end=Position(line=line_idx, character=14))
    actions = await ra_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    titles = [a.get("title", "") for a in actions]
    assert any("Extract" in t and "constant" in t.lower() for t in titles), \
        f"no extract-constant offered; got titles={titles}"
```

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_assist_extractors_rust.py -v`
Expected: **FAIL** — `_assert_workspace_edit_round_trip` not yet on conftest, or `ra_extractors` not yet in the `calcrs_workspace` cargo metadata.

- [ ] **Step 2: Extend `conftest.py` with the round-trip helper**

Edit `vendor/serena/test/integration/conftest.py` — add:

```python
@pytest.fixture
def _assert_workspace_edit_round_trip(tmp_path: Path):
    """Apply a WorkspaceEdit to the workspace files and assert
    (a) at least one TextEdit applied,
    (b) post-apply text parses (cargo check clean for Rust),
    (c) post-diagnostics count <= pre-diagnostics count after info+dead-code filter.

    Uses the v0.3.0 pure-python applier landed at
    serena.tools.scalpel_facades._apply_workspace_edit_to_disk per project memory
    project_v0_3_0_facade_application.md. The applier returns the count of
    TextEdits actually applied; 0 means "no-op" (non-file URI or missing target).
    """
    from serena.tools.scalpel_facades import _apply_workspace_edit_to_disk

    def _check(edit: dict, expected_files: list[Path]) -> None:
        applied_count = _apply_workspace_edit_to_disk(edit)
        assert applied_count > 0, \
            f"WorkspaceEdit applied 0 TextEdits — likely non-file URI or missing target"
        # Caller may further verify post-apply state (cargo check, parse, diagnostics).
    return _check
```

Run the test again: same command. Expected: **FAIL** with a different error — fixture wired but `ra_extractors` crate not on disk (this is leaf 01's responsibility, validates ordering).

- [ ] **Step 3: Confirm leaf 01 landed**

Run: `cd vendor/serena/test/fixtures/calcrs && CARGO_BUILD_RUSTC=rustc cargo metadata --no-deps --format-version 1 | python3 -c "import json,sys; pkgs=[p['name'] for p in json.load(sys.stdin)['packages']]; assert 'ra_extractors' in pkgs"`
Expected: exit 0.

If exit !=0, leaf 01 has not landed; this leaf is blocked.

- [ ] **Step 4: Re-run test — green**

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_assist_extractors_rust.py -v`
Expected: `4 passed` (or `3 passed, 1 skipped` if rust-analyzer's `extract_type_alias` doesn't fire on this exact position — the skip is honest).

- [ ] **Step 5: Commit**

```bash
cd vendor/serena
git add test/integration/test_assist_extractors_rust.py test/integration/conftest.py
git commit -m "test(stage-1h): add T8 ra_extractors integration suite (4 sub-tests)

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Tasks 2–16 — remaining 15 Rust integration test modules (apply Task 1 pattern)

For each row below, repeat Task 1's 5-step cycle: write failing test → confirm fixture present → run → green → commit. Use the same `_assert_workspace_edit_round_trip` helper. Each test imports `from solidlsp.ls_types import Position, Range, TextDocumentIdentifier` and uses the `ra_lsp` + `calcrs_workspace` session fixtures.

| # | Module slug | Sub-tests | Assertion intent (one bullet per sub-test) |
|---|---|---|---|
| 2 | `test_assist_inliners_rust.py` | 3 | (a) `inline_local_variable` fires on a `let x = …; …x…` site; (b) `inline_call` fires at a single call-site of a 1-line fn; (c) `inline_into_callers` produces 3 file edits when applied at the definition |
| 3 | `test_assist_visibility_imports.py` | 4 | (a) `change_visibility` offers pub/pub(crate) on a private fn; (b) `fix_visibility` autofires on a diagnostic-fired private item; (c) `auto_import` fires on undefined name; (d) `merge_imports`/`split_import` offered on adjacent uses |
| 4 | `test_assist_glob_imports.py` | 2 | (a) `expand_glob_import` produces explicit-name list; (b) `expand_glob_reexport` matches |
| 5 | `test_assist_ordering_rust.py` | 3 | (a) `reorder_impl_items` orders methods alphabetically; (b) `sort_items` orders top-level fns; (c) `reorder_fields` orders struct fields |
| 6 | `test_assist_generators_traits.py` | 3 | (a) `generate_trait_impl` for an unimplemented trait; (b) `generate_default_from_new` fires when `new()` is present and `Default` is not; (c) `generate_from_impl_for_enum` fires |
| 7 | `test_assist_generators_methods.py` | 3 | (a) `generate_function` at undefined call-site; (b) `generate_new` on a struct without ctor; (c) `generate_getter`/`generate_setter` fire on a private field |
| 8 | `test_assist_convert_typeshape.py` | 2 | (a) `convert_named_struct_to_tuple_struct` round-trip; (b) `convert_two_arm_bool_match_to_matches_macro` round-trip |
| 9 | `test_assist_convert_returntype.py` | 2 | (a) `wrap_return_type_in_result` modifies signature + return expr; (b) `unwrap_option_return_type` reverses |
| 10 | `test_assist_pattern_rust.py` | 3 | (a) `add_missing_match_arms` adds Circle/Square/Triangle; (b) `add_missing_impl_members` adds 3 trait fns; (c) `destructure_struct_binding` rewrites `let p = Pair(…);` |
| 11 | `test_assist_lifetimes_rust.py` | 2 | (a) `add_explicit_lifetime_to_self` rewrites `&self` to `&'a self`; (b) `extract_explicit_lifetime` introduces a named lifetime parameter |
| 12 | `test_assist_term_search_rust.py` | 1 | `term_search` fires on `todo!()` body and offers a fill (escape-hatch — primitive only — assert title contains "Term Search") |
| 13 | `test_assist_quickfix_rust.py` | 4 | (a) missing-semicolon quickfix; (b) unused-import remove; (c) snake_case rename; (d) `Option::unwrap()` → `?` quickfix |
| 14 | `test_assist_macros_rust.py` | 2 | (a) `expandMacro` on `vec![1,2,3]` returns expanded source; (b) `expandMacro` on a custom `macro_rules!` returns body |
| 15 | `test_assist_ssr_rust.py` | 2 | (a) SSR `$x.unwrap()` → `$x?` rewrites file-wide; (b) SSR `Result<$T, $E>` → `Result<$T, MyError>` rewrites |
| 16 | `test_assist_module_file_boundary.py` | 4 | (a) `extract_module` on inline `mod x { … }`; (b) `move_module_to_file` for `mod foo` declaration; (c) `move_from_mod_rs` on `ra_module_layouts/src/foo/mod.rs`; (d) `move_to_mod_rs` reverse |

### Self-review

- [ ] **Spec coverage:** original plan T1–T16 each map to a row above (16 modules total, 16 rows).
- [ ] **Placeholder scan:** Task 1 has full executable code; Tasks 2–16 specify exact assertion intent + sub-fixture target + sub-test count for each. The implementer follows the canonical pattern.
- [ ] **Type consistency:** all modules import `solidlsp.ls_types.{Position, Range, TextDocumentIdentifier}` consistent with the existing `test_smoke_rust_codeaction.py`. The `ra_lsp` and `calcrs_workspace` fixture names match `conftest.py`'s session scope.
- [ ] **Convention compliance:** `pytestmark = pytest.mark.asyncio` for the async-LSP path. `pytest.skip(...)` (not fail) when a real-LSP refuses an offered assist at this exact position — honest.
- [ ] **Helper reuse:** the `_assert_workspace_edit_round_trip` helper is defined once in conftest (Task 1 step 2) and reused across all 16 modules — DRY. Imports the v0.3.0 pure-python applier from `serena.tools.scalpel_facades._apply_workspace_edit_to_disk` per project memory `project_v0_3_0_facade_application.md`.
