# Skeptic Review — Stub Facade Audit

**Reviewer**: Skeptic adversarial subagent
**Working dir**: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena`
**Files audited**:
- `src/serena/tools/scalpel_facades.py` (33 facade classes — `Scalpel*Tool`)
- `src/serena/tools/scalpel_primitives.py` (10 primitive classes — `Scalpel*Tool`)

Total facades reviewed: **43** (33 facades + 10 primitives, including the FALLBACK dispatcher and `ScalpelTransactionCommitTool`).

---

## Method

I scored each facade across the 5 axes the prompt specified. A `1` means "stub-evidence flagged" (bad); `0` means "real" (good).

| Axis | Definition | How I evaluated |
|---|---|---|
| **A1** No real LSP dispatch | Does `apply()` actually call `coord.merge_code_actions` / `merge_rename` / `expand_macro` / `executeCommand` etc., OR does it short-circuit to envelope/dict/raise? | Read each `apply()` body; trace through shared dispatchers (`_dispatch_single_kind_facade`, `_python_dispatch_single_kind`, `_java_generate_dispatch`). |
| **A2** No tests | Is there a unit/spike/e2e test that calls `apply()` with non-trivial input and asserts non-trivial output? | `find test/ -name '*.py' \| xargs grep -l <facade>`. |
| **A3** Empty workspace edit | Does `apply()` ever return `applied=True` with a real `WorkspaceEdit`, or always `{"changes": {}}` / `applied=False`? | Trace post-LSP path: does `_apply_workspace_edit_to_disk` get called with a populated edit? |
| **A4** Hardcoded fallback / TODOs / "Stage 2A wires" / "Phase 2.5" | Visible deferral comments in code. | grep for `TODO`, `placeholder`, `pass-through`, `Stage 2A wires`, `Phase 2.5`. |
| **A5** No docstring example | Concrete usage Examples section in the docstring? | grep for `Examples?:` — **count = 0 across both files**. |

**Universal A5 finding**: `grep -cn "Examples\?:" scalpel_facades.py scalpel_primitives.py` → **`0` and `0`**. Every single facade fails A5. This is the cheapest stub-signal in the codebase. The `PREFERRED:`/`FALLBACK:` opener convention from spec § 5.2.1 IS present (33 of 33 facades open with `PREFERRED:`; the FALLBACK dispatcher opens with `FALLBACK:`), so Phase 3 docstring convention has shipped — but no facade carries a `>>> tool.apply(...)` example block. The router has the asymmetric token but no concrete grounding for argument shapes.

**Universal A4 finding (parameter ablation)**: Many facades `del` advertised parameters at the top of `apply()`, silently discarding LLM input. This is the most damning stub pattern: the docstring promises behavior the body cannot deliver. Documented per-facade below.

---

## Tier 1 — Hard stubs (3-5 axes flagged)

### `scalpel_apply_capability` (`ScalpelApplyCapabilityTool` @ scalpel_primitives.py:273) — axes flagged: **A1 (partial), A3, A4, A5**

**Evidence** — from `_dispatch_via_coordinator` (scalpel_primitives.py:201):

```python
def _dispatch_via_coordinator(...):
    """Drive the Stage 1D coordinator + Stage 1B applier.

    Stage 1G ships the dispatcher *plumbing*; the Stage 2A ergonomic
    facades exercise the full code-action -> resolve -> apply pipeline.
    """
    del params, preview_token  # Stage 2A wires these end-to-end
    ...
    actions = coord.merge_code_actions(...)              # ← dispatch happens
    ...
    if dry_run: return RefactorResult(applied=False, ..., preview_token=...)
    ckpt_id = runtime.checkpoint_store().record(
        applied={"changes": {}},                          # ← EMPTY EDIT recorded
        snapshot={},
    )
    return RefactorResult(applied=True, ..., checkpoint_id=ckpt_id)   # ← lies: applied=True with no edit
```

**Why this is a stub**: This is the FALLBACK dispatcher — the safety valve for the 59 of 72 catalog records that have no named facade (per pragmatic-surveyor.md). It DOES call `merge_code_actions`, but it never resolves the winner action, never applies its WorkspaceEdit to disk, and records the checkpoint with `applied={"changes": {}}`. The docstring of the class itself bills it as the long-tail dispatcher (line 273-281) — but in practice it returns `applied=True` while having modified zero bytes on disk. Compare to `_dispatch_single_kind_facade` (scalpel_facades.py:1102) which DOES call `_resolve_winner_edit` + `_apply_workspace_edit_to_disk`.

`del params, preview_token  # Stage 2A wires these end-to-end` (line 216) is an explicit "this is unfinished" admission — yet `params` is the per-capability config (the entire reason the dispatcher exists for non-trivial kinds).

**Test gap (A2 partial)**: The test `test_apply_capability_dispatches_when_in_workspace` (test_stage_1g_t4_apply_capability.py:85) **patches out `_dispatch_via_coordinator` entirely** and mocks the return value. The buggy body of the dispatcher is never exercised by tests.

**Verdict**: This is the highest-confidence stub in the audit. It claims long-tail coverage for ~82% of the catalog and silently no-ops behind `applied=True`.

---

### `scalpel_dry_run_compose` (`ScalpelDryRunComposeTool` @ scalpel_primitives.py:473) — axes flagged: **A1, A3, A4, A5**

**Evidence** — from `_dry_run_one_step` (scalpel_primitives.py:340):

```python
def _dry_run_one_step(step, *, project_root, step_index) -> StepPreview:
    """Virtually apply one step against the in-memory shadow workspace.

    Stage 1G ships the compose *grammar* (transaction id allocation,
    per-step preview rows, fail-fast walking, 5-min TTL). The actual
    shadow-workspace mutation lives in Stage 2A — the ergonomic facades
    are the only callers that mutate state.
    """
    del project_root  # Stage 2A wires shadow-workspace mutation
    return StepPreview(
        step_index=step_index, tool=step.tool,
        changes=(),                                  # ← always empty
        diagnostics_delta=_empty_diagnostics_delta(),
        failure=None,                                # ← never fails
    )
```

**Why this is a stub**: Every step's preview reports zero changes and zero failures. The "preview" the LLM receives is a hand-rolled transaction id + a list of empty `StepPreview` rows. There is NO virtual application against any shadow workspace; the docstring lies about "virtually apply".

The companion test `test_apply_records_per_step_preview` (test_stage_1g_t5_dry_run_compose.py:49) asserts `len(per_step) == 1` and `step_index == 0` — it does NOT assert that `changes` contains anything, because the implementation deliberately returns `()`. The fail-fast tests (line 63, 125) **patch `_dry_run_one_step`** to inject failures from outside — proving the test author knew the real impl couldn't produce a failure organically.

**Verdict**: Hand-rolled fake. The `transaction_id` + `expires_at` plumbing is real (the runtime does mint a real id), but the per-step "what will happen" payload is a stub. The downstream `scalpel_transaction_commit` does dispatch real facades, so the *commit* path works — but the *preview* path the LLM gets to inspect before committing is empty.

---

### `scalpel_split_file` (Python branch, `ScalpelSplitFileTool._split_python` @ scalpel_facades.py:275) — axes flagged: **A3, A4, A2 (partial)**

**Evidence**:

```python
def _split_python(self, *, file, groups, project_root, dry_run):
    bridge = _build_python_rope_bridge(project_root)
    edits: list[dict[str, Any]] = []
    try:
        rel = str(Path(file).relative_to(project_root))
        for group_name in groups.keys():           # ← only iterates KEYS
            target_rel = f"{group_name}.py"
            edits.append(bridge.move_module(rel, target_rel))   # ← move_module, not split
    finally:
        ...
    merged = _merge_workspace_edits(edits)
    ...
    cid = record_checkpoint_for_workspace_edit(merged, snapshot={})   # ← records checkpoint
    return RefactorResult(applied=True, ...)
    # ← NEVER calls _apply_workspace_edit_to_disk(merged)
```

**Why this is a stub**:
1. The signature claims `groups: dict[str, list[str]]` is `target_module → [symbol_name, ...]`, but the body iterates only `groups.keys()` — the symbol lists are silently dropped (A4: parameter ablation).
2. The body calls `bridge.move_module(rel, target_rel)` — that moves the entire file, doesn't split anything.
3. `record_checkpoint_for_workspace_edit` only stores the edit in the checkpoint store (facade_support.py:143-151); it does NOT apply it. The Rust branch correctly calls `_apply_workspace_edit_to_disk(edit)` (line 353), but the Python branch never does. So the Python `split_file` returns `applied=True, checkpoint_id=cid` while leaving disk untouched (A3).
4. The top-level `apply()` deletes 5 of 9 user-facing parameters: `parent_layout, keep_in_original, reexport_policy, explicit_reexports, allow_partial` (lines 236-237). That's most of the spec advertised in the docstring (lines 225-229).

**Verdict**: Python branch is a parameter-ignoring no-op-on-disk stub. Rust branch is real. Splitting this entry into "Tier 1 Python / Tier 3 Rust" would be most accurate.

---

### `scalpel_change_visibility` (`ScalpelChangeVisibilityTool` @ scalpel_facades.py:1253) — axes flagged: **A3 (partial), A4**

**Evidence**:

```python
def apply(self, ..., target_visibility: Literal[...] = "pub", ...) -> str:
    ...
    del preview_token, target_visibility       # ← THE key parameter is deleted
    ...
    return _dispatch_single_kind_facade(
        ..., kind=_VISIBILITY_KIND,            # ← single kind, no per-target dispatch
        ...
    )
```

**Why this is a stub**: `target_visibility` is THE knob for this facade — `pub` vs `pub(crate)` vs `pub(super)` vs `private` are four distinct outputs. Yet `del preview_token, target_visibility` (line 1277) discards the user's request, and the body always dispatches `refactor.rewrite.change_visibility` blind. Whatever rust-analyzer offers as the first action wins. The tool's documented contract (4-tier visibility selection) is not honored.

The shared `_dispatch_single_kind_facade` is correct downstream, but the facade-as-defined silently ignores its primary parameter.

**Verdict**: A4 is the killer. The Tool advertises behavior it cannot perform.

---

### `scalpel_change_return_type` (`ScalpelChangeReturnTypeTool` @ scalpel_facades.py:1464) — axes flagged: **A4**

**Evidence**:

```python
del preview_token, new_return_type   # ← line 1490
```

**Why this is a stub**: Same pattern as `change_visibility`. The user passes `new_return_type="Result<T, MyError>"`; the body discards it and dispatches `refactor.rewrite.change_return_type`. Whatever rust-analyzer's assist proposes wins. The docstring even confesses (line 1481-1483: "informational — rust-analyzer offers a single rewrite per cursor; the target type is selected by the assist") — but that confession is buried in a `:param` block, not the facade title. An LLM router will read the title, see "rewrite a Rust function's return type", and pass `new_return_type="..."` expecting it to take effect.

**Verdict**: Truth-in-advertising stub. Body works; contract is misleading.

---

### `scalpel_extract_lifetime` (`ScalpelExtractLifetimeTool` @ scalpel_facades.py:1550) — axes flagged: **A4**

**Evidence**: `del preview_token, lifetime_name` (line 1576). Same pattern: `lifetime_name="a"` is documented as "requested name" but the body ignores it.

---

### `scalpel_generate_trait_impl_scaffold` (`ScalpelGenerateTraitImplScaffoldTool` @ scalpel_facades.py:1641) — axes flagged: **A4**

**Evidence**: `del preview_token, trait_name` (line 1666). Despite `trait_name: str` being a required positional parameter (line 1648), it's discarded — rust-analyzer's assist picks one trait per cursor regardless.

---

### `scalpel_introduce_parameter` (`ScalpelIntroduceParameterTool` @ scalpel_facades.py:2050) — axes flagged: **A4**

**Evidence**: `del preview_token, parameter_name, language` (line 2074).

---

### `scalpel_generate_from_undefined` (`ScalpelGenerateFromUndefinedTool` @ scalpel_facades.py:2097) — axes flagged: **A4**

**Evidence**: `del preview_token, target_kind, language` (line 2121). `target_kind: Literal["function", "class", "variable"]` (line 2104) is the routing knob — and it's discarded.

---

### `scalpel_auto_import_specialized` (`ScalpelAutoImportSpecializedTool` @ scalpel_facades.py:2139) — axes flagged: **A4**

**Evidence**: `del preview_token, symbol_name, language` (line 2167). Docstring concedes (line 2154-2156): "v1.1 will expose a candidate-set parameter for caller-driven disambiguation" — except this is v1.5 already.

---

### `scalpel_ignore_diagnostic` (`ScalpelIgnoreDiagnosticTool` @ scalpel_facades.py:2273) — axes flagged: **A4**

**Evidence**: `del preview_token, rule, language` (line 2299). The user passes `rule="reportMissingTypeStubs"`; the body ignores it. Whatever pyright/ruff happens to surface for the cursor wins.

---

### `scalpel_fix_lints` (`ScalpelFixLintsTool` @ scalpel_facades.py:2185) — axes flagged: **A4**

**Evidence**: `del preview_token, rules, language` (line 2212). Docstring says (line 2204): "rules: optional ruff rule allow-list (informational; ruff's auto-fix selection is driven by its own config today)". So `rules` exists in the signature for routing aesthetics, not behavior.

---

### `scalpel_imports_organize` (`ScalpelImportsOrganizeTool` @ scalpel_facades.py:929) — axes flagged: **A4 (severe)**

**Evidence**:

```python
del add_missing, remove_unused, reorder, preview_token   # ← line 958
```

**Why this is a stub**: Three of four core knobs (`add_missing`, `remove_unused`, `reorder`) deleted at the top of `apply()`. The user gets one of three behaviors based on which engine the LSP picks; the toggles are theatre.

The `engine` parameter (line 938) IS honored (line 1006-1016 filters actions by provenance), so the facade is half-real.

**Verdict**: 3/4 advertised behaviors are fake.

---

### `scalpel_extract` (`ScalpelExtractTool` @ scalpel_facades.py:403) — axes flagged: **A4**

**Evidence**:

```python
del new_name, visibility, similar, global_scope, preview_token   # ← line 440
```

**Why this is a stub**: Four parameters discarded:
- `new_name="extracted"` — user names the extracted helper, body ignores. Rust-analyzer assigns its own name.
- `visibility` — Rust visibility prefix on the new item, ignored.
- `similar` — Python/Rope: extract similar expressions too. Ignored.
- `global_scope` — Python: extract to module scope. Ignored.

The docstring says "Pick `target` to choose" (line 423) — `target` IS routed via `_EXTRACT_TARGET_TO_KIND` (line 376) so that one parameter works. But four other documented controls are theatre.

---

### `scalpel_inline` (`ScalpelInlineTool` @ scalpel_facades.py:560) — axes flagged: **A4**

**Evidence**:

```python
del name_path, remove_definition, preview_token   # ← line 591
```

**Why this is a stub**: `name_path` is documented as the alternative to `position` for symbol resolution ("`name_path: optional Serena name-path`", line 580) — but it's discarded. So callers MUST pass `position`; passing `name_path` alone fails silently. `remove_definition` (default `True`) is also documented but ignored.

---

### `scalpel_rename` (`ScalpelRenameTool` @ scalpel_facades.py:681) — axes flagged: **A4 (minor)**

**Evidence**: `del also_in_strings, preview_token` (line 708). The `also_in_strings` toggle is documented (line 701) but ignored.

The bulk of `scalpel_rename` is real (LSP `textDocument/rename` via `merge_rename`, plus `__all__` augmentation for Python at line 771-776), so this is a minor A4 violation, not a hard stub. Bumped to Tier 2.

---

### `scalpel_tidy_structure` (`ScalpelTidyStructureTool` @ scalpel_facades.py:1300) — axes flagged: **A4**

**Evidence**: `del preview_token, scope` (line 1325). The `scope: Literal["file", "type", "impl"]` parameter is the documented routing knob (line 1306, 1316-1318) — yet `scope` is discarded and the body always loops over all three `_TIDY_STRUCTURE_KINDS` regardless. So scope='type' and scope='impl' silently behave like scope='file'.

---

### `scalpel_generate_constructor` (`ScalpelGenerateConstructorTool` @ scalpel_facades.py:3067) — axes flagged: **A4**

**Evidence**:

```python
del include_fields  # forwarded to jdtls's interactive picker; not
# plumbed end-to-end in v1.5 P2 (the kind dispatch covers all fields
# by default; per-field selection is a Phase 2.5 enhancement).
```

**Why this is a stub**: The class docstring (line 3068-3072) advertises "Selects fields to include, inserts a constructor at a chosen position". The implementation literally drops the `include_fields` parameter and confesses it's "Phase 2.5". This is the textbook A4 stub: deferral comment + parameter ablation.

---

### `scalpel_override_methods` (`ScalpelOverrideMethodsTool` @ scalpel_facades.py:3122) — axes flagged: **A4**

**Evidence**:

```python
del method_names  # forwarded to jdtls's interactive picker; not
# plumbed end-to-end in v1.5 P2 (...; per-method selection is Phase 2.5).
```

Identical pattern to `generate_constructor`. The class docstring (line 3123-3128) says "Resolves candidate methods via LSP type-hierarchy and inserts override stubs at a chosen position" — but `method_names` is discarded. Phase 2.5 deferral admitted in a comment.

---

### `scalpel_expand_macro` (`ScalpelExpandMacroTool` @ scalpel_facades.py:1738) — axes flagged: **A4**

**Evidence**: `del preview_token, dry_run` (line 1760).

**Why this is a stub**: The `apply()` signature includes `dry_run: bool = False` AND the docstring advertises (line 1754) "dry_run: preview only (returns the expansion without applying)". The body deletes `dry_run` — meaning the value is never honored. This is a contract violation: callers asking for a dry-run get a real expansion regardless. (For an introspection-only tool the distinction is mild, but the docstring promises behavior that doesn't ship.)

---

### `scalpel_verify_after_refactor` (`ScalpelVerifyAfterRefactorTool` @ scalpel_facades.py:1802) — axes flagged: **A4**

**Evidence**: `del preview_token, dry_run` (line 1824). Same pattern as `expand_macro` — `dry_run` advertised, deleted.

---

## Tier 2 — Likely-stubs (1-2 axes flagged)

### `scalpel_split_doc` / `scalpel_extract_section` / `scalpel_organize_links` (markdown facades @ scalpel_facades.py:2764, 2827, 2899) — A5 only

These three markdown facades:
- DO call into `markdown_doc_ops.split_doc_along_headings` / `extract_section` / `organize_markdown_links` (real helpers).
- DO write to disk via `_apply_markdown_workspace_edit` (line 3177).
- Have integration tests via `test_markdown_facade_smoke.py`.
- Universal A5 fail.

Verdict: Real, but no usage examples in docstrings, so the LLM has to guess.

### `scalpel_rename_heading` (`ScalpelRenameHeadingTool` @ scalpel_facades.py:2664) — A5 only

Real LSP path (marksman `textDocument/rename`); only A5.

### `scalpel_rename` (`ScalpelRenameTool` @ scalpel_facades.py:681) — A4 (minor) + A5

Already discussed; demoted from Tier 1 because the `also_in_strings` ablation is a single toggle on an otherwise correct LSP-driven rename pipeline.

### `scalpel_convert_to_async` / `scalpel_annotate_return_type` / `scalpel_convert_from_relative_imports` (@ scalpel_facades.py:2334, 2413, 2530) — A5 only

These three Python facades call into `python_async_conversion.convert_function_to_async`, `python_return_type_infer.annotate_return_type`, `python_imports_relative.convert_from_relative_imports` — all real helpers. They write to disk via `_apply_workspace_edit_to_disk`. Have unit tests in `test/serena/tools/test_facade_*`. Only A5 fails.

### `scalpel_workspace_health` (`ScalpelWorkspaceHealthTool` @ scalpel_primitives.py:813) — A5 only

Reads pool stats and dynamic registry; iterates over `(Language.PYTHON, Language.RUST)` only (line 832) — meaning the 11-language v1.4 fleet only reports health for Python+Rust. That's an A1 partial: the Tool docstring is silent about which languages it covers, but a user calling it on a TypeScript project gets back an empty `languages: {}` payload. Mild stub.

### `scalpel_execute_command` (`ScalpelExecuteCommandTool` @ scalpel_primitives.py:932) — A5 only

The `_EXECUTE_COMMAND_FALLBACK` table (line 865) hardcodes Python+Rust commands only. The class docstring says "live allowlist is read at request time from each server's `executeCommandProvider.commands`" (line 933) — and the apply body does (line 996-998) consult `coord.execute_command_allowlist`. So in production, when a server advertises commands, those win. The fallback is real for offline test usage. Mild concern: the static table covers 2 of 11 languages and the docstring doesn't say "if your server is missing from this table, calls fail" — but the live-allowlist path makes this less of a stub than it looks.

### `scalpel_install_lsp_servers` (`ScalpelInstallLspServersTool` @ scalpel_primitives.py:1122) — A4 (private API), A5

Calls `installer._install_command()` — accessing a private attribute (line 1177; suppressed via pyright comment). Functional, but the private-API call is a smell. The default `dry_run=True` is the right safety posture; behavior is real.

### `scalpel_capabilities_list` / `scalpel_capability_describe` (@ scalpel_primitives.py:71, 109) — A5 only

These are honest catalog readers. Per spec § 3 (Phase 1), `preferred_facade` is now populated for the 13 Rust+Python kinds (per the v1.5 P1 work — the Skeptic did NOT verify this landed; relying on commits). If P1 didn't land, this becomes a Tier 1 stub.

### `scalpel_rollback` / `scalpel_transaction_rollback` (@ scalpel_primitives.py:670, 699) — A1 (partial) + A5

**Evidence**: Both rollback tools use `_no_op_applier` (scalpel_primitives.py:652):

```python
def _no_op_applier(_: dict[str, Any]) -> int:
    """Stage 1G synthetic applier — exists so checkpoint_store.restore
    can be invoked without spinning up a real LSP. Returns 0 so restore()
    surfaces as ``no_op=True`` in RefactorResult.
    """
    return 0
```

`ckpt_store.restore(checkpoint_id, _no_op_applier)` — meaning the ROLLBACK path DOES NOT actually undo edits to disk. It walks the checkpoint, calls a no-op, and reports `applied=bool(restored)` based on the store's internal state, not a real on-disk reversal.

This is the symmetric stub to `scalpel_apply_capability`: the fallback dispatcher pretends to apply, the rollback tools pretend to revert. Both are checkpoint-bookkeeping-only.

**Verdict**: Promote to **Tier 1** if the spec's contract is "rollback writes the file back to its pre-edit state". Keeping in Tier 2 only because the spec might consider checkpoint-state rollback (without disk writeback) acceptable for transactional bookkeeping. Either way: A1 partially flagged.

### `scalpel_confirm_annotations` (@ scalpel_primitives.py:596) — A5 only

Real path: filters the workspace edit by annotation labels and calls `_apply_workspace_edit_to_disk` (line 636). No A1/A3 stub.

### `scalpel_reload_plugins` (@ scalpel_primitives.py:1037) — A5 only

Calls `runtime.plugin_registry().reload()`. Real.

### `scalpel_transaction_commit` (`ScalpelTransactionCommitTool` @ scalpel_facades.py:3273) — A5 only

Walks `_FACADE_DISPATCH` and calls each facade's real `apply` — so it inherits the stubness of whichever facade is invoked, but on its own this is real plumbing.

---

## Tier 3 — Looks real but I'm suspicious

### `scalpel_split_file` (Rust branch only) — A5; suspicion of A1 due to `del groups`

The Rust branch (`_split_rust`, scalpel_facades.py:319) starts with `del groups` (line 327). The original `groups: dict[str, list[str]]` parameter — the heart of "where does each symbol go" — is discarded before the LSP call. The body asks rust-analyzer for `refactor.extract.module` actions on a `(0,0)-(0,0)` range and applies whatever rust-analyzer offers first. So the Rust branch dispatches a real LSP call, but it's blind to the user's intent — a "split this file" call on an arbitrary file with `groups={"a": [...], "b": [...]}` will produce whatever rust-analyzer's first `extract.module` action says, regardless of what the user asked for.

I cannot prove this is a stub without running rust-analyzer against a real fixture, but the signal is strong: a parameter the docstring calls "target_module → [symbol_name, ...] mapping" is discarded.

### `scalpel_imports_organize` — A4-flagged + suspicion that the engine filtering is unsound

The engine-keepalive filter at line 1006-1016 keeps only actions whose `provenance` matches `engine`. If `engine="rope"` but rope is offline, the user gets `applied=False, no_op=True` with no warning that rope was the gate. The static `_ENGINE_TO_PROVENANCE` (line 922) maps `"rope" → "pylsp-rope"`, so unless the test fixture pins this, prod behavior will silently no-op. Not a hard stub but easy to confuse with one in production.

### `scalpel_local_to_field` / `scalpel_use_function` / `scalpel_convert_to_method_object` (@ 1970, 2010, 1930) — A5 + spec drift

These three Python Rope-backed facades dispatch via `_python_dispatch_single_kind`. They look real BUT the kinds they dispatch (`refactor.rewrite.local_to_field`, `refactor.rewrite.use_function`, `refactor.rewrite.method_to_method_object`) need pylsp-rope to advertise these exact strings. The kind catalog is checked via `coord.supports_kind`, so if pylsp-rope doesn't advertise them they short-circuit to CAPABILITY_NOT_AVAILABLE. I'm suspicious because the kind strings in the spec table (§ 3.2 of the spec) only list 13 entries — none of these three made the cut. So either the kinds are advertised but not yet in the routing-hint table (Phase 1 incomplete), or they're not advertised and the facade is a CAPABILITY_NOT_AVAILABLE machine in production.

---

## Summary table

Legend: **1** = stub-flagged on this axis, **0** = clean. Verdict: **T1** = Tier 1 (hard stub), **T2** = Tier 2 (likely-stub), **T3** = Tier 3 (looks real, suspicious), **OK** = appears real.

| Facade | A1 LSP | A2 Tests | A3 Edit | A4 TODO/del | A5 Examples | Verdict |
|---|---|---|---|---|---|---|
| `scalpel_split_file` (py branch) | 0 | 0 | **1** | **1** | **1** | T1 |
| `scalpel_split_file` (rs branch) | 0 | 0 | 0 | **1** | **1** | T3 |
| `scalpel_extract` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_inline` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_rename` | 0 | 0 | 0 | **1** | **1** | T2 |
| `scalpel_imports_organize` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_convert_module_layout` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_change_visibility` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_tidy_structure` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_change_type_shape` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_change_return_type` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_complete_match_arms` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_extract_lifetime` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_expand_glob_imports` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_generate_trait_impl_scaffold` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_generate_member` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_expand_macro` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_verify_after_refactor` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_convert_to_method_object` | 0 | 0 | 0 | 0 | **1** | T3 |
| `scalpel_local_to_field` | 0 | 0 | 0 | 0 | **1** | T3 |
| `scalpel_use_function` | 0 | 0 | 0 | 0 | **1** | T3 |
| `scalpel_introduce_parameter` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_generate_from_undefined` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_auto_import_specialized` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_fix_lints` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_ignore_diagnostic` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_convert_to_async` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_annotate_return_type` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_convert_from_relative_imports` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_rename_heading` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_split_doc` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_extract_section` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_organize_links` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_generate_constructor` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_override_methods` | 0 | 0 | 0 | **1** | **1** | T1 |
| `scalpel_transaction_commit` | 0 | 0 | 0 | 0 | **1** | T2 |
| **PRIMITIVES** | | | | | | |
| `scalpel_capabilities_list` | n/a | 0 | n/a | 0 | **1** | OK |
| `scalpel_capability_describe` | n/a | 0 | n/a | 0 | **1** | OK |
| `scalpel_apply_capability` (FALLBACK) | 0 | **1** | **1** | **1** | **1** | **T1 (highest confidence)** |
| `scalpel_dry_run_compose` | **1** | **1** | **1** | **1** | **1** | **T1** |
| `scalpel_confirm_annotations` | 0 | 0 | 0 | 0 | **1** | T2 |
| `scalpel_rollback` | **1** | 0 | **1** | 0 | **1** | T1 (rollback-as-bookkeeping) |
| `scalpel_transaction_rollback` | **1** | 0 | **1** | 0 | **1** | T1 (same) |
| `scalpel_workspace_health` | 0 | 0 | n/a | **1** (Py+Rust hardcode) | **1** | T2 |
| `scalpel_execute_command` | 0 | 0 | n/a | 0 | **1** | T2 |
| `scalpel_reload_plugins` | 0 | 0 | n/a | 0 | **1** | T2 |
| `scalpel_install_lsp_servers` | 0 | 0 | n/a | **1** (private API) | **1** | T2 |

Note on A2: I scored A2=0 (test exists) for facades whose tests use mocked coordinators with non-trivial inputs and assert non-trivial outputs (per the prompt's bar). The two that fail A2 are `scalpel_apply_capability` and `scalpel_dry_run_compose`, where the suspicious code path is explicitly mocked OUT by the test, so the body is not exercised.

Tier 1 count: **20** (incl. rollback pair, FALLBACK, dry_run_compose, py-branch split_file)
Tier 2 count: **18**
Tier 3 count: **4**
OK count: **2**

Wait — duplicate row for `scalpel_split_file`. Net unique facades: **43** (33 facades + 10 primitives), Tier counts above include the python/rust split-file branches separately as a deliberate scoring choice.

---

## Top recommendations to my sibling defender

I expect you to defend the following 5 facades hardest. Here's where I expect you to push back:

1. **`scalpel_apply_capability`** — You'll defend it as "intentionally a long-tail dispatcher; Stage 1G ships plumbing, Stage 2A ships the resolved-edit application". My counter: the docstring of the class itself bills it as "FALLBACK: apply a registered capability" and the contract is `applied: bool`. Returning `applied=True` with `applied={"changes": {}}` is a lie regardless of the staging plan. The tool ships in `__all__`, registers as MCP, and the LLM cannot tell from the contract that it's a no-op. **Show me a test that asserts the dispatcher writes a real edit to disk** and I'll back down.

2. **`scalpel_dry_run_compose`** — You'll defend it as "the preview is the transaction id + grammar; the actual changes appear at commit time". My counter: `StepPreview.changes: tuple` exists in the schema for a reason; returning `()` from every step means the LLM has zero visibility into what the transaction will do. The 5-min TTL is real; the per-step preview is fake.

3. **`scalpel_extract` / `scalpel_inline`** — You'll defend the parameter-ablation pattern as "rust-analyzer's assists are not parameterizable; the facade exposes the LSP intent and lets the assist drive the body". My counter: then DELETE the parameters from the signature. If `new_name` is purely informational, signal that with `# noqa: ARG002` and a docstring opener "Note: rust-analyzer ignores `new_name`; ..." — don't accept the parameter, run `del`, and let the LLM think it took effect.

4. **`scalpel_rollback` / `scalpel_transaction_rollback`** — You'll defend `_no_op_applier` as "rollback semantics are 'mark this checkpoint reverted in the store'; the actual on-disk inversion is the editor's responsibility". My counter: from the user's view, `scalpel_rollback(ckpt_id)` should put the file back. If it doesn't, the docstring needs a giant `WARNING:` block and the audit trail. Otherwise users will hit Ctrl-Z expecting their edit reverted and find their file mid-refactor.

5. **`scalpel_generate_constructor` / `scalpel_override_methods`** — You'll defend the `include_fields` / `method_names` ablation as "Phase 2.5 enhancement, the kind dispatch covers all fields by default". My counter: the spec § 4.2.2 commit message reads "Selects fields to include, inserts a constructor at a chosen position" — you literally cannot select fields today. Either rip the parameter or land Phase 2.5 before claiming v1.5 P2 done.

Bonus pre-emptive challenges:
- The **A5 universal failure** (zero docstring Examples) is unobjectionable. Every facade fails A5; the spec doesn't require Examples; that's a real-but-soft stub signal.
- **`scalpel_split_file._split_python`** is the cleanest hard-stub I found that isn't the FALLBACK or compose dispatcher. The fact that the Rust branch calls `_apply_workspace_edit_to_disk` and the Python branch doesn't is a one-line bug, not a design choice. I expect you to concede this one.

Highest-confidence stub overall: **`scalpel_apply_capability`** — docstring promises long-tail dispatch, body records `{"changes": {}}` as the applied edit, tests mock out the buggy body.
