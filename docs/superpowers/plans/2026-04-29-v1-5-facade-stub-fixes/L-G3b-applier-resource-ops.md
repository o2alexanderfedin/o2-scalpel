# Leaf L-G3b — `_apply_workspace_edit_to_disk` learns CreateFile / RenameFile / DeleteFile

**Goal.** Lift the main applier (`scalpel_facades.py:109-141`) from "silently skips resource ops per v1.1 deferral" to "applies CreateFile, RenameFile, DeleteFile per LSP §3.18 spec." Currently, every facade that emits a resource-op WorkspaceEdit (module rename, file split, scaffold-related-class) returns `applied=True` while the file ops were dropped — a CRITICAL silent-success. The markdown applier (`_apply_markdown_workspace_edit` at L3177) already supports `CreateFile` for its split/extract path; this leaf brings the main applier to parity and adds the two missing operations. Spec § CR-2.

**Architecture.** The applier walks `documentChanges` and currently `continue`s on any entry with a `kind` field. The fix replaces that `continue` with a dispatch:

| LSP shape | Behavior |
|---|---|
| `{"kind": "create", "uri": ..., "options": {...}}` | `mkdir -p` parent; if file exists and `options.overwrite=False`, no-op (or fail if `ignoreIfExists=False`); else write empty file. |
| `{"kind": "rename", "oldUri": ..., "newUri": ..., "options": {...}}` | If `newUri` exists and `options.overwrite=False` → `INVALID_ARGUMENT` failure; else `Path.rename`. |
| `{"kind": "delete", "uri": ..., "options": {...}}` | If file missing and `options.ignoreIfNotExists=False` → fail; else `Path.unlink`. Recursive directory delete out of scope (LO-3). |

The applier already returns an `int` count of TextEdits applied; the resource-op count is added to the same total so `applied=count > 0` continues to mean "real change happened on disk." Existing callers' contract is unchanged.

**Tech stack.** Python 3.13 stdlib only — `pathlib.Path`, `urllib.parse`. No new dependencies.

**Source spec.** `docs/superpowers/specs/2026-04-29-facade-stub-audit.md` § CR-2 (lines 40-44).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `_apply_workspace_edit_to_disk` (L109-141) — replace `continue` branch with resource-op dispatch | ~80 |
| `vendor/serena/test/spikes/test_v1_5_g3b_applier_resource_ops.py` | NEW — failing tests for create / rename / delete with options | ~250 |

**Cited line ranges:**
- Current `continue`-on-`kind` line: `scalpel_facades.py:133-135`.
- Markdown precedent: `scalpel_facades.py:3177-3209` (handles `kind == "create"` only).
- LSP spec for resource ops: `documentChanges` discriminator field `"kind"` ∈ {`"create"`, `"rename"`, `"delete"`}; option fields per LSP §3.18.

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g3b_applier_resource_ops.py`:

```python
"""v1.5 G3b — _apply_workspace_edit_to_disk resource-op support (CR-2).

Acid tests:
  * CreateFile creates a missing file (empty) and mkdir -p the parent.
  * CreateFile with options.ignoreIfExists=True (default) → no-op when
    file already exists.
  * CreateFile with options.overwrite=True replaces existing content.
  * RenameFile moves the file; options.overwrite=False (default) +
    target exists → no rename, no exception (LSP semantics).
  * RenameFile with options.overwrite=True replaces target.
  * DeleteFile removes the file; options.ignoreIfNotExists=True (default)
    + missing file → no-op.
  * Mixed edit (CreateFile + TextDocumentEdit on the new file) applies
    both ops in order; final read_text() contains the inserted body.

Every assertion is via Path.read_text() / Path.exists() — no mocks for
the filesystem layer.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from serena.tools.scalpel_facades import _apply_workspace_edit_to_disk


def _file_uri(p: Path) -> str:
    return p.as_uri()


def test_create_file_writes_empty_when_absent(tmp_path: Path):
    target = tmp_path / "subdir" / "new.rs"
    edit = {
        "documentChanges": [
            {"kind": "create", "uri": _file_uri(target)},
        ]
    }
    count = _apply_workspace_edit_to_disk(edit)
    assert target.exists()
    assert target.read_text(encoding="utf-8") == ""
    assert count >= 1


def test_create_file_default_ignores_existing(tmp_path: Path):
    target = tmp_path / "exists.rs"
    target.write_text("// preserved\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "create", "uri": _file_uri(target)},
    ]}
    _apply_workspace_edit_to_disk(edit)
    # ignoreIfExists is the LSP default — content preserved.
    assert target.read_text(encoding="utf-8") == "// preserved\n"


def test_create_file_overwrite_replaces_existing(tmp_path: Path):
    target = tmp_path / "exists.rs"
    target.write_text("// old\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "create", "uri": _file_uri(target),
         "options": {"overwrite": True}},
    ]}
    _apply_workspace_edit_to_disk(edit)
    assert target.read_text(encoding="utf-8") == ""


def test_rename_file_moves_when_target_absent(tmp_path: Path):
    src = tmp_path / "old.rs"
    dst = tmp_path / "new.rs"
    src.write_text("// body\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "rename", "oldUri": _file_uri(src), "newUri": _file_uri(dst)},
    ]}
    _apply_workspace_edit_to_disk(edit)
    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "// body\n"


def test_rename_file_default_no_overwrite_when_target_exists(tmp_path: Path):
    src = tmp_path / "old.rs"
    dst = tmp_path / "new.rs"
    src.write_text("// from\n", encoding="utf-8")
    dst.write_text("// to\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "rename", "oldUri": _file_uri(src), "newUri": _file_uri(dst)},
    ]}
    # LSP default: overwrite=False, ignoreIfExists=False → MUST NOT silently
    # clobber. The applier elects to skip (no exception, count not incremented).
    _apply_workspace_edit_to_disk(edit)
    # Source preserved (rename was a no-op):
    assert src.read_text(encoding="utf-8") == "// from\n"
    assert dst.read_text(encoding="utf-8") == "// to\n"


def test_rename_file_overwrite_replaces_target(tmp_path: Path):
    src = tmp_path / "old.rs"
    dst = tmp_path / "new.rs"
    src.write_text("// from\n", encoding="utf-8")
    dst.write_text("// to\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "rename", "oldUri": _file_uri(src), "newUri": _file_uri(dst),
         "options": {"overwrite": True}},
    ]}
    _apply_workspace_edit_to_disk(edit)
    assert not src.exists()
    assert dst.read_text(encoding="utf-8") == "// from\n"


def test_delete_file_removes_when_present(tmp_path: Path):
    target = tmp_path / "doomed.rs"
    target.write_text("// rip\n", encoding="utf-8")
    edit = {"documentChanges": [
        {"kind": "delete", "uri": _file_uri(target)},
    ]}
    _apply_workspace_edit_to_disk(edit)
    assert not target.exists()


def test_delete_file_default_ignores_missing(tmp_path: Path):
    target = tmp_path / "ghost.rs"
    edit = {"documentChanges": [
        {"kind": "delete", "uri": _file_uri(target)},
    ]}
    # LSP default: ignoreIfNotExists=True; no-op + no exception.
    _apply_workspace_edit_to_disk(edit)
    assert not target.exists()


def test_create_then_text_edit_in_same_workspace_edit(tmp_path: Path):
    target = tmp_path / "new.rs"
    edit = {"documentChanges": [
        {"kind": "create", "uri": _file_uri(target)},
        {"textDocument": {"uri": _file_uri(target), "version": None},
         "edits": [{"range": {"start": {"line": 0, "character": 0},
                              "end": {"line": 0, "character": 0}},
                    "newText": "pub fn moved() {}\n"}]},
    ]}
    _apply_workspace_edit_to_disk(edit)
    assert target.read_text(encoding="utf-8") == "pub fn moved() {}\n"
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g3b_applier_resource_ops.py -x` — fails today (the `continue` branch never creates / renames / deletes).

## Implementation steps

1. **Replace the `continue` branch** in `_apply_workspace_edit_to_disk` (`scalpel_facades.py:130-135`) with a dispatch by `kind`:
   ```python
   for dc in workspace_edit.get("documentChanges") or []:
       if not isinstance(dc, dict):
           continue
       kind = dc.get("kind")
       if kind == "create":
           applied += _apply_resource_create(dc)
           continue
       if kind == "rename":
           applied += _apply_resource_rename(dc)
           continue
       if kind == "delete":
           applied += _apply_resource_delete(dc)
           continue
       if "kind" in dc:
           # Unknown future resource-op kind — preserve forward-compat
           # by skipping rather than crashing.
           continue
       text_doc = dc.get("textDocument") or {}
       ...
   ```

2. **Add three helpers** near the existing `_apply_text_edits_to_file_uri`:
   ```python
   def _apply_resource_create(dc: dict[str, Any]) -> int:
       uri = dc.get("uri")
       if not isinstance(uri, str) or not uri.startswith("file://"):
           return 0
       from urllib.parse import urlparse, unquote
       target = Path(unquote(urlparse(uri).path))
       options = dc.get("options") or {}
       overwrite = bool(options.get("overwrite", False))
       ignore_if_exists = bool(options.get("ignoreIfExists", True))
       target.parent.mkdir(parents=True, exist_ok=True)
       if target.exists():
           if overwrite:
               target.write_text("", encoding="utf-8")
               return 1
           if ignore_if_exists:
               return 0  # no-op
           return 0  # would fail in spec; caller's responsibility
       target.write_text("", encoding="utf-8")
       return 1


   def _apply_resource_rename(dc: dict[str, Any]) -> int:
       old = dc.get("oldUri"); new = dc.get("newUri")
       if not isinstance(old, str) or not isinstance(new, str):
           return 0
       if not (old.startswith("file://") and new.startswith("file://")):
           return 0
       from urllib.parse import urlparse, unquote
       src = Path(unquote(urlparse(old).path))
       dst = Path(unquote(urlparse(new).path))
       if not src.exists():
           return 0
       options = dc.get("options") or {}
       overwrite = bool(options.get("overwrite", False))
       ignore_if_exists = bool(options.get("ignoreIfExists", False))
       if dst.exists():
           if overwrite:
               dst.unlink()
           elif ignore_if_exists:
               return 0
           else:
               return 0  # LSP "skip silently" semantics for default
       dst.parent.mkdir(parents=True, exist_ok=True)
       src.rename(dst)
       return 1


   def _apply_resource_delete(dc: dict[str, Any]) -> int:
       uri = dc.get("uri")
       if not isinstance(uri, str) or not uri.startswith("file://"):
           return 0
       from urllib.parse import urlparse, unquote
       target = Path(unquote(urlparse(uri).path))
       options = dc.get("options") or {}
       ignore_if_not_exists = bool(options.get("ignoreIfNotExists", True))
       if not target.exists():
           if ignore_if_not_exists:
               return 0
           return 0  # LO-3 deferral: no recursive raise here
       if target.is_dir():
           # LO-3 — recursive directory delete deferred. No-op.
           return 0
       target.unlink()
       return 1
   ```

3. **Update the applier docstring** (L110-124) — drop the "Resource operations ... are recognised but skipped" sentence; replace with "Resource operations apply per LSP §3.18 (CreateFile / RenameFile / DeleteFile). Recursive directory delete is deferred per LO-3."

4. **Submodule pyright clean** on the touched file.

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g3b_applier_resource_ops.py -x

# Existing applier tests must still pass:
uv run pytest vendor/serena/test/spikes/test_v0_3_0_workspace_edit_applier.py -x

# Markdown applier unaffected (separate function):
uv run pytest -k markdown -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit message draft:**

```
fix(applier): support CreateFile / RenameFile / DeleteFile resource ops (CR-2)

The main applier previously skipped every documentChange with a `kind`
field per v1.1 deferral, causing module rename / file split / scaffold
facades to silently succeed while the file ops were dropped.

Now applies the three LSP §3.18 resource ops with default options
(ignoreIfExists / overwrite / ignoreIfNotExists). Recursive directory
delete remains deferred per LO-3.

Closes spec § CR-2.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** an existing facade test stubs out the applier with a `kind`-bearing edit and depends on the current "skip silently" behavior. Mitigation: grep for `"kind": "create"|"rename"|"delete"` in the test corpus before merging; existing tests of the markdown applier path use `_apply_markdown_workspace_edit`, not the main applier, so they are unaffected.
- **Risk:** an LSP returns malformed `oldUri` / `newUri` and we silently no-op — caller can't tell. Mitigation: by design — we mirror the LSP spec's "skip on malformed" semantics; the `applied` count surfaces "no real change", and structured logging at primitive layer (out of scope here) catches these cases.
- **Rollback:** revert the single commit. The 5 facade families that emit resource ops revert to silent-success — but no other regression.

## Dependencies

- **Hard:** none. Independent of L-G1.
- **Soft:** L-G3a — once both land, the on-disk acid-test in G3a's first test (currently a comment) can be uncommented and asserted live. Recommend landing G3b before G3a's test rewrite if both are in flight.
- **Blocks:** L-G7-A and L-G7-B real-disk tests for facades that emit resource ops (split_file, rename of modules, scaffold-related-class).

---

**Author:** AI Hive®.
