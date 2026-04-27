# Leaf 01 — basedpyright Dynamic Capability Discovery

> **STATUS: SHIPPED 2026-04-26** — see `stage-v0.2.0-followups-complete` tag (parent + submodule). Cross-reference: `docs/gap-analysis/WHAT-REMAINS.md` §4 line 104 + `docs/superpowers/plans/stage-1h-results/PROGRESS.md` §85.
>
> **Implementation deviations from this plan** (recorded post-shipment):
> - Plan referenced `vendor/serena/src/solidlsp/language_server.py` (nonexistent); actual file is `vendor/serena/src/solidlsp/ls.py`.
> - Implementation reflected SoT in `DynamicCapabilityRegistry` keyed by `server_id` ClassVar (basedpyright + pylsp wired); future concrete servers opt in by setting `server_id: ClassVar[str]`.

**Goal.** Augment the `workspace_health` catalog post-init from each booted server's `client/registerCapability` events so basedpyright's diagnostic-only registration is reflected in `capabilities_count`, or explicitly mark diagnostic-only servers as hidden in the response schema. Closes WHAT-REMAINS.md §4 line 102.

**Architecture.** Static catalog in `solidlsp/language_servers_capabilities.py` is consulted at boot. After each server's `initialized` notification, dynamic `client/registerCapability` requests arrive (already accepted by `pylsp_server.py:166`, `eclipse_jdtls.py:880`, etc.) but are not surfaced to the workspace_health primitive. We add a per-server `dynamic_capabilities: list[str]` accumulator and merge it into `LanguageRecord.capabilities_count` when the workspace_health tool runs.

**Tech Stack.** Python 3.13, pydantic boundaries, pytest, pytest-asyncio. Reference WHAT-REMAINS.md §4 and `docs/design/mvp/open-questions/q3-basedpyright-pinning.md`.

**Source spec.** `stage-1h-results/PROGRESS.md:83` (basedpyright dynamic-capability bullet, anchor for the Concerns/follow-ups block); `vendor/serena/src/serena/tools/scalpel_primitives.py:533` (`capabilities_count` build site); `vendor/serena/src/serena/tools/scalpel_schemas.py:222` (`LanguageRecord.capabilities_count` field); `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:166` (existing register-capability handler).

**Author.** AI Hive(R).

## File Structure

| Path | Action | Approx LoC |
|------|--------|------------|
| `vendor/serena/src/solidlsp/dynamic_capabilities.py` | new — per-server dynamic capability registry | ~80 |
| `vendor/serena/src/solidlsp/language_server.py` | edit — wire registry into base `SolidLanguageServer` | ~20 |
| `vendor/serena/src/solidlsp/language_servers/pylsp_server.py` | edit — record dynamic registrations into registry | ~5 |
| `vendor/serena/src/solidlsp/language_servers/basedpyright_server.py` | edit — record dynamic registrations into registry | ~5 |
| `vendor/serena/src/serena/tools/scalpel_primitives.py` | edit — merge dynamic into `capabilities_count` | ~10 |
| `vendor/serena/src/serena/tools/scalpel_schemas.py` | edit — add `dynamic_capabilities: list[str]` field on `LanguageRecord` | ~3 |
| `vendor/serena/test/serena/test_dynamic_capabilities.py` | new — unit tests for registry | ~120 |
| `vendor/serena/test/serena/test_workspace_health_dynamic.py` | new — integration test for primitive surface | ~150 |

## Tasks

### Task 1 — Failing unit test for dynamic-capability registry

Create `vendor/serena/test/serena/test_dynamic_capabilities.py`:

```python
from __future__ import annotations

import pytest

from solidlsp.dynamic_capabilities import DynamicCapabilityRegistry


def test_registry_starts_empty() -> None:
    reg = DynamicCapabilityRegistry()
    assert reg.list_for("basedpyright") == []


def test_register_appends_unique_methods() -> None:
    reg = DynamicCapabilityRegistry()
    reg.register("basedpyright", "textDocument/publishDiagnostics")
    reg.register("basedpyright", "textDocument/publishDiagnostics")
    reg.register("basedpyright", "textDocument/codeAction")
    assert reg.list_for("basedpyright") == [
        "textDocument/publishDiagnostics",
        "textDocument/codeAction",
    ]


def test_register_isolates_per_server() -> None:
    reg = DynamicCapabilityRegistry()
    reg.register("basedpyright", "textDocument/publishDiagnostics")
    reg.register("ruff", "workspace/executeCommand")
    assert reg.list_for("basedpyright") == ["textDocument/publishDiagnostics"]
    assert reg.list_for("ruff") == ["workspace/executeCommand"]
    assert reg.list_for("absent") == []
```

Run `uv run pytest vendor/serena/test/serena/test_dynamic_capabilities.py -x` — confirm `ModuleNotFoundError`. Commit-stage the test only.

### Task 2 — Implement `DynamicCapabilityRegistry`

Create `vendor/serena/src/solidlsp/dynamic_capabilities.py`:

```python
"""Per-server dynamic-capability registry, populated from
`client/registerCapability` events at runtime (LSP 3.17 §10.6).

Scope of correctness: registry holds string method names only;
client decides whether a method counts toward `capabilities_count`.
"""
from __future__ import annotations

from threading import Lock


class DynamicCapabilityRegistry:
    """Append-only, thread-safe per-server registry.

    Keys are server identifiers (e.g. ``"basedpyright"``, ``"ruff"``);
    values are the LSP method names the server registered dynamically.
    Duplicate registrations are deduplicated.
    """

    def __init__(self) -> None:
        self._by_server: dict[str, list[str]] = {}
        self._lock = Lock()

    def register(self, server_id: str, method: str) -> None:
        with self._lock:
            existing = self._by_server.setdefault(server_id, [])
            if method not in existing:
                existing.append(method)

    def list_for(self, server_id: str) -> list[str]:
        with self._lock:
            return list(self._by_server.get(server_id, []))
```

Run `uv run pytest vendor/serena/test/serena/test_dynamic_capabilities.py -x` — three green. Commit `feat(stage-v0.2.0-followup-01a): introduce DynamicCapabilityRegistry`.

### Task 3 — Failing integration test for workspace_health surface

Create `vendor/serena/test/serena/test_workspace_health_dynamic.py`:

```python
from __future__ import annotations

import json

import pytest

from serena.tools.scalpel_primitives import build_workspace_health
from solidlsp.dynamic_capabilities import DynamicCapabilityRegistry


@pytest.mark.integration
def test_workspace_health_counts_dynamic_capabilities(tmp_path) -> None:
    registry = DynamicCapabilityRegistry()
    registry.register("basedpyright", "textDocument/publishDiagnostics")
    registry.register("basedpyright", "textDocument/codeAction")

    result = build_workspace_health(
        project_root=tmp_path,
        language="python",
        dynamic_registry=registry,
    )
    payload = json.loads(result)
    py_record = next(r for r in payload["languages"] if r["language"] == "python")
    assert "textDocument/codeAction" in py_record["dynamic_capabilities"]
    assert py_record["capabilities_count"] >= 2
```

Run `uv run pytest vendor/serena/test/serena/test_workspace_health_dynamic.py -x` — confirm failure (signature mismatch). Stage test only.

### Task 4 — Wire registry through `build_workspace_health`

Edit `vendor/serena/src/serena/tools/scalpel_schemas.py`:

```python
class LanguageRecord(BaseModel):
    language: str
    capabilities_count: int = 0
    dynamic_capabilities: list[str] = Field(default_factory=list)
```

Edit `vendor/serena/src/serena/tools/scalpel_primitives.py` near line 533:

```python
dyn = (dynamic_registry.list_for(lang) if dynamic_registry else [])
records.append(
    LanguageRecord(
        language=lang,
        capabilities_count=len(lang_records) + len(dyn),
        dynamic_capabilities=dyn,
    )
)
```

Add `dynamic_registry: DynamicCapabilityRegistry | None = None` to `build_workspace_health` signature. Run `uv run pytest vendor/serena/test/serena/test_workspace_health_dynamic.py -x` — green. Commit `feat(stage-v0.2.0-followup-01b): surface dynamic capabilities in workspace_health`.

### Task 5 — Wire registrations from pylsp + basedpyright handlers

Edit `vendor/serena/src/solidlsp/language_servers/basedpyright_server.py` (the `register_capability_handler` method, mirroring the existing handler at `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:166`):

```python
def register_capability_handler(params: dict[str, object]) -> dict[str, object]:
    for reg in params.get("registrations", []):
        method = reg.get("method")
        if isinstance(method, str):
            self._dynamic_registry.register("basedpyright", method)
    return {}
```

Mirror in `pylsp_server.py:166` (replace the existing no-op body with the same registration loop, parameterised on `"pylsp"`). Add a regression test asserting that booting basedpyright populates `dynamic_capabilities` for the `python` record. Run; commit `feat(stage-v0.2.0-followup-01c): record basedpyright + pylsp dynamic registrations`.

### Task 6 — Self-review and tag

Run `uv run pytest vendor/serena/test/serena/ -x -k "capabilit"` — all green. Run `uv run mypy vendor/serena/src/solidlsp/dynamic_capabilities.py` — clean. `git tag stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete`.

## Self-Review Checklist

- [ ] All three test files green; `pytest -p no:randomly` re-run ≥3× passes.
- [ ] No `dynamic_capabilities` field omitted on legacy `LanguageRecord` consumers.
- [ ] Registry is thread-safe (registrations may arrive on the LSP read thread).
- [ ] No emoji, no time estimates, author = AI Hive(R).
- [ ] WHAT-REMAINS.md §4 line 102 marked closed in the next gap-analysis pass.
