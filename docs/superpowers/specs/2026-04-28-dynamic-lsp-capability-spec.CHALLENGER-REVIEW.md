# Challenger Review of v1 Draft

**Reviewer**: AI Hive(R) (challenger of drafter+challenger pair)
**Date**: 2026-04-28
**Subject**: 2026-04-28-dynamic-lsp-capability-spec.md (v1 draft)

---

## Acceptance criteria (defined first, TDD-style)

- **AC-1**: The decision (Option A vs B) is stated unambiguously in §1 or §2 with a one-line summary.
- **AC-2**: Every numerical/file/line citation is traceable to the actual source (file exists, line number lands on the cited construct).
- **AC-3**: Both Mermaid diagrams are syntactically valid and match the prose.
- **AC-4**: The migration plan has explicit, testable exit criteria per phase (not just "do X").
- **AC-5**: The "what we DON'T do" section addresses param-reconstruction, send-and-catch, AND static-catalog replacement.
- **AC-6**: The 3-tier precedence (static catalog → dynamic registry → ServerCapabilities) is well-defined when sources disagree, and the diagram, prose and code match each other.
- **AC-7**: Edge cases are addressed: dynamic-registration race, documentSelector scoping, custom (rust-analyzer/*) methods, sub-capabilities (`prepareRename`).
- **AC-8**: Test strategy names a real synthetic-LSP fixture (file path) or mandates one be created with concrete shape.
- **AC-9**: The spec uses prescriptive ("MUST", "shall", "returns") voice rather than narrative ("we could", "consider") at decision points.
- **AC-10**: TRIZ/KISS/YAGNI principles from `CLAUDE.md` are visibly applied — speculative abstractions for hypothetical future consumers are absent or justified.
- **AC-11**: Every API the spec invents (`coord.supports_method`, `coord.supports_kind`, `_servers_by_id`, `_dynamic_registry`, `_catalog`) names a real attribute on the touched class — or explicitly flags the wiring as new and identifies the constructor change.
- **AC-12**: The `ScalpelAnnotateReturnTypeTool` story is consistent — the spec must not contradict feasibility.md §C (which puts it in Population B → no gate).

---

## Verification (PASS / PARTIAL / FAIL)

| # | AC | Verdict | Note |
|---|----|---------|------|
| 1 | Decision stated up front | PASS | §2 line 22: "We adopt Option A". Clean. |
| 2 | Line/file citations correct | **FAIL** | `ls.py:601` (PASS), `ls.py:432` (PASS), `ls.py:658` (PASS), `ls.py:686` (PASS), `rust_analyzer.py:780-783` (PASS), `scalpel_facades.py:1004` (PASS), `scalpel_facades.py:1766` (PASS), `scalpel_primitives.py:841` (PASS), `:908` (PASS), `:935` (PASS). **BUT** the four bespoke-facade citations in §4.5 table are mostly wrong — see MF-1. |
| 3 | Mermaid valid | PASS | Both `flowchart LR` (§4.1) and `graph TD` (§6) parse; node labels and edges are well-formed; the §4.1 short-circuit-OR semantics match the prose ("dynamic registry consulted before ServerCapabilities"). |
| 4 | Phase exit criteria | PASS | Each of P0–P6 has a concrete observable exit ("predicate returns the correct answer for Pyright `implementationProvider` regression case"; "grep confirms no `class.*Server.*` is missing the ClassVar"). |
| 5 | "Do NOT do" section | PASS | §5.1 (param-schema), §5.2 (send-and-catch — 4 enumerated failure modes), §5.3 (static-catalog wholesale replacement). All three boxes ticked. |
| 6 | 3-tier precedence well-defined | **PARTIAL** | The §4.1 diagram shows static → dynamic → caps. §4.4 prose says "dynamic registry → ServerCapabilities" with "static-catalog check is implicit at the kind level". The `supports_method` *code* (lines 178-189) skips the static-catalog tier entirely; only `supports_kind` (lines 191-203) consults the catalog. The diagram is therefore correct only for kind-routed paths, not method-routed. See MF-3. |
| 7 | Edge cases | PARTIAL | Dynamic-registration race is acknowledged (R3) but mitigation is "document and revisit". `documentSelector` is deferred (R6, §9). Custom methods (R7) are deferred. `prepareRename` (R5) gets an inline special case. The mid-request `client/registerCapability` ordering question is missing (see SC-1). |
| 8 | Synthetic LSP fixture exists | **FAIL** | §7 names `test_facade_capability_gate.py` (new) using "a synthetic LSP fixture (a `SolidLanguageServer` subclass...)". No file path, no existing fixture identified. Need to confirm whether the existing `_FakeServer` (`vendor/serena/test/spikes/conftest.py`, referenced at multi_server.py:749) can be re-used or whether a new fixture is needed. See MF-4. |
| 9 | Prescriptive voice | PASS | §4 uses "is", "becomes", "returns"; §6 uses "is the exit criteria"; §3.3 uses "Concretely:". Open-question section uses "Recommend" / "Defer" — appropriate for that section. |
| 10 | TRIZ/KISS/YAGNI applied | PARTIAL | YAGNI is correctly invoked to reject param-reconstruction (§5.1). KISS holds for the single capture-point in `_initialize_with_override`. **TRIZ ideal-final-result not pursued**: the spec keeps three sources of truth (static catalog, dynamic registry, ServerCapabilities) when at least the latter two could plausibly merge into one (the registry is just "additive deltas to caps"). See SC-2. |
| 11 | Invented APIs grounded | **FAIL** | §4.4 references `self._servers_by_id` and `self._dynamic_registry` and `self._catalog` on `MultiServerCoordinator`. Actual class (multi_server.py:744-779) has only `self._servers` and `self._action_edits`. The spec must either (a) rename the references to `self._servers`, or (b) add a §4.4-bis listing the new constructor signature and dependency-injection plan for the registry + catalog. See MF-2. |
| 12 | Annotate-return-type story consistent | **FAIL** | feasibility.md §C lines 110 explicitly puts `scalpel_annotate_return_type` in **Population B** (NON-LSP-routed) with the note "gated by `_get_inlay_hint_provider` which already does graceful None-return". Spec §4.5 contradicts this twice: (a) the bespoke-facade table lists it with a `textDocument/inlayHint` gate at line 916 (and 916 is the wrong line — it's `ScalpelImportsOrganizeTool`), and (b) the closing paragraph of §4.5 says "Population B... receive no gate" but does not list `scalpel_annotate_return_type` in Population B. See MF-1 + MF-5. |

---

## MUST FIX before v2

### MF-1: Bespoke-facade line citations are wrong (3 of 4)

**Location in spec**: §4.5, table at lines 254-258, and §6 P4 row referencing "lines 303, 447, 568, 916".

**Issue**: I opened each cited line in `vendor/serena/src/serena/tools/scalpel_facades.py` and ran `grep -n "^class Scalpel"`. The actual class boundaries are:
- `ScalpelSplitFileTool` 182-358 → contains line 303 ✓ (`scalpel_split_file` claim PASS).
- `ScalpelExtractTool` 359-501 → contains line 447. Drafter says line 447 is `scalpel_rename`. **Wrong** — `ScalpelRenameTool` starts at line 619 and its actual `merge_rename` dispatch is at **line 689**.
- `ScalpelInlineTool` 502-618 → contains line 568. Drafter says line 568 is `scalpel_imports_organize`. **Wrong** — `ScalpelImportsOrganizeTool` starts at line 860, its `merge_code_actions` call is at **line 916**.
- `ScalpelImportsOrganizeTool` 860-1100 → contains line 916. Drafter says line 916 is `scalpel_annotate_return_type`. **Wrong** — `ScalpelAnnotateReturnTypeTool` starts at line 2301, and the `textDocument/inlayHint` dispatch is at **lines 2358 / 2389**.

**Recommended fix**: rebuild the table by searching for the actual class definitions and the lines where `coord.merge_code_actions` / `coord.merge_rename` / `request("textDocument/...")` is called inside each Tool class. The corrected mapping is:
| Facade | Site (verified) |
|---|---|
| `scalpel_split_file` | `scalpel_facades.py:303` (inside `ScalpelSplitFileTool`) |
| `scalpel_extract` | `scalpel_facades.py:447` (inside `ScalpelExtractTool`) |
| `scalpel_inline` | `scalpel_facades.py:568` (inside `ScalpelInlineTool`) |
| `scalpel_rename` | `scalpel_facades.py:689` (inside `ScalpelRenameTool` 619-859) |
| `scalpel_imports_organize` | `scalpel_facades.py:916` (inside `ScalpelImportsOrganizeTool` 860-1100) |
| `scalpel_annotate_return_type` | `scalpel_facades.py:2358 / 2389` (inside `ScalpelAnnotateReturnTypeTool` 2301-2417) |

The "four bespoke facades" claim itself needs revisiting — `scalpel_extract` and `scalpel_inline` are *additional* call sites that don't go through the two shared dispatchers. The drafter conflated several. Re-derive Population A vs the bespoke set from the call-graph (use `grep -nE "_dispatch_single_kind_facade\(|_python_dispatch_single_kind\(" scalpel_facades.py` — I see 9 + 7 = 16 funnel callers, not 12 + 10 = 22 as the spec implies).

### MF-2: `MultiServerCoordinator` constructor wiring is unspecified

**Location in spec**: §4.4 lines 178-203.

**Issue**: The new `supports_method` code reads `self._dynamic_registry`, `self._servers_by_id`, and the `supports_kind` body reads `self._catalog`. The actual class (`multi_server.py:744-779`) holds only `self._servers` and `self._action_edits`. There is no plan in the spec for how the registry and catalog are injected, who owns them, or whether they become constructor params.

**Recommended fix**: add a §4.4-pre subsection "Coordinator dependencies" that:
1. Renames `self._servers_by_id` → `self._servers` to match reality.
2. Specifies the constructor change: `__init__(self, servers, *, dynamic_registry: DynamicCapabilityRegistry, catalog: CapabilityCatalog)`.
3. Identifies who passes those dependencies. The lazy-import in `_handle_register_capability` (`ls.py:675-676`) reaches `ScalpelRuntime.instance().dynamic_capability_registry()` — confirm whether the coordinator should pull from the same singleton or be DI'd at construction time.
4. Flags Phase 2's exit criterion to include "all existing `MultiServerCoordinator` constructions are updated (count: N call sites — `grep -rn 'MultiServerCoordinator(' vendor/serena/`)".

### MF-3: `supports_method` skips the static catalog tier — but §4.1 diagram and §3.3 prose say it consults it

**Location in spec**: §4.1 diagram (S → D → SC), §3.3 line 48 ("consult, in order: the static catalog → the dynamic registry → the captured `ServerCapabilities`"), §4.4 code lines 171-189.

**Issue**: The diagram and prose claim a 3-tier precedence applies to *both* `supports_method` and `supports_kind`. The actual code in §4.4 makes only `supports_kind` consult the catalog; `supports_method` is dynamic-registry-then-caps only. Comment on line 175 ("Static-catalog check is implicit at the kind level") signals the drafter knows but didn't propagate to the diagram or §3.3.

**Recommended fix**: either (a) extend `supports_method` to consult the catalog by inverse-mapping method → kind via `_METHOD_TO_PROVIDER_KEY` and the kind table, or (b) update §4.1 to draw two parallel branches — one for `supports_kind` (3 tiers) and one for `supports_method` (2 tiers) — and revise §3.3 to match. Pick (b) — (a) re-introduces a coupling YAGNI rejects.

### MF-4: Synthetic-LSP fixture is named but not located

**Location in spec**: §7 first integration-test bullet ("uses a synthetic LSP fixture").

**Issue**: The phrase reads as if the fixture exists; I cannot find one. The closest existing test scaffolding is `_FakeServer` in `vendor/serena/test/spikes/conftest.py` (referenced at `multi_server.py:749-750`). The spec must say *which* — re-using `_FakeServer` is preferable per DRY.

**Recommended fix**: in §7 replace "a synthetic LSP fixture (a `SolidLanguageServer` subclass...)" with one of:
- "extends the existing `_FakeServer` in `test/spikes/conftest.py` to accept a configurable `server_capabilities: dict` injected at construction" (preferred), or
- "a new `_CapabilityFakeServer` in `test/serena/refactoring/conftest.py` that subclasses `SolidLanguageServer` and overrides `_initialize_with_override` to seed `self._server_capabilities` directly" (only if `_FakeServer` cannot carry the new field).

Confirm by reading the existing fixture before locking the choice.

### MF-5: §4.5 contradicts feasibility.md and itself on `scalpel_annotate_return_type`

**Location in spec**: §4.5 table line 258 vs §4.5 closing paragraph (lines 259-260).

**Issue**: feasibility.md §C lines 110 puts `scalpel_annotate_return_type` in Population B — already gated via `_get_inlay_hint_provider`'s graceful None-return — and explicitly says Population B "fail gracefully through their own error paths" so dynamic gating has "zero benefit". Spec §4.5 contradicts feasibility.md by inserting a `textDocument/inlayHint` gate, then contradicts itself by listing only 5 facades in the "no gate" sentence (omitting `scalpel_annotate_return_type` from Population B).

**Recommended fix**: pick one of these and apply consistently:
- **Drop the gate** for `scalpel_annotate_return_type`. Its existing `_get_inlay_hint_provider() is None` check is the gate; the new envelope is not needed because the existing skip path (`scalpel_facades.py:2351`) already returns `status: "skipped"` with `language_options` carrying the provider-unavailable reason. Move it explicitly into the §4.5 "no gate" list. **Recommended** — matches feasibility.md.
- **Keep the gate** but justify the divergence from feasibility.md, document that the existing skip path is being replaced (not augmented), and update R-numbers to acknowledge the conflict.

---

## SHOULD CONSIDER

### SC-1: `client/registerCapability` arriving mid-request

A `client/registerCapability` notification can arrive between the gate check and the `merge_code_actions` call. The current `_handle_register_capability` runs synchronously on the message thread; gate + dispatch happens on the call thread. R3 already mentions this for the *deny → method-actually-supported-now* direction; the *allow → method-just-unregistered* direction is symmetric and missing. Add a one-line note in R3 that `unregisterCapability` race can produce false positives at the gate but the downstream JSON-RPC `MethodNotFound` provides a backstop.

### SC-2: TRIZ ideal-final-result — fold dynamic registry into a live caps view

If we capture `ServerCapabilities` at init and apply `client/registerCapability` deltas to that same dict over the lifetime of the connection, we have **one** source of runtime truth instead of two. The §4.4 `supports_method` becomes a single dict lookup and the diagram in §4.1 collapses to two tiers (static → live-caps). This is the IFR per CLAUDE.md TRIZ principle. Considered explicitly and rejected? Note that.

### SC-3: `pylsp-base` vs `pylsp` server-id naming

The spec's RuffServer ClassVar example uses `"ruff"` and rust-analyzer uses `"rust-analyzer"`. The existing pylsp adapter is `"pylsp-base"` (`pylsp_server.py:44`). Audit: do any existing tests / config / health-report consumers expect the bare `"pylsp"` token? If so, document the naming policy in the spec so Phase 6 doesn't introduce a regression.

### SC-4: Drift CI must be Phase 6 exit criterion, not just §7 fine print

§7 last sentence says "the 391/1-skip baseline catalog drift test must pass unchanged (Phase 6 audit must not alter the catalog content)". Promote this to Phase 6's exit-criterion column in the §6 table.

---

## Open question handed back to drafter

The drafter's R4 question: *"Should the catalog gain a `requires_dynamic_check: bool` flag per record so the LLM knows availability is session-dependent?"*

**My verdict**: NO for v1, YES eventually but as a separate follow-up. Reasoning: the current `scalpel_workspace_health` already exposes `dynamic_capabilities`; the LLM can cross-reference. Adding a per-record flag duplicates that signal in a second place (DRY violation per CLAUDE.md). When a concrete LLM-routing failure is observed, revisit and bias toward enriching `scalpel_capability_describe`'s output rather than mutating the catalog schema.

---

## Verdict

**REWORK**

Five MUST FIX items (one of which — MF-1 — is broad-impact: line citations across §4.5 and §6 are misaligned with the actual facade layout, and the dispatcher-caller counts disagree with what the source shows). MF-2 is structural (the coordinator-dependency story isn't told). MF-3 and MF-5 are internal-consistency violations. MF-4 is a test-strategy gap.

If MF-1, MF-2, MF-3, MF-5 (consistency tier) are addressed by re-grepping the source and fixing the table + §4.4 + the §4.1/§3.3/§4.4-code mismatch, AND MF-4 picks an existing fixture with named path, the v2 draft can ship. If the drafter prefers a smaller delta, MF-1 alone could be a "must fix" cherry-pick and the rest moved to v2.1 — but then the spec ships with known internal contradictions, which is worse than a single rework pass.

Recommend one re-draft pass focused on §4.4–§4.5 + §6 + §7 with the source files open in another tab.

**MUST FIX count: 5**

---

# v2 Sign-off

**Date**: 2026-04-28
**Verdict**: APPROVED

## MF verification

- **MF-1**: VERIFIED — 6 line citations spot-checked against `vendor/serena/src/serena/tools/scalpel_facades.py`, all land exactly on the cited construct:
  - `:689` → `_run_async(coord.merge_rename(...))` inside `ScalpelRenameTool` ✓
  - `:1004` → `def _dispatch_single_kind_facade(...)` ✓
  - `:1246` → `_run_async(coord.merge_code_actions(...))` inside `ScalpelTidyStructureTool` ✓
  - `:1766` → `def _python_dispatch_single_kind(...)` ✓
  - `:2116` → `_run_async(coord.merge_code_actions(...))` inside `ScalpelFixLintsTool` ✓
  - `:2602` → `_run_async(coord.merge_rename(...))` inside `ScalpelRenameHeadingTool` ✓
  - The §4.5 table now lists 8 bespoke dispatch sites (not 4) with verified Tool class spans; funnel counts corrected to 9+7=16 (not 12+10=22).
- **MF-2**: RESOLVED — §4.4.0 "Coordinator dependencies" subsection added; all attribute references use the real `self._servers` (verified at `multi_server.py:774`); constructor extension specified with `dynamic_registry: DynamicCapabilityRegistry | None = None` and `catalog: CapabilityCatalog | None = None` defaulting to `ScalpelRuntime` singleton/`build_capability_catalog()`; Phase 2 exit criterion updated to call out the two production sites + 37 backward-compat test sites.
- **MF-3**: RESOLVED via option (b) per challenger recommendation — `supports_method` is 2-tier (dynamic registry → caps); `supports_kind` is 3-tier (catalog → dynamic registry for `textDocument/codeAction` → caps codeActionKinds). §3.3 prose, §4.1 diagram (two parallel branches), and §4.4 code blocks (4.4.1 / 4.4.2) are internally consistent.
- **MF-4**: RESOLVED — §7 now reuses existing `_FakeServer` at `vendor/serena/test/spikes/conftest.py:171` (verified) extended with a `server_capabilities` field + accessor; DRY-compliant per CLAUDE.md.
- **MF-5**: RESOLVED — `scalpel_annotate_return_type` now in Population B "no gate" list (§4.5 line 345) matching feasibility.md §C line 110 verbatim; existing `_get_inlay_hint_provider() is None` skip path documented as the gate.

## SC verification

- **SC-1**: APPLIED — R3 paragraph extended with `unregisterCapability` symmetric race direction + `MethodNotFound` backstop note.
- **SC-2**: APPLIED — R9 added explicitly considering and rejecting the TRIZ ideal-final-result (folding registry into live caps view); rationale grounds the rejection in LSP 3.17's caps-immutability guarantee + production consumers.
- **SC-3**: APPLIED — R10 added documenting `pylsp-base` vs `pylsp` server-id naming policy (no silent rename in Phase 6 audit).
- **SC-4**: APPLIED — drift-CI green-light promoted to Phase 6 exit criterion in §6 table ("catalog content byte-identical to pre-Phase-6 baseline").

## New issues check

None. v2 introduced no new self-contradictions, no fictional APIs (the `MultiServerCoordinator` constructor change is explicitly grounded in the real `multi_server.py:762-775` shape), no mermaid syntax errors (both diagrams parse; §4.1 two-branch structure correctly mirrors the §4.4.1 / §4.4.2 code split), and no narrative-voice regressions in decision sections (R5 and R7 are now decisive commitments, not hedges; R4 is resolved with verdict; R8 is decisive ("Static for now"); only R6 remains an explicit out-of-scope deferral, which is appropriate). The only "Open" remaining is R1's empirical-population step for `gated_kinds`, which is correctly framed as ship-then-tune rather than a pre-merge unknown.

## Final spec status

The spec is implementation-ready. The drafter (or executor agents) may proceed with the 7-phase migration plan in §6.
