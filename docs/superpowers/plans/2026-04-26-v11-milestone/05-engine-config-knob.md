# 05 — Engine Config Knob

## Goal

Add a runtime engine-selection knob so callers can pick between LSP-write engines (today: the bundled o2-scalpel-engine fork of Serena; future: alternates such as native LSP-write integrations or `lspee` multiplexer when 1.0 lands). Project-memory note from v0.2.0 critical-path explicitly named this; MVP deferred.

**Size:** Small (~90 LoC + ~80 LoC tests).
**Evidence:** `WHAT-REMAINS.md` §5 line 117 ("Engine config knob — project-memory note from v0.2.0 critical-path"); project memory `project_v0_2_0_critical_path.md`; `B-design.md` §3 (Anthropic native LSP-write as deprecation trigger — knob is the seam for that handoff).

## Architecture decision

Knob is a single environment variable + matching pydantic-validated settings field, both pointing at a registry of engines. Registry is dict-of-protocols. Default value is `"serena-fork"` (current behavior). Validation rejects unknown engine ids by consulting the registry at runtime — **the engine id is a `str` validated against `EngineRegistry.default().keys()`, not a `Literal`** (per critic R1: a single-member `Literal` would block adding the named v1.x alternates without a backward-incompatible Settings change). Switching engines is a server-restart action (not hot-swap) — keeps the seam minimal.

```mermaid
graph LR
  ENV[O2_SCALPEL_ENGINE] --> S[Settings.engine]
  S --> V[validator queries EngineRegistry.default()]
  V --> R[EngineRegistry]
  R --> E1[serena-fork]
  R --> E2[future: native]
  R --> E3[future: lspee]
```

## File structure

| Path | Action | Purpose |
|---|---|---|
| `vendor/serena/src/serena/config/engine.py` | NEW | `Settings.engine` field + registry-backed validator. |
| `vendor/serena/src/serena/engine/registry.py` | NEW | `EngineRegistry` mapping id → factory. |
| `vendor/serena/test/serena/config/test_engine_setting.py` | NEW | Settings tests. |
| `vendor/serena/test/serena/engine/test_registry.py` | NEW | Registry resolution tests. |

## Tasks

### Task 1 — Engine settings field with registry-backed validator

**Step 1.1 — Failing test.** `test/serena/config/test_engine_setting.py`:

```python
import pytest
from pydantic import ValidationError
from serena.config.engine import Settings

def test_engine_default_is_serena_fork(monkeypatch):
    monkeypatch.delenv("O2_SCALPEL_ENGINE", raising=False)
    s = Settings()
    assert s.engine == "serena-fork"

def test_engine_from_env(monkeypatch):
    monkeypatch.setenv("O2_SCALPEL_ENGINE", "serena-fork")
    s = Settings()
    assert s.engine == "serena-fork"

def test_engine_unknown_value_rejected(monkeypatch):
    monkeypatch.setenv("O2_SCALPEL_ENGINE", "definitely-not-real")
    with pytest.raises(ValidationError):
        Settings()

def test_engine_accepts_newly_registered_id(monkeypatch):
    """Registering a new engine at runtime extends the accepted-value set
    without a Settings code change — confirms the registry-backed seam."""
    from serena.engine.registry import EngineRegistry
    EngineRegistry.default().register("native", lambda: object())
    try:
        monkeypatch.setenv("O2_SCALPEL_ENGINE", "native")
        s = Settings()
        assert s.engine == "native"
    finally:
        EngineRegistry.default()._factories.pop("native", None)
```

Run → fails.

**Step 1.2 — Implement.** `engine.py`:

```python
from __future__ import annotations
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime knob for selecting the LSP-write engine implementation.

    Per critic R1: `engine` is a registry-validated `str` rather than a
    single-member `Literal`. This keeps the seam open for the named v1.x
    alternates (`native`, `lspee`) — adding one becomes a single
    `EngineRegistry.default().register(...)` call with NO Settings change.
    """

    model_config = SettingsConfigDict(env_prefix="O2_SCALPEL_", extra="ignore")
    engine: str = "serena-fork"

    @field_validator("engine")
    @classmethod
    def _validate_engine_is_registered(cls, value: str) -> str:
        # Lazy import: importing the registry at module top would create a
        # settings-load loop with the applier (registry.default() pulls in
        # the applier factory, which itself reads Settings). See S5.
        from serena.engine.registry import EngineRegistry

        known = set(EngineRegistry.default().keys())
        if value not in known:
            raise ValueError(
                f"engine '{value}' is not registered; "
                f"known engines: {sorted(known)}"
            )
        return value
```

**Step 1.3 — Run passing + commit.**

### Task 2 — `EngineRegistry`

**Step 2.1 — Failing test.** `test/serena/engine/test_registry.py`:

```python
from serena.engine.registry import EngineRegistry

def test_registry_returns_factory_for_known_engine():
    reg = EngineRegistry.default()
    factory = reg.get("serena-fork")
    instance = factory()
    assert hasattr(instance, "apply_workspace_edit")

def test_registry_raises_on_unknown():
    reg = EngineRegistry.default()
    import pytest
    with pytest.raises(KeyError):
        reg.get("ghost")

def test_registry_keys_lists_registered_ids():
    reg = EngineRegistry.default()
    assert "serena-fork" in reg.keys()
```

Run → fails.

**Step 2.2 — Implement.** `registry.py`:

```python
from __future__ import annotations
from typing import Callable, Iterable, Protocol


class EngineProtocol(Protocol):
    def apply_workspace_edit(self, edit: object) -> object: ...


class EngineRegistry:
    """Process-wide registry mapping engine-id strings to factories.

    Adding a new engine is one `register(...)` call — no Settings code
    change required (the validator on `Settings.engine` queries this
    registry at validation time). See critic R1 for rationale.
    """

    _singleton: "EngineRegistry | None" = None

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], EngineProtocol]] = {}

    def register(self, engine_id: str, factory: Callable[[], EngineProtocol]) -> None:
        self._factories[engine_id] = factory

    def get(self, engine_id: str) -> Callable[[], EngineProtocol]:
        try:
            return self._factories[engine_id]
        except KeyError as exc:
            raise KeyError(f"engine '{engine_id}' is not registered") from exc

    def keys(self) -> Iterable[str]:
        return self._factories.keys()

    @classmethod
    def default(cls) -> "EngineRegistry":
        if cls._singleton is None:
            # Lazy import (S5): avoids a settings-load loop with the
            # applier — `build_default_applier` itself reads Settings,
            # and Settings imports this module to validate `engine`.
            # Importing at module top would deadlock the import graph.
            from serena.refactoring.applier import build_default_applier

            reg = cls()
            reg.register("serena-fork", build_default_applier)
            cls._singleton = reg
        return cls._singleton
```

**Step 2.3 — Run passing + commit.**

### Task 3 — Wire registry into server bootstrap

**Step 3.1 — Failing test.** Bootstrap test asserts the resolved applier matches the engine knob.

```python
def test_bootstrap_uses_engine_from_settings(monkeypatch):
    monkeypatch.setenv("O2_SCALPEL_ENGINE", "serena-fork")
    from serena.bootstrap import build_runtime
    rt = build_runtime()
    assert rt.engine_id == "serena-fork"
```

**Step 3.2 — Implement.** Edit bootstrap to read `Settings().engine`, call `EngineRegistry.default().get(...)`, instantiate, and stash `engine_id` on the runtime context.

**Step 3.3 — Run passing + commit.**

## Self-review checklist

- [ ] Default behavior unchanged (knob defaults to `"serena-fork"`).
- [ ] Unknown engine id is rejected at settings load (pydantic field validator), not at bootstrap.
- [ ] Registry is a clean seam — adding an engine is one `register(...)` call (R1).
- [ ] No `Literal` on `engine`; type is `str` validated against the live registry (R1).
- [ ] Engine swap requires restart (no hot-swap complexity).
- [ ] Lazy import of `build_default_applier` documented inline (S5 — load-order rationale).
- [ ] No emoji; Mermaid only.

*Author: AI Hive(R)*
