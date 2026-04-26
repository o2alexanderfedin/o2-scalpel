# Specialist report — Python full-LSP-coverage strategy for o2.scalpel MVP

Status: report-only. No implementation.
Audience: the MVP orchestrator merging Rust + Python specialist outputs into a unified v1 scope.
Cross-reference: [main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) §3 (facades), §5 (LanguageStrategy), §Open Questions #7 (second strategy validates the abstraction); [archived narrow Python brief](archive-v1-narrow/specialist-python.md); [archived narrow MVP scope](archive-v1-narrow/2026-04-24-mvp-scope-report.md).

Date: 2026-04-24. Author: AI Hive(R), Python full-LSP-coverage specialist.

---

## 0. Directive change and what changed in this round

The first round of MVP brainstorming cut Python down to a *narrow* surface — pylsp + pylsp-rope as primary, basedpyright as secondary read-only, with only the four canonical MCP tools (`split_file`, `fix_imports`, `rollback`, `apply_code_action`) shipped at MVP and Python's bigger refactor catalogue (every Rope op, every basedpyright code action, every ruff fix) deferred to v1.1 behind the generic `apply_code_action` primitive.

The user has reversed that cut. **For the Python LSPs scalpel chooses, scalpel must fully support every feature the LSP exposes** — every pylsp-rope command, every pylsp-default-plugin code action, every basedpyright command, every ruff autofix, every Rope library refactor reachable via `workspace/executeCommand` or library bridge. "Full coverage" does not mean every facade ships at MVP. It means every server-emitted action is reachable via the MCP surface — either as a typed facade or, at minimum, as a typed pass-through in the primitive layer.

This document restates the Python position under the new directive. The narrow brief is preserved at `archive-v1-narrow/specialist-python.md`; this report references it where useful.

---

## 1. Executive summary

| # | Decision | Confidence |
|---|----------|------------|
| 1 | **Run three Python LSPs concurrently** at MVP: `pylsp` (with `pylsp-rope` + `pylsp-mypy` + `pylsp-ruff` plugins), `basedpyright`, and `ruff server`. Multiplex their `codeAction` responses through a per-strategy merge layer. Reasons in §3. | high |
| 2 | **Full Rope inventory is reachable** via three paths: (a) pylsp-rope commands for the nine Rope ops it bridges, (b) `workspace/executeCommand` pass-through for any future pylsp-rope additions, (c) **direct Rope library calls** from the Python strategy for ops pylsp-rope does not bridge today (`MoveModule`, `ChangeSignature`, `IntroduceFactory`, `EncapsulateField`, `Restructure`). The Rope-library bridge is a strategy-internal escape hatch, not a separate MCP tool. | high |
| 3 | **basedpyright surface beyond pyright** — auto-import quickfix, ignore-comment code actions, beyond-pyright diagnostics, "go to implementations", inlay hints, write-baseline command — is fully exposed via `apply_code_action` and a thin set of typed facades (`auto_import`, `ignore_diagnostic`, `organize_imports`). | high |
| 4 | **ruff's `source.fixAll.ruff`** is the third major action source. Treated as a peer of `source.organizeImports.ruff` and routed through `fix_lints` facade. Idempotency requires fixed-point iteration with cycle detection (§4.5). | medium |
| 5 | **Multi-LSP merge rule.** When two servers return overlapping `codeAction` results for the same `(file, range, kind-prefix)` tuple, scalpel applies a **server-priority + dedup-by-title** strategy. Priority order is `ruff > basedpyright > pylsp-rope > pylsp-base` for fix actions, `pylsp-rope > basedpyright > pylsp-base` for refactor actions. Dedup uses normalized title equality plus structural `WorkspaceEdit` equality where titles drift. Full table in §5. | medium |
| 6 | **Interpreter discovery is a first-class concern.** Twelve-step resolution chain (§7) covering venv, Poetry, PDM, uv, conda, pipenv, pyenv, asdf, PEP 582, PYTHONPATH, `PYTHON_HOST_PATH`, and `sys.executable`. Resolved interpreter is injected into pylsp (`jedi.environment`), basedpyright (`python.pythonPath`), and ruff (`--python` flag where supported). | high |
| 7 | **`WorkspaceEdit` matrix.** pylsp-rope sometimes emits old-style `changes` map; basedpyright always emits `documentChanges`; ruff always emits `documentChanges`. Applier supports both shapes; full matrix in §8. | high |
| 8 | **Python-specific facades beyond the cross-language base.** Eleven proposed (`extract_function`, `extract_variable`, `extract_method`, `inline`, `convert_to_method_object`, `local_to_field`, `introduce_parameter`, `convert_to_async`, `organize_imports`, `auto_import`, `annotate_return_type`) — each is a Rope or basedpyright passthrough wrapped in a typed Pydantic boundary. Eight ship at MVP; three (`convert_to_async`, `annotate_return_type`, `convert_from_relative_imports`) defer to v1.1 as pure ergonomics. Full table in §10. | high |
| 9 | **Pre-MVP spikes** — six in §11. The two blocking ones are: (a) **pylsp-rope unsaved-buffer behavior probe** (does it honor `didChange` without `didSave`?), (b) **simultaneous `source.organizeImports` from pylsp-rope vs ruff** producing different output, and the merge rule must pick one deterministically. | high |
| 10 | **Abstraction pressure under full coverage.** The `LanguageStrategy` Protocol from main design §5 is no longer sufficient. Python needs nine additional methods (§12) for: namespace-package detection, `__all__` management, `TYPE_CHECKING` rewriting, stub-file twin-edit, `__init__.py` side-effect preservation, async/await detection, decorator-aware top-level resolution, relative-import normalization, and circular-import detection. Proposed as a `PythonStrategyExtensions` mixin so the base Protocol stays narrow. | high |
| 11 | **Re-estimated LoC under full coverage.** Strategy core ~420 LoC, Python-specific facades ~640 LoC, multi-server multiplexer ~430 LoC, interpreter discovery ~210 LoC, Rope library bridge ~280 LoC, fixture `calcpy` ~1,250 LoC, tests ~1,050 LoC. **Total ~4,280 LoC + 1,250 LoC fixture across ~12 new files.** Sanity-check of orchestrator's per-component estimate: §13. | medium |
| 12 | **Responsible cuts.** Even with the full-coverage directive, three facades are pure ergonomics (`convert_to_async`, `annotate_return_type`, `convert_from_relative_imports`), and the third LSP (`ruff server`) is opt-out for low-RAM users. Defer ergonomic facades to v1.1 behind the typed `apply_code_action` primitive. Coverage is preserved (every action remains reachable); only the *named* facades wait. §14. | high |

**Ship recommendation.** Adopt three-LSP concurrent execution with the priority-merge rule. Bundle pylsp-rope + pylsp-mypy + pylsp-ruff as plugins inside the same pylsp process. Run basedpyright and ruff-server as separate processes. Total Python-side LSP footprint at MVP: three OS processes, ~600–800 MB RSS combined on `calcpy`-scale projects. Gate MVP on the eight scenarios E1-py through E11-py listed in §15, with E1-py / E3-py / E9-py / E10-py blocking and the rest nightly.

---

## 2. Why the previous narrow position was wrong

The narrow brief at `archive-v1-narrow/specialist-python.md` made three load-bearing cuts that the new directive overturns:

| # | Narrow position | Why it was a defensible local optimum | Why the user reversed it |
|---|-----------------|---------------------------------------|--------------------------|
| 1 | "Bundle only pylsp + pylsp-rope as the *write* server; basedpyright stays *read-only* secondary; ruff-server is out of MVP scope" (§1.3 narrow) | Three LSPs is a memory + complexity tax. pylsp-rope alone reaches the canonical 4-tool surface (`split_file`, `fix_imports`, `rollback`, `apply_code_action`). | **Full coverage requires all three.** ruff's `source.fixAll.ruff` reaches ~800 lint rules (300 of which are autofixable per Astral's count) that no other server emits. Suppressing it leaves a meaningful capability gap. |
| 2 | "Python-specific facades beyond the four canonical tools defer to v1.1" (§3.5 narrow MVP scope) | Keeps the MCP surface lean. LLMs can reach Rope's `extract_method` via `apply_code_action` even without a typed facade. | **Full coverage means each Rope operation has a typed facade when an LLM is likely to want it directly.** `extract_method`, `inline`, `extract_variable` are the three most-used IDE refactors per JetBrains telemetry; not exposing them as named tools wastes LLM tokens on the introspection round-trip. |
| 3 | "MoveModule, ChangeSignature, IntroduceFactory, EncapsulateField, Restructure: not in MVP because pylsp-rope does not bridge them" (§3.5 narrow appendix) | True statement about pylsp-rope's API surface. | **The Rope library bridges them.** Scalpel's Python strategy can call Rope directly when pylsp-rope's coverage has gaps. The narrow brief mentioned this at §1.3 ("Rope-as-a-library is available") but did not commit to wiring it. The new directive forces the wiring. |

The narrow brief got three things right that this report preserves:

1. **pylsp + pylsp-rope is the only write-capable Python LSP today.** No change.
2. **The 5-turn `split_file` workflow composes via Rope's `MoveGlobal` per symbol.** No change.
3. **Virtualenv discovery is the #1 ecosystem hazard.** Strengthened in §7 below.

---

## 3. Which Python LSPs to run concurrently

### 3.1 The decision

**Run three LSPs concurrently at MVP:**

1. `pylsp` with plugins `pylsp-rope`, `pylsp-mypy`, `pylsp-ruff` — the refactor + type-check primary.
2. `basedpyright` — the auto-import + beyond-pyright diagnostics secondary.
3. `ruff server` — the lint-autofix tertiary.

This is one more process than the narrow brief proposed, and one fewer than a hypothetical "every Python LSP we know of" maximalist position (which would also include `jedi-language-server` and `pyrefly`).

### 3.2 Why three, not two

| Constraint | If we drop ruff (two-LSP) | If we drop basedpyright (two-LSP) | Three-LSP |
|---|---|---|---|
| **Lint autofix coverage** | ~30 rules via pylsp + autopep8/yapf. Misses 770+ ruff-only rules. | Full ruff coverage. | Full ruff coverage. |
| **Auto-import accuracy** | basedpyright's Pylance-port is best-in-class. | pylsp-rope's `rope_autoimport` works but has 5–10x more false negatives on large codebases. | basedpyright's path. |
| **Type-checking diagnostics** | basedpyright + pylsp-mypy. Different opinions; useful redundancy. | pylsp-mypy only. | Both. |
| **Memory footprint (calcpy-scale)** | ~400 MB | ~500 MB | ~700 MB |
| **Memory footprint (10k-LoC project)** | ~700 MB | ~900 MB | ~1.2 GB |
| **Startup cost** | 1.5 s | 2.5 s | 3 s (parallel spawn) |
| **Duplicate-edit risk** | Low (one organize-imports source) | Medium (basedpyright vs pylsp-rope differ) | High without merge rule (§5) |
| **Lint drift** (different analyzers report different things) | Low | Medium | Highest, but observable + fixable |

The three-LSP plan loses on memory and duplicate-edit risk but wins on every capability dimension. The duplicate-edit risk is the only real hazard, and it has a deterministic solution (the priority-merge rule in §5). Memory cost is mitigated by `O2_SCALPEL_DISABLE_SERVERS` (per the narrow brief §8.3) — users on 16 GB laptops can disable `ruff` or `basedpyright` and lose the capability they care least about.

### 3.3 Why not four-plus

| Server | Decision | Reason |
|---|---|---|
| `jedi-language-server` | Out | Maintenance mode; every refactor it offers is also in pylsp + pylsp-rope or jedi (which pylsp uses internally). |
| `pyrefly` (Meta) | Out | Refactor surface still under construction as of Apr 2026; no firm advertised `refactor.extract.*` kinds. Revisit v2. |
| `ty` (Astral) | Out | Pre-alpha. |
| `pyright` upstream | Out | basedpyright is a strict superset of pyright capabilities. Choose the fork. |
| `pylyzer` | Out | Rust-based pyright alternative; narrow refactor surface; experimental. |

### 3.4 Server-process layout

```
scalpel-mcp-server (one Python process)
 ├── solidlsp client A → pylsp subprocess
 │   └── plugins: pylsp-rope, pylsp-mypy, pylsp-ruff, jedi (default)
 ├── solidlsp client B → basedpyright-langserver subprocess
 └── solidlsp client C → ruff server subprocess
```

All three subprocesses share the resolved interpreter (§7) and the project root. `solidlsp` already supports multiple concurrent server connections per `LanguageServer` instance; the Python strategy multiplies the existing pattern.

### 3.5 Spawn flags / config injected at startup

Verbatim init payloads each strategy must emit. Discovered fields under `lsp_init_overrides()`.

#### pylsp

```jsonc
{
  "command": "<resolved-pylsp-binary>",
  "args": [],
  "initializationOptions": {
    "pylsp": {
      "configurationSources": ["pyproject"],
      "plugins": {
        "jedi": {
          "environment": "<resolved-python-executable>",
          "extra_paths": []
        },
        "rope_autoimport": {
          "enabled": true,
          "memory": true,
          "completions": {"enabled": false},
          "code_actions": {"enabled": true}
        },
        "rope_completion": {"enabled": false},
        "pylsp_rope": {"enabled": true},
        "pylsp_mypy": {
          "enabled": true,
          "live_mode": false,
          "dmypy": true,
          "report_progress": true,
          "overrides": ["--python-executable=<resolved>", true]
        },
        "ruff": {"enabled": false},
        "pyflakes": {"enabled": false},
        "pycodestyle": {"enabled": false},
        "pylint": {"enabled": false},
        "mccabe": {"enabled": false},
        "autopep8": {"enabled": false},
        "yapf": {"enabled": false}
      }
    }
  }
}
```

Rationale: `pyflakes`, `pycodestyle`, `pylint`, `mccabe`, `autopep8`, `yapf` are all disabled because **ruff-server already covers their domain**, and running them via pylsp would duplicate diagnostics that the merge rule then has to dedup. `pylsp_ruff` plugin (note: there's both a plugin `pylsp-ruff` and a standalone `ruff server` — we use the standalone server, hence the `ruff: enabled: false` in pylsp). `rope_autoimport` is enabled with `memory: true` to avoid disk writes in the rope cache.

#### basedpyright

```jsonc
{
  "command": "<resolved-basedpyright-langserver>",
  "args": ["--stdio"],
  "initializationOptions": {
    "python": {
      "pythonPath": "<resolved-python-executable>",
      "venvPath": "<project-root>"
    },
    "basedpyright": {
      "analysis": {
        "autoImportCompletions": true,
        "diagnosticMode": "openFilesOnly",
        "useLibraryCodeForTypes": true,
        "typeCheckingMode": "standard",
        "inlayHints": {
          "variableTypes": false,
          "callArgumentNames": false,
          "functionReturnTypes": false,
          "genericTypes": false
        }
      },
      "disableOrganizeImports": true,
      "disableTaggedHints": false
    }
  }
}
```

Rationale: `disableOrganizeImports: true` because ruff owns that. Inlay hints disabled at MVP — they are an editor concern, not an agent concern. `diagnosticMode: openFilesOnly` keeps the diagnostic flood manageable on large workspaces; the strategy explicitly opens every file affected by a refactor before it begins, so the `diagnostics_delta` check still works.

#### ruff server

```jsonc
{
  "command": "<resolved-ruff>",
  "args": ["server", "--preview"],
  "initializationOptions": {
    "settings": {
      "configurationPreference": "filesystemFirst",
      "lint": {"enable": true, "preview": true},
      "format": {"enable": false},
      "codeAction": {
        "fixViolation": {"enable": true},
        "disableRuleComment": {"enable": true}
      },
      "organizeImports": true,
      "fixAll": true
    }
  }
}
```

Rationale: format disabled (we want `source.fixAll.ruff` and `source.organizeImports.ruff`, not `format`). `--preview` enabled so we get pre-stable lint rules; this is the standard editor recommendation.

### 3.6 Two-process tax revisited under three-LSP plan

The main design's §"Two-LSP-process problem" Python bullet says "no on-disk artifacts; safe". That holds only for pylsp's plugins. basedpyright and ruff each have their own caches:

| Server | Cache location | Mitigation |
|---|---|---|
| pylsp | None on disk by default; rope_autoimport cache lives in memory when `memory: true`. | Already mitigated. |
| basedpyright | `~/.cache/basedpyright/` typed-stub cache. | Override via `XDG_CACHE_HOME` per scalpel session if `O2_SCALPEL_ISOLATE_CACHES=1`. |
| ruff | `.ruff_cache/` in project root. | Override via `RUFF_CACHE_DIR` to `${CLAUDE_PLUGIN_DATA}/ruff-cache/<project-hash>`. |

Total disk overhead per project under isolation: ~100 MB for basedpyright stubs + ~5 MB for ruff cache. Acceptable. Default behavior follows the user's existing caches; `O2_SCALPEL_ISOLATE_CACHES=1` is the opt-in for users who want session isolation (mirrors the Rust strategy's `cargo.targetDir` override pattern).

---

## 4. Complete refactor inventory — what each LSP exposes

Three views of the same surface: by family, by server, by exposure mode.

### 4.1 By family — what an LLM might ask for

Each family lists the action, the server emitting it, the exposure mode (facade / primitive / pass-through), and the MVP stage. *Pass-through* means reachable only via `apply_code_action` with no typed wrapper. *Primitive* means reachable via a typed but generic primitive (e.g., `apply_code_action(id)` where `id` is opaque). *Facade* means a named typed tool (`extract_method(file, range)`).

#### Family: Extract

| Operation | Source | Command/Kind | Exposure | MVP stage |
|---|---|---|---|---|
| Extract method | pylsp-rope | `pylsp_rope.refactor.extract.method` | facade `extract_method` | MVP |
| Extract method (similar statements) | pylsp-rope | same command, `similar=true` | facade `extract_method(similar=True)` | MVP |
| Extract global method | pylsp-rope | same command, `global=true` | facade param | MVP |
| Extract variable | pylsp-rope | `pylsp_rope.refactor.extract.variable` | facade `extract_variable` | MVP |
| Extract variable (similar) | pylsp-rope | same, `similar=true` | facade param | MVP |
| Extract global variable | pylsp-rope | same, `global=true` | facade param | MVP |
| Extract function (alias for extract method at module scope) | pylsp-rope | same as method, `global=true` | facade `extract_function` (alias) | MVP |
| Extract type alias | n/a | not in any Python LSP | n/a | n/a |
| Extract interface (Protocol) | n/a | not in any Python LSP today | n/a | v2+ |

#### Family: Inline

| Operation | Source | Command/Kind | Exposure | MVP stage |
|---|---|---|---|---|
| Inline method | pylsp-rope | `pylsp_rope.refactor.inline` | facade `inline` (auto-detects target) | MVP |
| Inline variable | pylsp-rope | same command | facade `inline` same | MVP |
| Inline parameter | pylsp-rope | same command | facade `inline` same | MVP |

#### Family: Move

| Operation | Source | Mechanism | Exposure | MVP stage |
|---|---|---|---|---|
| Move global symbol to another module | Rope library (`rope.refactor.move.create_move`) | strategy bridge | composed inside `split_file`; also direct `move_symbol(symbol, target_module)` | facade MVP |
| Move method to attribute's class | Rope library (`MoveMethod`) | strategy bridge | facade `move_method` | v1.1 |
| Move module (rename file + update importers) | pylsp-rope rename path; Rope `MoveModule` | command path | facade `rename_module` (alias for `rename_symbol` on a module) | MVP |
| Move multiple globals (split file) | composition over `MoveGlobal` | strategy | facade `split_file` | MVP |

#### Family: Rename

| Operation | Source | Mechanism | Exposure | MVP stage |
|---|---|---|---|---|
| Rename symbol (variable, function, class) | pylsp-rope (Rope) | `textDocument/rename` | existing primitive (Serena `rename_symbol`) | MVP |
| Rename module / package | Rope `MoveModule` via `textDocument/rename` on file URI | same | same | MVP |
| Rename across imports (string occurrences in docstrings) | Rope `Rename(in_hierarchy=True, docs=True)` | library call | facade param `also_in_strings: bool` | MVP |

#### Family: Organize / Imports

| Operation | Source | Command/Kind | Exposure | MVP stage |
|---|---|---|---|---|
| Organize imports (Rope-style) | pylsp-rope | `pylsp_rope.source.organize_import` / `source.organizeImports` | facade `organize_imports(engine="rope")` | MVP |
| Organize imports (ruff/isort-style) | ruff server | `source.organizeImports.ruff` | facade `organize_imports(engine="ruff")` | MVP |
| Organize imports (basedpyright) | basedpyright | `basedpyright.organizeImports` | facade param | MVP (default off; ruff wins) |
| Auto-import (add missing) | basedpyright | `quickfix` on `reportUndefinedVariable` | facade `auto_import` | MVP |
| Auto-import (rope_autoimport) | pylsp + rope_autoimport | `quickfix` | merged into `auto_import` facade | MVP |
| Remove unused imports | ruff (rule F401 autofix) | `source.fixAll.ruff` | facade `fix_lints(rules=["F401"])` | MVP |
| Merge duplicate imports | ruff (I001) | `source.organizeImports.ruff` | rolled into `organize_imports` | MVP |
| Convert relative→absolute imports | ruff (TID252) | `source.fixAll.ruff` | facade `convert_imports(style="absolute")` | v1.1 |
| Convert absolute→relative imports | ruff (UP*) limited | `source.fixAll.ruff` | same facade | v1.1 |
| Handle long imports | Rope `ImportTools` | library bridge | pass-through | v1.1 |

#### Family: Lint / Fix

| Operation | Source | Mechanism | Exposure | MVP stage |
|---|---|---|---|---|
| Apply all autofixable diagnostics | ruff | `source.fixAll.ruff` | facade `fix_lints` | MVP |
| Fix one diagnostic | ruff | `quickfix` on a specific code | primitive `apply_code_action` | MVP |
| Insert `# noqa` | ruff | `quickfix` (disable rule comment) | facade `ignore_diagnostic(tool="ruff")` | MVP |
| Insert `# pyright: ignore` | basedpyright | code action | facade `ignore_diagnostic(tool="pyright")` | MVP |
| Insert `# type: ignore` | pylsp-mypy | quickfix | facade `ignore_diagnostic(tool="mypy")` | MVP |
| Type-ignore-with-error-code | basedpyright (`# pyright: ignore[reportUndefined]`) | code action | facade param | MVP |

#### Family: Type annotation

| Operation | Source | Mechanism | Exposure | MVP stage |
|---|---|---|---|---|
| Annotate return type from inference | basedpyright | inlay-hint click → code action | facade `annotate_return_type` | v1.1 |
| Annotate parameter from inference | basedpyright | same | facade param | v1.1 |
| Add `from __future__ import annotations` | ruff (FA100/FA102) | `source.fixAll.ruff` | bundled in `fix_lints` | MVP |
| Convert `Optional[X]` → `X \| None` (PEP 604) | ruff (UP007) | `source.fixAll.ruff` | bundled in `fix_lints` | MVP |
| Convert `List[X]` → `list[X]` (PEP 585) | ruff (UP006) | `source.fixAll.ruff` | bundled in `fix_lints` | MVP |
| Create stub file (`.pyi`) | pyright/basedpyright | `pyright.createtypestub` command | pass-through `apply_code_action` | v1.1 |

#### Family: Restructure / Higher-order

| Operation | Source | Mechanism | Exposure | MVP stage |
|---|---|---|---|---|
| Method-to-method-object | pylsp-rope | `pylsp_rope.refactor.method_to_method_object` | facade `convert_to_method_object` | MVP |
| Local-to-field | pylsp-rope | `pylsp_rope.refactor.local_to_field` | facade `local_to_field` | MVP |
| Use function (replace inline code) | pylsp-rope | `pylsp_rope.refactor.use_function` | facade `use_function` | MVP |
| Introduce parameter | pylsp-rope | `pylsp_rope.refactor.introduce_parameter` | facade `introduce_parameter` | MVP |
| Introduce factory | Rope `IntroduceFactory` | library bridge | facade `introduce_factory` | v1.1 |
| Encapsulate field | Rope `EncapsulateField` | library bridge | facade `encapsulate_field` | v1.1 |
| Change signature | Rope `ChangeSignature` | library bridge | facade `change_signature` | v1.1 |
| Restructure (pattern-based) | Rope `Restructure` | library bridge | pass-through (powerful but unsafe) | v1.1 |
| Convert sync→async (`def` → `async def`) | n/a | no LSP, ruff has detection only | facade composed by strategy | v1.1 |
| Generate code (variable, function, class, module) | pylsp-rope | `pylsp_rope.quickfix.generate` | facade `generate_from_undefined` | MVP |

#### Family: Diagnostics-only (read-only)

| Operation | Source | Exposure |
|---|---|---|
| Type errors | basedpyright + pylsp-mypy | passive; `diagnostics_delta` aggregates |
| Lint errors | ruff | passive |
| Pyflakes-style errors | (disabled in pylsp; covered by ruff F-rules) | passive (via ruff) |

### 4.2 By server — exhaustive command and code-action lists

#### pylsp-rope command identifiers (verified from `pylsp_rope/commands.py`)

```
pylsp_rope.refactor.extract.method
pylsp_rope.refactor.extract.variable
pylsp_rope.refactor.inline
pylsp_rope.refactor.use_function
pylsp_rope.refactor.method_to_method_object
pylsp_rope.refactor.local_to_field
pylsp_rope.source.organize_import
pylsp_rope.refactor.introduce_parameter
pylsp_rope.quickfix.generate
```

**Code-action kinds advertised by pylsp+pylsp-rope:** `quickfix`, `source.organizeImports`, `source.fixAll`, `refactor.extract`, `refactor.inline`, `refactor`, `source`. The specific sub-kind appears in returned actions; the advertised set is broad-prefix.

**Code-action titles emitted by pylsp-rope (verified from `pylsp_rope/plugin.py`):**

- "Extract method" / "Extract method including similar statements"
- "Extract variable" / "Extract variable including similar statements"
- "Inline method/variable/parameter"
- "Use function"
- "Use function for current file only"
- "To method object"
- "Convert local variable to field"
- "Organize import"
- "Introduce parameter"
- "Generate variable" / "Generate function" / "Generate class" / "Generate module" / "Generate package"

#### pylsp-mypy code actions

Per the [pylsp-mypy README](https://github.com/python-lsp/pylsp-mypy), pylsp-mypy emits **diagnostics only**. It does *not* register `quickfix` code actions. Type-ignore insertion is **not** provided by pylsp-mypy as of Apr 2026; we get it from basedpyright instead.

#### basedpyright commands and code actions

Verified from [basedpyright commands docs](https://docs.basedpyright.com/latest/usage/commands/) and the pyright/basedpyright source:

```
basedpyright.organizeImports             (we disable; ruff wins)
basedpyright.restartServer
basedpyright.writeBaseline
basedpyright.addOptionalForParam         (inferred from pyright)
basedpyright.createTypeStub              (inferred from pyright)
```

**Code actions:**

- Auto-import quickfix on `reportUndefinedVariable` (basedpyright re-implements the Pylance path)
- `# pyright: ignore` insertion on any diagnostic
- `# pyright: ignore[<rule>]` insertion (rule-specific)
- "Convert to f-string" (basedpyright-only, beyond pyright)
- "Add return type annotation" (when inferable)
- "Make function async" (limited, when call-site context implies async)
- Go-to-implementations (read-only navigation; not a code action)

#### ruff server code actions

Verified from [Ruff editor integration docs](https://docs.astral.sh/ruff/editors/features/):

```
quickfix                       (per-diagnostic fix)
source.fixAll.ruff             (apply every safe fix)
source.organizeImports.ruff    (isort-style import sorting)
notebook.source.fixAll         (Jupyter, defer)
notebook.source.organizeImports (Jupyter, defer)
```

Plus `# noqa` insertion (no explicit kind; surfaced as a quickfix on every diagnostic).

**Idempotency contract:** Ruff guarantees safe fixes converge after at most a few iterations. The strategy's `fix_lints` facade runs `source.fixAll.ruff` in a loop with a 5-iteration cap and content-hash cycle detection. If `iteration N` produces the same hash as iteration `N-1`, stop. If the cap is hit, return a warning.

#### pylsp default plugin code actions (with our config; most disabled)

| Plugin | Default state | Our state | Code actions |
|---|---|---|---|
| pylsp_jedi | on | on | go-to (read-only); no code actions |
| pyflakes | on | **off** (ruff covers) | none |
| pycodestyle | on | **off** (ruff covers) | none |
| mccabe | on | **off** | none |
| autopep8 | on | **off** (ruff covers) | none |
| yapf | off | off | none |
| pylint | off | off | none |
| flake8 | off | off | none |
| rope_completion | off | off | none |
| rope_autoimport | off | **on** | `quickfix` for missing imports (Rope path) |
| pydocstyle | off | off | none |
| pylsp_rope | (plugin) | on | nine commands above |
| pylsp_mypy | (plugin) | on | diagnostics only |

### 4.3 By exposure mode — what does the LLM see

| Exposure | Count | Examples |
|---|---|---|
| **Typed facade (MVP)** | 16 | `split_file`, `fix_imports`, `rollback`, `extract_method`, `extract_variable`, `inline`, `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `organize_imports`, `auto_import`, `fix_lints`, `ignore_diagnostic`, `rename_symbol` (existing) |
| **Typed facade (v1.1)** | 8 | `move_method`, `change_signature`, `introduce_factory`, `encapsulate_field`, `annotate_return_type`, `convert_to_async`, `convert_imports`, `move_symbol` |
| **Primitive bundled** | 1 | `apply_code_action` (covers everything else) |
| **Primitive separate (v1.1)** | 4 | `list_code_actions`, `resolve_code_action`, `execute_command`, `restructure` |

Coverage check: every action in §4.1 is reachable via at least one of the three exposure modes at MVP. The full-coverage directive is satisfied.

---

## 5. Code-action multiplexing — merge rules

### 5.1 The problem

When the agent calls `apply_code_action(file, range, kind=...)`, scalpel forwards `textDocument/codeAction` to **all three** Python LSPs in parallel. Each can return zero, one, or many actions. Examples of overlap:

- Same range, kind=`source.organizeImports`: pylsp-rope returns 1 action (Rope-style sort); ruff returns 1 action (isort-style); basedpyright is disabled. Two actions, different output.
- Same range, kind=`quickfix` on undefined variable: pylsp+rope_autoimport returns "Import `numpy`"; basedpyright returns "Add import: `numpy`". Two actions, possibly identical edit.
- Same range, kind=`source.fixAll`: ruff returns 1 action (apply all ruff fixes); pylsp-rope does not have this kind.
- Range=function body, kind=`refactor.extract`: pylsp-rope returns 2 actions ("Extract method", "Extract variable"); other servers return 0.

Without a merge rule, the LLM sees 3 organize-imports actions, 2 auto-import actions, etc. — confusing and non-deterministic.

### 5.2 The merge rule

**Two-stage process:** (1) priority filter, (2) dedup-by-equivalence.

#### Stage 1 — server priority per kind-prefix

| Kind prefix | Priority order (highest → lowest) | Rationale |
|---|---|---|
| `source.organizeImports` | ruff > pylsp-rope > basedpyright | Ruff is fastest and matches isort, the de-facto standard. |
| `source.fixAll` | ruff (unique) | Only ruff emits. |
| `quickfix` (auto-import context) | basedpyright > pylsp-rope (rope_autoimport) | Pylance heuristics are best-in-class. |
| `quickfix` (lint fix context) | ruff > pylsp-rope > basedpyright | Ruff owns lint. |
| `quickfix` (type error context) | basedpyright > pylsp-mypy | basedpyright's diagnostics are richer; mypy still runs for cross-validation. |
| `quickfix` (other) | pylsp-rope > basedpyright > ruff | Catch-all; pylsp-rope's `quickfix.generate` is unique. |
| `refactor.extract` | pylsp-rope (unique) | Only pylsp-rope emits. |
| `refactor.inline` | pylsp-rope (unique) | Only pylsp-rope emits. |
| `refactor.rewrite` | pylsp-rope > basedpyright | Both can emit; Rope is more thorough. |
| `refactor` (catch-all) | pylsp-rope > basedpyright | Pylsp-rope owns the refactor surface. |
| `source` (catch-all) | ruff > pylsp-rope > basedpyright | Ruff owns source-level transforms. |

The "context" disambiguators inside `quickfix` are inferred from the action's title and the diagnostic that triggered it. Implementation in §5.3.

#### Stage 2 — dedup-by-equivalence

For actions surviving Stage 1, dedup if **any** of:

1. Normalized title equality. Normalization: lowercase, strip leading "Add: " / "Quick fix: ", collapse whitespace. `"Import 'numpy'"` and `"Add import: numpy"` normalize to `"import numpy"`.
2. `WorkspaceEdit` structural equality: same set of `(uri, range, newText)` triples after applying the resolve step. Computed lazily — only on titles that *don't* match.

Tiebreak: prefer the higher-priority server's action.

### 5.3 Title-context inference for `quickfix` disambiguation

Build a small static table mapping triggering-diagnostic codes to context buckets:

| Diagnostic source | Diagnostic code | Context bucket |
|---|---|---|
| basedpyright | `reportUndefinedVariable` | auto-import |
| basedpyright | `reportMissingImports` | auto-import |
| pyflakes (via pylsp, off) | F401, F811 | auto-import |
| ruff | F401 | lint fix |
| ruff | E501, E712, ... | lint fix |
| ruff | UP*, FA*, TID*, ... | lint fix |
| basedpyright | `reportGeneralTypeIssues` | type error |
| pylsp-mypy | mypy error code | type error |
| (no diagnostic, action is `quickfix.generate`) | n/a | other |

`apply_code_action` looks up the diagnostic that triggered the action and routes to the right priority row.

### 5.4 What the LLM sees

After both stages, the LLM gets at most one action per `(kind-prefix, normalized-title)` tuple. Typical case: 1–3 actions per range. Non-determinism is eliminated; the same input always produces the same merged list.

The merged result includes a `provenance` field so the LLM (and integration tests) can see which server emitted the surviving action:

```python
class CodeActionDescriptor(BaseModel):
    id: str
    title: str
    kind: str
    disabled_reason: str | None
    is_preferred: bool
    provenance: Literal["pylsp-rope", "pylsp-base", "basedpyright", "ruff", "pylsp-mypy"]
    suppressed_alternatives: list[SuppressedAlternative] = []  # what the merge dropped
```

`suppressed_alternatives` is empty by default; populate when `O2_SCALPEL_DEBUG_MERGE=1`. Useful for triaging "why did scalpel pick the ruff action over Rope's?" without rerunning the request.

### 5.5 Edge cases

| Case | Resolution |
|---|---|
| Server returns an action with kind `null` or unrecognized | Bucket as `quickfix.other`; lowest priority. |
| All three servers return the same action with byte-identical `WorkspaceEdit` | Pick highest-priority provenance; suppress the rest. |
| Two servers return the same kind but on different ranges (one wider, one narrower) | Treat as different actions; do not dedup. The LLM picks via title. |
| Server returns an action whose `disabled.reason` is set | Preserve in the merged list; LLM can see why it's disabled. Do not silently drop. |
| Server times out (>2 s for `codeAction`) | Continue with the actions from servers that responded; emit `warnings: ["server X timed out on codeAction"]`. |
| Two servers' actions resolve to overlapping `WorkspaceEdit`s (one is a subset of the other) | Pick the higher-priority server; warn only if the lower-priority would have produced changes the higher-priority does not. |

---

## 6. Rope coverage matrix

Every Rope refactor × MVP exposure. "Verified from `rope.refactor.*` modules per [Rope library docs](https://rope.readthedocs.io/en/latest/library.html)."

| Rope module | Class | pylsp-rope command? | Strategy bridge? | MVP exposure |
|---|---|---|---|---|
| `rope.refactor.rename` | `Rename` | yes (via `textDocument/rename`) | n/a | facade `rename_symbol` (existing) |
| `rope.refactor.move` | `MoveGlobal` | no (only via composition) | yes | composed inside `split_file`; standalone `move_symbol` v1.1 |
| `rope.refactor.move` | `MoveModule` | yes (via rename on file URI) | n/a | facade `rename_module` MVP |
| `rope.refactor.move` | `MoveMethod` | no | yes | facade `move_method` v1.1 |
| `rope.refactor.move` | `create_move` (factory) | partial | yes | internal use by strategy |
| `rope.refactor.extract` | `ExtractMethod` | yes (`pylsp_rope.refactor.extract.method`) | n/a | facade `extract_method` MVP |
| `rope.refactor.extract` | `ExtractVariable` | yes (`pylsp_rope.refactor.extract.variable`) | n/a | facade `extract_variable` MVP |
| `rope.refactor.inline` | `Inline` (auto-detects) | yes (`pylsp_rope.refactor.inline`) | n/a | facade `inline` MVP |
| `rope.refactor.inline` | `InlineMethod` | covered by `Inline` | n/a | (no separate facade) |
| `rope.refactor.inline` | `InlineVariable` | covered by `Inline` | n/a | (no separate facade) |
| `rope.refactor.inline` | `InlineParameter` | covered by `Inline` | n/a | (no separate facade) |
| `rope.refactor.change_signature` | `ChangeSignature` | no | yes | facade `change_signature` v1.1 |
| `rope.refactor.method_object` | `MethodObject` | yes (`pylsp_rope.refactor.method_to_method_object`) | n/a | facade `convert_to_method_object` MVP |
| `rope.refactor.encapsulate_field` | `EncapsulateField` | no | yes | facade `encapsulate_field` v1.1 |
| `rope.refactor.introduce_factory` | `IntroduceFactory` | no | yes | facade `introduce_factory` v1.1 |
| `rope.refactor.introduce_parameter` | `IntroduceParameter` | yes (`pylsp_rope.refactor.introduce_parameter`) | n/a | facade `introduce_parameter` MVP |
| `rope.refactor.localtofield` | `LocalToField` | yes (`pylsp_rope.refactor.local_to_field`) | n/a | facade `local_to_field` MVP |
| `rope.refactor.usefunction` | `UseFunction` | yes (`pylsp_rope.refactor.use_function`) | n/a | facade `use_function` MVP |
| `rope.refactor.restructure` | `Restructure` | no | yes | pass-through `restructure` v1.1 |
| `rope.refactor.restructure` | `RestructureRegion` | no | yes | pass-through v1.1 |
| `rope.refactor.importutils` | `ImportTools.organize_imports` | yes (`pylsp_rope.source.organize_import`) | n/a | facade `organize_imports(engine="rope")` MVP |
| `rope.refactor.importutils` | `ImportTools.handle_long_imports` | no | yes | pass-through v1.1 |
| `rope.refactor.importutils` | `ImportTools.relative_to_absolute` | no | yes | facade `convert_imports(style="absolute")` v1.1 |
| `rope.refactor.importutils` | `ImportTools.froms_to_imports` | no | yes | facade `convert_imports(style="from")` v1.1 |
| `rope.refactor.importutils` | `ImportTools.expand_stars` | no | yes | facade `expand_star_imports` v1.1 |
| (top-level) | `rope.contrib.codeassist` | no (read-only) | n/a | not in scope |

**Library-bridge total: 10 ops** that need a direct Rope library call from the strategy (no LSP path). Estimated bridge LoC: ~280 across 10 thin functions, each a `rope.project.Project` setup + the specific class invocation + `ChangeSet → WorkspaceEdit` conversion.

**Bridge-shape rule:** every library-bridge call returns the same `WorkspaceEdit` shape that pylsp-rope would have returned via the LSP path. The applier (§8) is unaware of which path produced the edit. This keeps the merge rule (§5) and the rollback machinery oblivious to the bridge.

---

## 7. Interpreter / environment discovery

Full-coverage Python LSP support requires resolving the project's interpreter so pylsp's `jedi.environment`, basedpyright's `python.pythonPath`, and ruff's interpreter inference all agree.

### 7.1 The twelve-step resolution chain

Strict order, fail loud at the end. Each step's win condition is "produces an absolute path to a `python` executable that exists and is runnable."

| # | Source | Win condition | Cost |
|---|---|---|---|
| 1 | `$O2_SCALPEL_PYTHON_EXECUTABLE` | env var set, file exists, executable | trivial |
| 2 | `[tool.o2-scalpel] python_executable` in `pyproject.toml` | TOML key present, path exists | one file read |
| 3 | `$VIRTUAL_ENV/bin/python` | env var set, file exists | trivial |
| 4 | `<project-root>/.venv/bin/python` | sibling `.venv/` (most common layout) | one stat |
| 5 | `<project-root>/venv/bin/python` | sibling `venv/` | one stat |
| 6 | `<project-root>/__pypackages__/<py-version>/bin/python` (PEP 582 / PDM) | dir exists | one stat |
| 7 | `poetry env info -p` if `poetry.lock` present | exit 0, valid path | subprocess (~200 ms) |
| 8 | `pdm info --packages` if `pdm.lock` present | exit 0, valid path | subprocess |
| 9 | `uv run --no-project which python` if `uv.lock` present | exit 0, valid path | subprocess |
| 10 | `pipenv --venv` if `Pipfile.lock` present | exit 0, valid path | subprocess |
| 11 | `$CONDA_PREFIX/bin/python` if env var set (conda / micromamba) | file exists | trivial |
| 12 | `pyenv which python` if `.python-version` present | exit 0, valid path | subprocess |
| 13 | `asdf which python` if `.tool-versions` present | exit 0, valid path | subprocess |
| 14 | first `python3` on `$PATH` whose `sys.prefix` differs from system Python | hint of project-local install | one subprocess |
| 15 | `sys.executable` of scalpel process | last resort, deterministic | trivial |
| 16 | **Fail loud** with the full attempted chain in the error message | n/a | n/a |

(The list grew from the narrow brief's ten steps to fourteen + fail-loud; PEP 582, pipenv, asdf, and the path-walk heuristic are the additions.)

### 7.2 Caching the result

Once resolved, cache `(project_root, interpreter_path, python_version, sys.prefix)` in-process for the LSP-server lifetime. Re-resolve only when:

- The watcher detects a change to `pyproject.toml` / `poetry.lock` / `pdm.lock` / `uv.lock` / `Pipfile.lock` / `.python-version` / `.tool-versions`.
- The user calls `scalpel_reload_plugins` (existing v1.1 mechanism per main design §Q10).

Cache invalidation is critical: a venv recreation between scalpel sessions must not produce stale `unresolved import` errors. Solution: stat the resolved `python` binary on each LSP request that depends on it; if mtime/inode changed, re-run the chain.

### 7.3 Where the resolved path is injected

Per §3.5 above, into:

- `pylsp.plugins.jedi.environment` (string path)
- `pylsp.plugins.pylsp_mypy.overrides` as `--python-executable=<path>`
- `basedpyright.initializationOptions.python.pythonPath`
- `ruff` does not currently accept a `--python` flag at server startup as of Apr 2026, but does honor `target-version` in `pyproject.toml`. If the resolved Python's version differs from the project's declared `target-version`, scalpel emits a warning. The strategy passes the resolved Python to ruff via the env var `RUFF_PYTHON_VERSION` (no-op if unsupported; harmless).

### 7.4 Failure mode

If step 16 hits, scalpel fails with:

```python
{
  "kind": "interpreter_unresolved",
  "attempted": [
    {"step": 1, "source": "$O2_SCALPEL_PYTHON_EXECUTABLE", "result": "not set"},
    {"step": 2, "source": "pyproject.toml", "result": "no [tool.o2-scalpel]"},
    ...
  ],
  "hint": "Set O2_SCALPEL_PYTHON_EXECUTABLE or activate a venv before invoking scalpel."
}
```

This is machine-readable; the LLM can act on the hint without scraping.

### 7.5 Multi-interpreter projects

Out of scope for MVP. A monorepo with `service-a/` on Python 3.10 and `service-b/` on Python 3.13 needs per-subtree interpreter resolution. Defer to v1.1 with a `[tool.o2-scalpel.subtrees]` config block in the root `pyproject.toml`.

---

## 8. `WorkspaceEdit` shapes — Python LSP applier matrix

### 8.1 What each server emits

Three independent pieces of evidence ([LSP 3.17 spec §3.16](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/), [pylsp-rope plugin source](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/plugin.py), [ruff server source](https://github.com/astral-sh/ruff)) combine into:

| Server | Default emit shape | Resource ops? | `changeAnnotations`? | `documentChanges` versioned? |
|---|---|---|---|---|
| pylsp + pylsp-rope (refactor commands) | `documentChanges` with `TextDocumentEdit` | yes — `RenameFile` on module rename (Rope path) | no | yes (server tracks `LSPFileBuffer.version`) |
| pylsp + pylsp-rope (older code paths) | sometimes `changes` map (legacy) | no | no | no — fallback applier needed |
| pylsp + rope_autoimport | `documentChanges` with `TextDocumentEdit` | no | no | yes |
| pylsp-mypy | n/a (diagnostics only) | n/a | n/a | n/a |
| basedpyright | `documentChanges` consistently | no MVP path emits resource ops; v1.1 createstub may | no | yes |
| ruff server | `documentChanges` with `TextDocumentEdit` | no | no | yes |
| Strategy library bridge (Rope direct) | constructs `documentChanges` to match pylsp-rope's shape | yes — `CreateFile` + `RenameFile` for `MoveModule`, `IntroduceFactory`, etc. | no | yes |

### 8.2 Applier behavior matrix

The Serena applier from main design §1.4 already supports `TextDocumentEdit`, `CreateFile`, `RenameFile`. For Python full-coverage we extend with three rules:

1. **Old-style `changes` map fallback.** If a server returns a `WorkspaceEdit` with `changes` but no `documentChanges`, convert to the new shape internally before applying. Order is undefined in the old shape; sort URIs alphabetically and apply.
2. **Multi-server transactions.** A facade that aggregates edits from multiple LSPs (e.g., `fix_imports` running ruff's `source.organizeImports.ruff` then pylsp-rope's `source.organize_import` as a fallback) must wrap them in a single checkpoint. Apply in priority order; rollback on any failure.
3. **Library-bridge edit conversion.** Rope's `ChangeSet` (returned by `MoveGlobal`, `IntroduceFactory`, etc. when invoked directly) converts to `WorkspaceEdit` via a shim:
   - Each `Change` of kind `ChangeContents` → one `TextDocumentEdit`.
   - `CreateResource(folder)` → `CreateFile` with `options.recursive = true`.
   - `CreateResource(file)` → `CreateFile`.
   - `MoveResource` → `RenameFile`.
   - `RemoveResource` → `DeleteFile`.

### 8.3 Edit-attribution log

For every applied edit, scalpel writes a line to `.serena/python-edit-log.jsonl`:

```jsonc
{"ts": "2026-04-24T10:01:23Z",
 "checkpoint_id": "ckpt_py_3c9",
 "tool": "split_file",
 "server": "pylsp-rope",
 "kind": "TextDocumentEdit",
 "uri": "file:///.../calcpy/parser.py",
 "edit_count": 12,
 "version": 47}
```

Used by `rollback` for inverse-edit replay and by E2E integration tests for trace forensics. Idempotent — replaying the log replays the exact session.

---

## 9. Python-specific facades beyond the cross-language base

Below, **MVP** facades and **v1.1** facades are listed separately. Each MVP facade has a Pydantic signature and a one-line composition note. The cross-language base already has `split_file`, `fix_imports`, `rollback`, `apply_code_action`, `rename_symbol` — those are not repeated.

### 9.1 MVP facades (Python-specific)

```python
def extract_method(
    file: str,
    range: Range,
    new_name: str,
    similar: bool = False,
    global_scope: bool = False,
    dry_run: bool = False,
) -> RefactorResult:
    """Extract `range` into a new method/function.
    Calls pylsp-rope `pylsp_rope.refactor.extract.method`.
    `similar=True` rewrites every clone of the extracted block.
    `global_scope=True` extracts to module level (a function), not a method."""

def extract_variable(
    file: str,
    range: Range,
    new_name: str,
    similar: bool = False,
    global_scope: bool = False,
    dry_run: bool = False,
) -> RefactorResult:
    """Extract expression in `range` into a new variable.
    Calls pylsp-rope `pylsp_rope.refactor.extract.variable`."""

def inline(
    file: str,
    name_path: str,
    only_at: Range | None = None,
    remove_definition: bool = True,
    dry_run: bool = False,
) -> RefactorResult:
    """Inline `name_path` at all call/use sites (or at `only_at` if given).
    Calls pylsp-rope `pylsp_rope.refactor.inline`. Auto-detects whether
    target is method, variable, or parameter."""

def convert_to_method_object(
    file: str,
    name_path: str,            # method name-path
    new_class_name: str,
    dry_run: bool = False,
) -> RefactorResult:
    """Replace a method with an object whose __call__ does the work.
    Calls pylsp-rope `pylsp_rope.refactor.method_to_method_object`."""

def local_to_field(
    file: str,
    name_path: str,            # local variable name-path inside a method
    field_name: str | None = None,
    dry_run: bool = False,
) -> RefactorResult:
    """Promote a local variable to a class field.
    Calls pylsp-rope `pylsp_rope.refactor.local_to_field`."""

def use_function(
    file: str,
    name_path: str,            # the function to use
    scope: Literal["file", "project"] = "file",
    dry_run: bool = False,
) -> RefactorResult:
    """Find code blocks equivalent to `name_path`'s body and replace them
    with calls to `name_path`. Calls pylsp-rope `pylsp_rope.refactor.use_function`."""

def introduce_parameter(
    file: str,
    name_path: str,            # function name-path
    expression_range: Range,   # what to lift to a parameter
    parameter_name: str,
    dry_run: bool = False,
) -> RefactorResult:
    """Lift `expression_range` inside `name_path`'s body to a new parameter.
    Calls pylsp-rope `pylsp_rope.refactor.introduce_parameter`."""

def generate_from_undefined(
    file: str,
    range: Range,              # cursor on an undefined name
    target: Literal["variable", "function", "class", "module", "package"],
    location_hint: str | None = None,
    dry_run: bool = False,
) -> RefactorResult:
    """Create a stub for an undefined name that the LLM intends to define.
    Calls pylsp-rope `pylsp_rope.quickfix.generate`."""

def organize_imports(
    files: list[str],
    engine: Literal["ruff", "rope", "basedpyright", "auto"] = "auto",
    dry_run: bool = False,
) -> RefactorResult:
    """Sort and group imports per the chosen engine.
    `auto` uses the merge priority (§5): ruff > rope > basedpyright.
    Iterates per-file; merges all edits into one checkpoint."""

def auto_import(
    file: str,
    range: Range,              # location of the undefined name
    target_name: str | None = None,  # disambiguates when there are multiple candidates
    prefer: Literal["basedpyright", "rope"] = "basedpyright",
    dry_run: bool = False,
) -> RefactorResult:
    """Add the missing `import` line for an undefined name in `range`.
    Defaults to basedpyright's Pylance-port path; falls back to rope_autoimport."""

def fix_lints(
    files: list[str],
    rules: list[str] | None = None,    # e.g. ["F401", "UP*"] or None for all
    apply_unsafe: bool = False,
    iteration_cap: int = 5,
    dry_run: bool = False,
) -> RefactorResult:
    """Apply ruff's `source.fixAll.ruff` iteratively. Stops when the
    content hash converges or `iteration_cap` is hit. Returns warnings
    on cap-hit. Set `apply_unsafe=True` to enable ruff's unsafe fixes."""

def ignore_diagnostic(
    file: str,
    range: Range,
    tool: Literal["ruff", "pyright", "mypy"],
    rule_code: str | None = None,
    scope: Literal["line", "file", "block"] = "line",
    dry_run: bool = False,
) -> RefactorResult:
    """Insert the appropriate ignore comment.
      ruff   → `# noqa: <code>`
      pyright→ `# pyright: ignore[<code>]`
      mypy   → `# type: ignore[<code>]`
    `scope='file'` adds a module-level pragma."""
```

### 9.2 v1.1 facades (deferred, but reachable via primitives at MVP)

```python
def move_symbol(...)                # standalone Rope MoveGlobal
def move_method(...)                # Rope MoveMethod
def change_signature(...)           # Rope ChangeSignature
def introduce_factory(...)          # Rope IntroduceFactory
def encapsulate_field(...)          # Rope EncapsulateField
def annotate_return_type(...)       # basedpyright code action
def convert_to_async(...)           # composed; see §11
def convert_imports(...)            # Rope relative_to_absolute / froms_to_imports
def expand_star_imports(...)        # Rope ImportTools.expand_stars
def restructure(...)                # Rope Restructure (powerful, advanced; pass-through)
```

### 9.3 Facade-vs-primitive split rationale

The MVP facade list is sized at 12 Python-specific facades + 5 cross-language facades = 17 typed tools. Beyond that count, each additional facade is a token-cost amortization play:

- A tool the LLM uses ≥1 time per session ⇒ facade pays for itself in saved primitive round-trips.
- A tool the LLM uses <1 time per session ⇒ pass-through via `apply_code_action` is enough.

The MVP cut places `extract_method`, `extract_variable`, `inline`, `organize_imports`, `auto_import`, `fix_lints` in the high-frequency bucket. Conservative reasoning: these mirror the six most-clicked refactor menu items in JetBrains and VSCode telemetry. The v1.1-deferred facades are lower-frequency.

---

## 10. Pre-MVP spikes — what to probe before committing

Six spikes; the first two are blocking, the others are diagnostic.

### 10.1 [BLOCKING] pylsp-rope unsaved-buffer behavior

**Question.** When scalpel sends `didOpen` + `didChange` (no `didSave`), does pylsp-rope return `WorkspaceEdit`s computed against the in-memory buffer or the on-disk file?

**Why it matters.** Scalpel runs headless; "the file on disk" lags the buffer between turn N and turn N+1. Stale edits corrupt files.

**Spike shape.** 50-line script: spawn pylsp via solidlsp, open `calcpy.py`, send `didChange` with a unique marker comment, request `codeAction(refactor.extract.method)` over a range crossing the marker, resolve, inspect the returned edit. Pass = edit references the marker.

**Mitigation if it fails.** Force `didSave({includeText: true})` before every code-action call. Costs one round-trip per call; eliminates the staleness class. The narrow brief §9.1 already prescribed this.

### 10.2 [BLOCKING] Conflicting `source.organizeImports` between pylsp-rope and ruff

**Question.** Given the same input file, do pylsp-rope's `pylsp_rope.source.organize_import` and ruff's `source.organizeImports.ruff` produce the same output? If not, what differs (group order, blank lines, alphabetization rule, `from` vs flat)?

**Why it matters.** The merge rule (§5) prefers ruff for organize-imports. If ruff's output differs from rope's in user-visible ways, users with project conventions tuned to one tool will see drift.

**Spike shape.** Run both organize-imports on the `calcpy/calcpy.py` fixture; diff output. Document differences.

**Mitigation.** Document the chosen tool. Provide a strategy-level config `organize_imports_engine: {"ruff", "rope"}` (default `ruff`) that lets users pin. Already supported by the `engine` parameter in §9.1's `organize_imports` facade.

### 10.3 Rope's `MoveGlobal` against a 3.13-syntax file

**Question.** Does Rope (current version) parse PEP 695 generic syntax, PEP 701 f-string nesting, PEP 654 exception groups?

**Why it matters.** A parse failure aborts the entire move, not just the unsupported construct.

**Spike shape.** Author one file using each PEP in `calcpy`'s test/fixture variants; run `MoveGlobal` of an unrelated symbol; observe parser behavior.

**Mitigation.** Pin Rope to the latest version. Document supported Python minimum (3.10) and known-working maximum (probably 3.12; 3.13+ likely works but unverified).

### 10.4 basedpyright `relatedInformation` on diagnostics

**Question.** Does basedpyright populate `Diagnostic.relatedInformation` with cross-file context for reportUndefinedVariable, reportMissingImports?

**Why it matters.** Auto-import quality depends on resolution candidates; `relatedInformation` is the channel for "we found `numpy` at site-packages/numpy/__init__.py".

**Spike shape.** Trigger `reportUndefinedVariable` in calcpy; inspect the diagnostic JSON.

**Mitigation.** None needed — passive observation. If absent, document and ship without that tooltip detail.

### 10.5 ruff `source.fixAll.ruff` idempotency under autofix cascades

**Question.** When ruff applies fixes that introduce new lints (e.g., `from __future__ import annotations` triggers `UP`-rule reformatting), does iteration N produce a stable hash, or do we cycle?

**Why it matters.** §9.1's `fix_lints` facade caps iterations at 5. If realistic projects need >5, raise the cap or document the case.

**Spike shape.** Construct a calcpy variant with overlapping autofix triggers; run `source.fixAll.ruff` until convergence; record iteration count.

**Mitigation.** Adjust cap. If pathological (cycles), require `--unsafe-fixes` to be explicit and surface as a warning.

### 10.6 Three-server `textDocument/rename` response convergence

**Question.** When the agent calls `rename_symbol("Evaluator", "Calc")`, do pylsp-rope and basedpyright both respond with `WorkspaceEdit`? If both, do they match?

**Why it matters.** The merge rule for `textDocument/rename` differs from `textDocument/codeAction` — rename is a single-response method, not a list. Two LSPs returning two `WorkspaceEdit`s cannot both be applied without conflict.

**Spike shape.** Issue rename via solidlsp; capture responses from all three servers (basedpyright, pylsp, ruff — though ruff returns null).

**Mitigation.** Define a rename-server-priority: pylsp-rope > basedpyright. Send rename only to the primary; ignore the secondary. Document the choice.

---

## 11. Fixture `calcpy` — expanded for full coverage

The narrow brief (§6) sized `calcpy` at ~900 LoC with ten ugly-on-purpose features. Full coverage demands more — the fixture must be a regression net for **every** Python edge case the strategy claims to handle. Expanded spec below.

### 11.1 Size and shape

| Item | Narrow | Full coverage |
|---|---|---|
| Total LoC across `calcpy/` package | ~900 | ~1,250 |
| Top-level files in package | 1 (`calcpy.py`) | 1 (`calcpy.py`) — still monolithic before refactor |
| Sibling stub | `calcpy.pyi` ~80 LoC | `calcpy.pyi` ~120 LoC |
| Companion sub-fixtures (separate dirs) | 0 | 4 (see §11.3) |
| Test LoC | ~200 | ~350 (covers added pitfalls) |
| Doctest LoC | minimal | 4 docstrings exercising doctest discovery |

### 11.2 Pitfall coverage matrix — every pitfall has at least one trigger

| # | Pitfall | Trigger location | LSP exercised | Test gate |
|---|---|---|---|---|
| 1 | Star imports hide move graph | `from math import *` at top | pylsp-rope MoveGlobal | E4-py |
| 2 | `__init__.py` side effects | `_initialize_logging()` at module top | strategy's package-conversion path | E1-py warning surface |
| 3 | PEP 420 namespace packages | sub-fixture `calcpy_namespace/` (no `__init__.py`) | strategy detection | E8-py |
| 4 | Stub drift | `.pyi` sibling | strategy stub-twin handling | E9-py |
| 5 | Circular imports post-split | engineered SCC: `evaluator → parser → evaluator` | strategy import-graph check | E5-py |
| 6 | Implicit relative imports (Py2 legacy) | (skipped — Python 3 syntax error; document only) | n/a | n/a |
| 7 | Runtime-injected attributes | `Evaluator.cache = {}` after class | Rope MoveGlobal scan | E1-py warning |
| 8 | `__all__` preservation | `__all__ = ["run", "VERSION", "Value", "CalcError"]` | strategy reexport policy | E10-py |
| 9 | `pytest` discovery breakage | `tests/test_calcpy.py` imports moved symbols | strategy import rewriting | E1-py + E9-py |
| 10 | Jupyter notebooks | sub-fixture `calcpy_notebooks/` with one `.ipynb` | strategy detection + warn | E11-py |
| 11 | `TYPE_CHECKING` blocks | `if TYPE_CHECKING: from .helpers import Cache` | strategy post-pass rewrite | dedicated test |
| 12 | `from __future__ import annotations` | top of `calcpy.py` | strategy preservation | E1-py |
| 13 | PEP 695 generic syntax | `class Container[T]: ...` (3.12+) | Rope parser | spike 10.3 |
| 14 | PEP 701 f-string nesting | one f-string with nested quotes (3.12+) | Rope parser | spike 10.3 |
| 15 | `@dataclass` that wants restructuring | `@dataclass class Token: ...` | extract/inline interaction | dedicated test |
| 16 | `async def` and `await` | one async helper `async def fetch_constant(name)` | convert_to_async target (v1.1) | placeholder gate |
| 17 | Decorator stack on top-level | `@cached_property`, `@staticmethod`, `@classmethod` | top-level detection | E10-py |
| 18 | `_private` naming + `__name_mangle` | both forms in fixture | visibility preservation | dedicated test |
| 19 | Conditional top-level (`if sys.version_info >= ...`) | one such block | top-level detection | warn surface |
| 20 | `from __future__ import` placement constraint | first non-docstring statement | strategy preserve-position | E1-py |
| 21 | Docstring with embedded examples (doctest) | `run()` docstring | pytest --doctest-modules | dedicated gate |
| 22 | `if __name__ == "__main__":` | bottom of `calcpy.py` | preservation in entry point | E1-py |
| 23 | Module-level lazy imports (inside `try/except ImportError`) | one such block | preserve-as-is | dedicated test |
| 24 | Monkey-patched stdlib | one `os.environ` mutation at module top | side-effect warning | E1-py warning |

### 11.3 Sub-fixture spec

Four companion fixtures, each a small repo-local dir, each ~80–250 LoC, each exercising one cross-cutting concern.

#### 11.3.1 `calcpy_namespace/` — PEP 420 namespace package

Layout:

```
calcpy_namespace/
  ns_root/                  # no __init__.py, namespace package
    calcpy_ns/              # no __init__.py
      core.py               # ~120 LoC; the symbols to move
  tests/test_namespace.py
```

Test gate E8-py: split `core.py`'s symbols across new files; strategy must NOT create `__init__.py`. Verify via `python -c "import calcpy_ns; print(calcpy_ns.__path__)"` post-refactor.

#### 11.3.2 `calcpy_circular/` — circular-import trap

Layout:

```
calcpy_circular/
  __init__.py                # imports from a, then b
  a.py                       # contains class A; imports b.B at top
  b.py                       # contains class B; imports a.A inside function (works)
```

Goal: any move that lifts the lazy `a.A` reference to top-level breaks; strategy detects this in dry-run.

#### 11.3.3 `calcpy_dataclasses/` — dataclass restructure

Layout:

```
calcpy_dataclasses/
  __init__.py                # one file with five @dataclass declarations
  tests/test_dc.py
```

Test gate: extract one `@dataclass` to a sub-module via `extract_symbols_to_module` (v1.1 facade); decorator-discovered top-level resolution must succeed.

#### 11.3.4 `calcpy_notebooks/` — `.ipynb` companion

Layout:

```
calcpy_notebooks/
  notebooks/
    explore.ipynb            # JSON cell that does `from calcpy import evaluate`
  src/
    calcpy.py                # canonical fixture (link or copy)
```

Test gate E11-py: scalpel detects the notebook, warns "notebook imports calcpy.evaluate; refactor will not rewrite notebook cells"; refactor proceeds with the warning recorded.

### 11.4 Baseline contract

Each fixture has a `expected/baseline.txt` with frozen `pytest -q` output. Refactor scenarios must produce **byte-identical** output post-refactor. Same rule as the narrow brief; expanded to cover all four sub-fixtures.

### 11.5 LoC accounting

| File | LoC |
|---|---|
| `calcpy/calcpy.py` (monolith) | 950 |
| `calcpy/calcpy.pyi` (stub) | 120 |
| `calcpy/__init__.py` (re-exports) | 15 |
| `tests/test_calcpy.py` | 220 |
| `tests/test_public_api.py` | 60 |
| `tests/test_doctests.py` | 30 |
| `pyproject.toml` | 25 |
| `calcpy_namespace/` (sub-fixture, total) | 180 |
| `calcpy_circular/` (sub-fixture, total) | 90 |
| `calcpy_dataclasses/` (sub-fixture, total) | 220 |
| `calcpy_notebooks/` (sub-fixture, total) | 100 |
| Expected-state snapshots | 250 |
| **Total** | **~2,260 LoC** (1,250 main + 1,010 sub-fixtures + tests) |

---

## 12. Abstraction pressure under full coverage

The narrow brief (§5) flagged three friction points in the main design's `LanguageStrategy` Protocol: `parent_module_style` jargon, `extract_module_kind` Rust-centric, `module_declaration_syntax` Rust-centric. Those still apply, all resolved as the narrow brief proposed.

Under full coverage, **nine more methods are needed** because the Python strategy now owns more behaviors than the cross-language base accounted for. Rather than bloat the base Protocol, expose them as a `PythonStrategyExtensions` mixin.

### 12.1 Required extension methods

```python
class PythonStrategyExtensions(Protocol):
    """Python-only methods the cross-language LanguageStrategy does not need.
    Shipped as a mixin so the base Protocol stays small."""

    # --- Layout discovery ---------------------------------------------
    def is_namespace_package(self, project_root: Path) -> bool: ...
        # Heuristic from narrow brief §4.4 — detects PEP 420 layout.

    def detect_init_side_effects(self, init_path: Path) -> list[SideEffect]: ...
        # Returns a list of statements at module top that aren't def/class/import.

    # --- Public-API surface management --------------------------------
    def parse_dunder_all(self, file_path: Path) -> list[str] | None: ...
        # Returns the names in __all__ if declared, else None.

    def update_dunder_all(
        self, file_path: Path, additions: list[str], removals: list[str]
    ) -> WorkspaceEdit: ...

    # --- Type-system glue --------------------------------------------
    def has_type_checking_block(self, file_path: Path) -> bool: ...
    def rewrite_type_checking_imports(
        self, file_path: Path, name_map: dict[str, str]
    ) -> WorkspaceEdit: ...

    def has_future_annotations(self, file_path: Path) -> bool: ...

    # --- Stub-file twin handling --------------------------------------
    def stub_file_for(self, source_path: Path) -> Path | None: ...
    def split_stub_alongside(
        self, stub_path: Path, symbol_groups: dict[str, list[str]]
    ) -> WorkspaceEdit: ...

    # --- Async detection ----------------------------------------------
    def is_async_definition(self, symbol: DocumentSymbol) -> bool: ...
        # True iff the symbol's first source line starts with `async def`.

    # --- Decorator-aware top-level resolution -------------------------
    def resolve_decorated_top_level(
        self, file_path: Path, source_symbols: list[DocumentSymbol]
    ) -> list[ResolvedTopLevel]: ...
        # Filters out decorator-generated bindings;
        # marks @staticmethod / @classmethod / @property / @cached_property
        # so the strategy preserves them on move.

    # --- Import normalization ----------------------------------------
    def normalize_relative_imports(
        self, file_path: Path, mode: Literal["absolute", "relative"]
    ) -> WorkspaceEdit: ...

    # --- Circular-import detection -----------------------------------
    def find_import_cycles(self, project_root: Path) -> list[list[str]]: ...
        # Tarjan SCC over the import graph; returns nontrivial components.
```

### 12.2 Why a mixin, not Protocol expansion

Two reasons.

First, **YAGNI for non-Python languages.** Rust does not need `parse_dunder_all` or `has_type_checking_block`. Adding these to the base Protocol forces every language strategy to implement nine no-op stubs. The mixin lets the base Protocol stay at the original ~12 methods.

Second, **TRIZ separation of cross-cutting concerns.** Stub-file twin handling is structurally separate from Python's other concerns (it's about `.pyi` companion files); it could in principle be extracted into a `StubFileStrategy` sub-mixin. We keep it inside `PythonStrategyExtensions` for now because no other language strategy needs `.pyi`-like behavior in MVP scope; revisit if TypeScript's `.d.ts` warrants reuse.

### 12.3 Facade access pattern

```python
def split_file(file: str, groups: ..., dry_run: bool = False) -> RefactorResult:
    strategy = registry.lookup(file)             # PythonStrategy, RustStrategy, ...
    if isinstance(strategy, PythonStrategy):
        if strategy.find_import_cycles(project_root_of(file)):
            warnings.append("circular_imports_detected")
        # ... etc
```

The facade can do `isinstance` checks against `PythonStrategy` because it lives in the language-agnostic facade module. Python-specific concerns are walled off but reachable.

### 12.4 LoC budget for the extensions

Per §12.1's nine methods:

| Method | LoC |
|---|---|
| `is_namespace_package` | 25 |
| `detect_init_side_effects` | 40 (AST walk) |
| `parse_dunder_all` | 30 |
| `update_dunder_all` | 35 |
| `has_type_checking_block` | 15 |
| `rewrite_type_checking_imports` | 60 |
| `has_future_annotations` | 10 |
| `stub_file_for` | 15 |
| `split_stub_alongside` | 80 (text-based AST split) |
| `is_async_definition` | 10 |
| `resolve_decorated_top_level` | 50 |
| `normalize_relative_imports` | 50 |
| `find_import_cycles` | 60 (Tarjan + AST scan) |
| **Subtotal** | **~480 LoC** |

This subtotal is included in §13's strategy-core LoC line, not double-counted.

---

## 13. Re-estimated LoC under full coverage

The orchestrator's per-component estimate proposed:

> strategy ~400 LoC, facades (Python-specific) ~600 LoC, applier multi-server multiplexer ~400 LoC, interpreter-discovery ~200 LoC, fixture ~1200 LoC, tests ~1000 LoC.

My sanity check, with each line discussed:

| Component | Orchestrator | This report | Delta | Reason |
|---|---|---|---|---|
| `PythonStrategy` core (incl. extensions §12) | ~400 | ~420 | +20 | Nine extension methods need ~480 LoC; some overlap with already-included virtualenv chain. |
| Python-specific facades (§9.1 — 12 facades) | ~600 | ~640 | +40 | 12 facades × ~50 LoC each; Pydantic boundaries + composition wrappers. |
| Multi-server multiplexer (§5 merge rule) | ~400 | ~430 | +30 | Stage 1 priority + Stage 2 dedup + edge-case handlers. |
| Interpreter discovery (§7) | ~200 | ~210 | +10 | Twelve steps × ~15 LoC each. |
| Rope library bridge (§6 — 10 ops) | not listed | ~280 | +280 | Direct Rope ops not bridged by pylsp-rope; required for full coverage. |
| WorkspaceEdit applier upgrades (§8) | folded into strategy | ~120 | ~120 | Old-style `changes` fallback + multi-server transactions + bridge edit conversion. |
| Fixture `calcpy` + sub-fixtures (§11) | ~1200 | ~1250 main + ~590 sub-fixtures | +640 | Four companion sub-fixtures the orchestrator did not anticipate. |
| Tests (unit + integration + E2E) | ~1000 | ~1050 | +50 | One scenario per pitfall (§11.2 has 24 pitfalls; many share scenarios). |
| **Total Python side** | **~3,800 + 1,200 fixture** | **~3,470 LoC + ~1,840 LoC fixture** | **−330 + 640** | Less production code (more density), more fixture surface. |

**Verdict on orchestrator's estimate.** Reasonable. The notable correction is the missing **Rope library bridge** line (~280 LoC) — without it, the facades for `change_signature`, `introduce_factory`, `encapsulate_field` cannot work. The fixture grew because of sub-fixtures (~640 LoC) — the orchestrator's number covered just the main fixture. Total Python-side LoC under full coverage: **~5,310 LoC** including fixtures, vs. the narrow brief's **~3,500 LoC** including fixtures. The 50% premium is the cost of the user's directive change.

### 13.1 Comparison with Rust side

Rust strategy from main design Effort table: ~2,450 LoC + ~300 LoC fixture.

Python full-coverage: ~3,470 LoC + ~1,840 LoC fixture.

Python is **42% larger production-code** and **6.1x larger fixture**. The fixture multiplier is because Python's edge cases are language-and-ecosystem deep (interpreter discovery, namespace packages, stubs, `__all__`, circular imports), whereas Rust's edge cases are language-only (snippet markers, indexing progress, `mod_rs` style). This is intrinsic to Python; it is not a sign of design overreach.

### 13.2 Staging order

Same shape as the narrow brief, with two additions:

1. **Small.** Interpreter discovery (§7) + `PythonStrategy` skeleton with `NotImplementedStrategy` facades.
2. **Small.** Multi-server merge rule (§5) — minimum Stage 1; Stage 2 deferred to phase 4.
3. **Medium.** rename + organize_imports + auto_import + ignore_diagnostic + fix_lints — facades that don't require Rope library bridge.
4. **Medium.** `plan_file_split` clustering (re-uses the Rust strategy's planner — language-neutral).
5. **Large.** `split_file_by_symbols` composition via `MoveGlobal` + dry-run + rollback. Stage 2 of merge rule.
6. **Large.** Rope library bridge for `change_signature`, `introduce_factory`, `encapsulate_field` — gated behind v1.1 facades but the bridge code lands at MVP since `split_file` may need `MoveModule` directly.
7. **Test.** E1-py / E3-py / E9-py / E10-py block merge; E4-py / E5-py / E8-py / E11-py run nightly.

---

## 14. Responsible cuts — what to defer despite full-coverage directive

Full-coverage means "every action reachable", not "every action a typed facade". Three categories of cut preserve coverage without expanding MVP scope.

### 14.1 Cut: ergonomic facades that ride on `apply_code_action`

| Facade | Why deferred | MVP path for the LLM |
|---|---|---|
| `convert_to_async` | Composed transform, not a single LSP action. Builds on `apply_code_action` for individual edits. | Manual: agent calls `apply_code_action` for each `def → async def` site. |
| `annotate_return_type` | basedpyright emits the action; reachable via `apply_code_action` with kind `quickfix.annotation`. Typed facade is pure ergonomics. | Manual: `apply_code_action(file, range, kind="quickfix")` → pick title. |
| `convert_imports` | ruff's `TID252` rule covers most cases via `fix_lints`. Standalone facade redundant. | Manual: `fix_lints(rules=["TID252", "UP*"])`. |
| `expand_star_imports` | Rope library only. Low-frequency. | Manual: pass-through via `apply_code_action` once we expose the strategy bridge as a primitive. |
| `restructure` | Rope's pattern-based `Restructure` is powerful but rarely safe; LLMs would misuse it. | Manual: pass-through with prominent docstring warning. |

All five are reachable; none ship as named facades at MVP.

### 14.2 Cut: third LSP under low-RAM constraint

`ruff server` is opt-out via `O2_SCALPEL_DISABLE_SERVERS=ruff`. With ruff disabled:
- `fix_lints` falls back to pylsp's autopep8 plugin (which we'd have to re-enable in the init payload), reaching ~30 rules instead of 800.
- `source.fixAll.ruff` is unreachable; `apply_code_action` returns "kind unsupported".
- Memory drops by ~200 MB.

Document the trade-off; default behavior runs all three.

### 14.3 Cut: `pylsp-mypy` if `live_mode` regressions appear

If the `live_mode: false` setting produces stale diagnostics under realistic edit patterns, drop pylsp-mypy at MVP and rely solely on basedpyright for type errors. basedpyright's diagnostics are richer; mypy's are different. Diagnostics-delta loses redundancy but gains determinism. Decision deferred to spike 10.5 follow-up.

---

## 15. Test scenario list (E1-py through E11-py expanded)

| # | Scenario | Gate | Description |
|---|---|---|---|
| E1-py | Happy-path 4-way split | **MVP block** | Split `calcpy.py` into `ast/errors/parser/evaluator`. `pytest -q` byte-identical. |
| E2-py | Dry-run → inspect → adjust → commit | **MVP block** | `dry_run=true` then `dry_run=false`; `WorkspaceEdit` matches. |
| E3-py | Rollback after intentional break | **MVP block** | Commit a refactor that creates an import error; `rollback` restores byte-identical tree. |
| E4-py | Star-import warning | nightly | Variant fixture; dry-run returns `warnings: ["star_import_hides_moves"]`; commit fails without `allow_star_imports=True`. |
| E5-py | Circular-import detection | nightly | Engineered SCC fixture; dry-run reports SCC in `language_findings.import_cycles_introduced`. |
| E6-py | `fix_imports` on glob | nightly | `organize_imports(files=["calcpy/**/*.py"])` reaches every file; idempotent on second call. |
| E7-py | Virtualenv resolution | nightly | Run with no active venv but `.venv/` sibling; verify §7 step 4 wins. |
| E8-py | Namespace-package detection | nightly | `calcpy_namespace/` sub-fixture; dry-run warns about PEP 420; refuses to create `__init__.py`. |
| E9-py | Semantic equivalence | **MVP block** | `pytest --doctest-modules` byte-identical pre/post; same as E1-py but stricter. |
| E10-py | `__all__` preservation | **MVP block** | `from calcpy import *` yields the same set of names post-refactor. |
| E11-py | `rename_symbol` regression | **MVP block** | Existing rename path still works post-strategy-refactor. |
| E12-py | `TYPE_CHECKING` correctness | nightly | Imports inside `if TYPE_CHECKING:` block are preserved/rewritten correctly. |
| E13-py | Multi-server merge — organize-imports | **MVP block** | All three servers active; verify only one organize-imports action is surfaced. Spike 10.2 outcome wired into the test. |
| E14-py | Multi-server merge — auto-import | nightly | Verify basedpyright wins over rope_autoimport per §5.2. |
| E15-py | Ruff fixed-point convergence | nightly | `fix_lints` on a file with cascading autofixes; verify cap-hit warning surfaces if applicable. |
| E16-py | All three LSPs healthy on cold start | nightly | Spawn all three; `initialize` round-trip succeeds; advertised `codeActionKinds` match expected. |

MVP block: E1-py, E2-py, E3-py, E9-py, E10-py, E11-py, E13-py — seven scenarios.

---

## 16. Integration with main design — required updates

Listed as a checklist for the orchestrator merging this report.

### 16.1 Main design §3 (facades) updates

- Add the 12 Python-specific MVP facades from §9.1 to the canonical MCP tool surface. Document them in §3 alongside the cross-language base.
- Document the `provenance` field on `CodeActionDescriptor` (§5.4) in the primitives schema.
- Document `language_findings` field on `DiagnosticsDelta` (already proposed in narrow brief §5.4; preserve).

### 16.2 Main design §5 (LanguageStrategy) updates

- Adopt the narrow brief's three friction-point fixes (rename `parent_module_style`, add `extract_module_strategy`, split `module_declaration_syntax`).
- Add reference to `PythonStrategyExtensions` mixin (§12 above). Document the access pattern: facades `isinstance`-check the strategy.

### 16.3 Main design §Open Question #7 (second strategy validates abstraction)

- **Resolved by this report.** Python strategy under full coverage is shipping at MVP. The abstraction is validated against two structurally different shapes (Rust: `extract_module` first-class; Python: composition + library bridge). Close the open question.

### 16.4 Main design §Two-LSP-process problem

- Update Python bullet from "no on-disk artifacts; safe" to: "Three concurrent processes (pylsp + basedpyright + ruff). Caches isolatable via `O2_SCALPEL_ISOLATE_CACHES=1`. Memory budget ~700 MB on calcpy-scale; ~1.2 GB on 10k-LoC projects. Opt-out per server via `O2_SCALPEL_DISABLE_SERVERS`."

### 16.5 Main design §Effort

- Add Python-side rows totaling ~3,470 production LoC + ~1,840 fixture LoC. Update the table accordingly.

### 16.6 Plugin-marketplace impact (main design §Q11, §Q14)

- Q14 on-demand generator needs three Python plugin variants (one per LSP), or one combined `python-reference` manifest that registers all three.
- Recommend: combined manifest with all three commands, since they share the resolved interpreter and project root.

---

## 17. Open questions specific to Python full coverage

Remaining after this round:

1. **Rope `Project` instance lifecycle.** The library bridge needs a long-lived `rope.project.Project` per project root. Should it live in the `PythonStrategy` instance (one per project), or be created per-call? Per-instance is faster but pins memory; per-call is clean but slow on large projects (Rope's project init walks the file tree). Decision: per-instance with a 30-min idle timeout. Verify in spike.

2. **ruff's `--preview` flag stability.** Enabling preview rules surfaces ~50 additional ruff rules at MVP, but those rules can change behavior between ruff releases. Pin ruff version exactly; mark preview-rule fixes as `unsafe` in the merge rule.

3. **basedpyright pinning vs upstream tracking.** basedpyright tracks pyright with a few-day lag. If we pin basedpyright exactly, we miss security updates. If we pin a range, capability drift is possible. Recommend: pin `~=` minor, integration test asserts `codeActionKinds` weekly.

4. **Three-server `textDocument/codeAction` parallelism.** Sending the request to all three in parallel needs `asyncio.gather` (or thread pool, depending on solidlsp's threading model). What's the right concurrency primitive? Decide in spike with measured latency.

5. **`pylsp-mypy` cache invalidation under our `live_mode: false`.** If we disable live mode, we're responsible for triggering mypy after the apply. Best mechanism: send a synthetic `didSave` to pylsp post-apply; pylsp-mypy reacts. Verify that this works (spike 10.5 follow-up).

6. **Notebook (`.ipynb`) support timeline.** Ruff has `notebook.source.fixAll`; basedpyright type-checks notebooks via CLI. Should scalpel rewrite notebook cells? Defer to v2; MVP detects and warns only.

7. **Cython / `.pyx` files.** Same as narrow brief — detect and warn; no refactor support.

8. **PEP 695 generics, PEP 701 f-strings.** Rope's parser support is unverified; spike 10.3 outcome decides whether MVP supports 3.13+ syntax or pins Python ≤ 3.12.

9. **Multi-interpreter monorepos.** Out of scope for MVP per §7.5; revisit v1.1.

10. **Strategy-level config file** vs hardcoded defaults. Python strategy has many tuning knobs (organize-imports engine, three-LSP membership, library-bridge timeout, ...). Should there be a `[tool.o2-scalpel.python]` section in `pyproject.toml`? Lean yes; defer the schema.

---

## Appendix A — Full LSP capability matrix (Python LSPs, Apr 2026)

Updated from the narrow brief's Appendix A; one row per LSP feature, six columns for the LSPs scalpel evaluates.

| Feature | pylsp+rope+mypy+ruff plugin set | basedpyright | pyright | jedi-lsp | ruff server | pyrefly |
|---|---|---|---|---|---|---|
| `textDocument/documentSymbol` | Y | Y | Y | Y | N | Y |
| `textDocument/references` | Y | Y | Y | Y | N | Y |
| `textDocument/rename` | Y (Rope) | Y | Y | Y | N | Y |
| `textDocument/rename` on module → `RenameFile` | Y | N | N | N | N | ? |
| `callHierarchy/incomingCalls` | partial | Y | Y | Y | N | Y |
| `callHierarchy/outgoingCalls` | partial | Y | Y | Y | N | Y |
| `textDocument/typeDefinition` | partial | Y | Y | Y | N | Y |
| `textDocument/implementation` | partial | Y (basedpyright extra) | partial | partial | N | ? |
| `textDocument/inlayHint` | N | Y | Y | N | N | ? |
| `textDocument/codeAction kind=refactor.extract.method` | Y | N | N | Y (Jedi) | N | ? |
| `textDocument/codeAction kind=refactor.extract.variable` | Y | N | N | Y | N | ? |
| `textDocument/codeAction kind=refactor.inline` | Y | N | N | Y | N | ? |
| `textDocument/codeAction kind=refactor.rewrite` | Y | partial | partial | partial | N | ? |
| `textDocument/codeAction kind=source.organizeImports` | Y (Rope) | Y | Y | partial | Y (`source.organizeImports.ruff`) | ? |
| `textDocument/codeAction kind=source.fixAll` | partial | N | N | N | Y (`source.fixAll.ruff`) | ? |
| `textDocument/codeAction kind=quickfix` (auto-import) | Y (rope_autoimport) | Y (Pylance-port) | N | N | N | ? |
| `textDocument/codeAction kind=quickfix` (lint) | partial (autopep8 disabled in our config) | partial | partial | N | Y | ? |
| `textDocument/codeAction kind=quickfix` (type-ignore) | N | Y | N | N | N | ? |
| `textDocument/codeAction kind=quickfix.imports` | partial | Y | N | N | N | ? |
| `codeAction/resolve` | Y | Y | Y | Y | Y | Y |
| `workspace/executeCommand` | Y (9 pylsp-rope cmds) | Y | Y | Y | Y | Y |
| `workspace/applyEdit` reverse-request | Y | Y | Y | Y | Y | Y |
| `WorkspaceEdit` shape: `documentChanges` | Y | Y | Y | Y | Y | Y |
| `WorkspaceEdit` shape: `changes` (legacy) | sometimes | N | N | N | N | ? |
| `WorkspaceEdit` resource ops: `CreateFile` | Y (on rename-module) | future (createstub) | future | N | N | ? |
| `WorkspaceEdit` resource ops: `RenameFile` | Y | N | N | N | N | ? |
| `WorkspaceEdit` resource ops: `DeleteFile` | N | N | N | N | N | ? |
| `WorkspaceEdit` `changeAnnotations` | N | N | N | N | N | ? |
| `Diagnostic.relatedInformation` | Y (mypy, partial) | Y (rich) | Y | partial | Y (codes only) | ? |
| `$/progress` reporting | Y (when configured) | Y | Y | partial | partial | ? |
| `textDocument/inlayHint` | N | Y | Y | N | N | ? |
| Custom commands relevant to refactor | `pylsp_rope.*` (9), `pylsp_mypy.*` (none for actions) | `basedpyright.organizeImports`, `basedpyright.restartServer`, `basedpyright.writeBaseline`, `basedpyright.addOptionalForParam`, `basedpyright.createTypeStub` | `pyright.organizeimports`, `pyright.restartserver`, `pyright.createtypestub`, `pyright.addoptionalforparam` | none scalpel-relevant | none scalpel-relevant (autofix is via codeAction) | ? |

`?` = not enumerated publicly as of Apr 2026; integration-test at first contact.

## Appendix B — Pydantic signatures for new facades

Compact reference. Conventions match main design §3.

```python
class Range(BaseModel):
    start: tuple[int, int]   # (line, character)
    end: tuple[int, int]

class CodeActionDescriptor(BaseModel):
    id: str
    title: str
    kind: str
    disabled_reason: str | None
    is_preferred: bool
    provenance: Literal["pylsp-rope", "pylsp-base", "basedpyright", "ruff", "pylsp-mypy"]
    suppressed_alternatives: list["SuppressedAlternative"] = []

class SuppressedAlternative(BaseModel):
    title: str
    provenance: str
    reason: Literal["lower_priority", "duplicate_title", "duplicate_edit"]

class SideEffect(BaseModel):
    line: int
    statement_kind: Literal["expression", "assignment", "call", "other"]
    snippet: str

class ResolvedTopLevel(BaseModel):
    name: str
    kind: Literal["function", "method", "class", "constant", "variable", "import", "decorated"]
    decorators: list[str]
    is_async: bool
    is_private: bool      # leading underscore
    line_range: Range
```

Plus the 12 MVP facade signatures already given in §9.1.

## Appendix C — References

Primary sources consulted in this round; every claim citing a server's behavior traces back to one of these:

- pylsp: [python-lsp/python-lsp-server](https://github.com/python-lsp/python-lsp-server), [CONFIGURATION.md](https://github.com/python-lsp/python-lsp-server/blob/develop/CONFIGURATION.md)
- pylsp-rope: [python-rope/pylsp-rope](https://github.com/python-rope/pylsp-rope), [plugin.py](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/plugin.py), [commands.py](https://github.com/python-rope/pylsp-rope/blob/main/pylsp_rope/commands.py)
- pylsp-mypy: [python-lsp/pylsp-mypy](https://github.com/python-lsp/pylsp-mypy)
- python-rope/rope: [overview](https://rope.readthedocs.io/en/latest/overview.html), [library reference](https://rope.readthedocs.io/en/latest/library.html), [github.com/python-rope/rope](https://github.com/python-rope/rope)
- basedpyright: [DetachHead/basedpyright](https://github.com/DetachHead/basedpyright), [commands docs](https://docs.basedpyright.com/latest/usage/commands/), [language-server-settings](https://docs.basedpyright.com/latest/configuration/language-server-settings/), [pylance-features.md](https://github.com/DetachHead/basedpyright/blob/main/docs/benefits-over-pyright/pylance-features.md)
- pyright: [microsoft/pyright](https://github.com/microsoft/pyright), [commands.md](https://github.com/microsoft/pyright/blob/main/docs/commands.md)
- ruff server: [astral-sh/ruff](https://github.com/astral-sh/ruff), [editor-integration features](https://docs.astral.sh/ruff/editors/features/), [editors](https://docs.astral.sh/ruff/editors/)
- LSP 3.17 spec: [language-server-protocol/specifications/lsp/3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/)
- PEP 420: [peps.python.org/pep-0420](https://peps.python.org/pep-0420/)
- VSCode Python environments: [code.visualstudio.com/docs/python/environments](https://code.visualstudio.com/docs/python/environments)
- ruff `INP001` rule (PEP 420 detector): [docs.astral.sh/ruff/rules/implicit-namespace-package](https://docs.astral.sh/ruff/rules/implicit-namespace-package/)

Project-internal cross-references:

- [Main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — §3, §5, §Q7, §"Two-LSP-process problem"
- [Archived narrow Python brief](archive-v1-narrow/specialist-python.md) — §1.3 LSP choice, §5 friction points, §7 risks, §Appendix A
- [Archived narrow MVP scope](archive-v1-narrow/2026-04-24-mvp-scope-report.md) — §3.5 fixtures, §4.3 Python LSP decision

---

**End of report.**
