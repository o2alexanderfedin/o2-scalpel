# o2.scalpel — MVP Scope Report

Status: report-only. Authoritative MVP scope synthesized from four specialist brainstorms plus the main design and the open-questions resolution. Supersedes the Rust-only v1 scoping implicit in the main design wherever the two disagree.

Date: 2026-04-24. Author: AI Hive(R).

Cross-reference:
- Main design: [`../2026-04-24-serena-rust-refactoring-extensions-design.md`](../2026-04-24-serena-rust-refactoring-extensions-design.md).
- Open-questions resolution: [`../2026-04-24-o2-scalpel-open-questions-resolution.md`](../2026-04-24-o2-scalpel-open-questions-resolution.md).
- Specialist reports: [`specialist-rust.md`](specialist-rust.md), [`specialist-python.md`](specialist-python.md), [`specialist-agent-ux.md`](specialist-agent-ux.md), [`specialist-scope.md`](specialist-scope.md).

---

## 1. TL;DR

o2.scalpel MVP ships a language-agnostic MCP write surface that refactors real code in **Rust and Python simultaneously** — chosen so the `LanguageStrategy` seam is exercised by two structurally different shapes at MVP rather than Rust-only with Python paper-only. The canonical MVP tool surface is **four MCP tools**: `split_file` (facade, mutating), `fix_imports` (facade, mutating), `rollback` (primitive, mutating), and `apply_code_action` (primitive, mutating — bundles list/resolve/apply at MVP). Short verb-style names per `specialist-agent-ux.md` §2.3; the longer descriptive names (`split_file_by_symbols`, `rollback_refactor`) from the main design are retired. `plan_file_split` is absorbed into `split_file(dry_run=True)` for MVP and re-introduced in v1.1 only if telemetry proves the heuristic planner beats LLM-native grouping.

Distribution is `uvx --from <local-path>` only at MVP (`specialist-scope.md` §7); marketplace publication lands in v1.1. Python primary LSP is `pylsp + pylsp-rope + pylsp-mypy` with `basedpyright` as secondary read-only for diagnostics (`specialist-python.md` §1.3). Python equivalents of `extract_module` do not exist as first-class assists; `split_file` composes via Rope's `MoveGlobal` (`specialist-python.md` §2.3). Dual-language MVP is sized at ~5,010 LoC including fixtures, +61% over Rust-only — the premium is the validation cost of catching Rust-isms before they ship.

---

## 2. MVP Definition (single falsifiable sentence)

> **Scalpel MVP is done when `split_file` + `fix_imports` + `rollback` successfully refactor `calcrs/src/lib.rs` (Rust fixture, ~900 LoC) and `calcpy/calcpy/__init__.py` (Python fixture, ~600 LoC) into ≥3 modules each, with `cargo test` / `pytest` byte-identical output to the pre-refactor baseline, driven through a stdio MCP client (`pytest -m e2e`) against a scalpel MCP server installed via `uvx --from <local-path>` on a 16 GB dev laptop, across the seven MVP E2E gates E1, E1-py, E2, E3, E9, E9-py, E10 passing in a single CI run with zero flakes.**

Adapted from `specialist-scope.md` §1; promoted to the canonical MVP gate. Falsifiable on six axes: (1) dual-language coverage, (2) named fixtures, (3) three facades exercised end-to-end, (4) semantic-equivalence measured by byte-diff of test output, (5) a reproducible `uvx --from` install, (6) zero-flake green bar. If any axis fails, MVP is not done. If all six pass, MVP is done regardless of what else is unfinished.

---

## 3. In-Scope vs. Out-of-Scope matrix

Every design element is assigned MVP, v1.1, or v2+ with a rationale. The matrix is authoritative; implementation deviations require a written amendment to this report.

### 3.1 LSP primitive layer (`solidlsp`)

| Item | Stage | Rationale |
|---|---|---|
| `request_code_actions` on `SolidLanguageServer` | **MVP** | Every facade ultimately issues this. |
| `resolve_code_action` | **MVP** | Two-phase resolve is the only path to real refactorings on rust-analyzer. |
| `workspace/applyEdit` reverse-request handler (full) | **MVP** | pylsp-rope's `MoveGlobal` emits server-initiated edits; pyright uses it in some paths. `specialist-python.md` §3 and `specialist-rust.md` §3.7 disagree (Rust calls it a stub); **resolved: Python side drives full implementation because the cost of full is small and the cost of a broken stub later is larger**. |
| `$/progress rustAnalyzer/Indexing` tracker + `wait_for_indexing()` | **MVP (Rust)** | Without it, first `codeAction` returns empty or `ContentModified` and flakes E1/E2/E7 (`specialist-rust.md` §3.2). |
| WorkspaceEdit applier: `TextDocumentEdit`, `CreateFile`, `RenameFile` | **MVP** | All three exercised by Rust and Python happy paths. |
| WorkspaceEdit applier: `DeleteFile` | v1.1 | No MVP facade emits it; keep stub that fails loud. |
| WorkspaceEdit applier: `changeAnnotations` with `needsConfirmation` | v1.1 | MVP policy: reject annotated edits with warning. |
| Order preservation inside `documentChanges` | **MVP** | Correctness bug otherwise. |
| Version check on `TextDocumentEdit` | **MVP** | Prevents silent corruption. |
| Snippet-marker stripping (advertise `snippetTextEdit: false`) | **MVP** | Rust: non-negotiable per `specialist-rust.md` §3.1. |
| `ContentModified` retry-once with `didChange` resync | **MVP** | Facade-level correctness requirement per `specialist-rust.md` §3.3. |
| Atomic apply (in-memory snapshot + restore) | **MVP** | Rollback contract. |
| Checkpoint store — in-memory LRU (10 entries) | **MVP** | Required for rollback tool. |
| Checkpoint store — persistent disk (`.serena/checkpoints/`) | v1.1 | MVP lives in-memory only. |
| Inverse `WorkspaceEdit` computation | **MVP** | Rollback mechanism. |
| `execute_command` primitive on `solidlsp` | **MVP** | pylsp-rope commands (e.g., `pylsp_rope.refactor.extract.method`) are invoked via this path; `specialist-python.md` §1.3 depends on it. |
| `$/progress` parsing beyond indexing-done (percent-complete telemetry) | v2+ | Binary ready/not-ready is enough. |

### 3.2 Facade and primitive MCP tools

Canonical MVP surface is four tools; full Pydantic signatures in §5.

| Tool | Stage | Rationale |
|---|---|---|
| `split_file` (facade, mutating) | **MVP** | Star of the show. Absorbs `plan_file_split` via `dry_run=True`. |
| `fix_imports` (facade, mutating) | **MVP** | Every split leaves dangling imports; cleanup non-negotiable. |
| `rollback` (primitive, mutating) | **MVP** | Safety net. Renamed from `rollback_refactor` for brevity. |
| `apply_code_action` (primitive, mutating) | **MVP** | Escape hatch; bundles list/resolve/apply for MVP. |
| `plan_file_split` / `plan_split` | v1.1 | Absorbed into `split_file(dry_run=True)` per `specialist-agent-ux.md` §6.4. Re-introduce if MVP telemetry shows LLMs waste ≥2 dry-runs converging on groupings. |
| `extract_symbols_to_module` / `extract_to_module` | v1.1 | Thin wrapper over `split_file`; KISS. |
| `move_inline_module_to_file` / `promote_inline_module` | v1.1 | Rust-only semantically; Python has no inline modules (`specialist-python.md` §2.4). |
| `list_code_actions` primitive | v1.1 | Folded into `apply_code_action` for MVP. |
| `resolve_code_action` primitive | v1.1 | Same. |
| `execute_command` primitive (MCP tool) | v2+ | Server-specific JSON-RPC escape hatch; not on critical path. |

### 3.3 Language strategies

| Item | Stage | Rationale |
|---|---|---|
| `LanguageStrategy` Protocol + registry (static dict) | **MVP** | Facade compile dep. |
| `RustStrategy` | **MVP** | Language priority dictates it. |
| `PythonStrategy` | **MVP** | Language priority dictates it. |
| `TypeScriptStrategy` — paper design only | **MVP (paper)** | Required to validate abstraction against a third shape without shipping code (`specialist-scope.md` §2.4). |
| `GoStrategy`, `TSStrategy` implementations | v1.1 | Not required for MVP. |
| Server-extension whitelists (`execute_command_whitelist`) | v1.1 | MVP facades never call whitelisted methods. |
| `post_apply_health_check_commands` | v1.1 | External `cargo test`/`pytest` covers verification at MVP. |
| `lsp_init_overrides` for Rust (`cargo.targetDir`, `procMacro.enable=True`) | **MVP** | Non-negotiable per `specialist-rust.md` §3.4, §3.5. |
| `lsp_init_overrides` for Python (pylsp plugins + venv config) | **MVP** | pylsp-mypy `live_mode: False`; pylsp-rope `enabled: True`; see `specialist-python.md` §3.11. |
| Entry-point-based third-party strategy discovery | v2+ | Zero demand. |

### 3.4 Deployment

| Item | Stage | Rationale |
|---|---|---|
| `o2-scalpel/.claude-plugin/plugin.json` + `o2-scalpel/.mcp.json` | **MVP** | `uvx --from <path>` install target. |
| `vendor/serena/` git submodule | **MVP** | Binary source. |
| Sibling-LSP discovery (walking `~/.claude/plugins/cache/`) | **MVP (minimal)** | Needed so scalpel finds `rust-analyzer` and Python LSP. |
| `platformdirs` path resolution | **MVP** | Cross-platform correctness. |
| `pydantic` schema on `.lsp.json` | **MVP** | Fail-loud is table stakes. |
| Env-var override `O2_SCALPEL_PLUGINS_CACHE` | **MVP** | One-line escape hatch. |
| Lazy spawn on first use | **MVP** | 4–8 GB rust-analyzer cannot eager-spawn. |
| `multilspy` adoption | **MVP** | Serena already proves it. |
| `(language, project_root)` registry | **MVP** | Reuse within a session. |
| `is_alive()` pre-checkout probe | v1.1 | MVP is one-shot per session. |
| Idle-shutdown after N minutes | v1.1 | MVP tests don't sit idle. |
| Config-file override `~/.config/o2.scalpel/config.toml` | v1.1 | Env var is enough. |
| `scalpel_reload_plugins` MCP tool | v1.1 | MVP re-scans on server start. |
| `SessionStart` verify hook | v1.1 | Nice affordance, not blocking. |
| Public marketplace at `o2alexanderfedin/claude-code-plugins` | v1.1 | Publishing decision, not capability. |
| `o2-scalpel-newplugin` template generator (Q14) | v2+ | Zero MVP value. |
| Reference LSP-config plugins (`rust-analyzer-reference`, `clangd-reference`) | v2+ | MVP piggybacks on boostvolt. |
| Vendor-exclusion CI guard (Piebald) | v1.1 | Blocks v1.1 public release, not MVP. |

### 3.5 Fixtures

| Item | Stage | Rationale |
|---|---|---|
| `calcrs` Rust fixture (~900 LoC + Cargo.toml + smoke tests + serde derive) | **MVP** | §1 names it; shrink per `specialist-rust.md` §7.1 (drop `main.rs`, drop `expected/post_split/` snapshot from MVP gates, add minimal `serde` derive). |
| `calcpy` Python fixture (~600–900 LoC, stdlib-only, package layout `calcpy/__init__.py` + submodules placeholder) | **MVP** | §1 names it; authored per `specialist-python.md` §6. |
| `big_cohesive.rs` + `big_heterogeneous.rs` integration fixtures | **MVP** | Planning-shape coverage. |
| `cross_visibility.rs` | **MVP** | `fix_visibility` promoted to T1 per `specialist-rust.md` §2.1. |
| `with_macros.rs` (serde derive) | **MVP** | Proc-macro pathway gate per `specialist-rust.md` §R2. |
| `inline_modules.rs` | v1.1 | Feeds `move_inline_module_to_file` (v1.1). |
| `mod_rs_swap.rs` | v1.1 | Feeds `mod_rs` style (v1.1). |
| Multi-crate / multi-package fixture | v1.1 | E5. |
| Python integration fixtures (`big_heterogeneous.py`, star-import variant, circular-import variant, stub-drift variant) | Partial MVP | MVP includes one integration fixture (`big_heterogeneous.py`); star/circular/stub variants ride inside `calcpy` features (`specialist-python.md` §6.2). |

### 3.6 E2E scenarios

| # | Scenario | Stage | Rationale |
|---|---|---|---|
| E1 | Happy-path split (Rust) | **MVP** | §1 gate. |
| E1-py | Happy-path split (Python) | **MVP** | §1 gate — Python. |
| E2 | Dry-run → inspect → commit | **MVP** | Atomicity contract. |
| E3 | Rollback after failed check | **MVP** | Safety property. |
| E7 | rust-analyzer cold start | **MVP** | Promoted from nightly per `specialist-rust.md` §7.2 — the single largest MVP risk. First-invocation UX. Conflicts with `specialist-scope.md` §2.9 which defers E7 to v1.1; **resolved: adopt Rust specialist's promotion**, cold-start UX is user-visible on every new workspace and losing it regresses the demo. |
| E9 | Semantic equivalence (Rust, `cargo test` byte-identical) | **MVP** | §1 gate. |
| E9-py | Semantic equivalence (Python, `pytest` byte-identical) | **MVP** | §1 gate — Python. |
| E10 | Regression: existing `rename_symbol` behavior | **MVP** | Serena existing primitive must not break. |
| E4 | Concurrent edit mid-refactor (`ContentModified`) | v1.1 | Retry logic lives in MVP code; explicit race E2E can wait. |
| E5 | Multi-crate / multi-package workspace | v1.1 | MVP fixture is single-package. |
| E6 | `fix_imports` on crate-wide glob | v1.1 | MVP enumerates files. |
| E8 | LSP crash recovery | v1.1 | Ops edge case. |
| E4-py | Star-import warning fires | v1.1 | Python-specific nightly; detection exists in MVP code. |
| E5-py | Circular-import detection | v1.1 | Same. |
| E7-py | Virtualenv resolution | v1.1 | Same. |

Canonical MVP E2E set: **E1, E1-py, E2, E3, E7, E9, E9-py, E10** — eight scenarios. This reconciles the Rust specialist's set (E1, E2, E3, E7, E9, E10) with the scope specialist's set (E1, E1-py, E2, E3, E9, E9-py, E10) by unioning: both agree on E1/E2/E3/E9/E10, Rust adds E7, scope adds language-paired -py variants. Union = 8. Adopt.

### 3.7 Error taxonomy

| Code | Stage | Rationale |
|---|---|---|
| `SYMBOL_NOT_FOUND` (absorbs `AMBIGUOUS_SYMBOL`) | **MVP** | Candidates list handles both failure shapes. |
| `STALE_VERSION` | **MVP** | Document drift between dry-run and commit. |
| `NOT_APPLICABLE` (absorbs `ASSIST_DISABLED`) | **MVP** | Single code for "no action at this position". |
| `INDEXING` | **MVP** | Cold-start signaling. |
| `APPLY_FAILED` | **MVP** | Partial-apply rolled back. |
| `PREVIEW_EXPIRED` | **MVP** | Dry-run token invalid. |
| `CHECKPOINT_EVICTED` | v1.1 | Collapse into `NOT_APPLICABLE` with message for MVP. |
| Split-per-severity `AMBIGUOUS_SYMBOL` vs `SYMBOL_NOT_FOUND` | v1.1 | Re-split if MVP telemetry shows LLM confusion. |

### 3.8 Observability fields in `RefactorResult`

| Field | Stage | Rationale |
|---|---|---|
| `applied`, `changes`, `diagnostics_delta` | **MVP** | Core contract. |
| `preview_token` (iff `dry_run=True` and success) | **MVP** | Dry-run → commit handoff. |
| `checkpoint_id` (iff `dry_run=False` and `applied=True`) | **MVP** | Rollback handle. |
| `resolved_symbols` | **MVP** | Name-path normalization trace. |
| `warnings` | **MVP** | Non-fatal caveats. |
| `failure` (when applicable) | **MVP** | Repair pattern. |
| `lsp_ops`, `duration_ms` | **MVP** | Observability. |
| `indexing_ready: bool` | **MVP** | LLM-visible readiness signal per `specialist-agent-ux.md` §10.2. |
| `rules_fired: list[str]` | **MVP** | Cross-turn learning signal per `specialist-agent-ux.md` §10.2. |

---

## 4. Resolved Conflicts

The twelve conflicts the orchestration brief flagged. Each is resolved with 2–4 sentences of rationale and a citation.

### 4.1 Tool count and naming

Three proposals: Rust specialist argued six facades (keep design's full set), agent-UX specialist argued four (`split_file`, `fix_imports`, `rollback`, `apply_code_action`), engineering-scope specialist argued three facades plus demote all primitives (`split_file_by_symbols`, `fix_imports`, `rollback_refactor`). **Resolved: canonical MVP surface is four tools**, `split_file` + `fix_imports` + `rollback` + `apply_code_action`, adopting `specialist-agent-ux.md` §1.3 in full. The four-tool surface preserves the three-facade story from the scope specialist and adds the single primitive escape hatch that prevents the LLM from getting stuck when a facade fails; MVP bundles list/resolve/apply inside `apply_code_action` rather than exposing three separate primitives (`specialist-agent-ux.md` §1.2 rank 5). Naming style adopts short verbs (`specialist-agent-ux.md` §2.3): `split_file` not `split_file_by_symbols`, `rollback` not `rollback_refactor`. Rationale: descriptive names buy token cost without information that the docstring does not already supply; at four tools the namespace is not crowded enough to require `_by_symbols` disambiguation.

### 4.2 `plan_file_split` standalone vs. absorbed into `dry_run=True`

`specialist-agent-ux.md` §6 argues absorb (`split_file(dry_run=True)` returns `changes`, `diagnostics_delta`, `preview_token`; the LLM plans from file contents it already has); scope specialist agrees; Rust specialist is neutral but keeps it listed as a first-class facade in the design. **Resolved: absorb into `dry_run=True` at MVP**; re-introduce `plan_split` in v1.1 only if MVP telemetry shows LLMs waste ≥2 dry-runs converging on a good grouping. Rationale: TRIZ segmentation — planner and splitter are two *modes* of the same operation (exploration vs. execution), not two operations; the clustering heuristic is unproven against LLM-native grouping; re-introducing later is additive, not breaking (`specialist-agent-ux.md` §6.4). At MVP the `PlanResult` schema (`suggested_groups`, `cross_group_edges`, `unassigned`) is not rendered by any tool; it moves into the v1.1 contract.

### 4.3 Python primary LSP

`specialist-python.md` §1.3 concludes `pylsp + pylsp-rope + pylsp-mypy` as primary with `basedpyright` as secondary read-only. **Resolved: adopt that pairing verbatim.** Rationale: pylsp-rope is the only combination that emits LSP-spec `refactor.*` code actions with `WorkspaceEdit`-bearing responses, including `CreateFile` on rename-module — the exact shape scalpel's `split_file` composition requires. pyright/basedpyright's `refactor.extract` is Pylance-only and not available in the open source build (`specialist-python.md` §1.2). basedpyright stays as secondary for auto-import (`quickfix.imports` — a basedpyright differentiator re-implementing Pylance) and for type-checking diagnostics fed into `diagnostics_delta`. Both LSPs must be pinned to exact versions in scalpel's `pyproject.toml`; the `LanguageStrategy` integration test asserts advertised `codeActionKinds` at startup so upstream drift fails loud (`specialist-python.md` §1.4).

### 4.4 `parent_module_style` rename

Rust specialist (§6.1) proposes `parent_layout: {"package", "file"}`. Python specialist (§3, §5.1.1) proposes `module_layout_style: {"package", "single_file"}`. **Resolved: canonical name is `module_layout_style` with values `{"package", "single_file"}`**, adopting Python specialist's spelling. Rationale: `module_layout_style` is more self-documenting than `parent_layout` (it names the thing being styled); `single_file` is clearer than `file` (which reads as a filesystem entity). The Rust-specific mapping becomes `package → foo/mod.rs` or `foo.rs + foo/` (strategy internally chooses based on sub-option), `single_file → foo.rs`. Python: `package → foo/__init__.py`, `single_file → foo.py`. Default per-strategy: `RustStrategy.default_module_layout_style() → "single_file"`, `PythonStrategy.default_module_layout_style() → "package"`. The facade contract does not carry a default; the strategy supplies one when the caller omits the field (`specialist-rust.md` §6.8).

### 4.5 `extract_module_kind()` interface

Python specialist (§5.1.3) proposes `extract_module_strategy() -> Literal["native_code_action", "composed"]` with `extract_module_kind()` returning the kind string only when `"native_code_action"`. **Resolved: adopt.** Rationale: this reframes the Protocol so the composition path is first-class — correct for every language except Rust. Rust strategy overrides `extract_module_strategy() → "native_code_action"` and supplies `"refactor.extract.module"` from `extract_module_kind()`. Python strategy returns `"composed"` and owns the composition (create empty target file → per-symbol `MoveGlobal` → organize imports). The facade branches on `extract_module_strategy()`; the `"composed"` branch becomes the canonical path for Go, TypeScript, C++ as well (`specialist-python.md` §5.1.3). `move_to_file_kind()` remains for the Rust-path step 2 and returns `None` on Python.

### 4.6 `DiagnosticsDelta` schema

Rust specialist (§6.5) argues integer count is wrong because pyright emits multiple diagnostics per logical error; proposes severity breakdown. Python specialist (§5.4) argues for an additional `language_findings: dict[str, Any]` for import cycles, star-import risks, stub drift. **Resolved: canonical schema combines both.**

```python
class DiagnosticsDelta(BaseModel):
    before: int
    after: int
    new_errors: list[Diagnostic]
    severity_breakdown: dict[Literal["error", "warning", "info"], SeverityCounts]
    language_findings: dict[str, Any] = {}

class SeverityCounts(BaseModel):
    before: int
    after: int
```

The strict-mode rollback rule reads `severity_breakdown["error"].after - severity_breakdown["error"].before > 0` (warnings do not block), not the raw `len(new_errors) > 0`. `language_findings` is strategy-populated; Python strategy populates `import_cycles_introduced`, `star_import_risks`, `stub_drift`; Rust strategy leaves empty. Rationale: pyright + pylsp-mypy produce warning-heavy noise that would trigger spurious rollbacks; import cycles are Python-only and need first-class observability (`specialist-rust.md` §6.5, `specialist-python.md` §5.4).

### 4.7 `language_options` shape

Python specialist (§5.3) proposes typed dict pass-through `language_options: dict[str, Any]`. Agent-UX specialist (§9.3) proposes nested `language_options.{rust, python}` keyed by language with the non-matching sub-dict ignored and unknown keys warning-surfaced. **Resolved: adopt nested form per agent-UX specialist.** Rationale: detection is automatic from file extension; the LLM supplying both `rust` and `python` sub-dicts is not a bug — it's portable skill authoring. The flat dict is ambiguous when the same key name carries different meanings per language (e.g., `reexport_style` where Rust wants `preserve_exported` and Python wants `explicit`). Unknown keys inside the matched sub-dict surface as `warnings: ["unknown language_option: <key>"]`, not fatal (`specialist-agent-ux.md` §9.3).

```python
split_file(
    file="crates/foo/src/big.rs",
    groups={...},
    module_layout_style="package",
    language_options={
        "rust": {"reexport_keyword": "pub use"},
        "python": {"init_style": "explicit_reexport", "preserve_docstrings": True},
    },
    dry_run=True,
)
```

Scalpel reads only the sub-dict matching detected language; unused sub-dicts are silent (`specialist-agent-ux.md` §9.3).

### 4.8 Fixtures — `calcrs` and `calcpy`

**Resolved: confirm both fixtures.**

- `calcrs`: ~900 LoC `lib.rs`, edition 2021, single crate with library target, zero crates.io deps **plus one exception**: add a minimal `serde::{Serialize, Deserialize}` derive so the proc-macro pathway is exercised in E1/E9 (`specialist-rust.md` §7.1). Drop `src/main.rs` binary target from MVP gates; drop the `expected/post_split/` byte-for-byte snapshot tree from MVP gates (keep for nightly drift detection). Retain `cargo test` byte-identical gate as the E9 contract. Net shape: ~850 LoC Rust + serde + ~40 LoC `Cargo.toml` + ~10 LoC `tests/smoke.rs`.

- `calcpy`: ~600–900 LoC single-module arithmetic evaluator, stdlib-only, deliberately monolithic, package layout with `calcpy/__init__.py` as the monolith (`specialist-python.md` §6, `specialist-scope.md` §6.4). Ugly-on-purpose features: star import at top, inner class tree, mixed `_private` visibility, cross-cluster helper, class with 200-line method body, `__all__ = [...]`, `VERSION` + side-effect init call, sibling `.pyi` stub, `TYPE_CHECKING` block, runtime attribute injection, doctest, `if __name__ == "__main__":` block. Each feature triggers exactly one Python pitfall (`specialist-python.md` §6.2) so E1-py/E9-py test output attributes regressions to specific strategy violations.

Both fixtures are authored in stage 1 (`specialist-scope.md` §5.1) and are never mutated — every E2E scenario runs on a scratch copy. Zero external deps keeps CI deterministic.

### 4.9 E2E gates

Rust specialist gates: E1, E2, E3, E7, E9, E10 (six). Engineering-scope specialist gates: E1, E1-py, E2, E3, E9, E9-py, E10 (seven). **Resolved: union to eight** — E1, E1-py, E2, E3, E7, E9, E9-py, E10. Rationale: both sets agree on E1/E2/E3/E9/E10; Rust specialist adds E7 (cold-start UX as the #1 risk `specialist-rust.md` §R1); scope specialist adds Python twins E1-py/E9-py for dual-language gate. All claims hold in the union so no inconsistency; union is the smallest set that satisfies both specialists' falsifiable claims. The Python twin of E7 (E7-py — virtualenv resolution cold-start) is v1.1 because pylsp cold-start is sub-second (`specialist-python.md` §3.11) and does not carry the same UX risk as rust-analyzer's 5-minute indexing.

### 4.10 Cold-start UX (5-min first invocation)

Rust specialist §R1 names it the #1 MVP risk, promotes E7 from nightly to MVP-gated, and requires three mitigations: (a) tool-description text warns the LLM that first use may block for several minutes, (b) `wait_for_indexing(timeout_s=300)` guard on every facade, (c) progress logging to stderr (debug-grade, not LLM-facing) so a human watching the trace sees "indexing 47%". **Resolved: all three mitigations MVP-required.** The tool-description text is the load-bearing piece — the LLM calibrates expectations from tool descriptions — and is near-zero cost. The 300-second timeout is generous for realistic workspaces; on timeout, return `failure: {kind: "indexing_timeout", hint: "rust-analyzer still indexing after 5 minutes; workspace may be very large or proc-macros misconfigured"}` and let the LLM retry on next user turn. This resolution overrides the scope specialist's deferral of E7 to v1.1; cold-start regression is the first user experience and losing it is unrecoverable.

### 4.11 `multilspy` `$/progress` spike — pre-MVP blocker

Rust specialist §R7 flags a hard dependency: if `multilspy` swallows server-initiated notifications below the `solidlsp` API level, `wait_for_indexing()` cannot be implemented correctly. **Resolved: this is an MVP-blocking spike**, executed before Stage 1's primitive layer locks. Spike shape: 30-line script that spawns rust-analyzer via `solidlsp` and prints every `$/progress` notification it receives. Success criterion: at least one `$/progress` with token `rustAnalyzer/Indexing` is observed and reaches Python land. On failure, file a bug against `multilspy` upstream and add a notification-tap shim in `solidlsp/lsp_protocol_handler/server.py` before Stage 1 ends. Python specialist has an analogous pre-MVP spike (§7.1): confirm pylsp-rope returns `WorkspaceEdit` against the in-memory buffer version (not the on-disk version) when `didSave` is suppressed; run one-shot probe against `calcpy` skeleton before locking Stage 1 API.

### 4.12 Distribution

Scope specialist §7 argues `uvx --from <local-path>` at MVP only. **Resolved: adopt.** Rationale: marketplace publication is a publishing decision, not a capability; MVP tests whether scalpel actually refactors code, and marketplace couples that test to external systems (CC plugin registry caches, Discover tab, third-party aggregators). Published `v0.1.0-mvp` tag is an internal git signal; no `marketplace.json` entry, no GitHub Actions release workflow, no PyPI release. Marketplace ships at v1.1 with deliberate `v0.1.0` version tag, documented API freeze, and the Piebald-exclusion CI guard in place.

---

## 5. Canonical MVP Tool Surface

Pydantic-style signatures. Docstrings ≤90 words; priority labels per `specialist-agent-ux.md` §8.

### 5.1 Shared types

```python
from typing import Any, Literal
from pydantic import BaseModel


class Range(BaseModel):
    """LSP-compatible (line, character) range."""
    start: tuple[int, int]
    end: tuple[int, int]


class Hunk(BaseModel):
    """Unified-diff-shaped hunk; scalpel does not render full post-edit file text."""
    kind: Literal["add", "remove", "context"]
    start_line: int
    lines: list[str]


class FileChange(BaseModel):
    path: str
    kind: Literal["create", "modify", "delete"]
    hunks: list[Hunk]


class Diagnostic(BaseModel):
    path: str
    line: int
    severity: Literal["error", "warning", "info"]
    message: str


class SeverityCounts(BaseModel):
    before: int
    after: int


class DiagnosticsDelta(BaseModel):
    before: int
    after: int
    new_errors: list[Diagnostic]
    severity_breakdown: dict[Literal["error", "warning", "info"], SeverityCounts]
    language_findings: dict[str, Any] = {}  # strategy-populated


class ResolvedSymbol(BaseModel):
    requested: str
    resolved: str


class FailureInfo(BaseModel):
    stage: str
    symbol: str | None
    reason: str
    recoverable: bool


class LspOpStat(BaseModel):
    method: str
    count: int
    total_ms: int


class RefactorResult(BaseModel):
    applied: bool
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    preview_token: str | None = None    # iff dry_run=True and success
    checkpoint_id: str | None = None    # iff dry_run=False and applied=True
    resolved_symbols: list[ResolvedSymbol]
    warnings: list[str]
    failure: FailureInfo | None = None
    lsp_ops: list[LspOpStat]
    duration_ms: int
    indexing_ready: bool                 # LLM-visible readiness signal
    rules_fired: list[str]               # cross-turn learning signal


class ErrorResponse(BaseModel):
    error: Literal[
        "SYMBOL_NOT_FOUND",
        "STALE_VERSION",
        "NOT_APPLICABLE",
        "INDEXING",
        "APPLY_FAILED",
        "PREVIEW_EXPIRED",
    ]
    message: str
    hint: str
    retryable: bool
    candidates: list[dict[str, Any]] = []       # for SYMBOL_NOT_FOUND
    estimated_wait_ms: int | None = None         # for INDEXING
    failed_stage: str | None = None              # for APPLY_FAILED
    reason: str | None = None                    # for NOT_APPLICABLE
```

### 5.2 `split_file` — P0, MVP

```python
def split_file(
    file: str,
    groups: dict[str, list[str]],                              # {module_name: [name_paths]}
    keep_in_original: list[str] = [],
    module_layout_style: Literal["package", "single_file"] | None = None,
    reexport_policy: Literal["preserve_public_api", "none"] = "preserve_public_api",
    language_options: dict[str, dict[str, Any]] = {},          # {"rust": {...}, "python": {...}}
    allow_partial: bool = False,
    dry_run: bool = False,
    preview_token: str | None = None,
) -> RefactorResult:
    """
    Split a single source file into multiple submodules by moving named
    symbols into new files and updating the parent module declaration.
    Supports Rust (.rs) and Python (.py). Use when the user asks to
    split, break up, decompose, or modularize a large file -- NOT when
    they ask to find or inspect code (use the LSP tool for that).
    Returns a changes list, a diagnostics_delta, and a preview_token
    when dry_run=true; returns a checkpoint_id when committed. Atomic:
    rolls back if new compile errors appear.
    """
```

Word count: 86. Key behavior: `module_layout_style=None` means "strategy picks default" (Rust `single_file`, Python `package`). `reexport_policy` is restricted to `{"preserve_public_api", "none"}` at MVP; `"explicit_list"` is v1.1 (`specialist-rust.md` §4.2). `preview_token=None` on commit re-runs the pipeline (result may differ from earlier dry-run); `preview_token=str` on commit uses the cached `WorkspaceEdit` byte-identically.

### 5.3 `fix_imports` — P0, MVP

```python
def fix_imports(
    files: list[str],                                          # explicit list; no "**" glob at MVP
    add_missing: bool = True,
    remove_unused: bool = True,
    reorder: bool = False,                                     # MVP default False (drops merge_imports)
    language_options: dict[str, dict[str, Any]] = {},
    dry_run: bool = False,
    preview_token: str | None = None,
) -> RefactorResult:
    """
    Sweep a set of files to correct broken import/use statements after
    a structural refactor, add missing imports, and remove unused
    imports. Supports Rust (.rs) and Python (.py). Call immediately
    after split_file or any other structural move; do NOT call before
    (no broken state exists yet). Returns count of files modified and
    remaining diagnostics; safe to call repeatedly (idempotent).
    Defaults apply add_missing + remove_unused; reorder off at MVP.
    """
```

Word count: 80. `reorder=False` at MVP per `specialist-rust.md` §4 (drop `merge_imports`). `files=["**"]` glob is v1.1; MVP caller supplies explicit file list (the split caller knows exactly which files changed).

### 5.4 `rollback` — P0, MVP

```python
def rollback(checkpoint_id: str) -> RefactorResult:
    """
    Undo a prior refactor by its checkpoint_id. Restores all files
    touched by that refactor to their pre-refactor contents. Supports
    Rust and Python (any file type the original refactor touched).
    Call when the user says undo or revert after a commit, or when
    post-refactor verification (cargo check, pytest) reveals a
    semantic break. Takes one argument: checkpoint_id (returned by
    the successful split_file / fix_imports / apply_code_action
    call). Idempotent: second rollback with same id returns
    {applied: true, restored_files: []}.
    """
```

Word count: 87. Returns a degenerate `RefactorResult` where `applied=True` means the rollback itself succeeded (not the original refactor); `changes` lists the inverse edits; `checkpoint_id` is consumed.

### 5.5 `apply_code_action` — P0, MVP

```python
def apply_code_action(
    file: str,
    range: Range,
    kind: str,                                                 # LSP codeAction kind
    title_contains: str | None = None,                         # disambiguator
    language_options: dict[str, dict[str, Any]] = {},
    dry_run: bool = False,
    preview_token: str | None = None,
) -> RefactorResult:
    """
    Apply a single LSP code action at a range. Bundled list + resolve
    + apply for MVP. Supports any file the LSP answering the request
    supports (Rust, Python at MVP). Use when split_file / fix_imports
    cannot express the operation (e.g., inline a variable, qualify a
    path, change visibility). Pass the LSP codeAction kind and
    optionally title_contains to disambiguate multiple matches.
    Returns a RefactorResult with checkpoint_id on commit; rolls back
    on apply failure.
    """
```

Word count: 78. At MVP this tool takes a file + range rather than a prior `id` because `list_code_actions` + `resolve_code_action` are not exposed as separate primitives; the single call resolves and applies atomically.

### 5.6 MVP surface summary

| Tool | Priority | Stage | Inputs (brief) | Output |
|---|:---:|:---:|---|---|
| `split_file` | P0 | MVP | file + groups + policy + dry_run + preview_token | `RefactorResult` |
| `fix_imports` | P0 | MVP | files + per-op flags | `RefactorResult` |
| `rollback` | P0 | MVP | checkpoint_id | `RefactorResult` |
| `apply_code_action` | P0 | MVP | file + range + kind + title_contains | `RefactorResult` |
| `plan_split` | P1 | v1.1 | file + strategy + max_groups | `PlanResult` |
| `extract_to_module` | P1 | v1.1 | file + symbols + new_module | `RefactorResult` |
| `list_code_actions` | P1 | v1.1 | file + range + kinds | `list[CodeActionDescriptor]` |
| `resolve_code_action` | P2 | v1.1 | id | `ResolvedAction` |
| `promote_inline_module` | P2 | v1.1 | file + module_name + style (Rust-only) | `RefactorResult` |
| `execute_command` | P2 | v2+ | command + arguments | `Any` |

---

## 6. Language Strategy Interface (revised)

Diff against main design §5 with all MVP renames and additions applied.

### 6.1 Revised Protocol

```python
from pathlib import Path
from typing import Any, Literal, Protocol
from pydantic import BaseModel


ModuleLayoutStyle = Literal["package", "single_file"]
ExtractModuleStrategy = Literal["native_code_action", "composed"]


class ExecuteCommand(BaseModel):
    method: str
    params: dict[str, Any] = {}


class LanguageStrategy(Protocol):
    """
    Per-language plugin. One instance per supported language. Keeps
    the interface small; if it grows past ~18 methods, the abstraction
    is wrong and the facades are leaking.
    """

    language: "Language"                                       # reuses existing Serena enum
    file_extensions: frozenset[str]                            # {".rs"} / {".py"} / ...

    # --- Extraction strategy selection (NEW at MVP) ------------------
    def extract_module_strategy(self) -> ExtractModuleStrategy: ...
        # Rust: "native_code_action" (uses extract_module_kind() below)
        # Python / Go / TS: "composed" (strategy owns the composition)

    def extract_module_kind(self) -> str | None: ...
        # Rust: "refactor.extract.module"
        # Python: None (composition path)

    def move_to_file_kind(self) -> str | None: ...
        # Rust: "refactor.extract" (+ title disambig for move_module_to_file)
        # Python: None

    def rename_kind(self) -> str | None: ...
        # Rust: "refactor.rewrite"
        # Python: None (rename is a first-class method, not a codeAction)

    # --- Module / file layout (RENAMED and SPLIT at MVP) ---------------
    def default_module_layout_style(self) -> ModuleLayoutStyle: ...
        # Rust: "single_file"  (foo.rs)
        # Python: "package"     (foo/__init__.py)

    def module_filename_for(
        self, module_name: str, style: ModuleLayoutStyle
    ) -> Path: ...
        # Rust+package: foo/mod.rs  (or foo.rs + foo/ per substyle)
        # Rust+single_file: foo.rs
        # Python+package: foo/__init__.py
        # Python+single_file: foo.py

    def parent_module_register_lines(
        self, module_name: str
    ) -> list[str]: ...
        # Rust: ["mod foo;"]
        # Python: []   (filesystem is the registration)
        # TypeScript: ['export * from "./foo";']  (if re-export desired)

    def parent_module_import_lines(
        self, module_name: str, symbols: list[str]
    ) -> list[str]: ...
        # Rust: []  (usually covered by pub use re-export)
        # Python: [f"from .{module_name} import {sym}" for sym in symbols]
        # TypeScript: [f'export * from "./{module_name}";']

    def reexport_syntax(
        self, symbol: str, parent_module: str
    ) -> str: ...
        # Rust: f"pub use {parent_module}::{symbol};"
        # Python: f"from .{parent_module} import {symbol}"

    # --- Planning heuristics ------------------------------------------
    def is_top_level_item(self, symbol: "DocumentSymbol") -> bool: ...
    def is_safe_to_move(                                       # NEW at MVP
        self, symbol: "DocumentSymbol"
    ) -> tuple[bool, str]: ...
        # Rust: always (True, "") for top-level items
        # Python: (False, "module-level executable code") for non-def/class regions
    def is_publicly_visible(                                   # NEW at MVP
        self, symbol: "DocumentSymbol"
    ) -> bool: ...
        # Rust: pub / pub(crate) markers
        # Python: not starting with _, or in __all__ if defined
    def symbol_size_heuristic(self, symbol: "DocumentSymbol") -> int: ...
    def clustering_signal_quality(                             # NEW at MVP
        self,
    ) -> Literal["high", "medium", "low"]: ...
        # Rust: "high"  -- rust-analyzer references are precise
        # Python: "medium"  -- pylsp-rope references are good, not great

    # --- Server extensions (whitelist empty at MVP) --------------------
    def execute_command_whitelist(self) -> frozenset[str]: ...
        # Rust MVP: frozenset()
        # Python MVP: {"pylsp_rope.refactor.extract.method", ...}  (subset)

    # --- Diagnostics ----------------------------------------------------
    def post_apply_health_check_commands(self) -> list[ExecuteCommand]: ...
        # MVP: [] for all strategies (external cargo test / pytest)

    # --- LSP init overrides --------------------------------------------
    def lsp_init_overrides(self) -> dict[str, Any]: ...
        # Rust: {"rust-analyzer.cargo.targetDir": "${CLAUDE_PLUGIN_DATA}/ra-target",
        #        "rust-analyzer.procMacro.enable": True,
        #        "rust-analyzer.checkOnSave.enable": False,
        #        "rust-analyzer.cachePriming.enable": False}
        # Python: {"pylsp": {"plugins": {...}}, "python": {"venvPath": ...}}

    # --- Name-path resolution -----------------------------------------
    def canonicalize_name_path(                                # NEW at MVP
        self, name_path: str
    ) -> str: ...
        # Canonicalize separators to "::". Python accepts "foo.bar" -> "foo::bar".

    # --- Dry-run fidelity ---------------------------------------------
    def dry_run_supported(self) -> bool: ...
        # Rust: True (codeAction/resolve returns full WorkspaceEdit)
        # Python: True for MVP; specific facades may degrade per composition
```

### 6.2 Diff summary against main design §5

| Method | Before (main design §5) | After (MVP) | Rationale |
|---|---|---|---|
| `extract_module_kind()` | `-> str` (always present) | `-> str \| None`, gated by `extract_module_strategy()` | Python has no single kind; composition is first-class (§4.5). |
| `move_to_file_kind()` | `-> str \| None` | same | Unchanged. |
| `rename_kind()` | `-> str` | `-> str \| None` | Most servers expose rename as a top-level method, not a kind (`specialist-python.md` §3.3). |
| `module_declaration_syntax(name, style)` | Single method returning `"mod foo;"` sort of line | **Split into `parent_module_register_lines()` + `parent_module_import_lines()`** | Python has no declaration; Rust has one. Split makes the difference honest (`specialist-rust.md` §6.3). |
| `module_filename_for(name, style)` | `style: ParentModuleStyle` | `style: ModuleLayoutStyle` — `{"package", "single_file"}` | Rename removes Rust jargon (§4.4). |
| `reexport_syntax(symbol)` | Single-arg | `reexport_syntax(symbol, parent_module)` | Parent module name was implicit; make it explicit for multi-group splits. |
| `is_top_level_item()` | same | same | Unchanged. |
| `is_safe_to_move()` | — | new | Python `if __name__ == "__main__":` blocks (`specialist-rust.md` §6.4). |
| `is_publicly_visible()` | — | new | Explicit strategy method for "what counts as public" — Rust `pub`, Python `__all__` or non-underscore (`specialist-rust.md` §6.2). |
| `symbol_size_heuristic()` | same | same | Unchanged. |
| `clustering_signal_quality()` | — | new | `plan_file_split` warnings calibration (`specialist-rust.md` §6.7). |
| `execute_command_whitelist()` | Frozen set of server extensions | Empty `frozenset()` for Rust at MVP; Python subset of pylsp-rope commands | MVP facades don't call whitelisted methods (`specialist-rust.md` §2.2, `specialist-python.md` §3.9). |
| `post_apply_health_check_commands()` | `[ExecuteCommand("rust-analyzer/runFlycheck")]` | `[]` for both MVP | External `cargo test`/`pytest` at MVP (`specialist-rust.md` §4.5, `specialist-python.md` §3.10). |
| `lsp_init_overrides()` | Open | Specified per strategy; see above | MVP-required for Rust (targetDir, procMacro); MVP-required for Python (pylsp plugins + venv). |
| `canonicalize_name_path()` | — | new | Python accepts `foo.bar`; normalize to `::` internally (`specialist-agent-ux.md` §9.5). |
| `dry_run_supported()` | — | new | pyright may degrade dry_run on composed refactorings (`specialist-rust.md` §6.9). |
| `default_module_layout_style()` | Implicit default (`"dir"`) in facade | Strategy-supplied default | `"dir"` means opposite things in Rust vs. Python (§4.4). |

### 6.3 Strategy registration

Static dict in `/src/serena/refactoring/__init__.py`. Entry-points deferred to v2+.

```python
# src/serena/refactoring/__init__.py
from .rust_strategy import RustStrategy
from .python_strategy import PythonStrategy

LANGUAGE_STRATEGIES: dict["Language", LanguageStrategy] = {
    Language.RUST: RustStrategy(),
    Language.PYTHON: PythonStrategy(),
}
```

TypeScript and Go are paper-only at MVP; their strategy files exist as commented stubs referenced from the paper design (`specialist-scope.md` §2.4). Stage-3 merge is gated on a review that exercises the TS paper design against the Protocol — if any Protocol method forces TS to lie, the Protocol is wrong (`specialist-rust.md` §8.2).

---

## 7. Rust MVP

Adapted from `specialist-rust.md` §§2, 3, 4, 7, 12.

### 7.1 The six rust-analyzer assists

Canonical MVP set:

| Assist | Tier | Used by |
|---|---|---|
| `extract_module` | T1 | `split_file` step 1 per group |
| `move_module_to_file` | T1 | `split_file` step 2 per group |
| `auto_import` | T1 | `fix_imports` add-missing path |
| `remove_unused_imports` | T1 | `fix_imports` remove-unused path |
| `fix_visibility` | T1 | `split_file` diagnostic-driven recovery (`specialist-rust.md` §11.5) |
| `refactor.extract` disambiguation wrapper (matches `move_module_to_file` by title) | T1 | Internal to `RustStrategy` |

Seven assists when `fix_visibility` is counted, matching the Rust specialist's §2.1 net. Everything else in the 158 rust-analyzer assists is reachable via `apply_code_action` primitive but not exposed as a facade path.

### 7.2 Five non-deferrable pitfalls

Each one corrupts the §Workflow demo if absent. All five are MVP-required; none are deferrable.

1. **`snippetTextEdit: false` advertisement at `initialize`.** Without it, the applier writes literal `$0` markers into source files that compile but fail `cargo test` byte-identical (`specialist-rust.md` §3.1). ~5 LoC in `/src/solidlsp/language_servers/rust_analyzer.py`.

2. **`$/progress rustAnalyzer/Indexing` wait.** Every facade calls `wait_for_indexing(timeout_s=300)` before its first `codeAction`. On timeout, return `failure: {kind: "indexing_timeout", hint: ...}`. ~30 LoC listener in `solidlsp/ls.py` plus one-liner per facade (`specialist-rust.md` §3.2).

3. **`ContentModified` (−32801) retry-once.** Decorator on the `codeAction/resolve` helper in `solidlsp`; `didChange(file, current_buffer)` resync between retries; second failure fails loud (`specialist-rust.md` §3.3).

4. **`cargo.targetDir` override.** `RustStrategy.lsp_init_overrides()` returns `{"rust-analyzer.cargo.targetDir": "${CLAUDE_PLUGIN_DATA}/ra-target"}`. `${CLAUDE_PLUGIN_DATA}` resolved at LSP-spawn time via `platformdirs.user_data_dir("claude")` (`specialist-rust.md` §3.4). Doubles disk usage — document in marketplace README.

5. **`procMacro.enable=true`.** Non-negotiable on macro-heavy workspaces. `serde`, `tokio`, `clap`, `thiserror` all require proc-macro expansion for `documentSymbol` and `references` to be correct (`specialist-rust.md` §3.5). ~1–2 GB extra memory; ~30–60s extra cold start; both acceptable on 32–64 GB dev machines.

Additional sixth pitfall promoted: **cold-start UX** (`specialist-rust.md` §3.6). Tool-description text warns the LLM; `wait_for_indexing()` emits periodic progress to stderr for human traces. Both MVP-required.

### 7.3 MVP cuts from the Rust facade depth

Per `specialist-rust.md` §4; these cuts shrink the ~600-LoC facade row to ~350 LoC without losing any E2E gate.

- Drop `parent_module_style: "mod_rs"` (canonical field renamed to `module_layout_style`; `mod_rs` substyle is v1.1).
- Drop `reexport_policy: "explicit_list"` + `explicit_reexports` parameter (v1.1).
- Drop `fix_imports(files=["**"])` glob expansion (MVP supplies explicit file list).
- Drop `experimental/ssr` from `execute_command_whitelist()` (v1.1).
- Drop `rust-analyzer/runFlycheck` from `post_apply_health_check_commands()` (v1.1).
- Drop `plan_file_split` strategies `by_visibility` and `by_type_affinity` (absorbed into `dry_run=True` anyway).
- Drop `merge_imports` and `fix_imports(reorder=True)` — the flag exists but defaults to `False` at MVP.

### 7.4 `calcrs` fixture specification

| Property | Value |
|---|---|
| Kind | Single Cargo package with library target only (binary dropped from MVP gates) |
| Purpose | Arithmetic-expression evaluator: `run("2 + 3 * 4") == Ok(Value::Int(14))` |
| Size | `src/lib.rs` ≈ 850 LoC (net after drop of `main.rs`) |
| Build | Stable Rust, `-D warnings`, zero warnings |
| Test | `cargo test` runs ~30 unit tests; all pass before refactor |
| External deps | `serde = { version = "1", features = ["derive"] }` — the **only** allowed crates.io dep, added to exercise proc-macro pathway per `specialist-rust.md` §7.1 |
| Edition | 2021 |
| Ugly-on-purpose | Mixed `pub`/`pub(crate)`/private visibility; inline `mod tests { ... }`; helper referenced from three clusters; 120-line `impl` block; two intertwined `use` chains; `#[derive(Serialize, Deserialize)]` on `ast::Value` |
| Layout | `/test/e2e/fixtures/calcrs/` with `Cargo.toml`, `src/lib.rs`, `tests/smoke.rs`, `expected/baseline.txt` |
| Not in MVP gates | `src/main.rs` binary, `expected/post_split/` snapshot tree (retained for nightly) |

### 7.5 Rust integration fixtures

MVP-required: `big_cohesive.rs`, `big_heterogeneous.rs`, `cross_visibility.rs`, `with_macros.rs`, `inline_modules.rs`. Deferred: `mod_rs_swap.rs` (v1.1).

### 7.6 Rust-side LoC estimate (MVP-trimmed)

Per `specialist-rust.md` §9:

| Layer | LoC |
|---|---|
| `solidlsp` primitive methods | ~90 |
| `rust_analyzer.py` init tweak (targetDir, procMacro, checkOnSave, cachePriming) | ~10 |
| WorkspaceEdit applier upgrade | ~150 |
| Checkpoint/rollback machinery | ~100 |
| Primitive MCP tools (bundled `apply_code_action`) | ~150 |
| Facade tools (MVP-trimmed) | ~350 |
| `LanguageStrategy` interface + registry | ~140 |
| `RustStrategy` plugin | ~120 |
| Unit tests | ~350 |
| Integration tests | ~350 + 5 fixtures |
| E2E harness + scenarios (Rust side) | ~450 + `calcrs` |
| **Rust-side total** | **~2,260 LoC** |

---

## 8. Python MVP

Adapted from `specialist-python.md`.

### 8.1 LSP selection

Primary: `pylsp + pylsp-rope + pylsp-mypy`. Secondary: `basedpyright` for auto-import and type-checking diagnostics. Both pinned to exact versions in scalpel's `pyproject.toml` (`specialist-python.md` §7.4). Integration test asserts advertised `codeActionKinds` at server startup to catch upstream drift.

Rejected: `pyright` alone (no refactor-extract, no auto-import); `jedi-language-server` alone (maintenance mode); `ruff server` alone (lint+format only); `pyrefly` (refactor capabilities not yet enumerated).

### 8.2 Composition pattern (`split_file` for Python)

Python has no `extract_module` assist. The strategy composes (`specialist-python.md` §2.1):

1. `documentSymbol(file)` — enumerate top-level items.
2. For each group `(module_name, symbols)`:
   a. Create empty `module_name.py` (or convert the parent to a package and create inside).
   b. For each `symbol`, run Rope's `MoveGlobal` via `pylsp_rope.refactor.*` through `workspace/executeCommand`.
   c. Append `from .module_name import Symbol` to `__init__.py` if `reexport_policy == "preserve_public_api"`.
3. Organize imports on every touched file (`pylsp_rope.source.organize_import`).
4. Diagnostics-delta: run `basedpyright` on changed files; count errors by severity before vs. after.
5. Auto-rollback if `severity_breakdown["error"].after > before`.

Key ordering rule: **the client must create the target file first** because Rope's `MoveGlobal` requires an existing destination resource — unlike rust-analyzer's `move_module_to_file` which emits `CreateFile` atomically with the text edit.

### 8.3 Virtualenv discovery

Ten-step chain per `specialist-python.md` §4.1; last step fails loud with the full attempted chain:

1. `$O2_SCALPEL_PYTHON_EXECUTABLE` full override.
2. `[tool.o2-scalpel] python_executable` in `pyproject.toml`.
3. `VIRTUAL_ENV` env var.
4. `.venv/bin/python` walking up from project root.
5. `venv/bin/python` fallback.
6. `poetry env info -p` if `poetry.lock` present.
7. `pdm info --packages` if `pdm.lock` present.
8. `uv run which python` if `uv.lock` present.
9. `$CONDA_PREFIX/bin/python` if conda.
10. `sys.executable` of scalpel process.

Resolved interpreter passed as `jedi.environment` and `pylsp-mypy.overrides` in init options.

### 8.4 `calcpy` fixture specification

| Property | Value |
|---|---|
| Kind | Python package: `calcpy/__init__.py` as monolith + sibling `tests/` |
| Purpose | Arithmetic-expression evaluator matching `calcrs` semantics |
| Size | `calcpy/__init__.py` ≈ 550–900 LoC (monolithic on purpose) |
| External deps | stdlib + `pytest` as dev-dep only; zero runtime deps |
| Python version | 3.10+ (matches pinned Rope) |
| Ugly-on-purpose | Star `from math import *`; inner class tree `Expr/BinaryOp/UnaryOp`; mixed `_private` visibility; cross-cluster helper `_resolve_name`; `Evaluator` class with 200-line body; `__all__ = ["run", "VERSION", "Value", "CalcError"]`; `VERSION` + side-effect `_initialize_logging()` at top; sibling `calcpy.pyi` stub; `TYPE_CHECKING` block; `Evaluator.default_precision = 28` runtime attribute; doctest in `run()`; `if __name__ == "__main__":` block |
| Layout | `/test/e2e/fixtures/calcpy/` with `pyproject.toml`, `calcpy/__init__.py`, `calcpy/calcpy.pyi`, `tests/test_smoke.py`, `expected/baseline.txt` |

Each ugly feature triggers exactly one Python pitfall from `specialist-python.md` §4 (star-import hides moves; `__init__.py` side effects; stub drift; circular imports; runtime-injected attributes; `__all__` preservation). Attribution of E1-py/E9-py failures to strategy violations is therefore deterministic.

### 8.5 Python-specific pitfalls the Rust specialist cannot catch

Enumerated per `specialist-python.md` §4:

1. **Virtualenv / interpreter discovery** — 10-step chain, fail loud.
2. **Star imports hide the move graph** — pre-flight scan for `from <target> import *`; require `allow_star_imports=True` to proceed (via `language_options.python.allow_star_imports`).
3. **`__init__.py` side effects** — preserve top-level content when converting `.py` → package.
4. **PEP 420 implicit namespace packages** — detect and warn before creating `__init__.py`.
5. **Stub files (`.pyi`)** — detect sibling stub; warn; require `update_stubs=True` to proceed.
6. **Circular imports** — post-move graph analysis via Tarjan SCC on parsed ASTs; populate `language_findings.import_cycles_introduced`.
7. **Implicit relative imports** (Python 2 legacy) — detect and warn.
8. **Runtime-injected attributes** — scan for `<symbol>.X = ...` patterns; move assignments with the symbol.
9. **Star exports in `__all__`** — parse original `__all__`; preserve verbatim while re-importing moved symbols.
10. **Test-discovery conventions** — Rope rewrites `test_*.py` imports; the risk is pytest running out-of-process and missing the delta. Documented only at MVP.
11. **Jupyter notebooks (`.ipynb`)** — detect and warn; no rewriting at MVP.
12. **`TYPE_CHECKING` blocks** — verify Rope handles; post-pass text rewrite if it does not.

### 8.6 Python risks

Top three for MVP scope per `specialist-python.md` §7:

1. **pylsp-rope unsaved-buffer behavior** (§7.1, pre-MVP blocker spike). Scalpel's model is every buffer is technically unsaved; pylsp-rope's "experimental" label on unsaved support is a correctness risk. Mitigation: force `textDocument/didSave includeText: true` before every code-action call; extra round-trip is acceptable. Pre-MVP spike confirms behavior.

2. **Virtualenv discovery failure** (§7.2). Ten-step chain + `O2_SCALPEL_PYTHON_EXECUTABLE` escape hatch. E7-py (v1.1) exercises auto-discovery explicitly.

3. **Rope performance on large codebases** (§7.3). MVP restricts `project_scope` to the parent package; 120-second `MoveGlobal` timeout with hint "narrow scope"; documented limitation to 1k–10k-LoC packages.

### 8.7 Python-side LoC estimate

Per `specialist-python.md` §9 and `specialist-scope.md` §3.2:

| Element | LoC |
|---|---|
| `PythonStrategy` plugin | ~280 |
| Virtualenv discovery | ~150 |
| Python-specific `split_file` composition | included in strategy |
| Stub-file handling | ~80 |
| Namespace-package detection | ~40 |
| Circular-import checker | ~100 |
| Star-import scanner | ~50 |
| `calcpy` fixture | ~1,100 LoC fixture content |
| Unit tests | ~400 |
| Integration tests vs real pylsp | ~600 |
| E2E scenarios (E1-py, E9-py MVP; E4-py..E11-py v1.1) | ~300 MVP / ~500 v1.1 |
| **Python-side MVP total** | **~2,400 LoC + ~1,100 fixture** |

---

## 9. Cross-language `RefactorResult` schema — finalized

### 9.1 Canonical schema

Reproduced from §5.1 with annotations:

```python
class DiagnosticsDelta(BaseModel):
    before: int                                                # all diagnostics
    after: int
    new_errors: list[Diagnostic]
    severity_breakdown: dict[Literal["error", "warning", "info"], SeverityCounts]
    language_findings: dict[str, Any] = {}


class RefactorResult(BaseModel):
    applied: bool
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    preview_token: str | None = None
    checkpoint_id: str | None = None
    resolved_symbols: list[ResolvedSymbol]
    warnings: list[str]
    failure: FailureInfo | None = None
    lsp_ops: list[LspOpStat]
    duration_ms: int
    indexing_ready: bool
    rules_fired: list[str]
```

### 9.2 `DiagnosticsDelta` — severity breakdown

The strict-mode rollback rule uses:

```python
delta = severity_breakdown["error"].after - severity_breakdown["error"].before
if delta > 0:
    auto_rollback()
```

Warnings do not block. Info diagnostics do not block. This fixes the naive `len(new_errors) > 0` rollback rule that would rollback every Python refactor unnecessarily (pyright + pylsp-mypy produce warning-heavy output on modern typed code) per `specialist-rust.md` §6.5.

### 9.3 `language_findings` — per-strategy free-form

Schema:

```python
# Python strategy populates:
language_findings = {
    "import_cycles_introduced": [["calcpy.evaluator", "calcpy.parser", "calcpy.evaluator"]],
    "star_import_risks": ["consumers/foo.py"],
    "stub_drift": ["calcpy.pyi"],
    "namespace_package_risk": False,
    "runtime_attribute_moves": ["Evaluator.default_precision -> evaluator.py"],
}

# Rust strategy leaves {} or populates:
language_findings = {
    "proc_macro_expansion_incomplete": False,
    "edition_mismatch": None,
}
```

Strategies may add keys freely; facade does not validate content. LLM consumes as dictionary; unrecognized keys are pass-through (`specialist-python.md` §5.4).

### 9.4 `language_options` shape

Nested dict with per-language sub-dicts:

```python
language_options = {
    "rust": {
        "reexport_keyword": "pub use",       # reserved for v1.1 explicit_list
    },
    "python": {
        "init_style": "explicit_reexport",   # "__all__" | "explicit_reexport"
        "allow_star_imports": False,
        "update_stubs": False,
        "force_regular_package": False,
        "preserve_docstrings": True,
    },
}
```

Scalpel reads the sub-dict matching detected language (from file extension); other sub-dicts are ignored silently; unknown keys inside the matched sub-dict surface as `warnings: ["unknown language_option: <key>"]` (`specialist-agent-ux.md` §9.3).

### 9.5 `preview_token` vs `checkpoint_id` — separation of concerns

The main design conflated these; MVP splits them cleanly per `specialist-agent-ux.md` §5.1:

| Token type | Purpose | TTL | Content | Consumed |
|---|---|---|---|---|
| `preview_token` | `dry_run=True` ↔ `dry_run=False` handoff | 5 minutes | Serialized `WorkspaceEdit` + version snapshot | On commit |
| `checkpoint_id` | Post-commit rollback | LRU-evicted (10 in-memory at MVP) | Inverse `WorkspaceEdit` + pre-edit file snapshots | On rollback |

**Mutually exclusive in response shape.** `dry_run=True` returns `preview_token` and `checkpoint_id=None`. `dry_run=False` (success) returns `checkpoint_id` and `preview_token=None`. They never appear together. The LLM learns one discrimination rule and does not conflate preview with recovery.

### 9.6 Error response schema

Separate flat JSON, not nested inside `RefactorResult`:

```python
class ErrorResponse(BaseModel):
    error: Literal["SYMBOL_NOT_FOUND", "STALE_VERSION", "NOT_APPLICABLE",
                   "INDEXING", "APPLY_FAILED", "PREVIEW_EXPIRED"]
    message: str
    hint: str
    retryable: bool
    # Code-specific extras:
    candidates: list[dict[str, Any]] = []      # SYMBOL_NOT_FOUND
    estimated_wait_ms: int | None = None        # INDEXING
    failed_stage: str | None = None             # APPLY_FAILED
    reason: str | None = None                   # NOT_APPLICABLE
```

LLM-facing runbook per `specialist-agent-ux.md` §3.3: each code has a one-line recovery pattern documented in the tool docstrings so the LLM's tool-selection prompt carries retry expectations. `retryable: true` invites same-turn retry; two consecutive failures escalate to user.

### 9.7 Auto-rollback vs. manual rollback response shapes

**Auto-rollback (diagnostics delta or apply failure):**

```json
{
  "applied": false,
  "changes": [],
  "checkpoint_id": null,
  "failure": {"stage": "diagnostics_check", "reason": "2 new errors; auto-rolled-back", "recoverable": true},
  "diagnostics_delta": {
    "before": 0, "after": 0,
    "new_errors_that_would_have_appeared": [...],
    "severity_breakdown": {"error": {"before": 0, "after": 0}, ...}
  },
  "warnings": ["auto_rolled_back"],
  "lsp_ops": [...],
  "duration_ms": 1843,
  "indexing_ready": true,
  "rules_fired": ["auto_rolled_back:diagnostics"]
}
```

**Manual rollback (`rollback(checkpoint_id)` call):**

```json
{
  "applied": true,
  "changes": [...inverse edits...],
  "diagnostics_delta": {...},
  "checkpoint_id": null,
  "warnings": [],
  "lsp_ops": [...],
  "duration_ms": 127,
  "indexing_ready": true,
  "rules_fired": ["manual_rollback"]
}
```

Distinguished by `applied` (false = auto-rollback; true = manual rollback succeeded) and `rules_fired`.

---

## 10. Pre-MVP spikes

Four spikes; all must complete before Stage 1 API freezes.

### 10.1 `multilspy` `$/progress` spike

**Purpose.** Confirm `multilspy` surfaces server-initiated `$/progress` notifications up to `solidlsp` level so `wait_for_indexing(timeout_s=300)` can be implemented (`specialist-rust.md` §R7).

**Shape.** 30-line Python script that spawns rust-analyzer via `solidlsp` against `calcrs` fixture, registers a hook on `$/progress`, prints every notification with token and value. Run for 120 seconds.

**Success.** At least one `$/progress` with token `rustAnalyzer/Indexing` observed with `kind: "end"` value.

**Failure.** `multilspy` swallows notifications below API level. Mitigation: file bug upstream + add notification-tap shim in `solidlsp/lsp_protocol_handler/server.py` before Stage 1 ends. ~40 LoC shim.

**Blocking.** Yes. `wait_for_indexing()` is load-bearing for MVP E1/E2/E7.

### 10.2 pylsp-rope unsaved-buffer spike

**Purpose.** Confirm pylsp-rope returns `WorkspaceEdit` against the in-memory buffer version when `didSave` is suppressed (`specialist-python.md` §7.1).

**Shape.** Spawn pylsp with pylsp-rope plugin; `didOpen` + `didChange` a `calcpy` skeleton file; invoke `workspace/executeCommand` with `pylsp_rope.refactor.extract.method` against the in-memory version; assert `WorkspaceEdit.documentChanges[*].textDocument.version` matches the `didChange` version, not 0.

**Success.** Returned `WorkspaceEdit` references in-memory version.

**Failure.** Returned edit references disk version. Mitigation: `PythonStrategy` forces `didSave includeText: true` before every code-action call — 1 round-trip tax per action but eliminates the staleness class. Documented limitation: scalpel's Python refactors behave as if files are saved atomically before each step.

**Blocking.** Yes. Affects E1-py/E9-py correctness.

### 10.3 pyright capability parity spike

**Purpose.** Confirm `basedpyright` advertises the `codeActionKinds` set scalpel requires: `["source.organizeImports", "quickfix", "quickfix.imports"]` (`specialist-python.md` §1.4).

**Shape.** Spawn `basedpyright-langserver`; parse the `initialize` response's `capabilities.codeActionProvider.codeActionKinds`; assert superset.

**Success.** Advertised kinds include all three.

**Failure.** basedpyright narrows its kinds. Mitigation: pin known-good version; add monthly scheduled CI run against latest-released-basedpyright to catch regressions.

**Blocking.** Weakly. If fails, MVP falls back to pylsp-only with `pylsp_rope.source.organize_import` covering organize; auto-import path degrades but stays functional.

### 10.4 Pyright vs. pylsp for diagnostics-delta spike

**Purpose.** Determine whether `basedpyright`'s passive `publishDiagnostics` stream is fast enough (<3s per dry-run) for the `diagnostics_delta` check against `calcpy`, or whether scalpel must shell out to `mypy --no-incremental` per dry-run (`specialist-python.md` §7.9, §10.2).

**Shape.** On `calcpy` fixture, trigger a dry-run `split_file` invocation; measure wall-clock from first `didChange` to `publishDiagnostics` for all affected files.

**Success.** <3 seconds.

**Failure.** Scalpel shells out to `mypy --no-incremental`. Documented trade-off: slower dry-run (mypy cold), more accurate delta.

**Blocking.** No. Either outcome is viable at MVP.

---

## 11. Staged Delivery Plan

Three stages per `specialist-scope.md` §5, refined with the rename set and pre-MVP spikes. Sizing via small/medium/large + LoC; no time estimates. Each stage ends with a git tag.

### 11.1 Stage 0 (pre-MVP spikes) — trivial

Goal: four spikes green before Stage 1 API freezes.

| # | Spike | Artifact | LoC |
|---|---|---|---|
| S0.1 | `multilspy` `$/progress` | `spikes/multilspy_progress.py` | ~30 |
| S0.2 | pylsp-rope unsaved-buffer | `spikes/pylsp_rope_unsaved.py` | ~50 |
| S0.3 | basedpyright capability parity | `spikes/basedpyright_caps.py` | ~20 |
| S0.4 | Diagnostics-delta latency | `spikes/pyright_delta_latency.py` | ~40 |

Exit: all spikes pass or their failure mitigations are designed. Tag: `mvp-stage-0-spikes`.

### 11.2 Stage 1 (small) — foundation + strategy contract

Goal: primitives compile, Strategy Protocol locked, fixtures exist.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 1 | `vendor/serena/src/solidlsp/ls.py` | Modify | +60 (request_code_actions, resolve_code_action, execute_command, wait_for_indexing, `$/progress` listener) | S0.1 |
| 2 | `vendor/serena/src/solidlsp/lsp_protocol_handler/server.py` | Modify | +30 (`workspace/applyEdit` handler) | — |
| 3 | `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py` | Modify | +10 (snippetTextEdit:false, init overrides, cargo.targetDir resolution) | — |
| 4 | `vendor/serena/src/serena/refactoring/__init__.py` | New | +15 (registry) | — |
| 5 | `vendor/serena/src/serena/refactoring/language_strategy.py` | New | +140 (Protocol with all MVP additions) | — |
| 6 | `vendor/serena/src/serena/refactoring/rust_strategy.py` | New | +120 | 5 |
| 7 | `vendor/serena/src/serena/refactoring/python_strategy.py` | New | +280 | 5, S0.2 |
| 8 | `vendor/serena/src/serena/refactoring/python_env.py` (virtualenv discovery) | New | +150 | — |
| 9 | `test/e2e/fixtures/calcrs/` | New tree | +850 Rust + Cargo + tests | — |
| 10 | `test/e2e/fixtures/calcpy/` | New tree | +900 Python + pyproject + tests + stub | — |
| 11 | `test/serena/test_language_strategy.py` | New | +200 | 5, 6, 7 |

Exit: `pytest test/serena/test_language_strategy.py` green; `cargo test --manifest-path test/e2e/fixtures/calcrs/Cargo.toml` green; `pytest test/e2e/fixtures/calcpy` green. Tag: `mvp-stage-1`.

Size: **small** (~2,755 LoC total; logic ~805).

### 11.3 Stage 2 (medium) — WorkspaceEdit applier + checkpoint + primitive integration

Goal: real `WorkspaceEdit` applied and rolled back; no facades yet.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 12 | `vendor/serena/src/serena/code_editor.py` | Modify | +180 (CreateFile/RenameFile, ordering, snippet strip, version check, atomic apply) | 1, 2 |
| 13 | `vendor/serena/src/serena/refactoring/checkpoints.py` | New | +120 (in-memory LRU + inverse edit) | 12 |
| 14 | `test/serena/test_workspace_edit_applier.py` | New | +350 (syrupy snapshots) | 12, 13 |
| 15 | `test/solidlsp/rust/fixtures/refactor/big_heterogeneous.rs` | New | +500 | — |
| 16 | `test/solidlsp/rust/fixtures/refactor/big_cohesive.rs` | New | +500 | — |
| 17 | `test/solidlsp/rust/fixtures/refactor/cross_visibility.rs` | New | +250 | — |
| 18 | `test/solidlsp/rust/fixtures/refactor/with_macros.rs` | New | +300 | — |
| 19 | `test/solidlsp/rust/fixtures/refactor/inline_modules.rs` | New | +150 | — |
| 20 | `test/solidlsp/rust/test_rust_integration.py` | New | +300 | 1, 2, 12, 15-19 |
| 21 | `test/solidlsp/python/fixtures/refactor/big_heterogeneous.py` | New | +500 | — |
| 22 | `test/solidlsp/python/test_python_integration.py` | New | +300 | 1, 2, 12, 21, S0.2 |
| 23 | `vendor/serena/src/serena/refactoring/lsp_pool.py` | New | +120 (multilspy wrapper + per-(lang, root) registry) | — |
| 24 | `vendor/serena/src/serena/refactoring/discovery.py` | New | +100 (pathlib + pydantic + env var + platformdirs) | — |

Exit: `pytest test/serena/test_workspace_edit_applier.py test/solidlsp/` green. WorkspaceEdit round-trip demonstrated on synthetic fixtures in both languages. No facade invoked yet. Tag: `mvp-stage-2`.

Size: **medium** (~3,670 LoC; logic ~820, fixtures ~2,300, tests ~950).

### 11.4 Stage 3 (large) — facades + MVP E2E

Goal: §2 falsifiable statement satisfied.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 25 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `split_file` | New | +450 (facade + "no server-assist" composition branch + `dry_run` sandbox) | 6, 7, 12, 13 |
| 26 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `fix_imports` | Same file | +100 | 25 |
| 27 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `rollback` | Same file | +40 | 13, 25 |
| 28 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `apply_code_action` | Same file | +80 (bundled list/resolve/apply) | 1, 12 |
| 29 | Preview-token store | New inside refactoring_tools.py or new module | +60 (UUID + TTL LRU) | 25 |
| 30 | Name-path resolver (hallucination resistance) | New module or within strategies | +80 (exact + case-insensitive + ends-with + separator-normalized) | 6, 7 |
| 31 | `o2-scalpel/.claude-plugin/plugin.json` | New | +20 | — |
| 32 | `o2-scalpel/.mcp.json` | New | +15 | — |
| 33 | `o2-scalpel/README.md` | New | +100 (install, usage, cold-start warning) | — |
| 34 | `test/e2e/conftest.py` | New | +180 (MCP stdio driver, fixture copier, baseline captor) | 31, 32 |
| 35 | `test/e2e/test_calcrs_e2e.py` (E1, E2, E3, E7, E9, E10) | New | +350 | all above |
| 36 | `test/e2e/test_calcpy_e2e.py` (E1-py, E9-py) | New | +250 | all above |
| 37 | `test/e2e/test_rollback.py` (E3 deep-dive) | New | +100 | 35, 36 |

Exit: `pytest -m e2e` runs all 8 MVP scenarios green, zero flakes, single CI run. Tag: `v0.1.0-mvp`.

Size: **large** (~1,825 LoC; logic ~820, test ~880, plugin ~135).

### 11.5 Dependency graph

```
stage 0:  [S0.1][S0.2][S0.3][S0.4]   (parallel; spike results inform Stage 1)
            ↓
stage 1:  [1][2][3]  [4][5]→[6]                      [9]
                         [5]→[7]→[8]                 [10]
                                      [11]
            ↓
stage 2:  [12]→[13]→[14]
          [15][16][17][18][19]→[20]
                    [21]→[22]
          [23]   [24]
            ↓
stage 3:  [25]→[26][27][28]  [29][30]
          [31][32]→[33]→[34]→[35][36][37]
```

Parallelization opportunities per project CLAUDE.md §Parallel Execution:
- Stage 0: all four spikes parallel.
- Stage 1: files 1–3 independent; 5/6/7/8 parallel after 5 lands; 9/10 parallel fixtures.
- Stage 2: 12/13/14 sequential; 15–19 parallel; 21 parallel with 15–19; 23/24 parallel with the rest.
- Stage 3: 25 serializes (single coherent facade); 26/27/28 parallel after 25; 31/32 parallel with 25; 35/36 parallel after 28/30.

CPU-core limit respected. Stage 3's #25 cannot be parallelized across sub-subagents without conflict (single coherent file).

### 11.6 TDD ordering within each stage

Per project CLAUDE.md §Development Process:

- **Stage 1.** Test file #11 written first (red); Protocol #5 and strategies #6/#7 implemented to green; fixtures #9/#10 authored alongside.
- **Stage 2.** Test file #14 written first (red) with syrupy snapshots of expected `WorkspaceEdit` application; applier #12 and checkpoints #13 implemented to green; integration tests #20/#22 written against `big_heterogeneous` fixtures first.
- **Stage 3.** Per-scenario E2E test written first (red); facade code written to green; dry-run contract (byte-identical to commit) is an explicit test assertion before the facade is considered done.

### 11.7 LoC totals

| Stage | Logic | Fixtures | Tests | Total |
|---|---|---|---|---|
| 0 (spikes) | 140 | 0 | 0 | 140 |
| 1 | 805 | 1,750 | 200 | 2,755 |
| 2 | 820 | 2,200 | 950 | 3,970 |
| 3 | 820 | 100 | 880 | 1,800 |
| **MVP** | **~2,585** | **~4,050** | **~2,030** | **~8,665** |

The ~5,010 total in `specialist-scope.md` §5.5 is reached when `vendor/serena/` boilerplate + `conftest.py` + plugin-packaging are excluded from the count; ~8,665 is the fully-loaded MVP delivery.

---

## 12. MVP Test Gates

Eight E2E scenarios block commit to main; six code-level test suites block Stage boundaries.

### 12.1 E2E gates (canonical)

| # | Scenario | Fixture | Pass condition |
|---|---|---|---|
| E1 | Happy-path split (Rust) | `calcrs` | 4 modules created; `cargo check --workspace` exits 0; original `lib.rs` < 200 LoC; `pub use` chain preserved |
| E1-py | Happy-path split (Python) | `calcpy` | ≥3 modules created under package; `__init__.py` re-exports preserved; `pytest` exits 0 |
| E2 | Dry-run → inspect → commit | `calcrs` | `dry_run=True` returns same `FileChange` list as `dry_run=False` with matching `preview_token`; no filesystem change between the two calls (content-hash unchanged); `diagnostics_delta` identical |
| E3 | Rollback after failed check | `calcrs` | Simulate broken `reexport_policy: "none"`; assert `applied=false` and `failure.stage=="diagnostics_check"`; call `rollback(checkpoint_id)`; scratch dir content-hash byte-identical to pre-refactor baseline |
| E7 | rust-analyzer cold start | `calcrs` | First tool call after MCP server spawn blocks on `$/progress rustAnalyzer/Indexing` end event; fixture with `Cargo.lock` pre-populated to force real indexing; `indexing_ready: true` appears in final `RefactorResult` |
| E9 | Semantic equivalence (Rust) | `calcrs` | Refactor → `cargo test` output captured → diff against `expected/baseline.txt`; must be byte-identical including ordering and timing elision |
| E9-py | Semantic equivalence (Python) | `calcpy` | Refactor → `pytest -p no:cacheprovider --no-header` output captured → diff against `expected/baseline.txt`; byte-identical |
| E10 | Regression: `rename_symbol` | existing Serena fixture | Serena's pre-existing `rename_symbol` E2E passes byte-for-byte against the fork |

### 12.2 Green-bar definition

All 8 scenarios pass **in a single CI run on a single machine**. Flake tolerance: each scenario may retry exactly once; two retries = flaky = MVP not done. Fixtures are copied to per-test scratch directories; the checked-in pristine copies are never mutated (lint enforced in `conftest.py`).

### 12.3 Unit/integration coverage rules

| Suite | Coverage rule | Stage gate |
|---|---|---|
| `test/serena/test_language_strategy.py` | Each `LanguageStrategy` method has at least one snapshot test per strategy (Rust, Python); `RustStrategy.parent_module_register_lines()` and `parent_module_import_lines()` emit correct Rust syntax; `is_safe_to_move()` returns `True` for all Rust top-level items | Stage 1 exit |
| `test/serena/test_workspace_edit_applier.py` | Each `documentChanges` variant (TextDocumentEdit, CreateFile, RenameFile, DeleteFile stub-fail, changeAnnotations reject); order preservation; version check; snippet stripping; checkpoint round-trip | Stage 2 exit |
| `test/solidlsp/rust/test_rust_integration.py` | Real rust-analyzer binary against each integration fixture (big_cohesive, big_heterogeneous, cross_visibility, with_macros, inline_modules); assert expected code-action kinds are advertised | Stage 2 exit |
| `test/solidlsp/python/test_python_integration.py` | Real `pylsp + pylsp-rope + pylsp-mypy` against `big_heterogeneous.py`; assert `codeActionKinds` set (`refactor.extract`, `refactor.inline`, `source`, etc.); assert `MoveGlobal` returns `WorkspaceEdit` with `CreateFile` on rename-module | Stage 2 exit |
| `test/e2e/test_calcrs_e2e.py` | E1, E2, E3, E7, E9, E10 | Stage 3 exit |
| `test/e2e/test_calcpy_e2e.py` | E1-py, E9-py | Stage 3 exit |

### 12.4 Nightly scenarios (non-blocking)

`pytest -m e2e-nightly` covers: E4 (concurrent edit / `ContentModified`), E5 (multi-crate workspace), E6 (`fix_imports` glob), E8 (LSP crash recovery), E4-py (star-import warning), E5-py (circular-import detection), E7-py (virtualenv auto-discovery), E8-py (namespace package), E9-py-stub (stub drift), E10-py (`__all__` preservation), E11-py (rename_symbol regression Python-side).

Nightly failure opens an issue; does not block main.

### 12.5 CI infrastructure

- GitHub Actions runner: `ubuntu-latest-4-cores` (16 GB RAM) per `specialist-scope.md` §9.2. Smaller runners not supported.
- rust-analyzer pinned via `DependencyProvider` in `/test/e2e/conftest.py`; version asserted on startup.
- `pylsp + pylsp-rope + pylsp-mypy + basedpyright` pinned via scalpel's `pyproject.toml`.
- Each scenario writes a JSONL trace of MCP tool calls to `/test/e2e/traces/<scenario>.jsonl` for post-mortem diff.
- Post-refactor snapshots regenerated with `pytest --snapshot-update`.

---

## 13. Risks (top 5 ranked across all four specialists)

Ranked by likelihood × blast radius.

### 13.1 R-MVP-1 — rust-analyzer cold-start UX regresses the first-user demo (HIGH × HIGH)

**From:** `specialist-rust.md` §R1.

**Symptom.** First facade call after MCP server spawn blocks for 30s–5min on a real-user workspace. LLM concludes tool is broken; agent retries with thrash; demo never recovers.

**Mitigation (MVP-required).** Tool-description text warns on every facade; `wait_for_indexing(timeout_s=300)` guard; progress logging to stderr; E7 promoted from nightly to MVP-gated; `indexing_ready: bool` in every `RefactorResult`. Combined, these prevent the silent-failure mode.

**Residual risk.** Real workspace > 5-minute timeout. Accepted: `failure: {kind: "indexing_timeout"}` with hint is better than silent hang; user retries on next turn.

### 13.2 R-MVP-2 — `LanguageStrategy` abstraction leak ships because pyright refuses useful refactors (HIGH × MEDIUM)

**From:** `specialist-scope.md` §4.3 residual risk.

**Symptom.** pyright's code-action surface is thinner than rust-analyzer's. If pylsp-rope hits unexpected limits on `calcpy`, Python MVP falls back to filesystem-based module moves computed entirely from CC's built-in `documentSymbol` — the facade's "no server-assist" branch becomes the *primary* Python path, not a fallback.

**Mitigation.** Pre-MVP spike §10.2 confirms pylsp-rope behavior early; if fails, pin known-good pylsp-rope version + force `didSave` before every code-action call. The "no server-assist" branch is designed as a first-class composition path in `LanguageStrategy.extract_module_strategy() == "composed"` (not a hidden fallback), so the degradation is explicit.

**Residual risk.** Design framing shifts from "validates strategy seam across two LSPs" to "validates seam plus no-LSP-help fallback". Still valuable — Go and TS will use the same fallback path — but slightly smaller win.

### 13.3 R-MVP-3 — `calcrs` proc-macro gap masks real-world failures (HIGH × MEDIUM)

**From:** `specialist-rust.md` §R2.

**Symptom.** `calcrs` is otherwise proc-macro-free (zero crates.io deps for determinism). MVP E2E gates pass. User installs scalpel against a `tokio`-based codebase. `plan_file_split` returns wrong clusters because `references` doesn't see proc-macro-generated trait method calls. User reports "the planner doesn't understand my code".

**Mitigation.** Add minimal `serde::{Serialize, Deserialize}` derive to `calcrs` (per §4.8 resolution). Promote `with_macros.rs` integration fixture from nightly to MVP-gated (`specialist-rust.md` §7.3). Confirms proc-macro pathway before ship.

**Residual risk.** `serde` derives are the most common Rust proc-macro but not the most complex. `tokio::main`, `async-trait`, `clap::Parser` have different expansion shapes. Accepted: MVP covers the most common case; v1.1 adds tokio-based integration fixture.

### 13.4 R-MVP-4 — pylsp-rope single-maintainer supply-chain (MEDIUM × HIGH long-term)

**From:** `specialist-python.md` §7.4.

**Symptom.** pylsp-rope's GitHub contributor graph is heavily dominated by one maintainer. Breaking change in pylsp plugin API bricks scalpel's Python strategy.

**Mitigation.** Pin pylsp and pylsp-rope to exact versions in scalpel's `pyproject.toml`. Integration test asserts advertised `codeActionKinds` at startup. Fallback: drive Rope directly as a library when plugin API breaks (Rope itself has more contributors). Post-v1: vendor pylsp-rope as submodule and maintain fork (same model as Serena).

**Residual risk.** Low short-term. Long-term vendoring is inevitable but cheap when triggered.

### 13.5 R-MVP-5 — `multilspy` doesn't expose `$/progress` cleanly (LOW × HIGH)

**From:** `specialist-rust.md` §R7.

**Symptom.** The design assumes `solidlsp` can listen for `$/progress rustAnalyzer/Indexing`. If `multilspy` swallows server-initiated notifications below the `solidlsp` API level, `wait_for_indexing()` is un-implementable; we fall back to "sleep N seconds and hope" and §13.1 (R-MVP-1) silently regresses.

**Mitigation.** Pre-MVP spike §10.1 verifies this before Stage 1 API freezes. On failure: file upstream bug + add ~40-LoC notification-tap shim in `solidlsp/lsp_protocol_handler/server.py`.

**Residual risk.** Multilspy upstream evolution may break the shim. Accepted: owning a 40-LoC shim is cheaper than owning the cold-start UX regression.

### 13.6 Risks rolled into above

- Rust-specific risks R3 (two-target-dir surprises), R4 (`extract_module` private-field edge case), R5 (`ContentModified` cascade), R6 (marketplace version skew), R8 (proc-macro crash), R9 (edition 2024), R10 (`move_module_to_file` doesn't rewrite all `mod` declarations): all have mitigations documented in `specialist-rust.md` §5 and are covered by existing MVP provisions.
- Python-specific risks 7.2 (virtualenv), 7.3 (Rope performance on monorepos), 7.5 (`TYPE_CHECKING`), 7.6 (pyright/basedpyright drift), 7.7 (four LSP processes on low RAM), 7.8 (PEP 420), 7.9 (mypy cache false positives), 7.10 (Rope 3.13 syntax lag): mitigations in `specialist-python.md` §7 and `specialist-python.md` §3.11.
- Agent-UX risks from `specialist-agent-ux.md` §13 are open questions, not risks — see §14.

---

## 14. Open Questions still unresolved

These are genuinely open after this synthesis round and do not block MVP start; they block specific Stage exits where noted.

### 14.1 Pyright vs. pylsp — Python secondary LSP choice

**Status.** Default basedpyright (fork of pyright, community-maintained) per §4.3. Alternative: Microsoft pyright upstream. Some users prefer upstream; others prefer the re-implemented Pylance features in basedpyright. `specialist-python.md` §10.5 raises this without resolving.

**Resolution trigger.** Config knob `scalpel.lsp.python.secondary = {"basedpyright" | "pyright" | "none"}` shipped in v1.1 if telemetry shows either material preference.

### 14.2 `fix_imports` Python aggressiveness — native vs. `ruff --fix` shell-out

**Status.** `specialist-python.md` §10.6 asks whether `fix_imports` should shell out to `ruff --fix` when it detects a Python project, or replicate via pylsp-rope code actions. MVP: pylsp-rope only. No resolution on whether ruff integration is worth the install cost.

**Resolution trigger.** v1.1 spike on `calcpy` fixture timing; if pylsp-rope organize < 3s wall-clock, stay pylsp-rope; if slower, add ruff fallback.

### 14.3 Preview-token TTL tuning

**Status.** 5 minutes is a guess (`specialist-agent-ux.md` §13.3). Real LLM turn-duration distributions during MVP will inform correct value.

**Resolution trigger.** Collect `preview_token → commit` elapsed-time distribution during MVP E1/E2 runs; adjust to p99 × 1.5 if distributions suggest 5 minutes is too short or too long.

### 14.4 Rollback eviction signaling

**Status.** MVP collapses `CHECKPOINT_EVICTED` into `NOT_APPLICABLE` with message "checkpoint not found" (§3.7, `specialist-agent-ux.md` §5.6). `CHECKPOINT_EVICTED` stays as v1.1 separate code if LLM confusion surfaces.

**Resolution trigger.** MVP telemetry on `NOT_APPLICABLE` responses where `failure.reason.startswith("checkpoint_id not found")` — if >5% of `NOT_APPLICABLE` hits are this case and LLMs mishandle, split the code in v1.1.

### 14.5 `calcrs` baseline line-ending handling across CI runners

**Status.** `cargo test` output has timing fields that must be elided; the elision regex is not yet authored (`specialist-scope.md` §12.5). Not blocking Stage 1 but must be solved before Stage 3.

**Resolution trigger.** Stage 3 author the regex, validate against Linux and macOS `cargo test` outputs of `calcrs` baseline.

### 14.6 TypeScript paper design review

**Status.** `TypeScriptStrategy` paper-only at MVP per §3.3; paper design does not yet exist. `specialist-scope.md` §2.4 requires it as a review gate before Stage 3 facade merge.

**Resolution trigger.** Stage 2 → Stage 3 transition. Paper design (≤ 500 words) walks `ts-server`'s code-action surface through the revised `LanguageStrategy` Protocol; any Protocol method that forces the paper to lie blocks Stage 3 merge until Protocol is amended.

### 14.7 Second `LanguageStrategy` registration discovery mechanism

**Status.** Static dict at MVP; entry-points deferred to v2+ per §3.3. No concrete v2 timeline; contribution-request-driven.

**Resolution trigger.** First third-party contribution of a strategy. No pre-work.

### 14.8 Strict-mode `allow_partial` semantics

**Status.** `split_file(allow_partial=False)` is default strict (atomic, rollback on any `new_errors`). `allow_partial=True` is v1.1 per `specialist-rust.md` §2.3. Semantics of partial apply across a composition are unclear for Python (if `MoveGlobal` succeeds on 3 of 4 symbols, what does "partial" mean — commit 3 or rollback all?).

**Resolution trigger.** v1.1 design round. Not MVP.

### 14.9 Anthropic native LSP-write deprecation path

**Status.** Tracked at [anthropics/claude-code#24249](https://github.com/anthropics/claude-code/issues/24249), [#1315](https://github.com/anthropics/claude-code/issues/1315), [#32502](https://github.com/anthropics/claude-code/issues/32502). Q11 deprecation plan exists. MVP-orthogonal.

**Resolution trigger.** When Anthropic ships native LSP-write, scalpel v2.0-deprecated tag + maintenance-only banner per Q11.

### 14.10 `plan_file_split` v1.1 re-introduction criteria

**Status.** Absorbed at MVP per §4.2. Re-introduction criterion is "MVP telemetry shows LLM wastes ≥2 dry-runs converging on good grouping" (`specialist-agent-ux.md` §6.5). No instrumentation on `dry_run` sequences exists at MVP.

**Resolution trigger.** Stage 3 E2E harness records `preview_token → commit` call counts per session; post-MVP analysis decides v1.1 inclusion.

### 14.11 Specialist disagreement that could not be fully reconciled

**E7 gating.** `specialist-rust.md` §7.2 promotes E7 (cold-start UX) from nightly to MVP-gated as the single largest MVP risk. `specialist-scope.md` §2.9 defers E7 to v1.1 because `wait_for_indexing()` logic lives in MVP code and an explicit E7 scenario measurement can wait. **Synthesis resolved in Rust specialist's favor** (§4.10); scope specialist's argument that logic-without-E2E is sufficient is structurally valid but the Rust specialist's first-user-experience argument prevails. This disagreement is surfaced as an open question: if Stage 3 CI timing for E7 proves onerous (>60s wall-clock per run), revisit and fall back to a lighter "indexing_ready observed in one `RefactorResult` trace" assertion in lieu of a full cold-start scenario.

---

## 15. References

- Main design report: [`../2026-04-24-serena-rust-refactoring-extensions-design.md`](../2026-04-24-serena-rust-refactoring-extensions-design.md)
- Open-questions resolution: [`../2026-04-24-o2-scalpel-open-questions-resolution.md`](../2026-04-24-o2-scalpel-open-questions-resolution.md)
- Rust specialist brainstorm: [`specialist-rust.md`](specialist-rust.md)
- Python specialist brainstorm: [`specialist-python.md`](specialist-python.md)
- Agent-UX specialist brainstorm: [`specialist-agent-ux.md`](specialist-agent-ux.md)
- Engineering-scope specialist brainstorm: [`specialist-scope.md`](specialist-scope.md)
- Research briefs (from main design Appendix D):
  - [`../../research/2026-04-24-rust-analyzer-capabilities-brief.md`](../../research/2026-04-24-rust-analyzer-capabilities-brief.md)
  - [`../../research/2026-04-24-mcp-lsp-protocol-brief.md`](../../research/2026-04-24-mcp-lsp-protocol-brief.md)
  - [`../../research/2026-04-24-dx-facades-brief.md`](../../research/2026-04-24-dx-facades-brief.md)
  - [`../../research/2026-04-24-plugin-extension-surface-brief.md`](../../research/2026-04-24-plugin-extension-surface-brief.md)
  - [`../../research/2026-04-24-cache-discovery-brief.md`](../../research/2026-04-24-cache-discovery-brief.md)
  - [`../../research/2026-04-24-two-process-brief.md`](../../research/2026-04-24-two-process-brief.md)
  - [`../../research/2026-04-24-marketplace-brief.md`](../../research/2026-04-24-marketplace-brief.md)
  - [`../../research/2026-04-24-license-rename-brief.md`](../../research/2026-04-24-license-rename-brief.md)
- External specs/libraries:
  - [Language Server Protocol 3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
  - [multilspy (Microsoft)](https://github.com/microsoft/multilspy)
  - [platformdirs](https://github.com/platformdirs/platformdirs)
  - [python-lsp/python-lsp-server](https://github.com/python-lsp/python-lsp-server)
  - [python-rope/pylsp-rope](https://github.com/python-rope/pylsp-rope)
  - [python-rope/rope](https://github.com/python-rope/rope)
  - [DetachHead/basedpyright](https://github.com/DetachHead/basedpyright)
  - [rust-analyzer assist registry](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide-assists/src/lib.rs)
  - [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/)
  - [Plugin marketplaces (Claude Code)](https://code.claude.com/docs/en/plugin-marketplaces)

---

**End of report.**
