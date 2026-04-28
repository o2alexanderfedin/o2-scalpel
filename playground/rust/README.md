# Rust Playground — o2-scalpel E2E fixture workspace

This is the baseline Cargo workspace used by the o2-scalpel-rust E2E
test suite (v1.2.2+).

**Spec reference**: `docs/superpowers/specs/2026-04-28-rust-plugin-e2e-playground-spec.md`
— in particular § 4.2 (playground content) and § 6 P1 (this phase).

---

## Crates

| Crate | Purpose |
|-------|---------|
| `calc/` | Minimal expression parser + evaluator. Split-file, rename, and extract targets live here. |
| `lints/` | Lint-pattern helpers. Inline and change-visibility targets live here. |

---

## Facade targets at a glance

| Facade | File | Symbol / location |
|--------|------|-------------------|
| `scalpel_split_file` | `calc/src/lib.rs` | inline modules `ast`, `parser`, `eval` → carved into sibling files |
| `scalpel_rename` | `calc/src/lib.rs` | `parser::parse_expr` → `parse_expression` |
| `scalpel_extract` | `calc/src/lib.rs` | `let result = a + b; Ok(result)` inside `eval::eval` → helper function |
| `scalpel_inline` | `lints/src/lib.rs` | `sum_helper` (single call site in `report`) → inlined away |
| `scalpel_change_visibility` | `calc/src/visibility.rs` | `promote_to_public` (`pub(super)` → `pub`) |

---

## Quickstart

```bash
# From the playground/rust/ directory:
cargo build
cargo test
```

Both commands must exit 0 on the **baseline** (unmodified) source.

---

## How the E2E suite uses this workspace

1. The pytest fixture `playground_rust_root` calls `shutil.copytree` to
   clone the entire workspace into `pytest`'s `tmp_path` directory.
   The `target/` build cache is stripped post-copy (stale incremental
   data causes non-deterministic rust-analyzer code-action results).

2. The test invokes a facade (e.g. `scalpel_split_file`) against the
   **clone** — never against this source-controlled directory.

3. After the refactor, the test asserts that new files exist, that the
   applied payload carries `"applied": true`, and optionally runs
   `cargo test --quiet` in the clone to confirm the workspace still
   compiles.

> **DO NOT hand-edit these source files without updating the E2E
> assertions.** The test suite asserts on specific symbol names, line
> ranges, and file paths that match the baseline exactly. If you change
> the baseline, update the corresponding test in
> `vendor/serena/test/e2e/test_e2e_playground_rust.py` in the same
> commit.

---

## Workspace policy

- `Cargo.lock` is committed (no `cargo update` runs during E2E execution).
- `rust-version = "1.74"` is pinned in the workspace `Cargo.toml`.
- `target/` is `.gitignore`-d.
- The `types/` crate placeholder is deferred to v1.3 (YAGNI — an empty
  crate provides zero test signal until the type-shape facades land).
