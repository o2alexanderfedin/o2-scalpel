# Q4 — `WorkspaceEdit.changeAnnotations` with `needsConfirmation: true` — auto-accept by default?

**Status:** resolved
**Owner:** AI Hive(R) (LSP protocol + safety/UX specialist)
**Date:** 2026-04-24
**Resolves:** [§19 open question 4](../2026-04-24-mvp-scope-report.md#19-open-questions-still-unresolved) — _"`changeAnnotations` auto-accept policy under full coverage."_
**Disagreement:** [`specialist-rust.md` §5.1, §5.2](../specialist-rust.md) (rejects annotated edits unless caller passes `allow_out_of_workspace=true`)
vs. [`specialist-scope.md` §2.4, §3.5](../specialist-scope.md) (auto-accept with audit log so SSR keeps working in full coverage)
vs. [user profile in `CLAUDE.md`](../../../CLAUDE.md) (regression aversion: _"Before modifying working code, verify the change is safe… Flag potential regression risks explicitly"_).

---

## 1. The question, restated

LSP §3.16 (`TextEdit & AnnotatedTextEdit`) defines:

```typescript
interface ChangeAnnotation {
  label: string;
  needsConfirmation?: boolean;   // default false
  description?: string;
}

interface WorkspaceEdit {
  // ...
  changeAnnotations?: { [id: ChangeAnnotationIdentifier]: ChangeAnnotation };
}
```

The protocol intent is **client-side UI**: the editor groups edits by annotation, prompts the user before applying any with `needsConfirmation: true`, and exposes per-annotation accept/reject toggles. Default-absent `needsConfirmation` means apply without prompting.

scalpel is an autonomous MCP server. There is no UI in the loop. Two facts collide:

1. **rust-analyzer attaches `needsConfirmation: true` to two distinct edit classes** (proven by source inspection in §3 below): edits whose target file lives in a "library" `SourceRoot` (sysroot, registry, external crate sources), and renames of locals where the new name shadows or is shadowed.
2. **`experimental/ssr` is the only MVP facade that frequently produces library-file edits** when a pattern matches against a generic call site whose definition resolves into a dependency. Reject-by-default means a class of valid SSR queries fail.

The four candidate policies — (A) auto-accept, (B) reject-and-require-flag, (C) workspace-boundary-filter, (D) per-annotation confirm-handle — trade ergonomics for regression safety differently. The user profile flags regression as the explicit Frustrations dimension, which biases toward the safer end of that axis but does not justify gold-plating.

---

## 2. LSP §3.16 spec semantics — exact behavior

Source: [LSP 3.17 spec, "TextEdit & AnnotatedTextEdit"](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textEdit). Verified verbatim against the spec page.

| Field | Type | Default | Semantics |
|---|---|---|---|
| `label` | `string` (required) | — | "human-readable string describing the actual change… rendered prominent in the user interface." |
| `needsConfirmation` | `boolean?` | **`false`** | "user confirmation is needed before applying the change." |
| `description` | `string?` | `undefined` | "rendered less prominent in the user interface" (supplementary). |

Spec text on client behavior: _"clients provide options to group the changes along the annotations they are associated with."_ Note the wording: the spec mandates that clients **support grouping**, not that clients **block** on `needsConfirmation`. The blocking-modal behavior is canonical (VSCode does it), but a non-UI client like scalpel is technically conformant whether it auto-accepts, rejects, or asks elsewhere — provided we surface the metadata to whoever can make the decision.

The **ChangeAnnotationIdentifier** is opaque: it's just a key into the `changeAnnotations` map. rust-analyzer uses one stable id (`"OutsideWorkspace"`) plus auto-numbered ids for SourceChange-internal annotations.

---

## 3. rust-analyzer emission patterns — verified via source

### 3.1 `OutsideWorkspace` annotation — the dominant case

Verbatim from [`crates/rust-analyzer/src/lsp/to_proto.rs:1113`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/rust-analyzer/src/lsp/to_proto.rs#L1113):

```rust
fn outside_workspace_annotation_id() -> String {
    String::from("OutsideWorkspace")
}
```

Construction site at line 1413–1422:

```rust
once((
    outside_workspace_annotation_id(),
    lsp_types::ChangeAnnotation {
        label: String::from("Edit outside of the workspace"),
        needs_confirmation: Some(true),
        description: Some(String::from(
            "This edit lies outside of the workspace and may affect dependencies",
        )),
    },
))
```

The id is attached to any `SnippetTextEdit`, `RenameFile` (for `MoveFile`), or `RenameFile` (for `MoveDir`) whose source `FileId` satisfies (lines 1305–1308, 1346–1350, 1361–1364):

```rust
if snap.analysis.is_library_file(file_id)? && snap.config.change_annotation_support() {
    for edit in &mut edits {
        edit.annotation_id = Some(outside_workspace_annotation_id())
    }
}
```

`is_library_file` is defined in [`crates/ide/src/lib.rs:357`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide/src/lib.rs#L357):

```rust
pub fn is_library_file(&self, file_id: FileId) -> Cancellable<bool> {
    self.with_db(|db| {
        let source_root = db.file_source_root(file_id).source_root_id(db);
        db.source_root(source_root).source_root(db).is_library
    })
}
```

`SourceRoot.is_library` is set when rust-analyzer registers the file under a `cargo` dependency, the rustup sysroot, an `extern crate` source, or any path the project model marks as immutable. In practice this is exactly: `~/.cargo/registry/src/index.crates.io-*/<crate>/`, `~/.rustup/toolchains/<channel>/lib/rustlib/src/rust/library/`, plus paths from `[patch]` overrides that point outside the workspace root.

### 3.2 Rename-shadowing annotation — secondary case

Verbatim from [`crates/ide-db/src/rename.rs:685–696`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide-db/src/rename.rs#L685):

```rust
if config.show_conflicts && !sema.rename_conflicts(&local, new_name).is_empty() {
    Some(
        source_change.insert_annotation(ChangeAnnotation {
            label: "This rename will change the program's meaning".to_owned(),
            needs_confirmation: true,
            description: Some(
                "Some variable(s) will shadow the renamed variable \
            or be shadowed by it if the rename is performed"
                    .to_owned(),
            ),
        }),
    )
} else { None };
```

This fires from `textDocument/rename` whenever a local rename introduces a shadowing conflict. The label `"This rename will change the program's meaning"` is a different, qualitatively-stronger warning than `OutsideWorkspace` — it says the edit is inside the workspace but the **semantics shift**.

### 3.3 Assist families that route through these paths

| Family | Annotation reached when… | Frequency |
|---|---|---|
| `experimental/ssr` | pattern matches against a call site whose definition is in `~/.cargo/registry/...` or sysroot (e.g., `Vec::push`, `Result::unwrap`) | high — primary risk |
| `auto_import` (D family) | the chosen import path resolves through a re-export whose origin is in a library file (rare; usually the edit itself is in the workspace, the *resolution* is library) | low |
| `move_module_to_file`, `move_to_mod_rs` (A family) | module being moved happens to be in a library SourceRoot — only if user opened a library file directly | very low |
| `textDocument/rename` (full coverage) | local rename introduces shadowing | low–medium |
| `inline_call`, `inline_into_callers` (C family) | callsite is in workspace but inlined body is from a library — does **not** hit `is_library_file` for the *edit target*, so does **not** annotate (verified by reading `to_proto.rs:1305`); only the *origin* matters | none |
| `extract_*` (B family) | typically edits the file containing the cursor; if user invoked from a library file (e.g., go-to-definition jumped them there) the resulting edit is annotated | very low |

**Conclusion:** SSR is the dominant emitter; rename-shadowing is the only second source. All other families are negligible at MVP.

### 3.4 Note on `solidlsp.workspace.workspaceEdit.changeAnnotationSupport`

rust-analyzer only emits `change_annotations` if the client advertises support (`snap.config.change_annotation_support()`). scalpel **must** advertise support — otherwise we lose the metadata entirely and an edit silently lands on `~/.cargo/registry/.../foo.rs`. Advertising support is mandatory; the policy debate is what we *do* with the metadata once we have it.

---

## 4. VSCode behavior — canonical client baseline

VSCode's `WorkspaceEdit` API ([`src/vscode-dts/vscode.d.ts:3933`](https://github.com/microsoft/vscode/blob/main/src/vscode-dts/vscode.d.ts#L3933)) defines the same shape:

```typescript
needsConfirmation: boolean;
label: string;
description?: string;
iconPath?: IconPath;
```

The bulk-edit preview ([`src/vs/workbench/contrib/bulkEdit/browser/preview/bulkEditPreview.ts`](https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/bulkEdit/browser/preview/bulkEditPreview.ts)) implements:

- **Grouping:** edits sorted into per-annotation categories; categories with `needsConfirmation: true` float to the top.
- **Default state:** `checked = !edit.metadata?.needsConfirmation` — i.e., **needs-confirmation edits start unchecked** (the user must explicitly tick them) while non-annotated edits are checked.
- **Workflow:** preview is non-modal; the user reviews the diff per-annotation; clicking "Apply" applies only the checked subset.

So canonical VSCode behavior is **per-annotation, default-OFF, in a side preview** — *not* a blocking modal, *not* per-edit. That mental model matters: scalpel's nearest equivalent is the dry-run output of `scalpel_dry_run_compose`, which already groups edits and surfaces metadata — but currently auto-applies on transaction commit regardless of annotation.

---

## 5. Attack and regression vectors

| # | Scenario | Impact under (A) auto-accept | Impact under (C) path-filter |
|---|---|---|---|
| 1 | LLM runs `scalpel_rust_ssr(pattern="$x.unwrap()", template="$x?")` on `calcrs`. SSR matches every `Result::unwrap` — including the std doc-test in `~/.rustup/toolchains/stable/lib/rustlib/src/rust/library/core/src/result.rs` if rust-analyzer indexes it. | **Silent mutation of stdlib source.** Next `cargo +stable build` likely picks up the modified file (rustup caches checksums; depends on toolchain setup). Highly difficult to detect/undo. | Edit dropped at the boundary check; SSR returns `EDIT_OUT_OF_WORKSPACE` with the rejected paths listed. LLM can refine the pattern. |
| 2 | LLM runs SSR `$x.foo()` → `$x.bar()` to migrate an internal API. Pattern accidentally matches a method in `~/.cargo/registry/src/.../serde-1.0.x/src/de.rs`. | **Silent corruption of cargo registry.** `cargo` re-extracts on `cargo clean --target-dir=…` but the local registry is the canonical source for offline builds; corrupted bytes propagate to any other workspace using the same registry until the user runs `cargo cache --clean` or `cargo clean --doc`. | Boundary check rejects; LLM sees the registry path and narrows the pattern (e.g., `files=["src/**"]`). |
| 3 | LLM runs `scalpel_imports_organize` and rust-analyzer's `auto_import` chooses an import path through a re-export. The auto-import edit itself targets the workspace file (not the library), so no `OutsideWorkspace` annotation fires; only the *resolution* crossed library boundaries. | Safe in both — edit target is in workspace. | Same — boundary check on edit target paths is consistent. |
| 4 | LLM runs `rename_symbol` on a local that introduces shadowing. rust-analyzer attaches `needs_confirmation: true` with label `"This rename will change the program's meaning"`. | Auto-accept silently changes program semantics; the rename-shadowing case is the textbook regression vector. | Boundary check passes (edit is in workspace). Annotation handling falls through — see §6 for our policy fork on rename-shadowing. |
| 5 | LLM runs SSR with a vendored crate at `vendor/serde-1.0.x/` that the user committed to git but rust-analyzer treats as a library. | Auto-accept mutates vendored crate inside the workspace tree — actually probably wanted? Or definitely not? Ambiguous. | Boundary check needs configurable allowlist; without one, vendored deps are blocked. **Recommended: ship `O2_SCALPEL_WORKSPACE_EXTRA_PATHS`** to opt-in vendored paths into the boundary. |
| 6 | Diagnostic-driven `quickfix` for `unused_import` in a generated file under `target/` that rust-analyzer has been told to track. | Auto-accept mutates `target/` artefacts. | Boundary check rejects (`target/` is outside `workspace/folders`). |

The vectors all point the same way: the **path of the edited file**, not the **annotation**, is the load-bearing signal. The annotation is necessary (rust-analyzer uses it to communicate intent) but neither sufficient (scenario 5 shows annotations and intent diverge for vendored deps) nor reliable (rename-shadowing is annotated for a reason orthogonal to workspace boundary).

---

## 6. The four options compared

| Option | Default behavior | SSR ergonomics | Regression risk | Implementation cost |
|---|---|---|---|---|
| **A. Auto-accept** (current §19 stance) | Apply every edit; emit audit log line | Best — SSR works on first try | High — scenarios 1, 2, 4 above land silently | ~5 LoC (just log-and-apply) |
| **B. Reject unless `allow_out_of_workspace=true`** (specialist-rust §5.2) | Reject any annotated edit; caller re-invokes with flag | OK — caller learns to pass the flag for SSR | Medium — relies on annotation, fragile to scenario 5 (vendored looks like library to rust-analyzer); scenario 4 (rename-shadowing) is wrongly blocked | ~30 LoC (flag-plumbing through facades) |
| **C. Path-filter (workspace-boundary)** | Reject any edit whose target path is not under `workspace/folders` (LSP-reported), regardless of annotation; treat annotation as advisory | Good — SSR works on workspace files; library matches dropped with clear `EDIT_OUT_OF_WORKSPACE` per path | Low — scenario 1, 2, 6 caught by path; scenario 4 caught by orthogonal "semantic-shift annotation" handler; scenario 5 needs allowlist | ~70 LoC (path canonicalization + filter + override env) |
| **D. Per-annotation confirm-handle** (`scalpel_confirm_annotations(transaction_id, accept=[…])`) | Surface in dry-run; block until LLM emits a follow-up `confirm` call | Slow — every SSR turns into a 2-step dialogue; LLM token cost roughly +400 per SSR | Very low | ~150 LoC + new MCP tool + state machine |

### 6.1 Why **option C** wins

Three independent reasons:

**(a) The annotation is too coarse to be the primary safety check.** rust-analyzer's `is_library_file` is *workspace-membership* in disguise. We don't need the server to tell us the edit is outside the workspace — **scalpel knows where the workspace is** because the LSP `initialize` handshake gives us `workspaceFolders`. Computing `path.is_relative_to(folder) for folder in workspace_folders` is one canonical-path comparison and 0 ms. Treating the server's annotation as the primary signal is "asking the server's permission for something we already know." TRIZ separation principle: **separate the safety check from the metadata channel.**

**(b) Path-filter handles scenarios annotation cannot.** Scenario 6 (rust-analyzer cleaning generated `target/` files) is **not** annotated as `OutsideWorkspace` because `target/` is technically inside the workspace `SourceRoot` if registered. Path-filter blocks it; annotation-policy doesn't. Symmetrically, scenario 5 (intentionally-edited vendored deps) is annotated as `OutsideWorkspace` even though the user wants those edits — the boundary check with an `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` opt-in is the right shape.

**(c) It honors the user's profile without paying option D's tax.** The Frustrations: regression directive says "verify the change is safe… flag potential regression risks." Path-filter is verification; per-call confirm dialogues are theatre. The risk option C still leaves on the table is the rename-shadowing annotation — handled by an **independent rule** (§7.3) that does *not* depend on file path: when scalpel sees `needs_confirmation: true` on a non-`OutsideWorkspace` annotation, treat it as a different warning class and surface it in `RefactorResult.warnings` even though the edit lands.

### 6.2 Why not B?

Option B treats `needsConfirmation` as authoritative. Scenario 5 breaks: vendored crates in `vendor/` are library files to rust-analyzer (read-only `SourceRoot`) but workspace files to the user. B rejects them; user has no recourse short of `allow_out_of_workspace=true`, which is a blunt instrument that *also* unblocks scenarios 1 and 2. The flag's true safety properties depend on what rust-analyzer chose to annotate — i.e., on third-party policy. C decouples scalpel's safety from rust-analyzer's heuristic.

### 6.3 Why not D?

Per-annotation confirm-handles are correct in spirit but cost-prohibitive at MVP. A typical SSR run touches 50–200 files; even with annotation-grouping, the LLM has to round-trip a `scalpel_confirm_annotations` call before commit. That's ~400 cold tokens per SSR (the new tool's docstring) plus per-call cost. At the MVP envelope (12 always-on tools + 11 deferred per `specialist-agent-ux.md` §15.1) this is a regressive trade.

D may earn a place in v1.1 as an **optional override** when the LLM passes `confirmation_mode="manual"` to `scalpel_dry_run_compose` — same mechanism the user gets in VSCode's preview. At MVP, C is enough.

---

## 7. Decided policy — exact applier behavior

### 7.1 Workspace-boundary check (the load-bearing rule)

After receiving any `WorkspaceEdit` and before applying, the applier computes:

```python
def is_in_workspace(path: Path, workspace_folders: list[Path], extra: list[Path]) -> bool:
    target = path.resolve(strict=False)
    candidates = [f.resolve(strict=False) for f in (workspace_folders + extra)]
    return any(target.is_relative_to(c) for c in candidates)
```

For every `documentChanges` entry (every `TextDocumentEdit`, `CreateFile.uri`, `RenameFile.oldUri` and `newUri`, `DeleteFile.uri`), if `is_in_workspace(...)` is `False`, the entire `WorkspaceEdit` is rejected with `RefactorResult.error_code = "EDIT_OUT_OF_WORKSPACE"` and the rejected paths in `error.details.rejected_paths`. **Atomicity preserved** — no partial application.

`workspace_folders` is the LSP-reported value from `initialize.params.workspaceFolders` (or the fallback `rootUri`). `extra` is `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` (colon-separated, optional) for vendored-dep workflows.

### 7.2 `OutsideWorkspace` annotation handling

When an annotation with id `"OutsideWorkspace"` (or any annotation whose `description` matches the regex `outside.*workspace|library|dependency`, case-insensitive — defensive against future label tweaks) is present:

- **Surface in dry-run preview** (`RefactorResult.preview.annotations`).
- **Surface in the audit log** (`audit.log` line: `WARN annotation_outside_workspace: paths=[...]`).
- **Do not** make the apply decision based on this annotation — that's §7.1's job.

The annotation is informational. The path filter is enforcement. Two independent layers; either alone is wrong, both together are right.

### 7.3 Non-`OutsideWorkspace` annotations (rename-shadowing)

When `needs_confirmation: true` arrives with an annotation that is **not** `OutsideWorkspace` (rust-analyzer's rename-shadowing case is the principal one in MVP), the policy is:

- **Apply the edit** (the path is in-workspace; refusing would block legitimate refactors).
- **Append `RefactorResult.warnings += [SemanticShiftWarning(label, description, affected_paths)]`** so the LLM sees it.
- **Add to checkpoint metadata** for one-click `rollback_refactor` if the LLM regrets it.

This is the deliberate "asymmetric" treatment: workspace boundary = hard reject, semantic-shift = soft warn. Justification: workspace-boundary violations are *unrecoverable* by scalpel (we can't undo writes to `~/.cargo/registry/` cleanly because cargo's checksum DB drift may already have happened); semantic-shift edits are recoverable (the checkpoint is intact, and the LLM has the warning).

### 7.4 Override for opt-in workspace-crossing operations

A facade may pass `allow_out_of_workspace: bool = False` (mirrors specialist-rust §5.2). When `True`:

- §7.1's path-filter is skipped.
- An `OutsideWorkspace` annotation still surfaces in the dry-run preview and audit log.
- `RefactorResult.warnings += [OutOfWorkspaceWarning]` regardless.

**No facade in the MVP set passes `allow_out_of_workspace=True`.** It is the escape hatch for a hypothetical future tool that explicitly targets vendored crates (e.g., a `scalpel_patch_vendored_dep` v2+ tool). If a user wants this at MVP, they construct a `scalpel_apply_capability(...)` call with the flag — the same escape hatch documented in the [main design Gap 6](../../2026-04-24-serena-rust-refactoring-extensions-design.md#gap-6-changeannotations-with-needsconfirmation-for-out-of-workspace-edits).

### 7.5 `RefactorResult` schema additions

Adds two fields to the schema in [§10 of the MVP report](../2026-04-24-mvp-scope-report.md#10):

```python
class RefactorResult(BaseModel):
    # ...existing fields...
    warnings: list[Union[SemanticShiftWarning, OutOfWorkspaceWarning]] = []
    rejected_paths_out_of_workspace: list[Path] = []  # populated only on EDIT_OUT_OF_WORKSPACE
```

Trivial schema change; ~20 LoC; does not affect existing facades.

---

## 8. Python LSP cross-check

### 8.1 Emission survey

Verified via GitHub code search across the four Python LSPs scalpel uses:

| Server | `changeAnnotation` references | `needsConfirmation: true` in production code |
|---|---|---|
| pylsp (`python-lsp/python-lsp-server`) | 0 | none |
| pylsp-rope (`python-rope/pylsp-rope`) | 1 (test fixture) | none |
| basedpyright (`DetachHead/basedpyright`) | 6 (all in `workspaceEditUtils.ts` + tests; passes annotations through; never sets `needsConfirmation: true`) | none in production paths |
| ruff (`astral-sh/ruff`) | 0 | none |

**Conclusion: no MVP-relevant Python LSP currently emits `needs_confirmation: true`.** The applier still must accept the `changeAnnotations` field (forward-compat) and surface it in dry-run, but the policy in §7 is rust-analyzer-specific in practice.

### 8.2 Python workspace-boundary rule

Even without annotations, Python edits can leak outside the workspace:

- **Stub files in virtualenvs** (`.venv/lib/python3.x/site-packages/<pkg>/foo.pyi`). pylsp-rope's `move_global` can in principle target these if the LLM points at them.
- **Site-packages source** (e.g., editing `requests/__init__.py` in the venv).
- **Conda envs**, `pipx`-installed packages — same shape.

Python policy = same §7.1 path-filter, with a stricter interpretation of "workspace":

```python
PYTHON_WORKSPACE_INFER = {
    "explicit": ["workspaceFolders"],          # LSP-reported
    "implicit_exclude": [".venv/", "venv/", "site-packages/", "__pypackages__/", "node_modules/"],
}
```

Any path containing any of `implicit_exclude` segments is rejected even if it appears to be under a workspace folder (some users' `.venv` is inside the project root). The `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` override applies symmetrically.

### 8.3 Multi-server consistency

The §11 multi-LSP merge already converges N edits into one `WorkspaceEdit` before the applier sees it. The path-filter runs **once, on the merged edit**. No new multi-server complexity.

---

## 9. Failure-mode test fixture

The boundary check needs a regression test that survives rust-analyzer version bumps. Fixture path: `tests/test_workspace_boundary.py`.

```python
# tests/test_workspace_boundary.py
"""
Verifies that EDIT_OUT_OF_WORKSPACE rejects an SSR result whose
WorkspaceEdit targets a file under ~/.cargo/registry. Independent of
whether rust-analyzer attaches `needsConfirmation: true` — the path
filter must catch it.
"""
import pytest
from pathlib import Path
from scalpel.applier import WorkspaceEditApplier, EditOutOfWorkspace
from scalpel.fixtures import workspace_with_calcrs

@pytest.mark.integration
def test_ssr_rejects_registry_edit(workspace_with_calcrs, mock_ra_session):
    workspace_root = workspace_with_calcrs.root  # e.g., /tmp/calcrs-ws
    registry_path = Path.home() / ".cargo/registry/src/index.crates.io-X/foo-1.0.0/src/lib.rs"

    # Synthesize a WorkspaceEdit that rust-analyzer 0.3.18xx WOULD produce
    # if SSR matched a method on a registry-vendored type.
    edit = {
        "documentChanges": [
            {
                "textDocument": {"uri": f"file://{workspace_root}/src/main.rs", "version": 1},
                "edits": [{"range": {...}, "newText": "x?"}],
            },
            {
                "textDocument": {"uri": f"file://{registry_path}", "version": 1},
                "edits": [{"range": {...}, "newText": "y?", "annotationId": "OutsideWorkspace"}],
            },
        ],
        "changeAnnotations": {
            "OutsideWorkspace": {
                "label": "Edit outside of the workspace",
                "needsConfirmation": True,
                "description": "This edit lies outside of the workspace and may affect dependencies",
            }
        },
    }

    applier = WorkspaceEditApplier(workspace_folders=[workspace_root])
    with pytest.raises(EditOutOfWorkspace) as exc:
        applier.apply(edit)

    # Atomicity: the workspace file is NOT modified either.
    assert (workspace_root / "src/main.rs").read_text() == ORIGINAL_MAIN_RS
    # Reject details surface the path.
    assert registry_path in exc.value.rejected_paths
    # The in-workspace annotation does NOT trigger a reject by itself.
    assert exc.value.error_code == "EDIT_OUT_OF_WORKSPACE"


@pytest.mark.integration
def test_rename_shadowing_warns_but_applies(workspace_with_calcrs, mock_ra_session):
    """Non-OutsideWorkspace `needsConfirmation: true` warns; does not block."""
    edit = {
        "documentChanges": [
            {
                "textDocument": {"uri": f"file://{workspace_with_calcrs.root}/src/main.rs", "version": 1},
                "edits": [{"range": {...}, "newText": "renamed", "annotationId": "0"}],
            }
        ],
        "changeAnnotations": {
            "0": {
                "label": "This rename will change the program's meaning",
                "needsConfirmation": True,
                "description": "Some variable(s) will shadow the renamed variable",
            }
        },
    }
    result = WorkspaceEditApplier(workspace_folders=[workspace_with_calcrs.root]).apply(edit)
    assert result.success is True
    assert any(w.kind == "semantic_shift" for w in result.warnings)
    assert "shadow" in result.warnings[0].description


@pytest.mark.integration
def test_extra_paths_opt_in(tmp_path, mock_ra_session):
    """O2_SCALPEL_WORKSPACE_EXTRA_PATHS allows edits in a vendored path."""
    workspace = tmp_path / "ws"; workspace.mkdir()
    vendored = tmp_path / "vendor-foo"; vendored.mkdir()
    (vendored / "lib.rs").write_text("fn x() {}")

    edit = {
        "documentChanges": [
            {"textDocument": {"uri": f"file://{vendored}/lib.rs", "version": 1},
             "edits": [{"range": {...}, "newText": "fn y() {}", "annotationId": "OutsideWorkspace"}]}
        ],
        "changeAnnotations": {"OutsideWorkspace": {"label": "...", "needsConfirmation": True}},
    }
    applier = WorkspaceEditApplier(
        workspace_folders=[workspace],
        extra_workspace_paths=[vendored],   # from O2_SCALPEL_WORKSPACE_EXTRA_PATHS
    )
    result = applier.apply(edit)
    assert result.success is True
    assert any(w.kind == "out_of_workspace" for w in result.warnings)  # still warned
```

These three cases pin the policy: hard reject of registry/sysroot, soft warn of in-workspace semantic-shift, opt-in of vendored. They are runnable against `calcrs` from §17 of the rust specialist; they don't depend on rust-analyzer's exact label text (only on the annotation id `"OutsideWorkspace"` and `needs_confirmation: true`).

---

## 10. Final answer (paragraph for §19)

scalpel does **not** auto-accept `changeAnnotations.needsConfirmation: true` and does **not** make annotation status its primary safety check. Instead, the WorkspaceEdit applier enforces a **workspace-boundary path filter** independently of any annotation: every `documentChanges` entry whose target path is not under an LSP-reported `workspaceFolders` (or the opt-in `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` set) causes the entire `WorkspaceEdit` to be rejected with `error_code = "EDIT_OUT_OF_WORKSPACE"` — atomically, with the rejected paths surfaced. The `OutsideWorkspace` annotation is treated as advisory and logged; the rename-shadowing annotation (rust-analyzer's other `needs_confirmation: true` emitter) is non-blocking but appended to `RefactorResult.warnings` as a `SemanticShiftWarning`. Facades may pass `allow_out_of_workspace=True` to skip the path filter, but no MVP facade does — the flag is the escape hatch reachable only via `scalpel_apply_capability(...)`. This separates the safety enforcement (path-filter, owned by scalpel) from the metadata channel (annotation, owned by the LSP server), and matches the user's regression-aversion profile without paying the per-call confirmation-handle cost of option D. Implementation: ~70 LoC in the applier, three integration tests in `tests/test_workspace_boundary.py`, and the schema additions `RefactorResult.warnings` and `RefactorResult.rejected_paths_out_of_workspace`.

---

## 11. References

- LSP 3.17 — [TextEdit & AnnotatedTextEdit](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textEdit) (ChangeAnnotation type, `needsConfirmation` semantics).
- LSP 3.17 — [WorkspaceEdit](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#workspaceEdit) (`changeAnnotations` map, `changeAnnotationSupport` capability).
- rust-analyzer — [`crates/rust-analyzer/src/lsp/to_proto.rs:1113`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/rust-analyzer/src/lsp/to_proto.rs#L1113) (`outside_workspace_annotation_id`), [lines 1305–1308, 1346–1364, 1413–1422](https://github.com/rust-lang/rust-analyzer/blob/master/crates/rust-analyzer/src/lsp/to_proto.rs#L1305) (annotation construction sites).
- rust-analyzer — [`crates/ide-db/src/source_change.rs:34`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide-db/src/source_change.rs#L34) (`ChangeAnnotation` struct).
- rust-analyzer — [`crates/ide-db/src/rename.rs:685`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide-db/src/rename.rs#L685) (rename-shadowing annotation).
- rust-analyzer — [`crates/ide/src/lib.rs:357`](https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide/src/lib.rs#L357) (`is_library_file`).
- VSCode — [`src/vscode-dts/vscode.d.ts:3933`](https://github.com/microsoft/vscode/blob/main/src/vscode-dts/vscode.d.ts#L3933) (`WorkspaceEditEntryMetadata`).
- VSCode — [`src/vs/workbench/contrib/bulkEdit/browser/preview/bulkEditPreview.ts`](https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/bulkEdit/browser/preview/bulkEditPreview.ts) (per-annotation default-off checkbox UX).
- basedpyright — [`packages/pyright-internal/src/common/workspaceEditUtils.ts`](https://github.com/DetachHead/basedpyright/blob/main/packages/pyright-internal/src/common/workspaceEditUtils.ts) (passes annotations through; never sets `needsConfirmation: true`).
- [`specialist-rust.md` §5.1, §5.2, §6.4](../specialist-rust.md) (assist matrix; SSR spike S4).
- [`specialist-scope.md` §2.4, §3.5, §13.7](../specialist-scope.md) (full-coverage cost analysis; regression-aversion note).
- Main design — [Gap 6](../../2026-04-24-serena-rust-refactoring-extensions-design.md#gap-6-changeannotations-with-needsconfirmation-for-out-of-workspace-edits) (workaround framing).
- [`CLAUDE.md`](../../../CLAUDE.md) — Frustrations: regression directive.
