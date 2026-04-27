# 03 — `scalpel_reload_plugins` MCP Tool

## Goal

Implement the `scalpel_reload_plugins` MCP tool named in Q10 resolution but unimplemented at MVP. Refreshes the in-process plugin/capability snapshot without restarting the server (mirrors Serena precedent — no filesystem watcher, explicit refresh tool only, per `B-design.md` §4 Q10).

**Size:** Small (~120 LoC + ~80 LoC tests).
**Evidence:** `WHAT-REMAINS.md` §5 line 115; `B-design.md` §4 row Q10 ("refresh via `scalpel_reload_plugins`, matches Serena precedent"); `open-questions-resolution.md` §Q10.

## Architecture decision

Tool is a `Tool` subclass next to `ScalpelCapabilitiesListTool` in `scalpel_primitives.py`. Reload path: re-scan `plugins/` directory, rebuild capability catalog, re-validate all plugin manifests via the marketplace pydantic schema (cross-leaf — see leaf 01), atomically swap the in-process registry.

```mermaid
graph LR
  T[scalpel_reload_plugins] --> S[scan plugins/]
  S --> V[validate manifests]
  V --> C[rebuild capability catalog]
  C --> A[atomic swap registry]
  A --> R[return reload report]
```

## File structure

| Path | Action | Purpose |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_primitives.py` | EDIT | Add `ScalpelReloadPluginsTool` class. |
| `vendor/serena/src/serena/plugins/registry.py` | EDIT (or NEW) | Add `reload()` to in-process plugin registry. |
| `vendor/serena/src/serena/plugins/reload_report.py` | NEW | Pydantic `ReloadReport`. |
| `vendor/serena/test/serena/tools/test_scalpel_reload_plugins.py` | NEW | Tool-level tests. |
| `vendor/serena/test/serena/plugins/test_registry_reload.py` | NEW | Registry-level tests. |

## Tasks

### Task 1 — `ReloadReport` pydantic model

**Step 1.1 — Failing test.**

```python
from serena.plugins.reload_report import ReloadReport

def test_reload_report_minimal() -> None:
    r = ReloadReport(added=("rust",), removed=(), unchanged=("python",), errors=())
    assert r.added == ("rust",)
    assert r.is_clean is True

def test_reload_report_errors_mark_unclean() -> None:
    r = ReloadReport(added=(), removed=(), unchanged=(),
                     errors=(("kotlin", "missing plugin.json"),))
    assert r.is_clean is False
```

Run → fails.

**Step 1.2 — Implement** `reload_report.py`:

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, computed_field

class ReloadReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]
    errors: tuple[tuple[str, str], ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_clean(self) -> bool:
        return not self.errors
```

**Step 1.3 — Run passing + commit.**

### Task 2 — Registry `reload()` method

**Step 2.1 — Failing test.** `test/serena/plugins/test_registry_reload.py`:

```python
from pathlib import Path
from serena.plugins.registry import PluginRegistry

def test_registry_reload_picks_up_new_plugin(tmp_path: Path) -> None:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    reg = PluginRegistry(plugins_dir)
    assert reg.list_ids() == []
    _make_plugin(plugins_dir / "rust", id_="rust")
    report = reg.reload()
    assert report.added == ("rust",)
    assert reg.list_ids() == ["rust"]
```

(`_make_plugin` writes `.claude-plugin/plugin.json`.) Run → fails.

**Step 2.2 — Implement.** `registry.py` `PluginRegistry.reload()`:

```python
def reload(self) -> ReloadReport:
    new_state = self._scan(self._plugins_dir)
    old_ids = set(self._state.keys())
    new_ids = set(new_state.keys())
    added = tuple(sorted(new_ids - old_ids))
    removed = tuple(sorted(old_ids - new_ids))
    unchanged = tuple(sorted(old_ids & new_ids))
    errors = tuple(self._collect_errors(new_state))
    self._state = new_state  # atomic swap
    return ReloadReport(added=added, removed=removed,
                        unchanged=unchanged, errors=errors)
```

**Step 2.3 — Run passing + commit.**

### Task 3 — `ScalpelReloadPluginsTool`

**Step 3.1 — Failing test.** `test/serena/tools/test_scalpel_reload_plugins.py`:

```python
from serena.tools.scalpel_primitives import ScalpelReloadPluginsTool

def test_reload_tool_returns_clean_report(monkeypatch, fake_registry):
    fake_registry.set_state({"rust": "0.1.0"})
    tool = ScalpelReloadPluginsTool(registry=fake_registry)
    out = tool.apply()
    assert out["is_clean"] is True
    assert out["unchanged"] == ["rust"] or out["added"] == ["rust"]

def test_reload_tool_surfaces_errors(fake_registry):
    fake_registry.inject_error("kotlin", "missing plugin.json")
    tool = ScalpelReloadPluginsTool(registry=fake_registry)
    out = tool.apply()
    assert out["is_clean"] is False
    assert out["errors"] == [["kotlin", "missing plugin.json"]]
```

Run → fails.

**Step 3.2 — Implement.** Add to `scalpel_primitives.py`:

```python
class ScalpelReloadPluginsTool(Tool):
    """Reload plugin/capability registry from disk without restarting the server.

    Use after generating a new plugin via `o2-scalpel-newplugin` or after editing
    a plugin manifest. Mirrors Serena's explicit-refresh model (no filesystem watcher).
    """

    def apply(self) -> dict[str, object]:
        report = self._registry.reload()
        return report.model_dump(mode="json")
```

The `Tool` registration mechanism is `iter_subclasses(Tool)` (per `scalpel_primitives.py:4` docstring) — class definition is sufficient for MCP exposure as `scalpel_reload_plugins`.

**Step 3.3 — Run passing + commit.**

### Task 4 — Smoke-test via MCP boundary

**Step 4.1 — Failing test.** Add an integration test that invokes the tool through the MCP transport (or its in-process equivalent) and confirms the snake-cased name matches.

```python
def test_reload_tool_registered_under_snake_case_name(mcp_test_harness):
    names = mcp_test_harness.list_tool_names()
    assert "scalpel_reload_plugins" in names
```

**Step 4.2 — Implement.** Make sure no `register=False` flag suppresses the class; verify `Tool.get_name_from_cls` returns `scalpel_reload_plugins`.

**Step 4.3 — Run passing + commit.**

## Self-review checklist

- [ ] Tool name resolves to `scalpel_reload_plugins` via existing class-name convention.
- [ ] Reload is atomic (swap, not in-place mutation).
- [ ] Errors per-plugin do not block reload of healthy plugins.
- [ ] `ReloadReport` is pydantic frozen.
- [ ] Manual-refresh model (no filesystem watcher) — matches Q10 decision.
- [ ] No emoji; Mermaid only.

*Author: AI Hive(R)*
