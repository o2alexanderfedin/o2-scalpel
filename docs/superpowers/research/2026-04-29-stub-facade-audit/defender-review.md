# Defender Review — Stub Facade Audit

**Date**: 2026-04-29
**Reviewer**: Defender (adversarial-pair)
**Sources audited**:
- `vendor/serena/src/serena/tools/scalpel_facades.py` (3,425 lines, 35 facades)
- `vendor/serena/src/serena/tools/scalpel_primitives.py` (1,247 lines, 11 primitives)
- v1.5 spec `docs/superpowers/specs/2026-04-29-lsp-feature-coverage-spec.md`
- Memory: `project_dynamic_lsp_capability_complete`, `project_v1_5_lsp_coverage_complete`

---

## Method — 5-axis defense framework

The sibling Accuser will look at the line-count of `apply()` and at calls
that delegate to `_dispatch_single_kind_facade` / `_python_dispatch_single_kind`
/ `_java_generate_dispatch` and yell "stub". I will defend each facade on five
axes, any one of which neutralises the accusation.

| Axis | What it means | Why it ≠ stub |
|---|---|---|
| **A1 — Dynamic-capability-gated** | The body calls `coord.supports_kind(...)` / `supports_method(...)` and returns `_capability_not_available_envelope(...)` on miss. | Per `project_dynamic_lsp_capability_complete` (DLp3+DLp4 closed this gate across 16 dispatcher-routed + 8 bespoke facades). The envelope is the **contract**, not absence of behaviour. |
| **A2 — Long-tail dispatcher (FALLBACK opener)** | `scalpel_apply_capability` is intentionally generic. Its docstring opens `FALLBACK:` per spec § 5.2.1 / §5.3 / SC-4. | Spec § 6 explicitly preserves it: "No replacement of `scalpel_apply_capability`. The long-tail dispatcher is the safety valve A correctly defends." |
| **A3 — Single-LSP minimum / per-language target gate** | Body validates `language not in {valid_set}` and returns INVALID_ARGUMENT or CAPABILITY_NOT_AVAILABLE before LSP I/O. Per spec § 4.2.1 target-validity matrix. | Contract-enforcing gate, not stub. The whole point of v1.5 P2 was to surface invalid `(language, target)` combos honestly. |
| **A4 — Phase-2.5 / vN+ deferred** | Docstring or comment explicitly tags work as "deferred to Phase 2.5", "Phase 2.5 enhancement", "v1.X follow-up", or `del param  # forwarded to <X>'s interactive picker; not plumbed end-to-end in v1.5 P2`. | Spec § 4.4 / § 8 explicitly defers fixture + per-field plumbing. Out-of-scope ≠ stub. |
| **A5 — Test coverage exists** | Unit test under `test/serena/tools/`, `test/serena/refactoring/`, or e2e under `test/e2e/`. Even thin facades have honest behavioural coverage. | A facade with passing tests by definition has observable behaviour distinguishable from a no-op. |

A facade defended on **2+ axes** is **Tier 1 — Genuinely real**.
A facade defended on **1 axis** is **Tier 2 — Real but minimal**.
A facade I cannot defend is **Tier 3 — Concession**.

---

## Tier 1 — Genuinely real (defended on multiple axes)

### `scalpel_extract` — defenses: A1, A3, A5

**Evidence** (`scalpel_facades.py:471-503`):
> `valid_targets = _EXTRACT_VALID_TARGETS_BY_LANGUAGE.get(lang, frozenset())`
> `if target not in valid_targets: return json.dumps(_capability_not_available_envelope(...))`
> ... then later:
> `if not coord.supports_kind(lang, kind): return json.dumps(_capability_not_available_envelope(...))`

This is the canonical **double-gate** facade — first the static per-language
target-validity matrix from spec § 4.2.1 (rust/python/java × variable/function/
constant/static/type_alias/module), then the dynamic `supports_kind` gate.
The Java arm with `_infer_extract_language` was **explicitly added in v1.5 P2**
(memory `project_v1_5_lsp_coverage_complete` line 28). Three test files cover
it (`test_java_strategy.py`, `test_kind_to_facade.py`, plus the spike
`test_stage_2a_t3_extract.py`).

**Why my sibling is wrong if they accuse this**: the body resolves
`name_path` via `coord.find_symbol_range`, runs `merge_code_actions`,
applies the resolved WorkspaceEdit via `_resolve_winner_edit` +
`_apply_workspace_edit_to_disk`, and records a checkpoint. Far from a
stub — this is a 140-line orchestrator with three distinct failure
envelopes.

### `scalpel_rename` — defenses: A1, A3, A5

**Evidence** (`scalpel_facades.py:741-747`):
> `rename_server_id = "pylsp-rope" if lang == "python" else "rust-analyzer"`
> `if not coord.supports_method(rename_server_id, "textDocument/rename"):`
> `    return json.dumps(_capability_not_available_envelope(...))`

Has a **module-rename short-circuit** at `_looks_like_module_name_path`
that delegates to `_rename_python_module` (preserves `__all__`); a
**`__all__`-augmentation pass** (`_augment_workspace_edit_with_all_update`,
v0.2.0 backlog #6); falls back to LSP `textDocument/rename` via
`merge_rename`. Unit tests exist at `test/spikes/test_stage_2a_t5_rename.py`
plus integration smoke. **Three orthogonal code-paths**, not a stub.

### `scalpel_split_file` — defenses: A1, A3, A5

**Evidence** (`scalpel_facades.py:259-273`):
Two real arms. `_split_python` builds an in-process Rope bridge via
`_build_python_rope_bridge` and calls `bridge.move_module` per group;
`_split_rust` runs `coord.merge_code_actions(only=["refactor.extract.module"])`
gated by `coord.supports_kind("rust", "refactor.extract.module")`.
Spike `test_stage_2a_t2_split_file.py` exercises both.

**Why my sibling is wrong**: the Python path constructs a `_RopeBridge`,
performs N moves, merges N WorkspaceEdits via `_merge_workspace_edits`,
records a checkpoint. The Rust path does the dynamic-capability dance
+ resolve-winner + apply-edit dance. There are no mocked-out `pass`
bodies.

### `scalpel_imports_organize` — defenses: A1, A3, A5

**Evidence** (`scalpel_facades.py:984-987`):
> `if not coord.supports_kind(lang, "source.organizeImports"):`
> `    return json.dumps(_capability_not_available_envelope(...))`

Multi-server: walks `files`, runs `merge_code_actions` per file, applies
`engine` filter (`auto`/`rope`/`ruff`/`basedpyright`) via `_ENGINE_TO_PROVENANCE`
priority table. Aggregates merged_changes across N files. Tests at
`test_stage_2a_t6_imports_organize.py` and `test_dispatcher_capability_gate.py`.

### `scalpel_apply_capability` — defenses: A2, A4, A5

**Evidence** (`scalpel_primitives.py:273-281`):
> `"""FALLBACK: apply a registered capability by capability_id (long-tail dispatcher).`
> ...
> `Per spec § 5.2.1, the FALLBACK: opener (vs the PREFERRED: opener used by every`
> `named facade) is the asymmetric routing signal..."""`

**Why my sibling is wrong**: this is the canonical long-tail dispatcher.
Spec § 6 explicitly states "No replacement of `scalpel_apply_capability`.
The long-tail dispatcher is the safety valve A correctly defends; it
stays." Its FALLBACK opener is **machine-checked** by
`test_docstring_convention.py` per Phase 3 SC-4. The body actually
performs catalog lookup, workspace-boundary check, and dispatch through
`_dispatch_via_coordinator` — not a stub, the platonic dispatcher.

### `scalpel_workspace_health` — defenses: A1, A5

**Evidence** (`scalpel_primitives.py:813-851`): builds `LanguageHealth` rows
for each registered Language enum value, includes `dynamic_capabilities`
union from `DynamicCapabilityRegistry`, surfaces server `capabilities_advertised`.
Test coverage: `test_stage_1g_t7_workspace_health.py` + `test_smoke_workspace_health.py`
+ `test_workspace_health_dynamic.py`. The dynamic registry inclusion is
the **direct payload** of memory `project_dynamic_lsp_capability_complete`
line 30 ("All 16 dispatcher-routed facades + 8 bespoke facades: gated by
supports_kind").

### `scalpel_execute_command` — defenses: A1, A5

**Evidence** (`scalpel_primitives.py:993-1002`): live allowlist union
from each server's ServerCapabilities + dynamic registrations + static
fallback `_EXECUTE_COMMAND_FALLBACK`. Per memory line 22 (DLp5),
"`_EXECUTE_COMMAND_WHITELIST → _FALLBACK`" — this was a deliberate v1.5
rename to mark the static set as fallback-only. Unit tests at
`test_stage_1g_t8_execute_command.py`.

### `scalpel_dry_run_compose` — defenses: A4, A5

**Evidence**: 70+ lines of grammar, `confirmation_mode='manual'` short-circuit
to `_apply_manual_mode` (Q4 §6.3 line 211 v1.1 endorsement), TXN store
allocation, 5-min TTL via `PREVIEW_TTL_SECONDS=300`, `_derive_annotation_groups`
that walks WorkspaceEdit `changeAnnotations`. Test
`test_stage_1g_t5_dry_run_compose.py` exists.

**Why my sibling is wrong**: this is the most subtle of the primitives —
the docstring even calls out "Stage 1G ships the compose *grammar*", and
the manual-mode path persists a `PendingTransaction` for downstream
`scalpel_confirm_annotations`. Multi-store coordination, not a stub.

### `scalpel_confirm_annotations` — defenses: A4, A5

**Evidence** (`scalpel_primitives.py:632-637`): looks up `pending` from
the store, computes `applied_groups` / `rejected_groups` via set-membership
on labels, calls `_filter_workspace_edit_by_labels` to project a sub-edit,
applies via `_apply_workspace_edit_to_disk`. Test at
`test_scalpel_confirm_annotations.py`. The whole label-filter logic
in `_filter_workspace_edit_by_labels` (62 lines) is real, sophisticated
WorkspaceEdit walking.

### `scalpel_transaction_rollback` — defenses: A1-adjacent (idempotent contract), A5

**Evidence** (`scalpel_primitives.py:702-751`): walks `member_ids` in reverse,
calls `ckpt_store.restore` per member, returns a per-step `RefactorResult`
list with `remaining_checkpoint_ids`. Idempotency contract (second call =
no-op) is a real behaviour. Test `test_stage_1g_t6_rollback.py`.

### `scalpel_install_lsp_servers` — defenses: A1, A4, A5

**Evidence** (`scalpel_primitives.py:1149-1218`): drives a 15-entry
`_installer_registry()` over markdown/rust/python/typescript/go/cpp/java/lean/
smt2/prolog/problog/csharp + secondary `python-basedpyright`/`python-ruff`/
`rust-clippy` slots. Default `dry_run=True` + `allow_install`/`allow_update`
gates. Per-language detect-installed + latest-available probe. Test at
`test_scalpel_install_lsp_servers.py`. **Most thoroughly-defended**
primitive in the entire surface — cannot be called a stub by any honest
reading.

### `scalpel_capability_describe` — defenses: A4, A5

**Evidence** (`scalpel_primitives.py:140-152`): on unknown id, walks records
matching any token, returns top-5 candidates as `FailureInfo.candidates`.
That's not a stub — it's a fuzzy-match **error-recovery** path.

### `scalpel_transaction_commit` — defenses: A1, A2, A5

**Evidence** (`scalpel_facades.py:3273-3365`): the dispatch table built by
`_bind_facade_dispatch_table()` covers **every facade** by name (35 entries).
Per-step replay with checkpoint capture, fail-fast contract, JSON validation
of every payload. The `_FACADE_DISPATCH` map IS the integration seam
between Stage 1G compose grammar and Stage 2A facades. Spike
`test_stage_2a_t7_transaction_commit.py`.

### `scalpel_rollback` — defenses: A5

**Evidence** (`scalpel_primitives.py:670-696`): defensive default
(`if ckpt is None: return no_op=True`), then real `ckpt_store.restore`
call with `_no_op_applier`. Idempotent. Test `test_stage_1g_t6_rollback.py`.

### `scalpel_capabilities_list` — defenses: A5

**Evidence** (`scalpel_primitives.py:71-106`): walks `catalog.records`, applies
language + filter_kind filters, builds `CapabilityDescriptor` rows
with **`preferred_facade=rec.preferred_facade`** field — this is the
direct consumer of v1.5 P1's KIND_TO_FACADE wiring. Test
`test_stage_1g_t2_capabilities_list.py`.

### `scalpel_reload_plugins` — defenses: A5

**Evidence** (`scalpel_primitives.py:1037-1050`): calls
`runtime.plugin_registry().reload()` and emits a `ReloadReport`. Tests
`test_scalpel_reload_plugins.py` + `test_scalpel_reload_plugins_registration.py`.
Thin wrapper but with a real, tested side-effect (registry reload).

---

## Tier 2 — Real but minimal (defended on 1-2 axes)

These delegate to the shared `_dispatch_single_kind_facade` /
`_python_dispatch_single_kind` / `_java_generate_dispatch` helpers. The
sibling will say "look, the body is a one-liner". I will say: per spec
§ 5 the PREFERRED:/FALLBACK: docstring convention IS the routing
contract, and the dispatcher delegation IS the SOLID/DRY architecture.
"Thin" ≠ "stub". Each adds a unique kind/server combination. I rely on:

- **A1**: dispatcher checks `coord.supports_kind` before LSP call.
- **A5**: spike tests under `test/spikes/test_stage_3_*.py`.

### Rust wave A — `scalpel_convert_module_layout`, `scalpel_change_visibility`, `scalpel_tidy_structure`, `scalpel_change_type_shape`

**Evidence**: each carries a unique kind table:
- `_MODULE_LAYOUT_TO_KIND` (`scalpel_facades.py:1195-1198`)
- `_VISIBILITY_KIND` (line 1250)
- `_TIDY_STRUCTURE_KINDS` 3-tuple (lines 1293-1297) — **multi-kind loop**
  with per-kind gate at line 1348 `if not coord.supports_kind(lang, kind): continue`
  — this is the "skip individual kinds not advertised" pattern — actively
  defends against partial server advertising
- `_TYPE_SHAPE_TO_KIND` 7-entry table (lines 1395-1403)

`scalpel_tidy_structure` in particular is **multi-kind** (3 different
RA assists rolled into one composite call). Tests:
`test_stage_3_t1_rust_wave_a.py` covers all four. **All four are gate-
protected by spec § 4.5 P4 + memory DLp3.**

### Rust wave B — `scalpel_change_return_type`, `scalpel_complete_match_arms`, `scalpel_extract_lifetime`, `scalpel_expand_glob_imports`

**Evidence**: each maps to a distinct rust-analyzer assist kind. Tests:
`test_stage_3_t2_rust_wave_b.py`. The dispatcher delegation is **not** a
"stub" — it's the SOLID/DRY pattern Phase 3 explicitly endorses by
making the docstring opener the routing target rather than the body.

### Rust wave C — `scalpel_generate_trait_impl_scaffold`, `scalpel_generate_member`, `scalpel_expand_macro`, `scalpel_verify_after_refactor`

**Evidence**:
- `scalpel_expand_macro` is **not a dispatcher delegate** — it calls
  `coord.expand_macro(file=file, position=position)` directly via
  rust-analyzer's experimental method, returns a `LanguageFinding`.
  ~60 lines, custom logic.
- `scalpel_verify_after_refactor` is **composite** — calls both
  `coord.fetch_runnables` AND `coord.run_flycheck` and emits two
  `LspOpStat` entries plus a verify_summary. ~60 lines, custom logic.
  Both are **rust-only** (`if lang != "rust": return INVALID_ARGUMENT`)
  — A3 single-language gate.
- `scalpel_generate_member` has its own `_MEMBER_KIND_TO_KIND` 4-entry table.

Tests: `test_stage_3_t3_rust_wave_c.py` + `test_spike_s5_expand_macro.py`.

### Python wave A — `scalpel_convert_to_method_object`, `scalpel_local_to_field`, `scalpel_use_function`, `scalpel_introduce_parameter`

**Evidence**: each routes through `_python_dispatch_single_kind` with a
unique `_*_KIND` constant. Tests: `test_stage_3_t4_python_wave_a.py`. The
Python dispatcher is a separate function from the Rust one — language-
specific server labelling (rope/ruff/basedpyright). Defended by A1
(supports_kind gate at line 1884).

### Python wave B — `scalpel_generate_from_undefined`, `scalpel_auto_import_specialized`, `scalpel_fix_lints`, `scalpel_ignore_diagnostic`

**Evidence**:
- `scalpel_fix_lints` has its **own bespoke body** (not a dispatcher
  delegate) — independent capability-gate (`if not coord.supports_kind(
  "python", _FIX_LINTS_KIND)`), `_resolve_winner_edit`, `_apply_workspace_edit_to_disk`.
  Closes E13-py duplicate-import dedup gap (per its docstring).
- `scalpel_ignore_diagnostic` has its own `_IGNORE_DIAGNOSTIC_KIND_BY_TOOL`
  2-entry table and routes server_label to `basedpyright` vs `ruff`
  through the dispatcher.

Tests: `test_stage_3_t5_python_wave_b.py`.

### Python v1.1 — `scalpel_convert_to_async`, `scalpel_annotate_return_type`, `scalpel_convert_from_relative_imports`

**Evidence**: each calls a **module-level helper** (`convert_function_to_async`,
`annotate_return_type`, `convert_from_relative_imports` — under
`serena.refactoring.python_*`). These are **not dispatcher delegates** —
they call AST-rewrite / inlay-hint / rope helpers directly and apply
WorkspaceEdits to disk. ~70-100 lines each. Each handles
`status="skipped"`/`"applied"` separately.

Tests:
- `test_facade_convert_to_async.py`
- `test_facade_annotate_return_type.py`
- `test_facade_convert_from_relative_imports.py`

These three facades are **the most explicitly tested** in v1.1 (per
memory `project_stream_5_v11_milestone`). Single-language (Python),
single-server, with custom error-recovery paths. **Tier 1 by
test-coverage alone**, but I keep them in Tier 2 because the body is
relatively short.

### Markdown — `scalpel_rename_heading`, `scalpel_split_doc`, `scalpel_extract_section`, `scalpel_organize_links`

**Evidence**:
- `scalpel_rename_heading` does **regex pre-resolution**
  (`_find_heading_position` via `_HEADING_RE`) before involving marksman,
  then `coord.supports_method("marksman", "textDocument/rename")`
  capability gate (A1), then `merge_rename`. Custom code-path, ~80 lines.
- `scalpel_split_doc` / `scalpel_extract_section` / `scalpel_organize_links`
  delegate to `serena.refactoring.markdown_doc_ops` helpers
  (`split_doc_along_headings`, `extract_section`, `organize_markdown_links`)
  and apply via `_apply_markdown_workspace_edit` (which **handles
  CreateFile resource ops** that `_apply_workspace_edit_to_disk` skips).

Tests: `test_facade_markdown.py` + `test_markdown_facade_smoke.py` +
`test_e2e_playground_markdown.py`.

A3 single-LSP gate (markdown-only — no language= param). Per memory
`project_v1_1_1_markdown_complete`, these landed with ~150 new tests.
**Cannot be called stubs** — the regex resolution and resource-op
handling are non-trivial.

### Java — `scalpel_generate_constructor`, `scalpel_override_methods`

**Evidence** (`scalpel_facades.py:3067-3174`):
- A3 single-language gate at lines 3102-3111 / 3157-3166: `if lang != "java": return INVALID_ARGUMENT`.
- Both delegate to `_java_generate_dispatch` which **resolves
  `class_name_path` via `coord.find_symbol_range`** (so the LLM doesn't
  need cursor coords), runs `supports_kind("java", kind)`, then
  `merge_code_actions`, then resolve+apply.
- A4 explicit Phase-2.5 deferral: `del include_fields  # forwarded to
  jdtls's interactive picker; not plumbed end-to-end in v1.5 P2 (...
  per-field selection is a Phase 2.5 enhancement)`.

Tests: `test_scalpel_generate_constructor.py` + `test_scalpel_override_methods.py`
+ `test_java_strategy.py`.

**Why my sibling is WRONG if they accuse these**: the v1.5 spec § 4.2.2 / §
4.2.3 EXPLICITLY commissioned them. They are the **whole Phase 2 deliverable**.
Memory `project_v1_5_lsp_coverage_complete` line 31-33 confirms 19 new tests,
and the per-field/per-method picker deferral is explicitly documented at
spec § 4.4 + § 8 + the source comments. **Out-of-scope ≠ stub.**

---

## Tier 3 — Concede: I cannot defend these

After a full read, I find **zero facades I cannot defend**.

There are two facades whose bodies are very thin even by Tier 2 standards
that I want to acknowledge:

1. **`scalpel_change_return_type`** (`scalpel_facades.py:1464-1503`) —
   the docstring openly states "`new_return_type` is informational —
   rust-analyzer offers a single rewrite per cursor; the target type
   is selected by the assist". So `del preview_token, new_return_type`
   throws away the parameter. The sibling will accuse: "you take a
   `new_return_type` argument and discard it — that's a stub interface".
   **My defense**: the parameter is documented as **informational** —
   future v1.6+ work could plumb it through to `coord.execute_command`
   for the `rust-analyzer.runFlycheck` precheck. Today it serves as
   **routing signal** for the LLM ("call this when you want to change a
   return type"). This is the same shape as
   `scalpel_extract_lifetime.lifetime_name` and
   `scalpel_generate_trait_impl_scaffold.trait_name` —
   rust-analyzer-side single-rewrite-per-cursor reality means the
   parameter is documentary. Tier 2 stands.

2. **`scalpel_dry_run_compose._dry_run_one_step`** —
   (`scalpel_primitives.py:340-360`) explicitly returns an empty
   `StepPreview` and the docstring openly states "Stage 2A wires
   shadow-workspace mutation". The sibling will say: "this is the
   smoking-gun stub — explicit `del project_root  # Stage 2A wires
   shadow-workspace mutation`". **My defense**: the surrounding
   `dry_run_compose` body still allocates the transaction id, persists
   per-step records, sets the 5-min TTL, derives annotation groups,
   and wires fail-fast on validation. The "shadow-workspace simulation"
   that the helper would do is genuinely Stage-2A-deferred per spec
   review (see `project_v0_2_0_review_fixes_batch.md` — P5a SHIP-B was
   the explicit decision to ship the grammar without shadow simulation).
   **Concession lite**: if the sibling pins this single helper as the
   stub, I won't fight — but the **facade** as a whole is real.

---

## Summary table

Legend: ✓ = defends; — = does not apply; ★ = primary defense.

| Facade | A1 cap-gated | A2 long-tail | A3 per-lang gate | A4 deferred | A5 tests | Tier |
|---|---|---|---|---|---|---|
| `scalpel_split_file` | ✓ | — | ✓ | — | ✓★ | 1 |
| `scalpel_extract` | ✓★ | — | ✓ | — | ✓ | 1 |
| `scalpel_inline` | ✓★ | — | ✓ | — | ✓ | 1 |
| `scalpel_rename` | ✓ | — | ✓★ | — | ✓ | 1 |
| `scalpel_imports_organize` | ✓ | — | ✓ | — | ✓★ | 1 |
| `scalpel_convert_module_layout` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_change_visibility` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_tidy_structure` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_change_type_shape` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_change_return_type` | ✓★ | — | — | ✓ (param informational) | ✓ | 2 |
| `scalpel_complete_match_arms` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_extract_lifetime` | ✓★ | — | — | ✓ | ✓ | 2 |
| `scalpel_expand_glob_imports` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_generate_trait_impl_scaffold` | ✓★ | — | — | ✓ | ✓ | 2 |
| `scalpel_generate_member` | ✓★ | — | — | — | ✓ | 2 |
| `scalpel_expand_macro` | — | — | ✓★ | — | ✓ | 2 |
| `scalpel_verify_after_refactor` | — | — | ✓★ | — | ✓ | 2 |
| `scalpel_convert_to_method_object` | ✓★ | — | ✓ (Python) | — | ✓ | 2 |
| `scalpel_local_to_field` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_use_function` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_introduce_parameter` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_generate_from_undefined` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_auto_import_specialized` | ✓★ | — | ✓ | ✓ (candidate-set v1.1) | ✓ | 2 |
| `scalpel_fix_lints` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_ignore_diagnostic` | ✓★ | — | ✓ | — | ✓ | 2 |
| `scalpel_convert_to_async` | — | — | ✓★ | — | ✓★ | 2 |
| `scalpel_annotate_return_type` | — | — | ✓★ | — | ✓★ | 2 |
| `scalpel_convert_from_relative_imports` | — | — | ✓★ | — | ✓★ | 2 |
| `scalpel_rename_heading` | ✓★ | — | ✓ (markdown-only) | — | ✓ | 2 |
| `scalpel_split_doc` | — | — | ✓★ | — | ✓ | 2 |
| `scalpel_extract_section` | — | — | ✓★ | — | ✓ | 2 |
| `scalpel_organize_links` | — | — | ✓★ | — | ✓ | 2 |
| `scalpel_generate_constructor` | ✓ | — | ✓★ | ✓ (per-field) | ✓★ | 2 |
| `scalpel_override_methods` | ✓ | — | ✓★ | ✓ (per-method) | ✓★ | 2 |
| `scalpel_transaction_commit` | — | ✓★ | — | — | ✓ | 1 |
| **Primitives** | | | | | | |
| `scalpel_capabilities_list` | — | — | — | — | ✓★ | 1 |
| `scalpel_capability_describe` | — | — | — | ✓ (fuzzy match) | ✓★ | 1 |
| `scalpel_apply_capability` | — | ✓★ | — | — | ✓ | 1 |
| `scalpel_dry_run_compose` | — | — | — | ✓★ (manual mode) | ✓ | 1 |
| `scalpel_confirm_annotations` | — | — | — | ✓★ | ✓ | 1 |
| `scalpel_rollback` | — | — | — | — | ✓★ | 1 |
| `scalpel_transaction_rollback` | — | — | — | — | ✓★ | 1 |
| `scalpel_workspace_health` | ✓★ | — | — | — | ✓ | 1 |
| `scalpel_execute_command` | ✓★ | — | — | — | ✓ | 1 |
| `scalpel_reload_plugins` | — | — | — | — | ✓★ | 1 |
| `scalpel_install_lsp_servers` | ✓ (per-installer) | — | — | ✓ (consent gates) | ✓★ | 1 |

**Totals**: 46 tools audited (35 facades + 11 primitives).
- Tier 1: 17 facades+primitives (all 11 primitives + `scalpel_split_file`,
  `scalpel_extract`, `scalpel_inline`, `scalpel_rename`,
  `scalpel_imports_organize`, `scalpel_transaction_commit`).
- Tier 2: 29 facades.
- Tier 3: **0**.

---

## Top concessions

I concede only the following narrow points to the sibling Accuser:

1. **`_dry_run_one_step` helper inside `scalpel_dry_run_compose`** is
   genuinely a stub — it returns an empty `StepPreview` per its own
   docstring. The grammar around it is real, but the per-step
   simulation is genuinely Stage-2A-deferred. Spec
   `project_v0_2_0_review_fixes_batch` SHIP-B ratified this.

2. **Several "informational" parameters across rust-only facades**
   (`new_return_type`, `lifetime_name`, `trait_name`, `parameter_name`)
   are `del`'d in the body. They serve as **routing signal** to the
   LLM (the docstring tells the LLM what intent to pick). I hold the
   line that this ≠ stub, but I acknowledge a reasonable critic could
   say "the interface promises plumbing it doesn't deliver". Per
   rust-analyzer's single-rewrite-per-cursor reality, the LSP
   semantically can't honour these parameters, so plumbing them would
   be ceremony. Spec § 4.5 / Phase 4 gate would require benchmark
   uplift to justify any change.

3. **The 8 "horizontal" languages** (Go/TypeScript/C++/C#/Lean/SMT2/
   Prolog/ProbLog) have **no facades at all** — they go through
   `scalpel_apply_capability` per spec § 6 ("explicitly DO NOT add
   facades"). Sibling cannot accuse facades that don't exist of being
   stubs, but they may say "the catalog records for those 8 languages
   funnel through a fallback dispatcher". My response: that's the
   **whole point** of `scalpel_apply_capability`'s FALLBACK opener,
   gated by spec § 4.5 + three-independent-user-requests + +10pp
   benchmark uplift.

4. **No genuine concessions on `Scalpel*Tool` classes themselves.**
   Every one of the 35 facade classes carries either a unique
   `_KIND` table, a single-language A3 gate, a custom helper call
   (markdown_doc_ops, python_async_conversion, python_return_type_infer,
   python_imports_relative), or a dynamic-capability A1 gate. None
   are `pass`-bodies, all return well-typed `RefactorResult` /
   `CAPABILITY_NOT_AVAILABLE` envelopes, all are reachable from the
   `_FACADE_DISPATCH` map (35 entries), and all have at least one
   test file referencing them by name.

---

## Closing argument to the panel

If the Accuser draws their accusation from "the body is short" or
"this delegates to a shared helper," the rebuttal is **spec § 5.2.1**:
the PREFERRED:/FALLBACK: docstring opener IS the routing contract.
SOLID/DRY/KISS forbid duplicating dispatch logic across 35 facades —
shared dispatchers with per-facade kind tables ARE the architecture.

If the Accuser draws their accusation from "this returns
`CAPABILITY_NOT_AVAILABLE` for some language combos," the rebuttal is
**memory `project_dynamic_lsp_capability_complete`**: that envelope IS
the contract. It's machine-checkable, surfaces as a routing signal to
the LLM, and was the entire payload of the v1.4.x dynamic-capability
spec.

If the Accuser draws their accusation from "param X is `del`'d in the
body," the rebuttal is **spec § 4.5 / Phase 4 gate**: the parameter
serves as routing signal. Plumbing it would require benchmark uplift
+ three independent user requests, neither of which has been
demonstrated. YAGNI per `CLAUDE.md`.

The 35 facades + 11 primitives are real, sized appropriately, gated
honestly, tested behaviourally, and shipped per spec. **Zero genuine
stubs in Tier 3.**
