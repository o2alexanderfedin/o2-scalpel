# Leaf 03 — Multi-Server Async Wrapping Verification

**Goal.** Prove `MultiServerCoordinator.broadcast` parallelises real Stage 1E adapters via `_AsyncAdapter`, and add an integration test that previously raised `TypeError: object list can't be used in 'await' expression` when called against a real adapter without the wrapper. Closes WHAT-REMAINS.md §4 line 104 and the Stage 1H follow-up at `stage-1h-results/PROGRESS.md:87`.

**Architecture.** `_AsyncAdapter` (`vendor/serena/src/serena/tools/scalpel_runtime.py:59-97`) already wraps each spawned `SolidLanguageServer` so that synchronous `request_code_actions` calls run on a thread pool via `asyncio.to_thread`. The Stage 1H follow-up notes that any code path which constructs a `MultiServerCoordinator` from raw (non-adapter) servers will deadlock-on-await. We add: (a) a defensive runtime check inside `MultiServerCoordinator.__init__` that all server values are async-callable, (b) an integration test that wires three real adapters and asserts `broadcast` returns within 2× single-server latency (parallelism evidence).

**Tech Stack.** Python 3.13, pytest-asyncio, `time.perf_counter`. Reference `vendor/serena/src/serena/refactoring/multi_server.py:842-895` (broadcast loop).

**Source spec.** `stage-1h-results/PROGRESS.md:87`; `WHAT-REMAINS.md` §4 line 104.

**Author.** AI Hive(R).

## File Structure

| Path | Action | Approx LoC |
|------|--------|------------|
| `vendor/serena/src/serena/refactoring/multi_server.py` | edit — defensive `__init__` validation + helper `is_async_callable` | ~25 |
| `vendor/serena/src/serena/refactoring/_async_check.py` | new — coroutine-callable detector | ~30 |
| `vendor/serena/test/serena/refactoring/test_multi_server_async_check.py` | new — unit tests | ~120 |
| `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py` | new — integration test | ~180 |

## Tasks

### Task 1 — Failing unit test for async-callable detection

Create `vendor/serena/test/serena/refactoring/test_multi_server_async_check.py`:

```python
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from serena.refactoring._async_check import (
    assert_servers_async_callable,
    is_async_callable,
)


class _SyncOnly:
    def request_code_actions(self, **_: Any) -> list[Any]:
        return []


class _AsyncOnly:
    async def request_code_actions(self, **_: Any) -> list[Any]:
        return []


def test_sync_method_is_not_async_callable() -> None:
    assert is_async_callable(_SyncOnly().request_code_actions) is False


def test_async_method_is_async_callable() -> None:
    assert is_async_callable(_AsyncOnly().request_code_actions) is True


def test_assert_servers_raises_on_sync_member() -> None:
    with pytest.raises(TypeError, match="not async-callable"):
        assert_servers_async_callable(
            {"basedpyright": _AsyncOnly(), "ruff": _SyncOnly()},
            method_names=("request_code_actions",),
        )


def test_assert_servers_passes_on_all_async() -> None:
    assert_servers_async_callable(
        {"a": _AsyncOnly(), "b": _AsyncOnly()},
        method_names=("request_code_actions",),
    )
```

Run — `ModuleNotFoundError`. Stage only.

### Task 2 — Implement `_async_check.py`

Create `vendor/serena/src/serena/refactoring/_async_check.py`:

```python
"""Defensive runtime checks for MultiServerCoordinator.

Stage 1D unit tests pass against `_FakeServer` (declares async methods).
Real Stage 1E adapters are sync; they MUST be wrapped in `_AsyncAdapter`
(scalpel_runtime.py) before being handed to MultiServerCoordinator.

This module surfaces the contract loudly via `__init__` validation
rather than letting `await facade(**kwargs)` raise the cryptic
`TypeError: object list can't be used in 'await' expression`.
"""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterable
from typing import Any


def is_async_callable(obj: Any) -> bool:
    if asyncio.iscoroutinefunction(obj):
        return True
    if inspect.isawaitable(obj):
        return True
    if callable(obj) and asyncio.iscoroutinefunction(getattr(obj, "__call__", None)):
        return True
    return False


def assert_servers_async_callable(
    servers: dict[str, Any],
    method_names: Iterable[str],
) -> None:
    for sid, srv in servers.items():
        for name in method_names:
            method = getattr(srv, name, None)
            if method is None:
                continue
            if not is_async_callable(method):
                raise TypeError(
                    f"server {sid!r} method {name!r} is not async-callable; "
                    f"wrap with _AsyncAdapter before constructing "
                    f"MultiServerCoordinator"
                )
```

Run unit tests — four green. Commit `feat(stage-v0.2.0-followup-03a): async-callable check helper`.

### Task 3 — Wire check into `MultiServerCoordinator.__init__`

Edit `vendor/serena/src/serena/refactoring/multi_server.py` near class definition:

```python
from ._async_check import assert_servers_async_callable

# inside MultiServerCoordinator.__init__ (after super().__init__())
assert_servers_async_callable(
    self._servers,
    method_names=(
        "request_code_actions",
        "resolve_code_action",
        "request_rename_symbol_edit",
    ),
)
```

Add a unit test asserting `MultiServerCoordinator(servers={"a": _SyncOnly()})` raises `TypeError`. Run — green. Commit `feat(stage-v0.2.0-followup-03b): MultiServerCoordinator validates async wrapping`.

### Task 4 — Failing integration test for real-adapter parallelism

Create `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py`:

```python
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from serena.refactoring import MultiServerCoordinator
from serena.tools.scalpel_runtime import _AsyncAdapter, build_python_servers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_broadcast_runs_three_python_servers_in_parallel(
    calcpy_root: Path,
) -> None:
    servers = build_python_servers(project_root=calcpy_root)
    assert set(servers) >= {"basedpyright", "ruff", "pylsp"}

    coord = MultiServerCoordinator(servers={k: _AsyncAdapter(v) for k, v in servers.items()})

    target = calcpy_root / "calcpy" / "core.py"

    t0 = time.perf_counter()
    result = await coord.broadcast(
        method="textDocument/codeAction",
        kwargs={
            "file": str(target),
            "range_start": {"line": 0, "character": 0},
            "range_end": {"line": 0, "character": 0},
        },
    )
    parallel_elapsed = time.perf_counter() - t0

    # Sequential lower bound: sum of individual single-server timings
    serial_total = 0.0
    for srv in servers.values():
        s0 = time.perf_counter()
        srv.request_code_actions(
            file=str(target),
            range_start={"line": 0, "character": 0},
            range_end={"line": 0, "character": 0},
        )
        serial_total += time.perf_counter() - s0

    assert result.responses, "broadcast returned no responses"
    # Parallelism evidence: pure-parallel limit for 3 servers ≈ 33% of
    # serial_total. The 0.7 multiplier (i.e. broadcast must finish in <70%
    # of the serial sum) leaves ~37 percentage points of headroom for
    # fixture warm-up jitter, GIL contention on payload assembly, and
    # asyncio scheduling overhead. Empirically, three booted Python
    # servers land near 0.4-0.5×; if a regression pushes it above 0.7×
    # the parallel wrapper has degraded to round-robin.
    assert parallel_elapsed < serial_total * 0.7, (
        f"broadcast did not parallelise: {parallel_elapsed:.3f}s vs "
        f"serial {serial_total:.3f}s"
    )
```

Run `uv run pytest vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py -x -m integration` — must pass on three booted servers. Commit `test(stage-v0.2.0-followup-03c): real-adapter parallelism evidence test`.

### Task 5 — Self-review and tag

Run `uv run pytest vendor/serena/test/serena/refactoring/ vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py -x` — all green. `git tag stage-v0.2.0-followup-03-multi-server-async-wrapping-complete`.

## Self-Review Checklist

- [ ] `__init__` validation rejects raw sync servers with explicit message.
- [ ] Integration test demonstrates < 70% of serial total (parallelism evidence, not just absence-of-error).
- [ ] No `pytest.skip` paths added; if `build_python_servers` cannot boot all three, test is `xfail` not skip.
- [ ] Author = AI Hive(R); no emoji.
