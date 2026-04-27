# Documentation Currency Review — Post v0.2.0 Follow-ups
**Date**: 2026-04-27
**Specialist**: Doc Currency

## Summary

The doc-closure commit (`34f7766`) successfully marked Leaves 02/03/04/05 CLOSED in `WHAT-REMAINS.md` and `stage-1h-results/PROGRESS.md`, and the new `docs/dev/host-rustc-shim.md` accurately describes the actual L04 mechanism. However, several doc-currency issues remain: the **per-leaf plan files were never annotated with post-shipment STATUS markers**, the **L04 plan still prescribes the rejected `addopts` mechanism** (only the prose-drift commit `cb0826b` patched the shim doc, not the plan), the **P5a spike-result file remains internally inconsistent** (verdict line says "DROP" while new measurements support "SHIP"), the **CHANGELOG.md is frozen at v0.1.0** (no v0.2.0 / v0.3.0 / followup entries), and the **MVP scope report's headline numbers** (13 always-on / 24 total tools) are stale relative to today's 8 + 25 = 34. None of these block functionality, but they invite re-confusion in the next planning round.

---

## Top-level docs (README, CLAUDE.md)

### `/Volumes/Unitek-B/Projects/o2-scalpel/README.md`
**Status: mostly current**

- Headline tool count (`README.md:7-13`) reflects v0.2.0 Stage 3 (25 facades + 8 primitives = 34) — accurate.
- Status banner says "v0.2.0 — Stage 3 ergonomic facades complete" (`README.md:5-7`). Per project memory, **v0.3.0 facade-application gap closure also landed** (tag `v0.3.0-facade-application-complete`). README is silent on v0.3.0 — minor staleness.
- No mention of the v0.2.0 follow-ups (multi-server async wrapping, RA preflight position validation, opt-in CARGO_BUILD_RUSTC plugin, basedpyright dynamic capability, E1-py determinism). README does not need to enumerate them, but a one-line "v0.2.0 + 5 follow-ups complete" pointer would help.
- Install instructions (`README.md:30-44`) match `docs/install.md` and current submodule layout.

### `/Volumes/Unitek-B/Projects/o2-scalpel/CLAUDE.md`
**Status: stale `Last Updated` field**

- `CLAUDE.md:89` reads `**Last Updated**: 2026-04-24`. Today is 2026-04-26 and the file references conventions still in force, but the date is now 3 days behind reality after roughly 8 stages + 5 followups landed. Cosmetic but trackable.

### `/Volumes/Unitek-B/Projects/o2-scalpel/CHANGELOG.md`
**Status: severely stale**

- Only the `[0.1.0] — 2026-04-24` block exists (`CHANGELOG.md:6-19`).
- No entries for: `v0.1.0-mvp`, `v0.2.0-critical-path-complete`, `v0.2.0-stage-3-complete`, `v0.3.0-facade-application-complete`, `stage-v0.2.0-followup-01-…-complete`, `stage-v0.2.0-followups-complete` (covering Leaves 02-05).
- The CHANGELOG is the user-facing source of truth for what shipped and is now ~7 tags out of date.

### Submodule docs (`vendor/serena/README.md`, `vendor/serena/CLAUDE.md`, `vendor/serena/CONTRIBUTING.md`)
**Status: upstream — not o2.scalpel-specific (acceptable by design)**

- `vendor/serena/README.md` is the unmodified upstream Serena README (no o2-scalpel mentions). Per `gap-analysis/B-design.md`, the fork strategy is "non-invasive extension under `src/serena/refactoring/` and `src/serena/tools/scalpel_*.py`". The submodule's user-facing docs intentionally do not duplicate scalpel content.
- `vendor/serena/CLAUDE.md` is a 3-line pointer to `.serena/memories/`. Acceptable.
- No `o2-scalpel-engine`-specific README under `vendor/serena/` advertising the fork's role. **Gap (low priority)**: a contributor cloning the engine repo standalone has no signal that it is the o2-scalpel engine fork until they read the project root README.

---

## Design docs (`docs/design/`)

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/design/mvp/2026-04-24-mvp-scope-report.md`
**Status: design-time snapshot — by-design preserved, but headline numbers now misleading without context**

- TL;DR (`mvp-scope-report.md:17`) says "**13 always-on MCP tools** plus **~11 deferred-loading specialty facades**". Today's reality is **8 always-on primitives + 25 always-on facades = 34 always-on tools** (per `README.md:7-13`, `install.md:96-104`). The "deferred-loading" mechanism became "always-on" between design and MVP cut.
- The `Stage 3 (the remaining 7 ergonomic facades + 6 long-tail E2E scenarios) becomes v0.2.0` clause (line 19) understates Stage 3 scope: `WHAT-REMAINS.md:35` records **23 specialty facades** in Stage 3, not 7.
- The MVP definition sentence (line 25) names "5 ergonomic facades" — the MVP did ship those 5, but Stage 3 added 23 more.
- This file is explicitly "report-only" and is preserved as a historical decision record. **Recommendation**: do NOT mutate it. Instead, add a single banner note at the top pointing readers at `WHAT-REMAINS.md` for the actual delivered surface.

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/design/2026-04-24-serena-rust-refactoring-extensions-design.md`
- Not opened in this pass. Per the gap-analysis Agent B audit, the design report holds; the gap analysis caveats apply.

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/design/2026-04-24-o2-scalpel-open-questions-resolution.md`
- Q10–Q14 resolutions reviewed (`open-questions-resolution.md:11-19`). Decisions are still in force per the v0.2.0 / v0.3.0 implementations. No drift.

---

## Gap analysis docs

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/gap-analysis/WHAT-REMAINS.md`
**Status: doc-closure update applied correctly**

Verified L02/L03/L04/L05 closure annotations:
- L01 (`WHAT-REMAINS.md:102`): _CLOSED 2026-04-26_ — accurate.
- L02 (`WHAT-REMAINS.md:103`): _CLOSED 2026-04-26 (Leaf 02)_ — accurate; cites correct paths (`solidlsp/util/file_range.py`, `RustAnalyzer.request_code_actions @override`).
- L03 (`WHAT-REMAINS.md:104`): _CLOSED 2026-04-26 (Leaf 03)_ — accurate; cites `serena.refactoring._async_check`, `MultiServerCoordinator.__init__`, `AWAITED_SERVER_METHODS` constant.
- L04 (`WHAT-REMAINS.md:105`): _CLOSED 2026-04-26 (Leaf 04)_ — accurate; cites `vendor/serena/test/conftest_dev_host.py`, `O2_SCALPEL_LOCAL_HOST=1`, `docs/dev/host-rustc-shim.md`.
- L05 (`WHAT-REMAINS.md:106-114`): _CLOSED by v0.2.0 followup-05_ — accurate.

**Minor inconsistency**: §1 still claims (line 53-55) that "Agent C and Agent D found **no mypy pin in code** — the Python toolchain still ships `pylsp + basedpyright + ruff` without mypy. So today three artifacts disagree: spike result says SHIP, ledger says DROP, code says DROP." This is the unresolved P5a decision flagged for future action; it remains accurate as a description of the open governance question, but per the §1 sequencing recommendation, it should be the next item picked up — and it has not been touched yet.

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/gap-analysis/D-debt.md`
**Status: §7 has the L05 closure note added (`D-debt.md:243-251`); §Summary table line 268 also updated.**

- E1-py flake row in summary table (`D-debt.md:268`) marked **CLOSED**. Accurate.
- However §2 (`D-debt.md:85-111`) still lists **6 inspect.getsource flakes** as outstanding — accurate per current state; not a doc-currency issue.
- Recommendations §3 (`D-debt.md:278`) was correctly updated to mark E1-py CLOSED. Good.

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/gap-analysis/A-plans.md`, `B-design.md`, `C-code.md`
- Not re-audited in this pass. These were generated 2026-04-26 by the gap-analysis sweep and feed `WHAT-REMAINS.md`. They are point-in-time audits; their currency is the responsibility of the next gap-analysis sweep.

---

## Per-leaf plan files

**Status: NO post-shipment STATUS annotations on any of the 5 leaves.**

All five plan files (`01-basedpyright-dynamic-capability.md`, `02-rust-analyzer-position-validation.md`, `03-multi-server-async-wrapping.md`, `04-cargo-build-rustc-workaround.md`, `05-e1-py-flake-rootcause.md`) read as still-pending plans. None have a top-of-file STATUS banner saying "COMPLETE — see `stage-1h-results/PROGRESS.md:85-89` for closure record" or similar.

The `git tag` instructions inside each plan (e.g., L01 line "`git tag stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete`") are present, and the tags exist, but a reader of the plan file alone cannot tell that the work shipped.

**Specific drift between plan and implementation:**

### Leaf 01 (`docs/superpowers/plans/2026-04-26-v020-followups/01-basedpyright-dynamic-capability.md`)
- File Structure table (`01-basedpyright-dynamic-capability.md:18`) lists `vendor/serena/src/solidlsp/language_server.py` as the edit target. **That file does not exist** — the actual base class lives in `vendor/serena/src/solidlsp/ls.py`. Implementation correctly wired `DynamicCapabilityRegistry` into `ls.py:663-665` (verified `grep`). Plan was never updated.
- Plan estimated "~80 LoC" for the registry; actual size of `dynamic_capabilities.py` not verified in this pass, but the file exists and the test (`test/serena/test_dynamic_capabilities.py`) exists.

### Leaf 02 (`docs/superpowers/plans/2026-04-26-v020-followups/02-rust-analyzer-position-validation.md`)
- Self-Review Checklist (`02-rust-analyzer-position-validation.md:175-179`) is unchecked; nothing in the plan itself records that all checkboxes were satisfied. The PROGRESS.md closure note (`stage-1h-results/PROGRESS.md:86`) carries the verification.
- Plan referenced `whole_file_range` at `vendor/serena/test/integration/conftest.py:185` (line 160 of plan); actual location is line 186 — minor 1-line drift after an edit. Closure also notes the fixture was migrated to "dual-mode (parametrized → helper; unparametrized → backwards-compat fallback)" (per `WHAT-REMAINS.md:103`). The plan's Task 5 prescribed a single-mode replacement that would `pytest.skip` if not parametrized, contradicting the dual-mode reality. **Plan-vs-impl drift, not documented in the plan.**

### Leaf 03 (`docs/superpowers/plans/2026-04-26-v020-followups/03-multi-server-async-wrapping.md`)
- Plan prescribes hard-coded `method_names=("request_code_actions", "resolve_code_action", "request_rename_symbol_edit")` in the `__init__` validation (line 138-144). The actual implementation per `WHAT-REMAINS.md:104` extracted these into a single source of truth `AWAITED_SERVER_METHODS` constant. **Plan-vs-impl drift, not documented.**
- Plan parallelism threshold: `parallel_elapsed < serial_total * 0.7` (line 208). Per WHAT-REMAINS, the implementation refers to "Amdahl-aware parallelism budget" — wording shift, may or may not reflect the same threshold; not verified.

### Leaf 04 (`docs/superpowers/plans/2026-04-26-v020-followups/04-cargo-build-rustc-workaround.md`)
- **Most significant plan drift.** Plan Task 2 (line 102-107) prescribes:
  ```toml
  [tool.pytest.ini_options]
  addopts = "-p test.conftest_dev_host"
  ```
  This approach was **rejected during implementation** because `addopts` is parsed before pytest adds the rootdir to `sys.path`. The actual mechanism uses `pytest_plugins = ["test.conftest_dev_host"]` in `vendor/serena/test/conftest.py:32`. Confirmed in `pyproject.toml:307-313` where the comment explicitly notes the swap.
- The `cb0826b` "prose drift" commit corrected `docs/dev/host-rustc-shim.md:32` but **left the plan file unchanged**. The plan's prescriptive code block (line 105-107) will mislead anyone re-reading the plan to understand what was actually built.

### Leaf 05 (`docs/superpowers/plans/2026-04-26-v020-followups/05-e1-py-flake-rootcause.md`)
- File Structure table (`05-e1-py-flake-rootcause.md:19`) prescribes a 15-LoC root-cause edit at `scalpel_facades.py`. Per `WHAT-REMAINS.md:106-114`, **no facade-side patch was required** because the flake did not reproduce on the Leaf 05 host (30/30 applies). The plan-prescribed code change never landed. **Plan-vs-impl drift, not annotated.**

---

## New docs from batch

### `/Volumes/Unitek-B/Projects/o2-scalpel/docs/dev/host-rustc-shim.md`
**Status: accurate and current.**

Verified every claim:
- "Auto-loaded via `pytest_plugins = ["test.conftest_dev_host"]` declared in `vendor/serena/test/conftest.py`" (`host-rustc-shim.md:32`) — verified at `vendor/serena/test/conftest.py:32`.
- The parenthetical explaining why the original `addopts` approach failed — accurate per `pyproject.toml:307-313` comment.
- Cross-references to `spike-results/PROGRESS.md:60` (`host-rustc-shim.md:65`) — verified, the line records the original 2026-04-24 origin of the workaround. Accurate.
- Cross-references to `stage-1h-results/PROGRESS.md:35` (`host-rustc-shim.md:69`) — verified, the line records the conftest module-load shim history. Accurate.
- Cross-references to `stage-1h-results/PROGRESS.md:88` (`host-rustc-shim.md:74`) — verified, the line is now the L04 closure note. Accurate.
- "Inline `setdefault` calls deleted from all 7 sites" (line 71) — matches the L04 plan's Task 3 enumeration of 7 sites.

**Minor cosmetic finding**: the "Verification" section (line 50-58) tells the reader to `cd vendor/serena && uv run pytest test/conftest_dev_host_test.py -x`. This works but does not exercise the `O2_SCALPEL_LOCAL_HOST=1` integration path (which `WHAT-REMAINS.md:105` says was also tested). A one-line "and re-run with `O2_SCALPEL_LOCAL_HOST=1` to exercise the activation path" would round it out. Nice-to-have.

---

## Spike-result re-runs

The 2026-04-26 commits `a53adb2` (baseline refresh) and `459cf8f` (cosmetic deltas) refreshed:
- `P5a.md` (twice — at baseline and during L05)
- `S1.md`, `S2.md`, `S3.md`, `S4.md`

**Critical drift in P5a.md**:

`docs/superpowers/plans/spike-results/P5a.md` now contains:
- Line 3: `**Outcome:** C - stale_rate >= 5% OR p95 >= 3s - DROP pylsp-mypy at MVP`
- Line 9-10: `Stale steps (oracle != pylsp-mypy): 0` / `Stale rate: 0.00%`
- Line 12: `p95 latency (s): 4.306`

The verdict line (Outcome C — DROP) is **internally inconsistent with its own evidence**. The new measurements (0% stale, p95 = 4.306s) actually meet **Outcome B** ("ship with documented warning") thresholds, not Outcome C. This is the same drift `WHAT-REMAINS.md` §1 calls out as the "highest-priority unresolved decision" — and it remains unresolved.

**No file explains the new numbers.** The two re-run commits' messages (`a53adb2`: "carry-overs from follow-up #01: re-runs of P5a (mypy stale rate now 0%)"; `459cf8f`: "spike result files carry small numeric deltas from re-runs during Leaf 03 integration testing — auto-generated test outputs, no semantic change") describe the deltas as cosmetic/auto-generated, but the P5a delta is **semantically significant** and contradicts the verdict line in the same file.

`docs/superpowers/plans/spike-results/SUMMARY.md` (line 25) and `PROGRESS.md` (line 31, 70, 101) still describe P5a as outcome C with the original 8.33% / 8.011s numbers and the "drop pylsp-mypy" decision. Neither was updated to acknowledge the re-run.

`docs/superpowers/plans/stage-1h-results/PROGRESS.md:94` ("P5a → C — pylsp-mypy DROPPED") is also stale relative to the re-run measurements.

**S1 / S4 deltas appear cosmetic** (S1: 207 events from 178 — listener delta; S4: RSS 16kB from 80kB — within noise band). No verdict change.

---

## Broken or stale cross-links

Spot-checked ~15 line-anchored cross-references in the v020-followups plan tree and gap-analysis docs. Findings:

| Citing file:line | Anchor | Anchor target line content | Status |
|---|---|---|---|
| `02-rust-analyzer-position-validation.md:160` | `vendor/serena/test/integration/conftest.py:185` | actual `whole_file_range` def is at line 186 | OFF-BY-ONE |
| `04-cargo-build-rustc-workaround.md:115` | `vendor/serena/test/integration/conftest.py:57` | line 56 now reads `# Note: the developer-host CARGO_BUILD_RUSTC=rustc shim now lives` (the inline `setdefault` was removed by L04 itself) | OBSOLETE-BY-EXECUTION (expected; plan's pre-implementation state) |
| `04-cargo-build-rustc-workaround.md:125,162` | `vendor/serena/test/integration/conftest.py:33` | line 33 reads `7. ``CARGO_BUILD_RUSTC=rustc`` is exported into the rust-analyzer` (docstring item 7) | ACCURATE |
| `host-rustc-shim.md:65` | `spike-results/PROGRESS.md:60` | line 60 reads `Spike tests on this host must os.environ.setdefault("CARGO_BUILD_RUSTC", "rustc") BEFORE booting rust-analyzer` | ACCURATE |
| `host-rustc-shim.md:69` | `stage-1h-results/PROGRESS.md:35` | line 35 reads `2026-04-25 — CARGO_BUILD_RUSTC=rustc workaround applied in conftest module-load …` | ACCURATE |
| `host-rustc-shim.md:74` | `stage-1h-results/PROGRESS.md:88` | line 88 is the L04 closure note | ACCURATE |
| `WHAT-REMAINS.md:103` | references L02 paths in prose; no line anchors | verified | ACCURATE |
| `WHAT-REMAINS.md:104` | references L03 paths in prose; no line anchors | verified | ACCURATE |
| `01-basedpyright-dynamic-capability.md:9` | `vendor/serena/src/serena/tools/scalpel_primitives.py:533` | not verified in this pass; file exists | UNVERIFIED |
| `01-basedpyright-dynamic-capability.md:9` | `vendor/serena/src/serena/tools/scalpel_schemas.py:222` | not verified in this pass; file exists | UNVERIFIED |
| `03-multi-server-async-wrapping.md:5` | `vendor/serena/src/serena/tools/scalpel_runtime.py:59-97` | not verified in this pass; file exists | UNVERIFIED |
| `03-multi-server-async-wrapping.md:7` | `vendor/serena/src/serena/refactoring/multi_server.py:842-895` | not verified in this pass; file exists | UNVERIFIED |
| `INDEX-post-v0.3.0.md:23-28` | various WHAT-REMAINS section anchors | section anchors only, not line-anchored | RESILIENT |

**Verdict on cross-link health**: the `host-rustc-shim.md` anchors (the new doc) are all current. The L02 plan has a **1-line drift** (185 → 186); the L04 plan's pre-implementation anchors are necessarily obsolete by virtue of the work having been executed (the inline shim was deleted).

---

## Orphan or stale docs

**No major orphans found**. All plan files in `docs/superpowers/plans/2026-04-26-v020-followups/` are referenced by `INDEX-post-v0.3.0.md:25` and the leaf-table `README.md`.

**Minor: archived narrow synthesis** — `docs/design/mvp/archive-v1-narrow/` (5 files) is correctly preserved as the rollback target per `mvp-scope-report.md:3`. Not an orphan.

**Minor: gap-analysis intermediate artifacts** — `docs/gap-analysis/REPORT-DRAFT-V1.md`, `REPORT-REVIEW.md`, `COORDINATOR-OUTLINE.md` are pair-programming artifacts. `WHAT-REMAINS.md:185-191` correctly catalogs them as preserved for traceability. Not orphans.

**No stale TODO docs found**. No half-written drafts.

---

## Missing docs

1. **L03 architecture overview**. The multi-server async wrapping work introduced a non-trivial coordination contract (`_AsyncAdapter` + `AWAITED_SERVER_METHODS` SoT + `__init__` validation gate). There is no developer-facing doc explaining "if you add a new method to the broadcast loop, update `AWAITED_SERVER_METHODS`". The plan file (`03-multi-server-async-wrapping.md`) is design-time and would mislead a maintainer (its `method_names` tuple is hard-coded). A `docs/dev/multi-server-coordinator.md` analogous to `host-rustc-shim.md` would close this gap.
2. **L02 RA preflight pattern**. Same shape as L03: `compute_file_range()` + `RustAnalyzer.request_code_actions @override` is now the canonical pattern for "pre-flight position validation before LSP round-trip". Future LSPs (basedpyright, jdtls, gopls) that are strict about positions will likely need the same shape. A short `docs/dev/lsp-preflight-validation.md` or a section in an existing dev doc would document the pattern.
3. **CHANGELOG entries** for v0.2.0, v0.3.0, and the v0.2.0-followups batch — see Top-level docs §CHANGELOG above.
4. **No release-notes doc** anchoring tags to user-facing summaries. The project memory has the per-stage summaries; a thin `docs/releases/` index would surface them outside `~/.claude/projects/.../memory/`.

---

## Recommendations (prioritized)

### Critical
1. **Resolve P5a internal contradiction** in `docs/superpowers/plans/spike-results/P5a.md`. The verdict line says DROP; the measurements support SHIP/B. Either (a) re-run, accept, and update verdict to B with a sentence explaining "post-Stage-1E re-run inverted the original cold-start finding", or (b) explicitly annotate "verdict held at C despite re-run measurements; rationale: <X>". Same change must propagate to `spike-results/SUMMARY.md` line 25, `spike-results/PROGRESS.md` lines 31/70/101, and `stage-1h-results/PROGRESS.md:94`. This is `WHAT-REMAINS.md` §1's standing recommendation.

2. **Fix L04 plan file** (`docs/superpowers/plans/2026-04-26-v020-followups/04-cargo-build-rustc-workaround.md`) lines 102-107 to reflect the actual `pytest_plugins` mechanism, mirroring the correction already applied to `host-rustc-shim.md:32`. Otherwise the next person to read the plan to understand what was built will reproduce the rejected approach.

### Important
3. **Add post-shipment STATUS banners** to all 5 v020-followup plan files. Single line at the top: `**STATUS: SHIPPED 2026-04-26 — see [stage-1h-results/PROGRESS.md:NN](../../stage-1h-results/PROGRESS.md) for closure record.**` Prevents future readers from treating the plan as still-active.

4. **Update CHANGELOG.md** with entries for `v0.1.0-mvp` through `stage-v0.2.0-followups-complete`. CHANGELOG is the user-facing release log and is currently 7 tags behind.

5. **Annotate plan-vs-impl drifts** in L02 (dual-mode fixture vs single-mode plan), L03 (`AWAITED_SERVER_METHODS` SoT vs hard-coded tuple), L04 (`pytest_plugins` vs `addopts`), L05 (no facade patch vs prescribed 15-LoC fix). One-line addendum per plan saying "Implementation deviated as follows: …".

### Minor
6. **Bump `CLAUDE.md:89` Last Updated date** to 2026-04-26 (or remove the date field entirely — it tends to drift).

7. **Add a banner** to `mvp-scope-report.md` pointing readers at `WHAT-REMAINS.md` for the actual delivered tool surface (13/24 → 33/34 drift). Do NOT mutate the report itself.

8. **Add `docs/dev/multi-server-coordinator.md`** to document the L03 contract for adding new awaited methods.

9. **Add `docs/dev/lsp-preflight-validation.md`** (or a section in an existing doc) to document the L02 pattern for future strict-position LSPs.

10. **Spot-fix the L02 plan's 1-line drift** (`whole_file_range` is now at conftest line 186, not 185) — only worth doing if Recommendation 5 is being applied anyway.

11. **Add a brief `vendor/serena/README-OVERLAY.md`** (or similar) so a contributor cloning the engine fork standalone has signal that it is the o2-scalpel engine fork. Not required if the engine repo is never cloned standalone.

---

*Author: AI Hive(R)*
