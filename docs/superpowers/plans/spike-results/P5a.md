# P5a - pylsp-mypy stale-rate under live_mode:false + dmypy:true

**Outcome:** B (SHIP with documented cold-daemon warning) - re-run on 2026-04-26 reversed both falsifier axes (stale_rate 0.00%, p95 2.668s); see `solidlsp.decisions.p5a_mypy`. Original 2026-04-24 run recorded INDETERMINATE / "verdict C" (kept below as historical evidence).

**Evidence:**

- Total internal apply-equivalent steps: 12
- pylsp-mypy plugin loaded (mypy-sourced diagnostic observed): False
- Stale steps (oracle != pylsp-mypy): 12
- Stale rate: 100.00%
- Latencies (s, all 12): [8.0238, 8.0108, 8.0126, 8.0001, 8.0385, 8.0201, 8.039, 8.0279, 8.0146, 8.0176, 8.0519, 8.0286]
- p95 latency (s): 8.052
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
