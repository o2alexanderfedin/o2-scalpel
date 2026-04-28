# v1.2.1 — installer privacy + README provenance banner cleanup

**Date drafted**: 2026-04-28
**Trigger**: v1.1.1 deferred follow-ups #2 (install_command privacy) + #4 (README templates lack SHA banner)
**Type**: TREE-of-2 (mechanical cleanup, low blast radius)

## Why now

Two paper cuts surfaced during v1.1.1 + v1.2 reviews — both small, both fix existing-contract drift, both safe to land before larger v1.3/v2 work:

1. **`install_command` is public on the ABC** but the v1.1.1 brief specified `_install_command` (private). Public surface implies external callers are expected; we have none — only the ABC's own `install()` / `update()` invoke it. Privatize to match intent.
2. **Generator-emitted README lacks the provenance banner** that `marketplace.json` and the original hand-stamped `o2-scalpel-python/README.md` both carry. The o2-scalpel-markdown README (freshly generated v1.1.1) shipped without it — visible inconsistency.

## Leaves

| # | Title | Files touched | Tests | Order |
|---|---|---|---|---|
| A | Rename `install_command()` → `_install_command()` | installer/installer.py + 6 `*_installer.py` + 7 test files (~20 refs) | submodule pyright 0/0/0 + all installer tests pass | 1st |
| B | README template provenance banner | templates/readme.md.tmpl + plugin_generator.py + cli_newplugin.py + 3 regenerated plugin trees | submodule pyright 0/0/0 + +1 banner-presence test | 2nd (no overlap with A but cheap to serialize) |

Both leaves serial (per subagent-driven-development "no parallel implementers" rule). Each:
- TDD: failing test first → implementer → spec-reviewer → quality-reviewer → commit.
- Submodule branch off `main`, parent feature branch off `main`.
- Atomic submodule commit per leaf; parent pointer bumped at finalize.

## Done definition

- All installer tests pass with privatized name (no `install_command` references remain except in test internals if needed for mock dispatch — even those should rename).
- All 3 regenerated READMEs (`o2-scalpel-markdown/`, `-python/`, `-rust/`) carry the `<!-- Generated... --><!-- Regenerate... -->` banner with current submodule SHA.
- `make generate-plugins` is byte-stable (running twice in a row produces identical files).
- Submodule pyright 0/0/0 across touched files.
- Tag `v1.2.1-cleanup-complete` on parent main, pushed to origin.

## Out of scope

- pipx-managed PyPI version probe (deferred follow-up #1) — network-bound, best-effort, not a contract bug. Defer to v1.3 or beyond.
- v1.3 (additional markdown LSPs) — separate plan.
- v2 (new language strategies) — separate plan.
