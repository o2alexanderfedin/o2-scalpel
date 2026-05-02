# P5a - pylsp-mypy stale-rate under live_mode:false + dmypy:true

**Outcome:** INDETERMINATE - pylsp-mypy never published mypy-sourced diagnostics; plugin-load failure

**Evidence:**

- Total internal apply-equivalent steps: 12
- pylsp-mypy plugin loaded (mypy-sourced diagnostic observed): False
- Stale steps (oracle != pylsp-mypy): 12
- Stale rate: 100.00%
- Latencies (s, all 12): [8.0184, 8.0274, 8.0498, 8.0098, 8.0127, 8.0412, 8.043, 8.0067, 8.045, 8.0352, 8.0028, 8.0188]
- p95 latency (s): 8.050
- (oracle_errors, pylsp_errors) pairs: [(2, 0), (2, 0), (2, 0), (2, 0), (2, 0), (3, 0), (2, 0), (3, 0), (2, 0), (2, 0), (2, 0), (2, 0)]
- dmypy oracle failures: []

**Configuration (per Q1 resolution):**

- pylsp-mypy: `live_mode: false`, `dmypy: true` (sent via both `initializationOptions` and `workspace/didChangeConfiguration`).
- Each step writes the mutated file to disk, sends `didChange` (full sync), then `didSave({includeText: true})`.
- Oracle: `dmypy run -- <file>` invoked from `seed_python_root` after each step (warm daemon after step 1).

**Wrapper-gap findings:**

- `_pylsp_client.PylspClient` extended with `diagnostics_by_uri` capture for this spike (last-write-wins per URI). Mirrors the `_ruff_client.RuffClient.diagnostics` capture pattern.
- `workspace/didChangeConfiguration` plumbing must be re-implemented in Stage 1E `PylspServer` adapter; SolidLanguageServer has no facade for `notify_did_change_configuration`.

**Decision:**

- A -> ship pylsp-mypy with `live_mode: false` + `dmypy: true` in MVP active server set.
- B -> ship with `CHANGELOG.md` note 'expect occasional latency >1s on first didSave after long idle'.
- C -> drop pylsp-mypy from MVP active set; update `python_strategy.py` and `multi_server.py` accordingly. basedpyright remains authoritative for `severity_breakdown` per MVP §11.1.
- INDETERMINATE -> file pylsp-mypy plugin-load failure as Phase 0 finding; Stage 1E must investigate before activating.
