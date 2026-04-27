# 02 — Persistent Disk Checkpoints

## Goal

Replace the LRU-only in-memory `CheckpointStore` with a durable disk-backed store so checkpoints survive process restarts. The MVP store evicts at LRU(50); v1.1 keeps the LRU recency layer in front of a write-through pydantic-serialized disk store under `${O2_SCALPEL_CACHE}/checkpoints/`.

**Size:** Medium (~280 LoC + ~180 LoC tests).
**Evidence:** `WHAT-REMAINS.md` §5 line 114; `B-design.md` §4 row "Persistent disk checkpoints"; existing in-memory store at `vendor/serena/src/serena/refactoring/checkpoints.py:124` (`class CheckpointStore`); LRU(50) doc comment at line 6.
**Existing collaborators:** `Checkpoint` dataclass at `checkpoints.py:108`; `inverse_workspace_edit` at `checkpoints.py:23`.

## Architecture decision

```mermaid
graph LR
  Caller[applier] --> Store[CheckpointStore]
  Store --> LRU[LRU(50) cache]
  Store --> Disk[DiskCheckpointStore]
  Disk --> File[(pydantic JSON files)]
```

LRU stays in front (hot-path latency). Disk acts as the source of truth across sessions. On `get`, miss in LRU falls back to disk. On `put`, both are written. Eviction from LRU does NOT delete from disk; disk has its own retention (configurable; default 200 entries, oldest first).

## File structure

| Path | Action | Purpose |
|---|---|---|
| `vendor/serena/src/serena/refactoring/checkpoint_disk.py` | NEW | `DiskCheckpointStore` with pydantic schema. |
| `vendor/serena/src/serena/refactoring/checkpoint_schema.py` | NEW | `PersistedCheckpoint` pydantic model. |
| `vendor/serena/src/serena/refactoring/checkpoints.py` | EDIT | `CheckpointStore` composes `DiskCheckpointStore`. |
| `vendor/serena/test/serena/refactoring/test_checkpoint_disk.py` | NEW | Disk store tests. |
| `vendor/serena/test/serena/refactoring/test_checkpoint_persistence.py` | NEW | Cross-session integration test. |

## Tasks

### Task 1 — Define `PersistedCheckpoint` schema

**Step 1.1 — Failing test.** `test/serena/refactoring/test_checkpoint_disk.py`:

```python
import pytest
from pydantic import ValidationError
from serena.refactoring.checkpoint_schema import PersistedCheckpoint

def test_persisted_checkpoint_required_fields() -> None:
    p = PersistedCheckpoint(
        id="ckpt-1", schema_version=1, created_at_ns=1,
        inverse_edit={"changes": {}}, file_versions={"file:///a.py": 0},
    )
    assert p.id == "ckpt-1"

def test_persisted_checkpoint_rejects_extras() -> None:
    with pytest.raises(ValidationError):
        PersistedCheckpoint(id="x", schema_version=1, created_at_ns=1,
                            inverse_edit={}, file_versions={}, junk="no")  # type: ignore[call-arg]
```

Run → fails.

**Step 1.2 — Implement** `checkpoint_schema.py`:

```python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class PersistedCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int = Field(default=1, ge=1)
    id: str = Field(min_length=1)
    created_at_ns: int = Field(ge=0)
    inverse_edit: dict[str, Any]
    file_versions: dict[str, int]
```

**Step 1.3 — Run passing + commit.**

### Task 2 — Implement `DiskCheckpointStore` (write/read/list/evict)

**Step 2.1 — Failing test.**

```python
from pathlib import Path
from serena.refactoring.checkpoint_disk import DiskCheckpointStore
from serena.refactoring.checkpoint_schema import PersistedCheckpoint

def test_disk_store_round_trip(tmp_path: Path) -> None:
    s = DiskCheckpointStore(tmp_path)
    p = PersistedCheckpoint(id="c1", schema_version=1, created_at_ns=10,
                            inverse_edit={"changes": {}}, file_versions={})
    s.put(p)
    got = s.get("c1")
    assert got == p

def test_disk_store_evicts_oldest(tmp_path: Path) -> None:
    s = DiskCheckpointStore(tmp_path, max_entries=2)
    for i, ts in enumerate([10, 20, 30]):
        s.put(PersistedCheckpoint(id=f"c{i}", schema_version=1,
                                  created_at_ns=ts, inverse_edit={}, file_versions={}))
    assert s.get("c0") is None
    assert s.get("c1") is not None and s.get("c2") is not None
```

Run → fails.

**Step 2.2 — Implement** `checkpoint_disk.py`:

```python
from __future__ import annotations
import json
from pathlib import Path
from .checkpoint_schema import PersistedCheckpoint

class DiskCheckpointStore:
    def __init__(self, root: Path, max_entries: int = 200) -> None:
        self._root = root
        self._max = max_entries
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, ckpt_id: str) -> Path:
        return self._root / f"{ckpt_id}.json"

    def put(self, ckpt: PersistedCheckpoint) -> None:
        self._path(ckpt.id).write_text(ckpt.model_dump_json())
        self._evict()

    def get(self, ckpt_id: str) -> PersistedCheckpoint | None:
        path = self._path(ckpt_id)
        if not path.is_file():
            return None
        return PersistedCheckpoint.model_validate_json(path.read_text())

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self._root.glob("*.json"))

    def _evict(self) -> None:
        files = sorted(self._root.glob("*.json"),
                       key=lambda p: p.stat().st_mtime)
        while len(files) > self._max:
            files.pop(0).unlink(missing_ok=True)
            files = sorted(self._root.glob("*.json"),
                           key=lambda p: p.stat().st_mtime)
```

**Step 2.3 — Run passing + commit.**

### Task 3 — Compose disk store into `CheckpointStore`

**Step 3.1 — Failing test.** `test_checkpoint_persistence.py`:

```python
from pathlib import Path
from serena.refactoring.checkpoints import CheckpointStore, Checkpoint

def test_checkpoint_survives_store_recreation(tmp_path: Path) -> None:
    s1 = CheckpointStore(disk_root=tmp_path)
    ckpt = Checkpoint.from_workspace_edit("ckpt-x", inverse={"changes": {}}, file_versions={})
    s1.put(ckpt)
    del s1
    s2 = CheckpointStore(disk_root=tmp_path)
    got = s2.get("ckpt-x")
    assert got is not None and got.id == "ckpt-x"
```

Run → fails (current `CheckpointStore` is in-memory only).

**Step 3.2 — Edit `checkpoints.py`.** Add optional `disk_root` constructor param; on `put`, mirror to `DiskCheckpointStore`; on `get`, fall back to disk on miss; on init, do NOT eagerly load (lazy fetch only).

```python
from .checkpoint_disk import DiskCheckpointStore
from .checkpoint_schema import PersistedCheckpoint

class CheckpointStore:
    def __init__(self, max_size: int = 50, disk_root: Path | None = None) -> None:
        # Note (per critic S3): `disk_root=None` is preserved as a test override only.
        # Production callers MUST receive a disk_root from settings (Task 4 wires
        # the platformdirs-based default). Leaf 06 ("scalpel_confirm_annotations")
        # depends on disk persistence — bypassing it via None breaks pending-tx
        # survival across process restart.
        self._max_size = max_size
        self._lru: collections.OrderedDict[str, Checkpoint] = collections.OrderedDict()
        self._disk = DiskCheckpointStore(disk_root) if disk_root else None
        self._lock = threading.Lock()

    def put(self, ckpt: Checkpoint) -> None:
        with self._lock:
            self._lru[ckpt.id] = ckpt
            self._lru.move_to_end(ckpt.id)
            if len(self._lru) > self._max_size:
                self._lru.popitem(last=False)
        if self._disk is not None:
            self._disk.put(ckpt.to_persisted())

    def get(self, ckpt_id: str) -> Checkpoint | None:
        with self._lock:
            if ckpt_id in self._lru:
                self._lru.move_to_end(ckpt_id)
                return self._lru[ckpt_id]
        if self._disk is None:
            return None
        persisted = self._disk.get(ckpt_id)
        if persisted is None:
            return None
        return Checkpoint.from_persisted(persisted)
```

Add `to_persisted()` / `from_persisted()` on `Checkpoint`.

**Step 3.3 — Run passing + commit.**

### Task 4 — Wire `disk_root` from settings

**Step 4.1 — Failing test.** Settings test asserts default disk root is `${O2_SCALPEL_CACHE}/checkpoints/` (resolved via `platformdirs`), and the production `CheckpointStore` factory always supplies it (test-only constructor with `None` is the only opt-out).

**Step 4.2 — Implement.** In settings module (`serena/config/`), expose `checkpoint_disk_root: Path` with platformdirs default. The production factory at `serena/refactoring/factory.py` (existing) MUST pass this through; assert this with a unit test that pickles the factory output and checks `_disk is not None`.

**Step 4.3 — Run passing + commit.**

## Self-review checklist

- [ ] LRU(50) recency layer preserved (hot path unchanged).
- [ ] Pydantic schema rejects unknown fields and validates on read.
- [ ] No eager disk load at construction (lazy fetch).
- [ ] Cross-session test demonstrates durability.
- [ ] Eviction policy documented (LRU front, time-based at disk).
- [ ] Production factory always supplies `disk_root`; `None` is test-override only (S3 guard).
- [ ] No emoji; Mermaid only.

*Author: AI Hive(R)*
