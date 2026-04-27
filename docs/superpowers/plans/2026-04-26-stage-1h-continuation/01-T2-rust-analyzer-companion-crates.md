# Leaf 01 — T2: 17 RA Companion Crates

**Goal:** Extend the existing `vendor/serena/test/fixtures/calcrs/` Cargo workspace from 1 baseline crate to 18 by adding 17 atomic companion crates, one per rust-analyzer assist family. Each crate is `[lib]`, edition 2021, `publish = false`, declared as a workspace member, and passes `cargo check -p <name>` clean (under the `CARGO_BUILD_RUSTC=rustc` workaround until `v020-followups/04` lands).

**Architecture:** Each companion crate owns one assist family per the fixture-LoC table at `docs/superpowers/plans/2026-04-24-stage-1h-fixtures-integration-tests.md:95–113`. Assist families use atomic crates so Stage 1H integration tests (leaf 03) can scope rust-analyzer's response to one family at a time and so a crash in one family's grammar does not fan out across the workspace.

**Tech stack:** Cargo workspace, Rust 1.74.0, edition 2021. Crates declare `#[allow(dead_code)]` on every fixture item (these exist only as refactor targets — silencing dead-code lints prevents drowning the diagnostics-delta gate documented in the original plan §Conventions).

**Source spec:** original Stage 1H plan §File structure F5–F23 (paths `test/fixtures/calcrs/ra_<family>/`) and §Task 2 (lines 1489–2416 of `2026-04-24-stage-1h-fixtures-integration-tests.md`).

**Original Stage 1H task:** **T2** ("13 additional RA companion crates"). Deferred from v0.1.0 per `stage-1h-results/PROGRESS.md:14` and re-routed here at the corrected count of 17 (the v0.1.0 cut shipped 1 of the originally-planned 5 baseline crates — the remaining 4 baseline crates `ra_extractors`, `ra_inliners`, `ra_visibility`, `ra_imports` are also in scope here, raising 13 → 17).

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/fixtures/calcrs/`) | Change | LoC | Crate role |
|---|---|---|---|
| `Cargo.toml` | Modify | +30 (workspace member list) | Workspace manifest grows from 2 to 19 members |
| `ra_extractors/Cargo.toml` + `src/lib.rs` | New | ~250 | Family B: 8 extractors |
| `ra_inliners/Cargo.toml` + `src/lib.rs` | New | ~200 | Family C: 6 inliners |
| `ra_visibility/Cargo.toml` + `src/lib.rs` | New | ~150 | Family E: visibility assists |
| `ra_imports/Cargo.toml` + `src/lib.rs` | New | ~300 | Family D: 8 import assists |
| `ra_glob_imports/Cargo.toml` + `src/lib.rs` | New | ~120 | Family D glob subfamily |
| `ra_ordering/Cargo.toml` + `src/lib.rs` | New | ~180 | Family F: ordering |
| `ra_generators_traits/Cargo.toml` + `src/lib.rs` | New | ~250 | Family G trait scaffolders |
| `ra_generators_methods/Cargo.toml` + `src/lib.rs` | New | ~200 | Family G method scaffolders |
| `ra_convert_typeshape/Cargo.toml` + `src/lib.rs` | New | ~150 | Family H type-shape |
| `ra_convert_returntype/Cargo.toml` + `src/lib.rs` | New | ~120 | Family H return-type |
| `ra_pattern_destructuring/Cargo.toml` + `src/lib.rs` | New | ~150 | Family I patterns |
| `ra_lifetimes/Cargo.toml` + `src/lib.rs` | New | ~180 | Family J lifetimes |
| `ra_proc_macros/Cargo.toml` + `src/lib.rs` | New | ~200 | Proc-macro pathway (only crate with crates.io deps) |
| `ra_ssr/Cargo.toml` + `src/lib.rs` | New | ~180 | Extension SSR |
| `ra_macros/Cargo.toml` + `src/lib.rs` | New | ~150 | `expandMacro` extension |
| `ra_module_layouts/Cargo.toml` + `src/lib.rs` + `src/foo/mod.rs` + `src/foo/bar.rs` + `src/baz.rs` | New | ~200 | Family A module-layout swap targets |
| `ra_quickfixes/Cargo.toml` + `src/lib.rs` | New | ~250 | Family L diagnostic-quickfixes |
| `ra_workspace_edit_shapes/Cargo.toml` + `src/lib.rs` | New | ~120 | Every WorkspaceEdit variant |
| `ra_term_search/Cargo.toml` + `src/lib.rs` | New | ~80 | Family K `term_search` escape-hatch |

**LoC total:** ~3,230 (raw Rust + manifests). Original-spec budget envelope ~2,500 — the +~730 surplus tracks the 4 baseline crates carried in from T1's deferred portion (see "Original Stage 1H task" note above) plus per-crate manifest overhead.

## Tasks

Pattern: per the writing-plans skill rule "Similar to Task N — repeat the code", we define the **canonical TDD cycle for one crate** (Task 1 — `ra_extractors`) with full content, then list the remaining 16 crates with assertion intent + lib.rs body specification. The implementer agent applies the same cycle pattern.

### Task 1 — `ra_extractors` (canonical pattern)

- [ ] **Step 1: Write failing workspace-membership test**

Create `vendor/serena/test/fixtures/calcrs/tests/test_workspace_members.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
expected="ra_extractors"
actual=$(CARGO_BUILD_RUSTC=rustc cargo metadata --format-version 1 --no-deps \
  | python3 -c "import json,sys; print('\n'.join(p['name'] for p in json.load(sys.stdin)['packages']))")
echo "$actual" | grep -qx "$expected" || { echo "missing crate: $expected"; exit 1; }
echo "OK: $expected present"
```

Run: `bash vendor/serena/test/fixtures/calcrs/tests/test_workspace_members.sh`
Expected: **FAIL** with `missing crate: ra_extractors` (red).

- [ ] **Step 2: Add crate to workspace manifest**

Edit `vendor/serena/test/fixtures/calcrs/Cargo.toml`:

```toml
[workspace]
resolver = "2"
members = [
    "calcrs",
    "calcrs-core",
    "ra_extractors",
]

[workspace.package]
edition = "2021"
publish = false
rust-version = "1.74"
```

The `[workspace.package]` block defines the workspace-wide defaults. Per-crate manifests (Step 3) declare `publish = false` directly rather than `publish.workspace = true` to make non-publishability unambiguous on inspection. `edition` and `rust-version` are inherited via `.workspace = true` because their values are uncontroversial.

- [ ] **Step 3: Create `ra_extractors/Cargo.toml`**

Create `vendor/serena/test/fixtures/calcrs/ra_extractors/Cargo.toml`:

```toml
[package]
name = "ra_extractors"
version = "0.0.0"
edition.workspace = true
publish = false
rust-version.workspace = true

[lib]
path = "src/lib.rs"
```

Note: `publish = false` is declared directly (not `publish.workspace = true`) so a reader sees the non-publish intent without cross-referencing the workspace manifest. `edition` and `rust-version` inherit because their workspace defaults are stable and uncontroversial.

- [ ] **Step 4: Create `ra_extractors/src/lib.rs` with 8-extractor refactor targets**

Create `vendor/serena/test/fixtures/calcrs/ra_extractors/src/lib.rs`:

```rust
//! Family B: extractors. Every public item exists only as a refactor target.
//! `extract_function`, `extract_variable`, `extract_type_alias`,
//! `extract_struct_from_enum_variant`, `promote_local_to_const`,
//! `extract_constant`, `extract_module`, `extract_expression`.
#![allow(dead_code)]

pub fn extract_function_target(x: i64, y: i64) -> i64 {
    let sum = x + y;
    let scaled = sum * 2;
    let offset = scaled + 7;
    offset
}

pub fn extract_variable_target() -> i64 {
    (1 + 2) * (3 + 4)
}

pub fn extract_type_alias_target() -> Result<Vec<(String, i64)>, std::io::Error> {
    Ok(vec![("a".to_string(), 1)])
}

pub enum ExtractStructFromVariant {
    First,
    Pair { left: i64, right: i64 },
    Triple(i64, i64, i64),
}

pub fn promote_local_to_const_target() -> i64 {
    let pi_thousandths: i64 = 3142;
    pi_thousandths
}

pub fn extract_constant_target() -> i64 {
    42 * 1024
}

pub mod extract_module_target {
    pub fn alpha() -> i64 { 1 }
    pub fn beta() -> i64 { 2 }
    pub fn gamma() -> i64 { 3 }
}

pub fn extract_expression_target() -> i64 {
    let a = 1;
    let b = 2;
    a + b + a * b
}
```

- [ ] **Step 5: Run test — green**

Run: `bash vendor/serena/test/fixtures/calcrs/tests/test_workspace_members.sh`
Expected: `OK: ra_extractors present`

Run: `cd vendor/serena/test/fixtures/calcrs && CARGO_BUILD_RUSTC=rustc cargo check -p ra_extractors`
Expected: `Finished dev` clean exit code 0.

- [ ] **Step 6: Commit (submodule)**

```bash
cd vendor/serena
git add test/fixtures/calcrs/Cargo.toml \
        test/fixtures/calcrs/ra_extractors \
        test/fixtures/calcrs/tests/test_workspace_members.sh
git commit -m "fixtures(stage-1h): add ra_extractors companion crate (T2)

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Tasks 2–17 — remaining 16 companion crates (apply Task 1 pattern)

For each row below, repeat Task 1's 6-step cycle: extend `members = [...]`, create `Cargo.toml` (declaring `publish = false` directly per Task 1 step 3 rationale), create `src/lib.rs` with the listed refactor targets, extend the workspace-membership test with the new crate name, run → green, commit.

| # | Crate | Refactor targets in `src/lib.rs` |
|---|---|---|
| 2 | `ra_inliners` | `inline_local_variable_target`, `inline_call_target` (call-site + body), `inline_into_callers_target` (one definition + 3 callers), `inline_type_alias_target`, `inline_macro_target` (`macro_rules! square`), `inline_const_as_literal_target` |
| 3 | `ra_visibility` | private struct + private fn + private mod, plus a `pub(crate)` candidate; one diagnostic-bound private item used from a sibling module to fire `fix_visibility` |
| 4 | `ra_imports` | unused `use std::collections::HashMap;`, mergeable `use std::io::{Read}; use std::io::{Write};`, qualifyable `Vec::new()` call, two split-target `use` siblings, two normalize-target tree-imports |
| 5 | `ra_glob_imports` | `use std::io::*;` + `pub use crate::inner::*;` for `expand_glob_import` and `expand_glob_reexport` |
| 6 | `ra_ordering` | `impl Foo` block with 3 methods in non-alphabetic order, free fn list with non-alphabetic order, struct with reorder-target field list |
| 7 | `ra_generators_traits` | bare struct `Token` (no `Default`/no `From`); enum `Color` (no `From`); `pub struct Builder { name: String }` with `new()` (so `generate_default_from_new` fires) |
| 8 | `ra_generators_methods` | `pub struct User { id: u64, name: String }` (no constructor / no getters / no setters); call-site to a not-yet-defined fn so `generate_function` fires |
| 9 | `ra_convert_typeshape` | named struct `pub struct Point { x: i64, y: i64 }`, tuple struct `pub struct Pair(i64, i64)`, two-arm bool match candidate |
| 10 | `ra_convert_returntype` | 4 fns each returning a non-wrapped type: `i64`, `Result<T, _>` to unwrap, `Option<T>`, plain `T` to wrap in Option |
| 11 | `ra_pattern_destructuring` | `enum Shape { Circle, Square, Triangle }` + non-exhaustive match; trait with 3 unimplemented members; `let pair = Pair(1, 2);` ready for destructure |
| 12 | `ra_lifetimes` | `impl Foo { fn name(&self) -> &str { &self.s } }` with elided lifetimes; cross-borrow candidate; one `'static` reference reduceable to a named lifetime |
| 13 | `ra_proc_macros` | depends on `serde = { version = "1", features = ["derive"] }`, `tokio = { version = "1", features = ["macros", "rt"] }`, `async-trait = "0.1"`, `clap = { version = "4", features = ["derive"] }`. Items: `#[derive(Serialize, Deserialize)]`, `#[tokio::main]`, `#[async_trait]`, `#[derive(clap::Parser)]` |
| 14 | `ra_ssr` | functions with `.unwrap()` on `Option`, `Result<T, E>` typedefs, a literal pattern `match x { 0 => "zero", _ => "other" }` |
| 15 | `ra_macros` | `vec![1, 2, 3]` call, custom `macro_rules! double { ($x:expr) => { $x * 2 } }` invocation, `#[derive(Debug)]` on a struct |
| 16 | `ra_module_layouts` | `src/lib.rs` declaring `mod foo;` (file form) + `pub mod baz;` (file form); `src/foo/mod.rs` (mod-rs form) declaring `pub mod bar;`; `src/foo/bar.rs` empty pub fn; `src/baz.rs` empty pub fn — both layouts coexist so `convert_module_layout` has a target either direction |
| 17 | `ra_quickfixes` | one item per kind cluster: missing semicolon, missing type annotation on `let x = 1;` candidate (already typed in baseline; trigger by removing in tests), missing turbofish `Vec::new()` in generic context, dead-code item, snake_case lint trigger, `let_else` candidate, `Option::unwrap()` candidate (4 sub-clusters × ~7 items) |

Plus two "extension shape" crates carried over from baseline-of-T1 deferral:
- `ra_workspace_edit_shapes` — items for each WorkspaceEdit variant per scope-report §4.6: TextDocumentEdit-only target, SnippetTextEdit candidate, CreateFile candidate (referenced-but-missing module `pub mod missing;`), RenameFile candidate (file with mismatched primary-symbol name), DeleteFile candidate (`#[deprecated]` empty file), changeAnnotations candidate (renameable item).
- `ra_term_search` — single fn `pub fn fill_me() -> i64 { todo!() }` — the only assist target.

### Self-review

- [ ] **Spec coverage:** map each F5–F23 row in original plan §File structure to one task above. Every row mapped.
- [ ] **Placeholder scan:** every `src/lib.rs` either contains complete code (Task 1) or is specified by enumerated refactor-targets list (Tasks 2–17). No "TBD" / "appropriate" / "similar to" left.
- [ ] **Type consistency:** every crate name `ra_<family>` matches the fixture path in original plan §File structure F5–F23. Workspace manifest member-list spelling matches each `Cargo.toml`'s `name = ...`.
- [ ] **Cargo correctness:** every per-crate Cargo.toml uses `edition.workspace = true` + `rust-version.workspace = true` for stable defaults and `publish = false` declared directly to make non-publishability unambiguous. `ra_proc_macros` is the only crate with non-workspace `[dependencies]`.
- [ ] **Convention compliance:** every fixture item carries `#[allow(dead_code)]` either at module-level (`#![allow(dead_code)]`) or per-item.
