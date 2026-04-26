# Stage 2B — E2E Harness + 9 MVP Scenarios + Q3/Q4 Fixtures — PROGRESS

| Task | Branch SHA (submodule) | Outcome | Follow-ups |
|---|---|---|---|
| T0 | f9c71345 (entry) | OPEN | bootstrap |
| T1 | | | |
| T2 | | | |
| T3 | | | |
| T4 | | | |
| T5 | | | |
| T6 | | | |
| T7 | | | |
| T8 | | | |
| T9 | | | |
| T11 | | | |
| T12 | | | |
| T13 | | | |
| T14 | | | |

## Entry baseline

- Submodule branch: `feature/stage-2b-e2e-harness-scenarios` from `origin/main` @ `f9c71345`
- Parent branch: `feature/stage-2b-e2e-harness-scenarios` from `origin/develop` @ `1a52b82e`
- Stage 2A exit tag: `stage-2a-ergonomic-facades-complete`
- Test baseline: `pytest test/spikes/ test/integration/ -q --co` collects 593 tests.

## E2E run command

```bash
cd vendor/serena
O2_SCALPEL_RUN_E2E=1 PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/e2e/ -v -m e2e
```

Wall-clock budget: aggregate <= 12 min (scope-report S16.4 cap).

## LSP binary discovery

- `rust-analyzer`: /Users/alexanderfedin/.cargo/bin/rust-analyzer (system PATH)
- `cargo`: /Users/alexanderfedin/.cargo/bin/cargo (system PATH)
- `ruff`: /Library/Frameworks/Python.framework/Versions/3.12/bin/ruff (system PATH)
- `pylsp`, `basedpyright-langserver`, `basedpyright`, `ruff` (newer): venv-only

The conftest discovers binaries via `shutil.which`; for venv binaries, the
`PATH="$(pwd)/.venv/bin:$PATH"` prefix exposes them.
