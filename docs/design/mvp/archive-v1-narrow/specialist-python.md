# Specialist report — Python strategy for o2.scalpel MVP

Status: report-only. No implementation.
Audience: the MVP orchestrator merging the Rust + Python specialist outputs into a unified v1 scope.
Cross-reference: [main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) §§3 (facades), §5 (LanguageStrategy), §Open Questions #7 (second strategy to validate the abstraction); [open-questions resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) §Q12 (two-process tax — Python bullet).

Date: 2026-04-24. Author: AI Hive(R), Python specialist.

---

## Executive summary

| # | Decision | Confidence |
|---|----------|------------|
| 1 | **Primary Python LSP for scalpel's write path: `pylsp` + `pylsp-rope` + `pylsp-mypy`.** It is the only Python LSP today that emits LSP-spec `refactor.*` code actions with `WorkspaceEdit` payloads end-to-end — including `CreateFile` on rename-module. Fallback: `basedpyright` (read-only + `source.organizeImports` + auto-import code actions; no `refactor.extract`). | high |
| 2 | **Python equivalent of `split_file_by_symbols` is a composition, not a single assist.** Rope has `MoveGlobal` and `create_move`, but neither pylsp-rope nor any other Python LSP exposes a "split file into N submodules" action. Scalpel composes: (1) create target `foo.py` with stub, (2) per symbol run pylsp-rope's `MoveGlobal` via `workspace/executeCommand`, (3) Rope rewrites every importer automatically, (4) add `from .foo import Symbol` re-exports in `__init__.py` if policy requires. Five turns, same shape as Rust. | medium |
| 3 | **`LanguageStrategy` answers for Python** are cleaner than Rust: no `mod foo;` declarations (filesystem is the module system), no `mod.rs` dichotomy (there is only `package/__init__.py` vs. `module.py`). The Rust-flavored enum `parent_module_style: {"dir","mod_rs"}` does not map. Proposed language-neutral name: `module_layout_style: {"package","single_file"}` (`dir`→`package`, `mod_rs`→this does not exist in Python; `single_file`→`.py` next to siblings). | high |
| 4 | **Pitfalls the Rust specialist does not flag**: virtualenv discovery, star imports (`from foo import *` hides the move-graph from Rope), `__init__.py` side effects, PEP 420 namespace packages, `.pyi` stub drift, circular imports that worked before a move and break after, implicit relative imports (Python 2 legacy still lurking in corpora). Each requires specific facade behavior (§5). | high |
| 5 | **Abstraction pressure on the design**: three Rust-jargon artifacts in §3/§5 do not map — `parent_module_style: {"dir","mod_rs"}`, `reexport_policy: "preserve_public_api"` (Rust `pub use`, Python `__all__`), and `extract_module` as the canonical kind. Facades must accept a language-neutral enum and let the strategy translate. Rename recommendations in §6. | high |
| 6 | **Testing fixture `calcpy`** — 900-LoC single-module arithmetic evaluator, stdlib-only, exercises star-import trap + `_private` visibility + nested class tree that wants clustering + a circular-import trigger. Layout and expected-state fixtures in §7. | high |
| 7 | **Top three Python risks** to MVP scope: (a) pylsp-rope's experimental status on unsaved buffers (§1 & §9), (b) the virtualenv-discovery mess when the agent's project root is ambiguous (§4.1), (c) Rope's performance on 10k-file monorepos — which is outside MVP scope for Python but users will try it anyway. Mitigations in §9. | medium |

**Ship recommendation for MVP.** Adopt the primary + fallback pairing. The write facades work by driving pylsp-rope through `workspace/executeCommand`; the read facades (`plan_file_split` in particular) can fall back to basedpyright + Rope-as-a-library when pylsp-rope isn't running. Require the Python strategy to pass scenarios E1–E3, E6, E9 (adapted to `calcpy`) before the MVP tag.

---

## 1. Which Python LSP should scalpel target?

### 1.1 The shortlist

| Server | Binary | LoC shape | GitHub stars (Apr 2026) | Maintained? | Language | Upstream |
|---|---|---|---|---|---|---|
| **`pylsp` / python-lsp-server** | `pylsp` | ~30k Python | ~2.5k | Yes (Spyder team + community) | Python | [python-lsp/python-lsp-server](https://github.com/python-lsp/python-lsp-server) |
| **`pyright`** (Microsoft) | `pyright-langserver` | ~250k TS | ~15k | Yes (MS) | TypeScript (Node) | [microsoft/pyright](https://github.com/microsoft/pyright) |
| **`basedpyright`** (DetachHead fork) | `basedpyright-langserver` | ~250k TS (fork) | ~3.3k (114 forks) | Yes (active) | TypeScript (Node) | [DetachHead/basedpyright](https://github.com/DetachHead/basedpyright) |
| **`jedi-language-server`** | `jedi-language-server` | ~3k Python | ~800 | **Maintenance mode** (upstream recommends Zuban) | Python | [pappasam/jedi-language-server](https://github.com/pappasam/jedi-language-server) |
| **`ruff server`** (native) | `ruff server` | ~200k Rust | ~40k (ruff itself) | Yes (Astral, very active) | Rust | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **`pyrefly`** (Meta) | `pyrefly lsp` | ~100k Rust | growing | Yes (Meta) | Rust | [facebook/pyrefly](https://github.com/facebook/pyrefly) |

`ty` (Astral's new type checker + LSP) is explicitly out of scope for MVP — it was announced late 2025 and is pre-alpha per [astral.sh/blog/ty](https://astral.sh/blog/ty). Revisit post-v1.

### 1.2 Evaluation matrix

Columns are the five dimensions the MVP orchestrator asked for. A cell reads "what does this server actually emit when an MCP client asks for `refactor.extract.*` or `source.organizeImports` or auto-import?" Evidence links follow each cell; citations are primary (upstream repos, READMEs, PyPI project pages) wherever available.

| Dimension | `pylsp` + `pylsp-rope` | `pyright` | `basedpyright` | `jedi-language-server` | `ruff server` | `pyrefly` |
|---|---|---|---|---|---|---|
| **Extract function** (`refactor.extract.function`) | **Yes** — Rope via pylsp-rope command `pylsp_rope.refactor.extract.method` ([pylsp-rope README](https://github.com/python-rope/pylsp-rope)) | **No** — refactor assists are Pylance-only (closed source); open pyright does not expose them ([pylance-release #1262](https://github.com/microsoft/pylance-release/issues/1262), [pylance-release #6654](https://github.com/microsoft/pylance-release/issues/6654)) | **No** — refactor.extract is still Pylance-only; basedpyright re-implements auto-import and organize-imports only ([basedpyright changelog](https://docs.basedpyright.com/), [#896 lspconfig](https://github.com/neovim/nvim-lspconfig/issues/896)) | **Yes** — `refactor.extract` `extract_function`/`extract_variable` via Jedi ([jedi-language-server README](https://github.com/pappasam/jedi-language-server)) | **No** — ruff is lint+format only; no refactor assists ([ruff editors docs](https://docs.astral.sh/ruff/editors/)) | **Unclear** — pyrefly markets "advanced refactoring" but LSP capabilities list in [facebook/pyrefly](https://github.com/facebook/pyrefly) does not enumerate `refactor.extract.*` kinds as of Apr 2026 |
| **Extract variable** | Yes (Rope) | No | No | Yes (Jedi) | No | Unclear |
| **Extract method** | Yes (Rope) | Pylance-only (not open pyright) | Pylance-only feature not back-ported ([basedpyright v1.28 commands](https://docs.basedpyright.com/v1.28.1/configuration/language-server-settings/)) | Partial — Jedi has no "extract method" distinct from extract function | No | Unclear |
| **Extract module / move item to new file** | **Partial** — Rope's `MoveGlobal` + `create_move` exist as library calls; pylsp-rope exposes rename-module via the standard `textDocument/rename` path ([Rope library docs](https://rope.readthedocs.io/en/latest/library.html), [pylsp-rope plugin.py](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/plugin.py)) | No | No | No | No | No |
| **Rename symbol** (`textDocument/rename`) | Yes (Rope) | **Yes** — `textDocument/rename` works, the one refactor pyright reliably ships | Yes | Yes (Jedi rename) | No | Yes |
| **Organize imports** (`source.organizeImports`) | Yes (Rope `source.organize_import`) | Yes (`pyright.organizeimports`, [pyright commands.md](https://github.com/microsoft/pyright/blob/main/docs/commands.md)) | Yes (with `basedpyright.disableOrganizeImports` toggle) | Partial — via Jedi but implementation narrower | **Yes, strong** — `source.organizeImports` + `source.fixAll` are ruff's two code-action kinds | Unclear |
| **Auto-import** (`quickfix` on unresolved symbol) | Yes (Rope) | **No** — Pylance-only ([basedpyright docs](https://docs.basedpyright.com/v1.18.1/usage/commands/)) | **Yes** — basedpyright's main differentiator: re-implemented from Pylance | No | No (diagnostic-driven fix only, not symbol resolution) | Unclear |
| **`WorkspaceEdit` with `CreateFile`** | **Yes** on rename-module (Rope emits a `CreateFile` + edits to all importers) | Not emitted (no refactors need it) | Not emitted | Not emitted | Not emitted | Unknown |
| **`codeActionProvider.resolveProvider`** | Yes (via `pylsp` capabilities) | Yes | Yes | Yes | Yes | Yes |
| **Project detection** | `pyproject.toml`, `setup.py`, `setup.cfg`, `.git` ([pylsp config docs](https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md)) | `pyproject.toml [tool.pyright]`, `pyrightconfig.json` | same as pyright + `[tool.basedpyright]` | `pyproject.toml` via Jedi sys-path discovery | `pyproject.toml [tool.ruff]`, `ruff.toml`, `.ruff.toml` | `pyproject.toml`, `pyrefly.toml` |
| **Virtualenv discovery** | Plugin config `pylsp.plugins.jedi.environment` explicit; no heuristic auto-detect — **weak** ([neovim discourse thread](https://neovim.discourse.group/t/pylsp-pylint-configuration/2232)) | `python.pythonPath` (VSCode) / `venvPath` / `venv` in pyrightconfig; **weak** without client help | same as pyright | Jedi auto-detects `.venv/` sibling; moderate | N/A (no type info needed) | `pyrefly.toml` `python_executable` or `python_version` |
| **Bare scripts (no project)** | Works with pylsp defaults | Works | Works | Works | Works | Works |
| **GitHub stars (Apr 2026)** | ~2.5k | ~15k | ~3.3k | ~800 (archived-adjacent) | ~40k (ruff) | growing |
| **Maintenance cadence** | Healthy, monthly-ish releases | Fast, weekly | Fast fork, tracks pyright | **Maintenance mode** | Very active | Active (Meta-backed) |

### 1.3 The decision

**Primary: `pylsp` + `pylsp-rope` + `pylsp-mypy`.**

This is the only combination that satisfies o2.scalpel's write-path contract. Specifically:

1. **It emits `refactor.*` code actions with `WorkspaceEdit`-bearing responses.** pylsp-rope exposes nine commands — `pylsp_rope.refactor.extract.method`, `pylsp_rope.refactor.extract.variable`, `pylsp_rope.refactor.inline`, `pylsp_rope.refactor.local_to_field`, `pylsp_rope.refactor.method_to_method_object`, `pylsp_rope.refactor.use_function`, `pylsp_rope.refactor.introduce_parameter`, `pylsp_rope.quickfix.generate`, `pylsp_rope.source.organize_import` ([plugin.py](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/plugin.py)).
2. **Rename is built on Rope.** `textDocument/rename` on a module name moves the file and rewrites every import — exactly the `MoveModule` refactor scalpel needs for `split_file_by_symbols`.
3. **It supports the full 2-phase `codeAction` → `codeAction/resolve` dance** inherited from pylsp itself. Resolve exists; `WorkspaceEdit` includes `documentChanges` with `TextDocumentEdit` entries. `CreateFile` appears only on rename-module paths today (verify in integration tests).
4. **Rope-as-a-library is available.** When the LSP layer does not expose a refactor that Rope has, scalpel's Python strategy can drive Rope directly via `from rope.refactor.move import create_move` ([Rope library docs](https://rope.readthedocs.io/en/latest/library.html)). This preserves the §2 (main spec) principle that facades use LSP primitives where possible, but the pylsp-rope bridge is thin enough that dropping to the library is idiomatic when the LSP coverage has gaps.

**Fallback: `basedpyright`** for three cases where pylsp-rope is not available or returns an error:

1. **Auto-import**, which pylsp-rope supports but basedpyright's re-implemented Pylance path is faster and more accurate on large codebases (the Pylance heuristics have years of tuning; Rope's equivalent is narrower).
2. **Organize imports** when the user has configured `pyright.organizeimports` as their canonical sort order.
3. **Type-checking diagnostics** consumed by the `diagnostics_delta` field in `RefactorResult`. `basedpyright` emits far more precise diagnostics than pylsp + pylsp-mypy on modern typed code.

Scalpel's Python strategy should run `pylsp` (with `pylsp-rope` + `pylsp-mypy`) as the **primary** LSP and `basedpyright` as a **secondary read-only** LSP for the diagnostics-delta check. This is the Python analogue of the Rust strategy's "rust-analyzer + cargo check" pair. Two processes, both lightweight (~100–300 MB each), total well under the two rust-analyzer budget.

**Rejected and why:**

- **`pyright` alone** — no refactor-extract, no auto-import. Fails the §3 facade contract.
- **`jedi-language-server` alone** — extract-function/variable work, but no module-move, no Rope-grade rename. Plus the project is in maintenance mode (upstream README recommends successor `Zuban` — not ready for MVP).
- **`ruff server` alone** — lint and format only. Excellent complement but not a refactor server.
- **`pyrefly` as primary** — the refactoring story is documented in marketing copy; the LSP capability list in the repo as of Apr 2026 ([facebook/pyrefly](https://github.com/facebook/pyrefly)) does not yet enumerate the `refactor.extract.*` kinds scalpel needs. Strong candidate for v2 once the feature set hardens.

### 1.4 A concrete evidence table (what each server actually returns on a `codeAction` request)

Asking an MCP agent to pick an LSP on marketing copy is a regression hazard. What follows is the set of kinds each server advertises under `capabilities.codeActionProvider.codeActionKinds`, derived from source code and project docs. Treat it as the table to beat in integration tests.

| Server | `codeActionKinds` advertised | `resolveProvider` | Notes |
|---|---|---|---|
| `pylsp` (base) | `["quickfix", "source.organizeImports", "source.fixAll"]` | true | Expands with each registered plugin. |
| `pylsp` + `pylsp-rope` | base ∪ `["refactor.extract", "refactor.inline", "refactor", "source"]` — Rope registers under the `refactor.*` and `source` prefixes. | true | The published plugin registers broad prefixes; specific sub-kinds appear in the returned actions. |
| `pylsp` + `pylsp-mypy` | `["quickfix"]` (type-ignore insertions) | true | Additive. |
| `pyright` | `["source.organizeImports", "quickfix"]` | true | `quickfix` is narrow — mostly "create missing return" etc. |
| `basedpyright` | `["source.organizeImports", "quickfix", "quickfix.imports"]` | true | `quickfix.imports` is the re-imported-Pylance auto-import path. |
| `jedi-language-server` | `["refactor.extract", "refactor.inline"]` | true | Narrow but real. |
| `ruff server` | `["source.organizeImports", "source.fixAll", "quickfix"]` | true | Strongest on `source.fixAll` (rule-driven autofix). |
| `pyrefly` | (TBD — check `initialize` response in integration tests) | true | Treat as unknown until we have a live probe. |

**Integration-test contract:** scalpel's Python strategy must assert these sets at server startup in a `test_capability_parity.py`. If a future pylsp-rope release narrows its advertised kinds, we want the test to fail loudly. Mirror of the Rust strategy's `assert rust_analyzer_kinds >= expected`.

### 1.5 Capability gaps vs. the Rust strategy

For a row-by-row comparison, the Python LSP write-path is narrower than rust-analyzer's in two specific ways:

| Rust (rust-analyzer) | Python (pylsp + pylsp-rope) | Impact on facades |
|---|---|---|
| `extract_module` (creates inline `mod foo { … }`) + `move_module_to_file` (emits `CreateFile`) | No native "extract module". `MoveGlobal` moves one symbol at a time. | `split_file_by_symbols` must loop `MoveGlobal` per symbol or create the file out-of-band. See §2. |
| 158 assists enumerated | ~9 pylsp-rope commands + pylsp base | Python facades have a thinner primitive catalog. |
| `experimental/ssr` (structural search-replace) | None | `fix_imports` cannot lean on server-side SSR — must use Rope directly. |
| `rust-analyzer/runFlycheck` | None equivalent. `pylsp-mypy` runs on `didChange` only. | Post-refactor diagnostics come from `basedpyright` + `pylsp-mypy` passive flow. |

These are acceptable gaps. The §3 facades can absorb them because they never committed to a specific code-action kind — only to the language-neutral contract `split_file_by_symbols(file, groups, …) -> RefactorResult`. The Python strategy's job is to translate that contract into whatever Rope composition makes it happen.

---

## 2. Python equivalent of the 5-turn split-file workflow

### 2.1 What rust-analyzer does, what Python does instead

The main spec §Workflow walks through a 5-turn refactor:

1. **Plan** (`plan_file_split`) — read-only analysis.
2. **Dry-run split** (`split_file_by_symbols` with `dry_run=true`).
3. **Commit split** (`dry_run=false`).
4. **`fix_imports`** crate-wide.
5. **Verify** via `cargo check` / `rust-analyzer/runFlycheck`.

For the Rust pipeline, step 3 decomposes into `extract_module` → `move_module_to_file` per group. **Python has no equivalent sequence built into any LSP.** The Python pipeline must compose:

1. `documentSymbol(file)` — enumerate top-level items (functions, classes, constants).
2. For each group `(module_name, symbols)`:
   a. Create empty `module_name.py` next to the source file (or inside the parent package directory).
   b. Compute parent module path (`pkg.module_name`).
   c. For each `symbol` in the group, run Rope's `MoveGlobal(project, resource, offset, dest)` — Rope moves the symbol and rewrites every importer in the project.
   d. If `reexport_policy == "preserve_public_api"`, append `from .module_name import Symbol` to the parent package's `__init__.py`.
3. Organize imports on every touched file (`pylsp_rope.source.organize_import`).
4. Diagnostics-delta: run `basedpyright` on changed files, count errors before vs. after.
5. Checkpoint-based rollback if the delta is positive in strict mode.

**The critical composition insight:** in Rust, `move_module_to_file` emits the `CreateFile` atomically with the `TextDocumentEdit` that inserts `mod foo;` in the parent. In Python, **the client must create the file first**, then call `MoveGlobal`, because Rope's `MoveGlobal` requires a destination resource that already exists. The Python strategy's `split_file_by_symbols` implementation owns this ordering.

### 2.2 End-to-end walk-through (pseudo-JSON, 5 turns)

Target: `calcpy/calcpy.py` (~900 LoC — see §7 fixture design).

**Turn 1 — understand the file.**

```json
{"tool": "plan_file_split",
 "args": {"file": "calcpy/calcpy.py",
          "strategy": "by_cluster", "max_groups": 4}}
```

The Python strategy's implementation of `plan_file_split`:

1. Calls `textDocument/documentSymbol` on pylsp.
2. For each top-level symbol, calls `textDocument/references` (or `callHierarchy/incomingCalls` where pylsp supports it).
3. Builds a symbol-reference graph.
4. Runs label-propagation clustering (same algorithm the main spec §Open Question #1 picks for Rust — language-neutral).
5. Groups → 4 suggested modules `{ast, errors, parser, evaluator}`.

Response shape is identical to Rust's (same `PlanResult` schema, same `SuggestedGroup`, same `CrossEdge`). That is the whole point of the language-neutral facade.

**Turn 2 — dry-run the split.**

```json
{"tool": "split_file_by_symbols",
 "args": {"file": "calcpy/calcpy.py",
          "groups": {
            "ast":       ["Expr", "BinaryOp", "UnaryOp", "Value"],
            "errors":    ["CalcError", "ParseError", "RuntimeError"],
            "parser":    ["parse", "tokenize", "Token"],
            "evaluator": ["evaluate", "apply_binary", "apply_unary"]},
          "keep_in_original": ["run", "VERSION"],
          "module_layout_style": "package",
          "reexport_policy": "preserve_public_api",
          "dry_run": true}}
```

Note the enum value **`package`** — language-neutral rename of Rust's `dir` (see §5 for rationale). The Python strategy translates `package` to "create `calcpy/` directory, convert `calcpy.py` to `calcpy/__init__.py`, create sibling `ast.py`/`errors.py`/`parser.py`/`evaluator.py`".

The Python strategy's dry-run implementation:

1. Snapshots buffer state.
2. Runs the composition against a scratch Rope project copy (Rope supports `ChangeSet.get_changes()` without applying).
3. Serializes the resulting Rope `ChangeSet` as a `WorkspaceEdit` (list of `TextDocumentEdit` + one `CreateFile` per group).
4. Runs `basedpyright` on the would-be files in a temp dir.
5. Returns `RefactorResult` with `applied: false`.

Example response (abridged):

```json
{"applied": false,
 "changes": [
    {"path": "calcpy/__init__.py", "kind": "create", "hunks": [...]},
    {"path": "calcpy/ast.py",      "kind": "create", "hunks": [...]},
    {"path": "calcpy/errors.py",   "kind": "create", "hunks": [...]},
    {"path": "calcpy/parser.py",   "kind": "create", "hunks": [...]},
    {"path": "calcpy/evaluator.py","kind": "create", "hunks": [...]},
    {"path": "calcpy/calcpy.py",   "kind": "delete", "hunks": []}
 ],
 "diagnostics_delta": {"before": 0, "after": 2,
                       "new_errors": ["evaluator.py:17: 'tokenize' is not exported from 'parser'"]},
 "checkpoint_id": null,
 "resolved_symbols": [...],
 "warnings": ["star-import detected in calcpy.py; post-split consumers may break"]}
```

The star-import warning is a Python-specific output the strategy must produce. Rust doesn't have this problem.

**Turn 3 — adjust and commit.** LLM flips `reexport_policy: "explicit_list"`, sets `explicit_reexports: ["parser.tokenize"]`, flips `dry_run: false`. Response: `applied: true`, `checkpoint_id: "ckpt_py_3c9"`, `diagnostics_delta: {before: 0, after: 0}`.

**Turn 4 — tidy imports package-wide.**

```json
{"tool": "fix_imports",
 "args": {"files": ["calcpy/**.py"]}}
```

The Python strategy's `fix_imports` implementation:

1. For each file, request `codeAction` with `only: ["source.organizeImports"]`.
2. pylsp-rope returns a `WorkspaceEdit` that sorts imports and groups them (stdlib → third-party → local).
3. Apply.
4. Second pass: request `only: ["quickfix"]` filtered for auto-import diagnostics; run any remaining unresolved-import quickfixes from basedpyright.

**Turn 5 — verify.**

Two verification paths:

- `python -m py_compile calcpy/**.py` — cheap syntax check. Every file must parse.
- `python -m pytest calcpy/tests/` — the fixture's own test suite. If the baseline passes before refactor, it must pass byte-identical after.

Neither is part of the MCP surface; they are external to scalpel (mirrors the Rust strategy's `cargo check` convention). Scalpel's job is the `diagnostics_delta` pre-check; the user owns the final compile/test gate.

### 2.3 Does Python have `extract_module`?

**Short answer: no, not as a single atomic LSP action.**

- Rope has `MoveGlobal` (one symbol at a time) and a `Restructuring` engine. It does not have a "take N symbols, create a new module, wire everything up" operation.
- pylsp-rope exposes neither an `extract_module` code action nor a `move_module` code action.
- basedpyright / pyright / jedi-language-server have nothing in this space.

**The Python analogue of `extract_module` + `move_module_to_file` is:**

```
create_file(target) → MoveGlobal(symbol_1) → … → MoveGlobal(symbol_N) → organize_imports
```

This is a pure composition at scalpel's facade layer, exactly the same shape as Rust's `extract_module` → `move_module_to_file` → `didChange` → `rename`. The LLM never sees the decomposition — it calls `split_file_by_symbols` with a `groups` dict and the strategy does the rest.

### 2.4 `move_module_to_file` equivalent

In Rust, `move_module_to_file` takes an inline `mod foo { … }` and turns it into `foo.rs` + `mod foo;` in the parent. Python has **no inline module** concept — modules are files on disk. The Rust facade `move_inline_module_to_file` (§3.4 in the main spec) has no meaningful Python analogue.

**Proposed facade behavior:** on Python, `move_inline_module_to_file` returns `failure: {kind: "not_applicable", hint: "Python has no inline modules; use split_file_by_symbols instead"}`. The `LanguageStrategy.move_to_file_kind() -> str | None` hook in the main spec §5 already has the `None` escape hatch for exactly this case.

### 2.5 Aside: `rename` is a full-range operation

Rope's rename is the one place where a single LSP call does heavy lifting comparable to rust-analyzer:

- `textDocument/rename` on a function, class, or module name → Rope scans the project, rewrites every `import`, every callsite, every attribute access.
- On a **module** name specifically, Rope renames the file on disk — emitting a `WorkspaceEdit` with `RenameFile` + `TextDocumentEdit`s across every importer.

This gives scalpel a free primitive for the post-split rename-to-user-chosen-name step (main spec §3.2 step 3). The Python strategy should use `textDocument/rename` whenever the generated module name differs from the caller-supplied one, same as Rust.

---

## 3. `LanguageStrategy` answers for Python

Mapping onto the Protocol in main spec §5. One row per method.

### 3.1 `extract_module_kind() -> str`

**Python: `"refactor.rewrite"`** (pylsp-rope registers move operations under the broad `refactor` prefix; the specific command is `pylsp_rope.refactor.use_function` or driven via Rope library directly — see §1.2). There is **no single kind string that uniquely identifies "extract module"** in pylsp-rope because it is not a first-class assist.

Implication for the design: the method name `extract_module_kind` is Rust-flavored. It assumes every language has a single code-action kind that creates a new module. Python breaks this assumption. Proposed fix in §5.

### 3.2 `move_to_file_kind() -> str | None`

**Python: `None`.** No LSP assist named this. The strategy handles the composition itself.

### 3.3 `rename_kind() -> str`

**Python: `"refactor.rewrite"`** or **not applicable** — `textDocument/rename` is not a code action, it is a top-level LSP method. This method name in the Protocol assumes rename goes through the code-action machinery. It does not on most servers.

Implication: `rename_kind()` is redundant for languages where rename is a first-class method. Propose deprecating it from the Protocol or repurposing it as `rename_preflight_kind()` for languages that only expose rename via code actions (rare).

### 3.4 `module_declaration_syntax(module_name, style) -> str`

**Python has no module declaration.** The filesystem is the module system. The function can return:

- `style == "package"` → `""` (nothing; the existence of `module_name/__init__.py` is sufficient).
- `style == "single_file"` → `""` (the existence of `module_name.py` is sufficient).

Or, if we reinterpret the method to mean "the import statement callers write to use this module", then:

- `style == "package"` → `"from .{parent}.{module_name} import …"` with the specifics decided by `reexport_syntax` (§3.6).
- `style == "single_file"` → same shape.

**Recommendation:** split the method in §5 into two: `module_declaration_syntax` (produces the `mod foo;` sort of glue, returns `None` for Python) and `importer_syntax` (produces the `from X import Y` sort of glue, which is what every language has).

### 3.5 `module_filename_for(module_name, style) -> Path`

- `style == "package"` → `Path(module_name) / "__init__.py"`.
- `style == "single_file"` → `Path(f"{module_name}.py")`.

Note: PEP 420 namespace packages (no `__init__.py`) are a third style. MVP ignores them — scalpel only creates regular packages. A fourth `style == "namespace_package"` enum value could be added post-MVP; for the v1 it is a documented limitation.

### 3.6 `reexport_syntax(symbol) -> str`

Rust's `pub use foo::Bar;` has three Python analogues; the strategy must pick one based on a second argument.

| Python idiom | Rendering | When to use |
|---|---|---|
| Explicit re-import | `from .foo import Bar` (appended to `__init__.py`) | Default. Works with every consumer. |
| `__all__` extension | Append `"Bar"` to `__all__` in `__init__.py` (already imported above) | When the package has an existing `__all__` and the policy requires it. |
| Star re-export | `from .foo import *` | Legacy; **scalpel should never emit this** — it hides the move-graph and breaks future refactors. |

**Proposal: add a `reexport_style` parameter to `split_file_by_symbols`** with values `"explicit"` (default), `"__all__"`, and `"none"`. Maps to `reexport_policy` in the current §3.2 signature. Python strategy's implementation picks the idiom; Rust strategy ignores the parameter.

### 3.7 `is_top_level_item(symbol) -> bool`

Python definition: a symbol is top-level if its `containerName` is the module itself (no parent class or function). Filter out:

- Decorator-generated items (they appear as top-level but are bound indirectly).
- `if __name__ == "__main__":` guarded assignments (still top-level symbol-wise, but moving them across files is almost always wrong — warn).
- Items starting with `_` when `reexport_policy == "preserve_public_api"` (they are private by convention; the strategy must preserve private-ness).

### 3.8 `symbol_size_heuristic(symbol) -> int`

LoC of the symbol's range from `documentSymbol`. Same as Rust. Python's `DocumentSymbol.range` is reliable for this.

### 3.9 `execute_command_whitelist() -> frozenset[str]`

Minimum viable set for MVP:

```python
{"pylsp_rope.refactor.extract.method",
 "pylsp_rope.refactor.extract.variable",
 "pylsp_rope.refactor.inline",
 "pylsp_rope.source.organize_import",
 "pylsp_rope.refactor.use_function"}
```

Plus basedpyright's relevant commands if the secondary LSP is live:

```python
{"basedpyright.organizeimports",
 "basedpyright.restartserver"}
```

(Pyright's `pyright.createtypestub`, `pyright.addoptionalforparam` etc. are not on the refactor hot path — omit for v1.)

### 3.10 `post_apply_health_check_commands() -> list[ExecuteCommand]`

Python has no direct `cargo check` equivalent. Options:

1. `basedpyright` diagnostics (already flowing via `textDocument/publishDiagnostics`).
2. `pylsp-mypy` diagnostics (same channel).
3. External `python -m py_compile <file>` — cheap but fork-exec cost per call.

**Recommendation:** return `[]` — rely on the passive diagnostic stream. The `diagnostics_delta` field in `RefactorResult` is populated from `publishDiagnostics` aggregation across both LSPs; no explicit post-apply command needed.

### 3.11 `lsp_init_overrides() -> dict` (per main spec §Two-LSP-process problem)

Python's bullet in that section says "no on-disk artifacts; safe". Correct — but we want to be explicit about a few environment sticky points:

```python
{
  "pylsp": {
    "plugins": {
      "pylsp_mypy": {"enabled": True, "live_mode": False},
      "pylsp_rope": {"enabled": True},
      "jedi": {"environment": "<auto-detect>"},
      "rope_autoimport": {"enabled": True, "memory": True},
    }
  },
  "python": {
    "venvPath": "<project-root>/.venv",  # fallback if no explicit config
  }
}
```

`pylsp_mypy.live_mode: False` — important. Live mode re-runs mypy on every `didChange`, which will race with scalpel's apply. We run mypy on-demand after apply.

`jedi.environment` — scalpel resolves this from (a) `pyproject.toml [tool.o2-scalpel] python_executable`, (b) the `VIRTUAL_ENV` env var if set, (c) the first `.venv/bin/python` found walking up from project root, (d) `sys.executable`. Failure to resolve is a loud error (same shape as the main spec's fail-loud discipline).

### 3.12 Summary: Python strategy fits the abstraction with three friction points

The Protocol in main spec §5 is mostly a clean fit. Three friction points:

1. `extract_module_kind` and `rename_kind` assume every language has a single code-action kind for these. False for Python. Split into sub-methods or make them optional.
2. `module_declaration_syntax` assumes a `mod foo;`-like glue. Python has no such thing. Split into the `mod`-glue (None on Python) and the importer-glue (a `from X import Y` line).
3. `parent_module_style: {"dir", "mod_rs"}` leaks Rust jargon. See §5.

Everything else maps. The Python strategy is a small file (~250 LoC estimated, on par with the Rust strategy's ~180 LoC in the main spec Effort table).

---

## 4. Pitfalls the Rust specialist will not flag

Tabulated; each row lists the pitfall, what it breaks, and the mitigation scalpel's Python strategy should carry.

### 4.1 Virtualenv / interpreter discovery

**What goes wrong:** pylsp spawns, tries to resolve `import numpy` against the wrong Python interpreter, reports `unresolved import: numpy` for every scientific codebase. The user's `.venv` is ignored because pylsp was started from a shell that didn't activate it.

**Scalpel's reality:** scalpel spawns pylsp via `uvx` or similar. The spawn environment is whatever inherited from Claude Code, which is whatever inherited from the user's login shell. None of this is guaranteed to be the project's venv.

**Mitigation chain (same shape as main spec §Q10 for cache paths):**

1. `$O2_SCALPEL_PYTHON_EXECUTABLE` — full override.
2. `[tool.o2-scalpel] python_executable` in `pyproject.toml`.
3. `VIRTUAL_ENV` env var if set.
4. `.venv/bin/python` walking up from the project root (most projects).
5. `venv/bin/python` fallback.
6. `poetry env info -p` if `poetry.lock` present.
7. `pdm info --packages` if `pdm.lock` present.
8. `uv run which python` if `uv.lock` present.
9. Conda: `$CONDA_PREFIX/bin/python` if set.
10. `sys.executable` of the scalpel process (last resort — likely wrong but deterministic).
11. Fail loud with the full attempted chain.

Once resolved, pass as `jedi.environment` and `pylsp-mypy.overrides` in the init options.

**Reference:** [VSCode Python environments docs](https://code.visualstudio.com/docs/python/environments) explains the same chain for VSCode; scalpel replicates the core ideas but makes the chain explicit for agent debugging. The [neovim discourse thread](https://neovim.discourse.group/t/pylsp-pylint-configuration/2232) confirms "no mature solution yet" — this is genuinely ecosystem-wide.

### 4.2 Star imports hide the move graph

**What goes wrong:** `from calcpy import *` in a consumer file. Scalpel moves `calcpy.tokenize` to `calcpy.parser.tokenize`. Rope's `MoveGlobal` rewrites explicit `from calcpy import tokenize` but **cannot rewrite `*`** — it doesn't know that `tokenize` is among the symbols pulled in. Consumer breaks at runtime.

**Mitigation:** pre-flight scan for `from <target_module> import *` across the project. If found, return a warning `"star_import_hides_moves"` in the dry-run output and require explicit `allow_star_imports=True` to proceed. MVP default is to fail. Document the trade-off.

This is the single most Python-flavored regression risk in the entire pipeline.

### 4.3 `__init__.py` side effects

**What goes wrong:** `calcpy/__init__.py` has `_initialize_logging()` at import time. Scalpel splits `calcpy.py` into a package — creates `__init__.py` — and the side effect is duplicated (or lost). Tests that assumed the side effect fires exactly once break.

**Mitigation:** when the strategy converts a `.py` file into a package (the `single_file` → `package` case under `split_file_by_symbols`), it must:

1. Move the original module-level code into the new `__init__.py`.
2. Not create an `__init__.py` ex nihilo — preserve the original's top-level content.
3. Emit a warning if the original file had side-effect code (lines outside of `def`, `class`, and imports at module scope).

The warning is language-specific output in `RefactorResult.warnings`.

### 4.4 PEP 420 implicit namespace packages

**What goes wrong:** project uses PEP 420 (no `__init__.py` anywhere), scalpel creates `calcpy/__init__.py` on split, breaks the namespace package contract. Downstream tooling (ruff's `INP001` rule, [Ruff docs](https://docs.astral.sh/ruff/rules/implicit-namespace-package/)) flags the violation.

**Mitigation:** detect namespace-package convention before creating any `__init__.py`. Heuristic:

1. If no sibling `__init__.py` exists in the entire parent package tree → treat as namespace package.
2. If `pyproject.toml` has `[tool.setuptools.packages.find] namespaces = true` → explicit.
3. Warn and require `force_regular_package=True` to convert.

See [PEP 420](https://peps.python.org/pep-0420/) for the full specification. The [Real Python article on namespace packages](https://realpython.com/python-namespace-package/) has accessible examples.

### 4.5 Stub files (`.pyi`)

**What goes wrong:** `calcpy.py` has a sibling `calcpy.pyi` stub. Scalpel splits `calcpy.py` into four modules. The `.pyi` now describes a file that no longer has the symbols it claims. Type checkers read `calcpy.pyi` before `calcpy/`, silently masking the actual post-split types.

**Mitigation:** detect `<module>.pyi` next to the target. MVP behavior: emit a warning, require `update_stubs=True` to proceed. If `update_stubs=True`, split the `.pyi` alongside the `.py` (Rope does not handle this; the strategy does a text-based split using the same symbol map).

### 4.6 Circular imports — the post-refactor killer

**What goes wrong:** `calcpy.py` works because it is one file — `evaluator` calls into `parser` and `parser` references `evaluator.Value` at runtime; Python resolves this at access time, not at import time, so no circular-import error. Post-split: `evaluator.py` has `from .parser import …` at top, and `parser.py` has `from .evaluator import Value` at top. Circular import, `ImportError` at load time.

**Mitigation:** the dry-run's `diagnostics_delta` must include an *import-graph circularity check*. Implementation:

1. After computing the dry-run `WorkspaceEdit`, in-memory apply to a copy.
2. Walk every new file; parse with `ast.parse`.
3. Extract every top-level `import` and `from X import Y`.
4. Build an import dependency graph.
5. Run Tarjan's SCC; any non-trivial SCC is a cycle.
6. Report cycles in `warnings` with the minimum fix hint: "move `X` and `Y` to a common parent module, or use lazy import inside function body."

Rust has no runtime-only cross-module references (the type system forbids them), so this check is Python-specific.

### 4.7 Implicit relative imports (Python 2 legacy)

**What goes wrong:** some corpora still have `import sibling` (Python 2 implicit relative import) at the top of a module. This was removed in PEP 328 + Python 3.0, but corpora built from 2to3 often preserve the ambiguous form — it now means "find `sibling` on `sys.path`", which typically fails.

**Mitigation:** detect and warn before split. pylsp already emits diagnostics for this (Pyflakes rule `F401`/`F811` adjacent). Scalpel includes those diagnostics in `diagnostics_delta.new_errors`.

### 4.8 Runtime-injected attributes

**What goes wrong:** `calcpy.py` has `class Evaluator: ...` and later `Evaluator.cache = {}` at module level. Scalpel moves `Evaluator` to `evaluator.py` and leaves the `cache` assignment in `__init__.py`. The assignment now has no `Evaluator` to attach to; `NameError` at import.

**Mitigation:** Rope's `MoveGlobal` moves the class but not the subsequent attribute assignment. The strategy must:

1. Before move, scan for `<symbol>.X = …` patterns referencing the about-to-move symbol.
2. Move those assignments to the destination module.
3. Preserve order.

Not elegant. Emit a `warnings: ["mutation of {symbol} detected; moved with symbol"]` note.

### 4.9 Star exports in `__all__`

**What goes wrong:** `calcpy.__all__ = ["parse", "evaluate", "Evaluator"]`. Split puts `parse` in `parser.py`, `evaluate`/`Evaluator` in `evaluator.py`. The old `__all__` still references those names but they no longer exist at the root; `from calcpy import *` produces `ImportError` for every consumer.

**Mitigation:** when `reexport_policy == "preserve_public_api"`, the strategy must:

1. Parse the original `__all__` list.
2. For each name, emit the re-import in `__init__.py`.
3. Preserve `__all__` verbatim.

Covered in §3.6. Documented here because it's easy to miss.

### 4.10 Test-discovery conventions

**What goes wrong:** `pytest` discovers tests by walking `test_*.py` or `*_test.py`. Splitting `calcpy.py` may leave `test_calcpy.py` referencing symbols that moved. pytest's import machinery produces cryptic `ModuleNotFoundError` messages.

**Mitigation:** Rope's `MoveGlobal` does rewrite test imports (they are just imports). The risk is that pytest is run out-of-process and scalpel's diagnostics-delta doesn't see the failure. Document that E2E tests must run pytest in the verification turn (same shape as Rust's `cargo test`).

### 4.11 Jupyter notebooks (`.ipynb`)

**What goes wrong:** project has a `notebooks/` directory with `.ipynb` files using `from calcpy import evaluate`. These are JSON blobs, not Python. Rope doesn't know about them; imports in notebooks do not get rewritten.

**Mitigation for MVP:** document. Scan for `.ipynb` in the project; if any contain `import <target_module>`, warn. Updating notebooks is out of scope for v1.

### 4.12 Top-level `if TYPE_CHECKING:` blocks

**What goes wrong:** `from __future__ import annotations` and `if TYPE_CHECKING: from .other import X`. Rope's import-rewriting may or may not recognize the `TYPE_CHECKING` guard. Post-split, type-only imports may be moved or duplicated.

**Mitigation:** verify in integration tests. If Rope mishandles them, the strategy does a post-pass text rewrite. Low-frequency issue; document and monitor.

---

## 5. Abstraction pressure on the main design

Audit of the §5 LanguageStrategy protocol and §3 facade signatures against the Python shape.

### 5.1 Rust-jargon artifacts that do not map

**Three specific leaks.**

#### 5.1.1 `parent_module_style: {"dir", "mod_rs"}` (main spec §3.2)

Rust has two file layouts for the same module:
- `foo/mod.rs` — the old style.
- `foo.rs` + optional `foo/` — the new style (post Rust 2018).

The enum `{"dir", "mod_rs"}` makes sense in Rust but is meaningless in Python:
- Python has `foo/__init__.py` (package) vs `foo.py` (module). Analogous, not identical.
- `mod_rs` in particular has no Python cognate — Python never puts the package's `__init__.py` on a different name.

**Proposed rename (language-neutral):** `module_layout_style: {"package", "single_file"}`.

| Language | `package` | `single_file` |
|---|---|---|
| Rust | `foo/mod.rs` (older) or `foo.rs` + `foo/` (2018+) | `foo.rs` only, no directory |
| Python | `foo/__init__.py` with sibling modules | `foo.py` |
| TypeScript | `foo/index.ts` + siblings | `foo.ts` |
| Go | `foo/` directory (package) | n/a — Go packages are directories |

`package` means "create a directory and put the module's entry point inside a conventionally-named file". `single_file` means "the module is one file". Each strategy translates.

Rust strategy internal mapping: `package` → `foo/mod.rs` (or `foo.rs` with sibling `foo/` depending on a sub-option). `single_file` → `foo.rs`. The old `mod_rs` meaning is preserved inside the Rust strategy's implementation; it just isn't in the facade contract.

#### 5.1.2 `reexport_policy: "preserve_public_api"` semantics

In Rust, "preserve public API" means emitting `pub use new_mod::Item;` in the parent file for every item that was `pub` before the move. Mechanical.

In Python, "preserve public API" is three different things depending on convention:
1. Explicit `from .new_mod import Item` in `__init__.py`.
2. Extend `__all__`.
3. Star re-export (discouraged but common in legacy code).

The single string `"preserve_public_api"` is adequate for the facade (the intent is identical across languages); the strategy picks the idiom. But the strategy needs an additional per-call parameter for the Python idiom choice — either via a sub-field or a strategy-level default.

**Proposal:** keep the enum `{"preserve_public_api", "none", "explicit_list"}`; add an optional `reexport_style: {"explicit", "__all__", "star"} | None = None` that lets the caller override the strategy's default. Python strategy default: `"explicit"`. Rust strategy ignores the parameter.

#### 5.1.3 `extract_module_kind() -> str` as the only shape

The Protocol assumes every language has a single canonical "extract module" code-action kind. Python has none. TypeScript has `refactor.extract.interface` / `refactor.extract.type` but no "extract N exports to a new module" action either. Rust is an outlier here because it has `extract_module` as a first-class assist.

**Proposal:** add `extract_module_strategy() -> Literal["native_code_action", "composed"]`. If `"native_code_action"`, `extract_module_kind()` returns the kind string. If `"composed"`, the strategy owns the composition directly (Python case). Default is `"composed"`; Rust strategy overrides to `"native_code_action"`.

This reframes the Protocol so the composition path is first-class — which it is, for every language except Rust.

### 5.2 Facades that should be deprecated for Python

Main spec §3.4 — `move_inline_module_to_file`. Rust-specific; Python has no inline modules. **Recommendation:** keep the facade in the MCP surface, return a structured failure for Python, document the cross-language inventory.

### 5.3 Facades that gain Python-specific parameters

Main spec §3.2 — `split_file_by_symbols`. Needs:

- `reexport_style: {"explicit", "__all__", "star"} | None = None` (§3.6).
- `update_stubs: bool = False` (§4.5).
- `allow_star_imports: bool = False` (§4.2).
- `force_regular_package: bool = False` (§4.4).

Argue for **none of these in the top-level facade signature.** Instead, pass them as a `language_options: dict[str, Any]` pass-through that each strategy interprets. Rust strategy ignores it. Python strategy parses and validates.

This is the TRIZ-segmentation move: the facade stays language-neutral by admitting "I don't know what options this language needs; here's a bag."

### 5.4 Facades that need diagnostics-delta expansion

Main spec's `DiagnosticsDelta` schema counts errors. For Python, we also need:

- `import_cycles_introduced: list[list[str]]` — the Tarjan SCC output from §4.6.
- `star_import_risks: list[str]` — consumer files that may break.
- `stub_drift: list[str]` — `.pyi` files that now mismatch.

**Proposal:** add a free-form `language_findings: dict[str, Any]` to `DiagnosticsDelta`. Python strategy populates; Rust strategy leaves empty.

### 5.5 Summary of proposed design changes

| # | Change | Scope | Cost |
|---|--------|-------|------|
| 1 | Rename `parent_module_style` → `module_layout_style` with values `{"package", "single_file"}` | Facade signature, all strategies | Small — pure rename in untouched v1 code |
| 2 | Add `extract_module_strategy() -> Literal["native_code_action", "composed"]` to Protocol | Protocol, Rust strategy override | Small |
| 3 | Add `language_options: dict[str, Any]` parameter to `split_file_by_symbols` | Facade signature | Small |
| 4 | Add `language_findings: dict[str, Any]` to `DiagnosticsDelta` | Schema | Small |
| 5 | Keep `move_inline_module_to_file` but allow it to return `not_applicable` per strategy | No change; existing error path | Zero |
| 6 | Split `module_declaration_syntax` into "glue" (returns None on Python) and `importer_syntax` (universal) | Protocol | Small |

None of these block MVP. Items 1 and 2 should land before the Python strategy is merged; items 3–4 can land post-MVP based on Python integration-test learnings.

---

## 6. Testing fixture: `calcpy`

Purpose-built throwaway fixture, analogous to the Rust spec's `calcrs`. ~900 LoC, stdlib-only, deliberately monolithic.

### 6.1 What it is

A single-module arithmetic expression evaluator. Same mental shape as `calcrs`:

```python
calcpy.run("2 + 3 * 4") == Value.int_of(14)
calcpy.run("(1 + 2) * (3 - 4)") == Value.int_of(-3)
calcpy.run("10 / 3") == Value.float_of(3.333…)
calcpy.run("x + 1", env={"x": 5}) == Value.int_of(6)
```

Operators: `+ - * / % ** == != < <= > >=`. Unary `- +`. Parentheses. Variables (via env dict). Literal kinds: int, float, bool, string (for error messages). No user-defined functions (keeps size bounded).

### 6.2 Ugly-on-purpose features (the whole point of a fixture)

Each feature triggers a specific Python-flavored refactor edge case.

| Feature | Where it goes | What it tests |
|---|---|---|
| Star import at top: `from math import *` | Module top | §4.2 — star-imports-hide-moves; dry-run must warn |
| Inner class tree: `class Expr: class BinaryOp: class UnaryOp:` | Lines 80–230 | Clustering — `plan_file_split` should propose grouping these |
| Mixed visibility: `_parse_operand`, `_TOKEN_REGEX`, `_UnaryOpKind`, public `parse` / `evaluate` / `run` | Throughout | §4.1 preserve-private-ness invariant |
| A helper `_resolve_name(env, name)` used from three clusters | Line 420-ish | Cross-group edge; §4.6 circular-import risk |
| One `class Evaluator` with 200 lines of `def _eval_*` methods | Lines 500–700 | Method-clustering heuristic; symbol_size_heuristic |
| `__all__ = ["run", "VERSION", "Value", "CalcError"]` | Line 15 | §4.9 `__all__` preservation after split |
| `VERSION = "0.1.0"` + side-effect `_initialize_logging()` at module top | Line 10 | §4.3 `__init__.py` side-effect preservation |
| A `.pyi` sibling describing the public API | Sibling file | §4.5 stub-drift detection |
| A `TYPE_CHECKING` import block | Line 25 | §4.12 `TYPE_CHECKING` handling |
| Runtime attribute injection: `Evaluator.default_precision = 28` at module level after class def | Line 720 | §4.8 runtime-injected attributes |
| Doctest in a docstring | `run()` docstring | `pytest --doctest-modules` gate |
| `if __name__ == "__main__":` block at bottom | Lines 880-900 | Must stay in whatever becomes the entry point |

### 6.3 Layout

```
/test/e2e/fixtures/calcpy/
├── pyproject.toml               # package name = "calcpy-fixture"
├── calcpy/
│   ├── __init__.py              # re-exports run + VERSION (~10 lines)
│   ├── calcpy.py                # ~900 LoC — the monolith under test
│   └── calcpy.pyi               # ~80 LoC — public-API stub sibling
├── tests/
│   ├── test_calcpy.py           # ~200 LoC of arithmetic cases
│   └── test_public_api.py       # asserts __all__ contents remain exported
└── expected/
    ├── post_split_package/      # expected tree after 4-way package split
    │   ├── __init__.py          # re-exports + __all__
    │   ├── ast.py               # Expr, BinaryOp, UnaryOp, Value
    │   ├── errors.py            # CalcError, ParseError, RuntimeError
    │   ├── parser.py            # parse, tokenize, Token
    │   └── evaluator.py         # Evaluator, evaluate, apply_binary, apply_unary
    └── baseline.txt             # frozen pytest output; byte-identical after refactor
```

`pyproject.toml` uses only stdlib + `pytest` as a dev dep. No runtime deps whatsoever — mirrors calcrs's "no crates.io" stance.

### 6.4 Baseline and test commands

```bash
# Baseline (pristine fixture)
cd /test/e2e/fixtures/calcpy
python -m pytest -q                             # must pass green
python -m py_compile calcpy/calcpy.py           # must parse
python -m pytest --doctest-modules calcpy       # doctests pass

# Post-refactor (on a scratch copy)
cp -r /test/e2e/fixtures/calcpy $SCRATCH/
cd $SCRATCH/calcpy
# ... run the 5-turn MCP sequence against this copy ...
python -m py_compile calcpy/**.py               # every split file parses
python -m pytest -q                             # byte-identical pass count to baseline
diff <(python -c 'from calcpy import *; print(sorted(dir()))') \
     expected/public_symbols.txt                # public API unchanged
```

The pristine fixture is never mutated (same rule as calcrs). Every E2E scenario works on a scratch copy.

### 6.5 Why this shape satisfies MVP

- **900 LoC** is the same order of magnitude as `calcrs`, exercising multi-module splits without being unauditable.
- **Stdlib-only** means zero flakiness from pip/wheels, matching calcrs's zero-crates-io stance.
- **Four natural clusters** (`ast`, `errors`, `parser`, `evaluator`) give `plan_file_split` a non-trivial target without being ambiguous — the test knows the right answer.
- **The ugly features are one-per-pitfall** so test output lets us attribute regressions. When test N fails with "star-import-hides-moves", we know which pitfall the strategy violated.

### 6.6 Scenarios (adapted from main spec §E2E)

| # | Scenario | What it proves |
|---|----------|----------------|
| E1-py | Happy-path 4-way split of `calcpy.py` into `ast/errors/parser/evaluator` | The 5-turn workflow works end-to-end; post-state parses and passes pytest. |
| E2-py | Dry-run → inspect → adjust → commit | `dry_run=true` returns the same `WorkspaceEdit` that `dry_run=false` applies; `diagnostics_delta` matches. |
| E3-py | Rollback after failed pytest | `rollback_refactor(checkpoint_id)` restores byte-identical tree. |
| E4-py | Star-import warning fires | Fixture has `from calcpy import *`; dry-run returns `warnings: ["star_import_hides_moves"]`; commit fails without `allow_star_imports=True`. |
| E5-py | Circular-import detection | Intentional move creates `evaluator → parser → evaluator` cycle; dry-run reports the SCC in `language_findings.import_cycles_introduced`. |
| E6-py | `fix_imports` on glob | `organize_imports` reaches every `*.py` in `calcpy/`; idempotent on second call. |
| E7-py | Virtualenv resolution | Run with no active venv but a `.venv/` sibling present; pylsp picks it up via the mitigation chain (§4.1). |
| E8-py | Namespace package detection | Variant fixture without `__init__.py`; dry-run warns about PEP 420. |
| E9-py | Stub drift | Fixture has `.pyi`; split must offer `update_stubs=True` path or warn. |
| E10-py | `__all__` preservation | After split, `from calcpy import *` yields the same set of names. |
| E11-py | Regression: `rename_symbol` | Existing rename path still works. |

E1-py, E2-py, E3-py, E10-py, E11-py block commits. Others run nightly.

---

## 7. Risks specific to Python that could blow MVP scope

Ranked by likelihood × cost-if-triggered.

### 7.1 pylsp-rope's "experimental" unsaved-buffer support

**Signal:** [pylsp-rope README](https://github.com/python-rope/pylsp-rope) calls out "Support for working on unsaved documents is currently experimental." Scalpel's model is that the agent drives refactors without a live editor — every buffer is technically "unsaved" from the LSP's perspective. We do synchronous `didChange` + code-action, the buffer never gets a disk-save round-trip.

**Risk:** pylsp-rope silently returns stale `WorkspaceEdit` against the on-disk version, not the in-memory version the agent believes is current.

**Mitigation:**
- Scalpel's Python strategy forces a disk-save (via `textDocument/didSave` with `includeText: true`) before every code-action call. This costs one extra round-trip per action but eliminates the staleness class.
- Integration test E4-py extends the main spec's E4 (concurrent edit during refactor) to specifically exercise the unsaved case; failing E4-py blocks merge of the Python strategy.
- Document the limit: scalpel's Python refactors behave as if files are saved atomically before each step. Users who care about live-buffer semantics are outside scope.

**Likelihood:** high. **Cost:** medium (manifests as intermittent wrong-version edits, hard to diagnose). **Handled scope:** extra save-round-trip is the v1 answer.

### 7.2 Virtualenv discovery failure

**Signal:** §4.1's ten-step chain is already long. Real-world corpora have conda, micromamba, pyenv, asdf, and hand-rolled venv layouts. Getting this wrong means every `import numpy` error becomes a scalpel bug report.

**Risk:** scalpel resolves to the wrong Python, produces "unresolved import" diagnostics that block every dry-run's `diagnostics_delta` check, refactor is blocked or — worse — proceeds with a bogus delta.

**Mitigation:**
- The ten-step chain with loud failure at the end.
- `O2_SCALPEL_PYTHON_EXECUTABLE` as the escape hatch, documented prominently.
- Integration test E7-py verifies `.venv/` sibling auto-discovery.
- E2E test harness runs scenarios under an explicit `VIRTUAL_ENV` to avoid ambient-interpreter pollution.

**Likelihood:** high for bug reports, medium for broken scenarios. **Cost:** medium. **Handled scope:** in MVP via the chain.

### 7.3 Rope performance on large codebases

**Signal:** Rope's `MoveGlobal` scans every file in the project to rewrite importers. On a 10k-file monorepo, a single symbol move can take 30–120 seconds. `split_file_by_symbols` moves N symbols — multiply accordingly.

**Risk:** users try scalpel on their big Python monorepo (Dropbox-scale, Instagram-scale), the first facade call takes 20 minutes, the user assumes scalpel is broken.

**Mitigation:**
- Scope `fix_imports` to a user-supplied glob (default: the parent package only, not `**`).
- Add a `project_scope: list[str] = ["<parent-package>/**"]` parameter that narrows Rope's `Project` instance to just the relevant subtree.
- Fail loud with a timeout of 120 seconds per `MoveGlobal` by default; suggest narrowing scope.
- Document the limitation: scalpel's Python strategy is designed for 1k–10k-LoC packages, not 1M-LoC monorepos.

**Likelihood:** medium. **Cost:** medium (bad reviews from big-project users). **Handled scope:** in-MVP via scope parameter + timeout.

### 7.4 pylsp-rope is maintained by one person

**Signal:** the GitHub contributor graph is heavily dominated by the maintainer. Single-maintainer dependency is a supply-chain concern.

**Risk:** pylsp-rope stops getting updates; a breaking change in pylsp's plugin API bricks scalpel's Python strategy.

**Mitigation:**
- Pin pylsp and pylsp-rope to exact versions in scalpel's `pyproject.toml`.
- Integration test asserts the advertised `codeActionKinds` set at startup.
- Fall back to driving Rope directly as a library when the plugin API breaks — Rope itself has more contributors and is less exposed.
- File a tracking issue at o2.scalpel for "pylsp-rope is behind pylsp X.Y."
- Post-v1, explore vendoring pylsp-rope as a submodule and maintaining our own fork (mirror of the Serena strategy — we already fork upstreams).

**Likelihood:** medium. **Cost:** low short-term, high long-term. **Handled scope:** pin + fallback in MVP; vendoring deferred.

### 7.5 Rope's handling of `TYPE_CHECKING` blocks

**Signal:** no explicit evidence that Rope handles `if TYPE_CHECKING: from .x import Y` correctly on move.

**Risk:** post-move, the `TYPE_CHECKING` import still references the old location; type checker is unhappy.

**Mitigation:**
- Integration fixture E12-py (new) exercises `TYPE_CHECKING` blocks explicitly.
- If Rope mishandles them, the strategy does a post-pass text rewrite (cheap).

**Likelihood:** unknown (test to find out). **Cost:** small. **Handled scope:** ship the fixture; fix if red.

### 7.6 pyright vs basedpyright behavioral drift

**Signal:** basedpyright is a fork that re-implements Pylance features. Each upstream pyright release risks breaking basedpyright.

**Risk:** scalpel's secondary LSP (basedpyright for diagnostics-delta) returns different results on different versions; our `diagnostics_delta` check is non-deterministic.

**Mitigation:**
- Pin basedpyright to exact version.
- Snapshot the expected diagnostic count per fixture scenario; assert equality.
- Document that users who run a different pyright-family server see a different delta (acceptable — the delta is advisory, not gating at the MCP boundary).

**Likelihood:** low. **Cost:** small. **Handled scope:** pin.

### 7.7 Two LSP processes (pylsp + basedpyright) on large projects

**Signal:** the main spec's §Q12 Python mitigation says "no optimization; pylsp spawn is ~300 MB and sub-second". True for pylsp alone. With pylsp + basedpyright + pylsp-mypy all running, plus CC's own read-only LSP also running, a project can see four Python LSPs.

**Risk:** 1–1.5 GB total memory overhead just for Python, on top of scalpel's own process. Acceptable on dev machines; painful on 16 GB laptops in Python-heavy monorepos.

**Mitigation:**
- Inherit the main spec's `O2_SCALPEL_DISABLE_LANGS=python` opt-out.
- Allow per-server disable: `O2_SCALPEL_DISABLE_SERVERS=basedpyright` so the user can run only pylsp-rope.
- Document the resident-set cost in the README.

**Likelihood:** medium on low-RAM dev machines. **Cost:** low. **Handled scope:** opt-out flag.

### 7.8 PEP 420 namespace-package friction

**Signal:** ruff's `INP001` rule actively discourages implicit namespace packages in source trees. Modern codebases using `setuptools.find_packages(namespaces=True)` exist but are unusual for apps (common for SDK distributions).

**Risk:** scalpel creates `__init__.py` where none belongs and breaks a legitimate namespace-package layout.

**Mitigation:**
- Detection heuristic (§4.4).
- `force_regular_package=True` override.

**Likelihood:** low for MVP's likely users. **Cost:** small but annoying for the impacted users. **Handled scope:** in-MVP detection.

### 7.9 Diagnostics-delta false positives from mypy

**Signal:** pylsp-mypy runs mypy in incremental mode. Incremental mypy is known for spurious errors after structural changes until the cache invalidates.

**Risk:** `diagnostics_delta.new_errors` reports phantom errors from stale mypy cache; strict-mode `split_file_by_symbols` rolls back a perfectly valid refactor.

**Mitigation:**
- Clear the mypy incremental cache before the dry-run check (`rm -rf .mypy_cache` or use `--no-incremental`).
- Document the trade-off: slower dry-run (mypy cold), but accurate.
- Alternative: disable pylsp-mypy entirely and rely on basedpyright's own type checker for the delta. Faster, slightly different error taxonomy.

**Likelihood:** medium in real projects. **Cost:** medium (false-positive rollbacks are exactly the regression the user profile flags). **Handled scope:** doc + opt-out config.

### 7.10 `rope` AST parser vs 3.13+ syntax features

**Signal:** Rope has historically lagged on new Python syntax. 3.12's PEP 695 generics, 3.13's type parameter syntax, match statements, walrus operator — each has required a Rope update.

**Risk:** scalpel refactors against 3.13+ code; Rope parser rejects a file; entire refactor aborts.

**Mitigation:**
- Pin a Rope version known to support the target Python.
- Integration tests include a 3.13-syntax fixture variant.
- Document the supported Python minimum (likely 3.10 for MVP; 3.12/3.13 with caveats).

**Likelihood:** low-medium. **Cost:** medium (user-facing "unsupported syntax" error). **Handled scope:** version pinning + documented compat matrix.

---

## 8. Integration points with the main design

### 8.1 What the main design gets right and should keep

- **Facade contracts are language-neutral.** The `PlanResult`, `RefactorResult`, `FileChange`, `DiagnosticsDelta` schemas work for Python with only the additions proposed in §5.5.
- **Name-paths, not byte ranges, at the API boundary.** Python's `pkg.mod.Class.method` style maps cleanly to the name-path convention.
- **`dry_run` on every mutator.** Essential for Python because the pipelines are compositions and the LLM needs to see the intermediate result.
- **Atomic by default + checkpoint rollback.** Even more important for Python than Rust — partial moves leave `ImportError` at runtime, and the LLM cannot recover without a rollback.
- **Hallucination resistance via fuzzy symbol resolution.** Python LLMs routinely hallucinate `Calcpy.run` for `calcpy.run` (module vs class). The same case-insensitive + ends-with match works.

### 8.2 What the main design must adjust before the Python strategy merges

- §3.2 `parent_module_style` rename (§5.1.1 above).
- §5 Protocol additions: `extract_module_strategy()`, split `module_declaration_syntax` into two methods, optional `language_options` pass-through.
- `DiagnosticsDelta` gets `language_findings`.
- Facade `move_inline_module_to_file` documents "Python: not applicable" in the MCP tool description.

### 8.3 Deployment-layer impact (main spec §Deployment)

- Sibling-plugin discovery must recognize `.py` → Python strategy. The boostvolt/Piebald plugin registry already has Python LSP manifests; scalpel inherits the `command`/`args` from whichever is installed.
- `.mcp.json` env-var additions (optional, documented):
  - `O2_SCALPEL_PYTHON_EXECUTABLE`
  - `O2_SCALPEL_DISABLE_SERVERS` (csv — `basedpyright` excluded → only pylsp runs)
- Two LSP processes (pylsp + basedpyright) per Python project; both lightweight. No additional mitigation beyond the main spec §Q12 recommendations.

### 8.4 Plugin marketplace impact (main spec §Q11, §Q14)

The Q14 on-demand plugin generator (`o2-scalpel-newplugin`) needs two Python plugin variants:
- `pylsp-reference` (hand-authored) — registers pylsp + pylsp-rope + pylsp-mypy.
- `basedpyright-reference` (hand-authored) — the fallback LSP manifest.

Both follow the Q14 clean-room rule: generated from upstream docs, never from boostvolt/Piebald sources.

---

## 9. Effort estimate (Python strategy only)

| Layer | Files | New LoC | Complexity |
|---|---|---|---|
| `PythonStrategy` plugin | 1 (`python_strategy.py`) | ~280 | Small |
| Virtualenv discovery | 1 (`python_env.py`) | ~150 | Small |
| Python-specific `split_file_by_symbols` composition | Part of PythonStrategy | included above | Medium (Rope orchestration) |
| Stub-file handling | Part of PythonStrategy | ~80 | Small |
| Namespace-package detection | Part of PythonStrategy | ~40 | Trivial |
| Circular-import checker | 1 (`import_graph.py`) | ~100 | Small |
| Star-import scanner | Part of PythonStrategy | ~50 | Trivial |
| `calcpy` fixture | ~3 files | ~1100 LoC fixture | Small |
| Unit tests | 1 | ~400 LoC | Small |
| Integration tests vs real pylsp | 1 + fixtures | ~600 LoC | Medium |
| E2E scenarios E1-py through E11-py | 11 scenarios | ~800 LoC | Medium |

**Total: ~2,400 LoC + ~1,100 LoC of fixture, across ~8 new files.** Same order of magnitude as the Rust strategy's ~2,450 LoC. Shippable in MVP.

**Staging:**

1. Small: virtualenv discovery + `PythonStrategy` skeleton with `NotImplementedStrategy` facades.
2. Medium: rename + `fix_imports` working; skip `split_file_by_symbols` for now.
3. Medium: `plan_file_split` with clustering (re-uses the Rust strategy's planner — language-neutral).
4. Large: `split_file_by_symbols` composition via `MoveGlobal` + dry-run + rollback.
5. Test: E1-py → E3-py → E10-py → E11-py block merge; others run nightly.

Staging order gives an escape-hatch-first MVP (primitive tools work; basic rename and organize-imports work) before the big compositional facade.

---

## 10. Open questions specific to Python

Genuinely open after this round; not hidden by confident prose.

1. **pylsp vs pylsp-rope plugin init order.** pylsp-rope must be registered with pylsp; if scalpel spawns pylsp via `uvx`, it needs to ensure both packages share a venv. Proposed fix: scalpel ships a wheel group `scalpel-python-backend` that pins `python-lsp-server[rope]==1.x` + `pylsp-rope==0.y` + `pylsp-mypy==0.z` + `basedpyright==1.w`. User installs once; scalpel spawns from this isolated env. Defer decision until we test the `uvx` path.
2. **Live-mode mypy vs on-demand.** Integration tests will tell us whether passive mypy diagnostics are fast enough for the delta check, or whether we need to fork a one-shot mypy process per dry-run. Start with passive; switch if latency is > 3 s per dry-run.
3. **`__init__.py` vs `__init__.pyi` semantics in a split.** When both exist, do we split both atomically? MVP answer: yes if `update_stubs=True`; otherwise warn. Revisit if users request finer control.
4. **Cython / `.pyx` / `.pyi.in` files.** Scalpel does not refactor these in MVP. Detection + ignore-with-warning is cheap; implement in the file-walker.
5. **Secondary LSP choice: basedpyright vs pyright.** Default to basedpyright because of the auto-import feature. But basedpyright is a community fork; pyright is Microsoft. Some users may prefer the upstream. Config: `scalpel.lsp.python.secondary = {"basedpyright" | "pyright" | "none"}`.
6. **Does `ruff server` replace pylsp-mypy entirely?** Ruff's autofix is very strong. For MVP, run both: ruff handles lint-driven fixes, pylsp-mypy handles type-driven. Revisit after E2E latency measurements.

---

## Appendix A — Python LSP capability matrix, full evidence

Formatted for integration test fixtures. Each row is one LSP feature scalpel needs; columns are the LSPs.

| Feature | pylsp + pylsp-rope | basedpyright | pyright | jedi-lsp | ruff | pyrefly |
|---|---|---|---|---|---|---|
| `textDocument/documentSymbol` | Y | Y | Y | Y | N | Y |
| `textDocument/references` | Y | Y | Y | Y | N | Y |
| `textDocument/rename` | Y (Rope) | Y | Y | Y | N | Y |
| `textDocument/rename` on module → `CreateFile`/`RenameFile` | **Y** | N | N | N | N | ? |
| `callHierarchy/incomingCalls` | partial | Y | Y | Y | N | Y |
| `codeAction` `refactor.extract.function` | Y (pylsp-rope) | N | N | Y (Jedi) | N | ? |
| `codeAction` `refactor.extract.variable` | Y | N | N | Y | N | ? |
| `codeAction` `refactor.inline` | Y | N | N | Y | N | ? |
| `codeAction` `source.organizeImports` | Y | Y | Y | partial | Y | ? |
| `codeAction` `quickfix` auto-import | Y (Rope) | **Y** | N | N | N | ? |
| `codeAction/resolve` | Y | Y | Y | Y | Y | Y |
| `workspace/executeCommand` | Y | Y | Y | Y | Y | Y |
| Custom commands relevant to refactor | `pylsp_rope.*` (9) | `basedpyright.organizeimports` | `pyright.organizeimports` | — | — | ? |

`?` = not enumerated publicly as of Apr 2026; integration-test at first contact.

---

## Appendix B — References

Primary sources used in this report. Prefer primary over third-party wherever both exist.

**LSPs and tools**
- [python-lsp/python-lsp-server](https://github.com/python-lsp/python-lsp-server) — pylsp repo.
- [python-lsp/python-lsp-server CONFIGURATION.md](https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md) — init options.
- [python-rope/pylsp-rope](https://github.com/python-rope/pylsp-rope) — Rope integration plugin.
- [python-rope/pylsp-rope plugin.py](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/plugin.py) — command registrations.
- [python-rope/rope](https://github.com/python-rope/rope) — underlying refactoring library.
- [Rope library docs](https://rope.readthedocs.io/en/latest/library.html) — `MoveGlobal`, `create_move`.
- [Rope overview](https://rope.readthedocs.io/en/latest/overview.html) — supported refactorings.
- [pylsp-mypy](https://github.com/python-lsp/pylsp-mypy) — mypy plugin for pylsp.
- [microsoft/pyright](https://github.com/microsoft/pyright) — upstream pyright.
- [microsoft/pyright commands.md](https://github.com/microsoft/pyright/blob/main/docs/commands.md) — `pyright.organizeimports`.
- [DetachHead/basedpyright](https://github.com/DetachHead/basedpyright) — pyright fork.
- [basedpyright docs — commands](https://docs.basedpyright.com/v1.18.1/usage/commands/) — enumeration of commands.
- [basedpyright docs — language server settings](https://docs.basedpyright.com/v1.28.1/configuration/language-server-settings/) — `disableOrganizeImports`.
- [pappasam/jedi-language-server](https://github.com/pappasam/jedi-language-server) — README and changelog.
- [astral-sh/ruff — Editor Integration](https://docs.astral.sh/ruff/editors/) — ruff server code-action surface.
- [astral-sh/ruff — implicit-namespace-package rule (INP001)](https://docs.astral.sh/ruff/rules/implicit-namespace-package/) — PEP 420 detection rule.
- [astral.sh — ty announcement](https://astral.sh/blog/ty) — next-gen checker (out of MVP scope).
- [facebook/pyrefly](https://github.com/facebook/pyrefly) — Meta's Python LSP.
- [pyrefly.org](https://pyrefly.org/) — product site.

**Language and ecosystem**
- [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/) — namespace-package semantics.
- [Python import system reference](https://docs.python.org/3/reference/import.html) — `__init__.py`, `__path__`, loader rules.
- [Real Python — Namespace packages](https://realpython.com/python-namespace-package/) — readable explainer.
- [VSCode Python environments](https://code.visualstudio.com/docs/python/environments) — the canonical virtualenv-discovery chain reference.

**LSP spec**
- [Language Server Protocol 3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) — WorkspaceEdit, code actions, resource operations.

**Project-internal cross-references**
- [Main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — §3 facades, §5 LanguageStrategy, §Q7 second-strategy question.
- [Open-questions resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) — §Q12 Python bullet.
- [MCP ↔ LSP protocol brief](../../research/2026-04-24-mcp-lsp-protocol-brief.md) — code-action pipeline.
- [DX facades brief](../../research/2026-04-24-dx-facades-brief.md) — facade design rationale.
