# Minimalist Plan — STUB Facade Fix v1.6
**Stance**: YAGNI; v1.6 ships only must-fix bugs + doc convention sweep
**Date**: 2026-04-29
**Author**: AI Hive® (minimalist planner, adversarial-pair round)
**Inputs**: STUB-FACADE-AUDIT.md (43 tools), defender-review.md (Tier 1/2 framing), spec § 4.5 + § 6, CLAUDE.md (YAGNI mandate)

---

## TL;DR

- **MUST-FIX**: **2 facades** (one bug that is a real contract violation; one bug that lies on disk to Python users)
- **DOC-ONLY**: **15 facades** (one batch PR — opener-tag the informational params; *no* Examples-block sweep)
- **DEFER**: **5 facades + 1 helper** (gate: 3 independent user requests OR +10pp benchmark uplift)

The audit identified 4 STUB + 18 HYBRID. The exhaustive sibling will plan ~22 fixes. **My claim: 2 of those produce user-visible breakage today; the other 20 are LLM contract polish that does not move the v1.5 routing-accuracy needle (53.3%) above the §4.5 +10pp gate floor.** The §6 explicit "do not" list already amputates 8 horizontal language waves and 4 speculative facade classes. We extend the same discipline inward: do not refactor the 18 HYBRIDs without evidence.

---

## MUST-FIX (v1.6 contract bugs)

Two and only two. Both fail the simplest LLM-on-loop sanity test: a tool reports `applied=True` while the disk is unchanged. That is the one shape we cannot ship.

### Fix 1 — `scalpel_apply_capability` reports false success

- **What breaks today**: `_dispatch_via_coordinator` (`scalpel_primitives.py:201–270`) calls `coord.merge_code_actions`, gets a non-empty `actions` list, then **skips** `_resolve_winner_edit` + `_apply_workspace_edit_to_disk`, records `applied={"changes": {}}` on the checkpoint, and returns `RefactorResult(applied=True)`. Any LLM that routes a long-tail action through the FALLBACK dispatcher (per spec § 6, this is the **safety valve covering 82% / 59 catalog records across 9 languages** per pragmatic-surveyor) gets a green check while disk is untouched. Every Phase-4-eligible language flows through this one function.
- **Minimum fix**: copy the canonical pattern from `_split_rust:351–356`. Replace `applied={"changes": {}}` (line 261) with `edit = _resolve_winner_edit(coord, actions[0])`; call `_apply_workspace_edit_to_disk(edit)` before `runtime.checkpoint_store().record(applied=edit, snapshot=...)`. ~8 lines.
- **Test that proves it**: `test_apply_capability_writes_real_edit_for_rust_assist` — pick any RA assist not covered by a named facade (e.g. `assist.move_format_string_arg`), assert post-call `Path.read_text()` differs from pre-call. The existing `test_apply_capability_dispatches_when_in_workspace` patches `_dispatch_via_coordinator` *out* and never exercises the body — that's why this bug shipped.
- **Effort**: **M** (8 lines of code + 1 test + need a fixture that produces a non-empty action list — fixture cost dominates).
- **Branch**: `fix/v1.6-apply-capability-real-apply`
- **Tag**: `v1.6.0-apply-capability-fix`

### Fix 2 — `scalpel_split_file` (Python branch) records checkpoint, never writes disk

- **What breaks today**: `_split_python` (`scalpel_facades.py:275–305`) calls `bridge.move_module(...)`, merges N WorkspaceEdits, calls `record_checkpoint_for_workspace_edit(merged, snapshot={})` — but `facade_support.py:143–151` confirms that helper **only stores the edit; it does not apply**. Returns `applied=True`. Compare with `_split_rust:353` which does call `_apply_workspace_edit_to_disk`. Python users invoking `scalpel_split_file` on a 3-language playground (per memory `project_v1_3_milestone_complete`) get green-check + zero disk delta.
- **Minimum fix**: insert one line at line 296 (after `_merge_workspace_edits`): `_apply_workspace_edit_to_disk(merged)` before `record_checkpoint_for_workspace_edit`. ~1 line. *Do not* fix the `groups[*]` symbol-list-vs-keys mismatch in this PR — that is a separate semantic question that requires rope-bridge work, and `bridge.move_module` (whole-module move) is what 100% of the existing tests exercise.
- **Test that proves it**: `test_split_python_applies_to_disk` — already-existing fixture in `test_stage_2a_t2_split_file.py::test_split_file_python_branch`; just add a post-call assertion `assert Path(target).exists() and Path(source).read_text() != original`.
- **Effort**: **S** (1 line + 1 assertion).
- **Branch**: `fix/v1.6-split-python-apply-to-disk`
- **Tag**: `v1.6.0-split-python-fix`

---

## DOC-ONLY (single batch PR)

**Branch**: `docs/v1.6-facade-informational-params-batch`
**Tag**: `v1.6.0-doc-convention`

The audit's most defensible critique (§ A4 cluster of 12 silently-dropped parameters) is a **docstring convention gap, not a bug**. The defender's argument that `del param` parameters serve as "routing signals to the LLM" is correct *if* the docstring announces them as informational. Spec § 5.2.1 already mandates the `PREFERRED:` opener convention; we extend it: any `del`'d parameter gets a one-line `Note: <param> is informational; <LSP> picks the action per cursor.` block in the docstring.

**Single PR, ~15 facades, no signature changes, no behavior changes, no test changes.** This is the maximum-leverage minimum-risk move: it converts the LLM-contract critique into surface honesty without touching dispatch code.

Facades getting a `Note: informational` block:

| Facade | Param to tag |
|---|---|
| `scalpel_change_visibility` | `target_visibility` |
| `scalpel_change_return_type` | `new_return_type` (already informally tagged — promote to opener) |
| `scalpel_extract_lifetime` | `lifetime_name` |
| `scalpel_introduce_parameter` | `parameter_name` |
| `scalpel_generate_from_undefined` | `target_kind` |
| `scalpel_auto_import_specialized` | `symbol_name` |
| `scalpel_ignore_diagnostic` | `rule` |
| `scalpel_extract` | `new_name`, `visibility`, `similar`, `global_scope` |
| `scalpel_inline` | `name_path`, `remove_definition` |
| `scalpel_imports_organize` | `add_missing`, `remove_unused`, `reorder` |
| `scalpel_split_file` (Rust branch) | `groups` |
| `scalpel_tidy_structure` | `scope` |
| `scalpel_expand_macro` | `dry_run` |
| `scalpel_verify_after_refactor` | `dry_run` |
| `scalpel_fix_lints` | `rules` (already tagged — promote to opener) |

**Explicitly excluded from this batch**:
- **No `Examples:` blocks.** The audit § A5 finding (zero Examples blocks across 43 tools) is real but soft. Spec § 5.2.1 routing is asymmetric on `PREFERRED:`/`FALLBACK:` openers, **not** Examples. Adding 43 Examples blocks is ~700 LoC of doc bloat with zero benchmark signal. **DEFER until §4.5 routing accuracy < 53.3% baseline** for an `Examples`-grounded prompt set.
- **No signature surgery.** Removing the `del`'d parameters from method signatures is a breaking API change. We don't have evidence callers pass them deliberately. Tagging informational is forward-compatible; removing is not.

---

## DEFER (gate criteria attached)

| Facade / helper | Why DEFER (cite) | Un-defer when |
|---|---|---|
| `scalpel_rollback` + `scalpel_transaction_rollback` (`_no_op_applier`) | YAGNI per CLAUDE.md. The defender's "idempotency contract" defense holds — second call IS no-op. The "rollback puts disk back" expectation is real but speculative; v1.5 never benchmarked rollback usage. Spec § 6 doesn't require it. **A real reverse-applier is L-effort** (must populate `snapshot=` everywhere first — 4 call sites — then thread inverse through checkpoint store). L-effort items are out of scope per round-rules. | 3 users hit "rollback didn't undo my edit" OR add a P3 doc-only WARNING block in the v1.6.1 patch (cheap insurance — 4 lines per docstring; included in DOC-ONLY batch as a stretch). |
| `scalpel_dry_run_compose._dry_run_one_step` | Defender concedes this stub but spec `project_v0_2_0_review_fixes_batch.md` SHIP-B **explicitly ratified shipping without shadow simulation**. The commit path (`scalpel_transaction_commit`) does dispatch real facades, so the user CAN compose+commit; only the *preview* is empty. YAGNI. Effort is L (shadow-workspace stub + dispatcher integration). | A composed transaction silently corrupts state because no preview surfaced a failure. Today fail-fast in commit catches the same case. |
| `scalpel_workspace_health` (11-language partial walk) | HYBRID-P3 only; only iterates `(Language.PYTHON, Language.RUST)` (line 832). Surfaces empty `languages: {}` for the other 9 languages per memory v1.4. **Cosmetic** — health probe not a write op. No user has filed it. | TypeScript/Go/Java users open an issue saying "workspace_health says my project has no languages". |
| `scalpel_split_file` (Python branch — `groups[*]` symbol lists) | Already in MUST-FIX for the disk-apply (Fix 2). The semantic gap (iterating keys not values) is **a separate concern requiring rope-bridge symbol-move support**. Tests pass with whole-module moves; no user has shown a `groups: {"a.py": ["foo", "bar"]}` payload that breaks. | One real fixture demonstrates the symbol-list intent, OR rope-bridge gains `move_symbols_to_module`. |
| `scalpel_generate_trait_impl_scaffold.trait_name` | The audit calls this the *one* `del`-of-required-positional case. **Defender's A4 defense holds** (rust-analyzer is single-rewrite-per-cursor; the LSP semantically can't honor it). Plumbing to `coord.execute_command` is speculative LSP-shape work. Doc-only opener-tag goes in the DOC-ONLY batch. | RA exposes a parameterized `extract.trait_impl` command with explicit `trait_name` arg. |
| Examples blocks (universal A5 gap) | Spec § 5.2.1 makes routing asymmetric on `PREFERRED:`/`FALLBACK:` tokens; Examples are **not** part of that contract. § 4.5 baseline is 53.3% routing accuracy with zero Examples — Examples have no demonstrated uplift. CLAUDE.md YAGNI. | `routing_accuracy < 53.3%` on a refreshed benchmark scorer that consumes Examples blocks. |

---

## Why this beats over-planning

**Argument 1 — § 6 already drew the line; we honor it inward.** Spec § 6 lists six explicit "do nots": no facades for 8 horizontal languages, no replacement of `apply_capability`, no read-only LSP facades, no `change_signature`/`pull_up`/`push_down`/`surround_with`, no extra markdown facades, no facade count past 40. The exhaustive sibling will respect § 6 outwardly while quietly producing 20+ fixes inwardly that grow the surface area we promised not to grow. The minimalist position is consistent: § 6's discipline applies to *all* speculative work, including HYBRID-cluster fixes that no benchmark and no user has requested. **A facade with a `del param` and a `Note: informational` docstring is 100% spec-compliant per § 5.2.1.** Doc tag, ship, move on.

**Argument 2 — § 4.5 demands evidence, not symmetry.** The Phase 4 gate is +10pp routing-accuracy uplift OR three independent user requests, *whichever comes first*. v1.5's measured baseline is 53.3% (memory `project_v1_5_lsp_coverage_complete`). Of the audit's 22 STUB+HYBRID facades, exactly **0** have a benchmark trace showing they cause routing failures, and **0** have three user requests filed. Applying the gate symmetrically: most of these "fixes" cannot pass their own door. The two MUST-FIX items pass a different gate — the **truth-in-applied** gate, which is non-negotiable because it's the contract `RefactorResult.applied=True` makes to *every* downstream tool, including `scalpel_transaction_commit`'s fail-fast walk and `scalpel_rollback`'s checkpoint store.

**Argument 3 — Group aggressively to prove YAGNI and keep the v2.0 ceiling at 40.** v1.5 sits at 36 facades; v2.0 ceiling is 40 (spec § 6). The exhaustive sibling will produce 4–6 PRs across the 22-facade audit; each PR adds review surface, regression risk, and CHANGELOG noise. The minimalist plan is **3 PRs total**: (1) `apply_capability` real-apply, (2) `split_python` real-apply, (3) the docstring-batch sweep covering 15 facades + maybe rollback-warning stretch. **3 PRs, ≤ ~25 lines of behavior change, 1 batch of doc edits, zero new facades, zero signature breaks.** That's the minimum-viable-fix set that genuinely moves the contract honesty needle without burning v1.6's budget on speculative completion. The remaining DEFER items live behind the §4.5 gate, where they belong, with their un-defer criteria documented above so future maintainers (or this same agent next quarter) have a clear trigger condition.

---

## Convention compliance check

- **Atomic plan file** drafted 2026-04-29; STATUS update due 2026-05-06 per CLAUDE.md plan-file conventions (executed / deferred / superseded).
- **No new facades**, no signature changes, no v2.0-ceiling impact (still 36).
- **No commits** in this round (READ-ONLY mandate).
- **All DEFER items have un-defer triggers** (CLAUDE.md "review changes with a separate subtask before commit" — gate is the trigger).
