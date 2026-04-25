# P5a - pylsp-mypy stale-rate under live_mode:false + dmypy:true

**Outcome:** B - stale_rate < 5% AND p95 1-3s - SHIP with documented warning

**Evidence:**

- Total internal apply-equivalent steps: 12
- pylsp-mypy plugin loaded (mypy-sourced diagnostic observed): True
- Stale steps (oracle != pylsp-mypy): 0
- Stale rate: 0.00%
- Latencies (s, all 12): [2.7196, 1.2387, 1.2231, 1.2577, 1.2282, 1.2349, 1.26, 1.2238, 1.2301, 1.2662, 1.3328, 1.2619]
- p95 latency (s): 2.720
- (oracle_errors, pylsp_errors) pairs: [(1, 1), (1, 1), (1, 1), (1, 1), (1, 1), (2, 2), (1, 1), (2, 2), (1, 1), (1, 1), (1, 1), (1, 1)]
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
