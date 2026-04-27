# P5a mypy Decision Reconciliation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the P5a SHIP-vs-DROP reversal by ratifying SHIP across the three disagreeing artifacts (spike-result, `PROGRESS.md:70`, Python LSP adapter) so a single coherent record survives.
**Architecture:** A single decision-task TDD cycle locks "SHIP" in an executable assertion, then propagates to (a) `PROGRESS.md` (append-only supersede), (b) `pylsp_server.py` initializationOptions, (c) CHANGELOG cold-start caveat. No behaviour change beyond enabling the plugin via existing plumbing at `pylsp_server.py:142–155`. **Architectural distinction:** `pylsp-mypy` is a *plugin inside the pylsp-rope process* (via `initializationOptions`), NOT a `PythonStrategy.SERVER_SET` entry. Stage 1E tests asserting `"pylsp-mypy" not in servers` therefore remain *correct*; only docstrings referencing "verdict C" need updates.
**Tech Stack:** Python 3.13, pytest, `pylsp` 1.x + `pylsp-mypy` 0.7.x, `dmypy` daemon, `pydantic`.
**Source spec:** `docs/gap-analysis/WHAT-REMAINS.md` §1 (lines 46–55).
**Submodule git-flow:** every submodule commit lands on `feature/decision-p5a-mypy` per `PROGRESS.md:72` (pre-commit hook `PROTECTED_BRANCHES="^(main|develop)$"`).
**Author:** AI Hive(R)

---

## File Structure

| Action | Path | Purpose |
|---|---|---|
| Create | `vendor/serena/test/decisions/test_p5a_mypy_decision.py` | TDD lock: pytest assertion that the canonical decision record reads `SHIP`. |
| Create | `vendor/serena/src/solidlsp/decisions/__init__.py` | Package init for decision-record module. |
| Create | `vendor/serena/src/solidlsp/decisions/p5a_mypy.py` | Pydantic model + frozen singleton encoding the SHIP outcome with measurement evidence. |
| Modify | `vendor/serena/src/solidlsp/language_servers/pylsp_server.py` | Flip `pylsp_mypy.enabled` via decision-record; replace P5a-C docstring with P5a-B; preserve "pylsp-rope auto-discovered" rationale comment. |
| Modify | `vendor/serena/src/serena/refactoring/python_strategy.py` | Update verdict-C docstrings to verdict-B (plugin-mode SHIP); SERVER_SET unchanged (pylsp-mypy is a plugin, not a server). |
| Modify | `docs/superpowers/plans/spike-results/PROGRESS.md` | Append 2026-04-26 row that supersedes (not overwrites) the 2026-04-24 §70 row; flip §Spike-outcome-quick-reference row at line 101 to outcome B. |
| Modify | `CHANGELOG.md` | Add `## [Unreleased]` section (none exists — verified `grep "## \["` returns only `## [0.1.0]`) with pylsp-mypy SHIP note. |

---

## Recommendation

**SHIP** pylsp-mypy in the MVP active server set with `live_mode: false` + `dmypy: true`, per `P5a.md` §Decision (outcome B threshold = `stale_rate < 5%` AND `p95` within 1–3s). Rationale (per `P5a.md:5–14` and `WHAT-REMAINS.md` §1):

- `stale_rate` 8.33% → **0.00%** (0/12 stale steps; oracle and pylsp-mypy converge).
- `p95` 8.011s → **2.668s** (within the 1–3s outcome-B window; cold-start outlier did not reproduce).
- Both falsifier axes (`stale_rate ≥ 5%` AND `p95 ≥ 3s`) now fail simultaneously per `P5a.md:30`.

Path of least code change: ratify the new measurements, enable the already-present `pylsp_mypy` toggle, add the documented warning, update the ledger.

---

## Tasks

### Task 1: Encode the SHIP decision as a frozen pydantic record

**Files:** `vendor/serena/src/solidlsp/decisions/__init__.py`, `vendor/serena/src/solidlsp/decisions/p5a_mypy.py`, `vendor/serena/test/decisions/test_p5a_mypy_decision.py`

- [ ] **Step 1: Write failing test** — Create `vendor/serena/test/decisions/test_p5a_mypy_decision.py`:
  ```python
  """Lock test for P5a pylsp-mypy decision (asserts SHIP + re-run measurements)."""
  from __future__ import annotations

  from solidlsp.decisions.p5a_mypy import P5A_MYPY_DECISION


  def test_p5a_mypy_decision_is_ship() -> None:
      assert P5A_MYPY_DECISION.outcome == "SHIP"
      assert P5A_MYPY_DECISION.stale_rate == 0.0
      assert P5A_MYPY_DECISION.p95_latency_seconds == 2.668
      assert P5A_MYPY_DECISION.axes_that_failed_falsifier_check == (
          "stale_rate",
          "p95_latency",
      )


  def test_p5a_mypy_decision_pylsp_config_enables_plugin() -> None:
      cfg = P5A_MYPY_DECISION.pylsp_initialization_options
      assert cfg["pylsp"]["plugins"]["pylsp_mypy"]["enabled"] is True
      assert cfg["pylsp"]["plugins"]["pylsp_mypy"]["live_mode"] is False
      assert cfg["pylsp"]["plugins"]["pylsp_mypy"]["dmypy"] is True
  ```

- [ ] **Step 2: Run test, verify fail** — From `vendor/serena/`:
  ```bash
  uv run pytest test/decisions/test_p5a_mypy_decision.py -x -p no:randomly
  ```
  Expected: `ModuleNotFoundError: No module named 'solidlsp.decisions'` (collection-time failure).

- [ ] **Step 3: Implement** — Create `vendor/serena/src/solidlsp/decisions/__init__.py` with:
  ```python
  """Frozen decision records for spike outcomes that gate adapter behaviour."""
  ```
  Then create `vendor/serena/src/solidlsp/decisions/p5a_mypy.py`:
  ```python
  """Canonical record of the P5a pylsp-mypy SHIP decision.

  Source: P5a.md:5-14. Reconciles WHAT-REMAINS.md §1 reversal:
  stale_rate 8.33% -> 0.00%, p95 8.011s -> 2.668s.
  ``axes_that_failed_falsifier_check`` = axes where the falsifier threshold
  (>=5% stale, >=3s p95) was NOT crossed on re-run, i.e., axes that
  "passed" by failing to falsify, satisfying outcome B per P5a.md:30.
  """
  from __future__ import annotations

  from typing import Any, Literal

  from pydantic import BaseModel, ConfigDict


  class P5aMypyDecision(BaseModel):
      """Frozen pydantic record encoding the ratified pylsp-mypy outcome."""

      model_config = ConfigDict(frozen=True)

      outcome: Literal["SHIP", "DROP"]
      stale_rate: float
      p95_latency_seconds: float
      axes_that_failed_falsifier_check: tuple[str, ...]
      pylsp_initialization_options: dict[str, Any]


  P5A_MYPY_DECISION = P5aMypyDecision(
      outcome="SHIP",
      stale_rate=0.0,
      p95_latency_seconds=2.668,
      axes_that_failed_falsifier_check=("stale_rate", "p95_latency"),
      pylsp_initialization_options={
          "pylsp": {
              "plugins": {
                  "pylsp_mypy": {
                      "enabled": True,
                      "live_mode": False,
                      "dmypy": True,
                  },
              },
          },
      },
  )
  ```

- [ ] **Step 4: Run test, verify pass** — From `vendor/serena/`:
  ```bash
  uv run pytest test/decisions/test_p5a_mypy_decision.py -x -p no:randomly
  ```
  Expected: `2 passed`.

- [ ] **Step 5: Branch + commit (submodule, feature branch — protected `main`/`develop`)** — From repo root:
  ```bash
  git -C vendor/serena checkout -B feature/decision-p5a-mypy
  git -C vendor/serena add src/solidlsp/decisions/__init__.py src/solidlsp/decisions/p5a_mypy.py test/decisions/test_p5a_mypy_decision.py
  git -C vendor/serena commit -m "feat(decisions): lock P5a pylsp-mypy SHIP outcome (stale 0.00%, p95 2.668s)"
  ```
  Expected: commit succeeds. (Direct `commit` to `main`/`develop` would be rejected by `.git/modules/vendor/serena/hooks/pre-commit` per `PROGRESS.md:72`.)

### Task 2: Wire the SHIP decision into `PylspServer` initialization

**Files:** `vendor/serena/src/solidlsp/language_servers/pylsp_server.py`, `vendor/serena/test/decisions/test_p5a_mypy_decision.py`

- [ ] **Step 1: Write failing test** — Append to `vendor/serena/test/decisions/test_p5a_mypy_decision.py`:
  ```python
  def test_pylsp_server_initialize_params_enable_mypy(tmp_path) -> None:
      """PylspServer must consume P5A_MYPY_DECISION.pylsp_initialization_options."""
      from solidlsp.language_servers.pylsp_server import PylspServer

      params = PylspServer._get_initialize_params(str(tmp_path))
      plugins = params["initializationOptions"]["pylsp"]["plugins"]
      assert plugins["pylsp_mypy"]["enabled"] is True
      assert plugins["pylsp_mypy"]["live_mode"] is False
      assert plugins["pylsp_mypy"]["dmypy"] is True
  ```

- [ ] **Step 2: Run test, verify fail** — From `vendor/serena/`:
  ```bash
  uv run pytest test/decisions/test_p5a_mypy_decision.py::test_pylsp_server_initialize_params_enable_mypy -x -p no:randomly
  ```
  Expected: `AssertionError: assert False is True` (current value is `enabled: False` per `pylsp_server.py:152`).

- [ ] **Step 3: Implement** — In `vendor/serena/src/solidlsp/language_servers/pylsp_server.py`:
  - Replace the docstring line `pylsp-mypy is DELIBERATELY NOT enabled here — Phase 0 P5a verdict C.` (currently at line 15) with: `pylsp-mypy is enabled with live_mode=false + dmypy=true per P5a re-run outcome B (stale 0.00%, p95 2.668s); see solidlsp.decisions.p5a_mypy.`
  - Add at the top of the file (after the existing imports at lines 18–32):
    ```python
    from solidlsp.decisions.p5a_mypy import P5A_MYPY_DECISION
    ```
  - Replace the `"initializationOptions"` block (lines 142–155) with the following — preserving the rationale comment per S5:
    ```python
    # pylsp-rope is auto-discovered; only declare plugin toggles that
    # override defaults. Owned by `solidlsp.decisions.p5a_mypy` so any
    # future re-flip is gated by `test/decisions/test_p5a_mypy_decision.py`.
    "initializationOptions": P5A_MYPY_DECISION.pylsp_initialization_options,
    ```

- [ ] **Step 4: Run test, verify pass** — From `vendor/serena/`:
  ```bash
  uv run pytest test/decisions/test_p5a_mypy_decision.py -x -p no:randomly
  ```
  Expected: `3 passed`. Then run the full pylsp adapter suite to verify no regression:
  ```bash
  uv run pytest test/spikes/test_stage_1e_t3_pylsp_server_spawn.py test/spikes/test_stage_1e_t4_pylsp_apply_edit_drain.py -x -p no:randomly
  ```
  Expected: all selected tests pass.

- [ ] **Step 5: Commit (same submodule feature branch)** — From repo root:
  ```bash
  git -C vendor/serena checkout feature/decision-p5a-mypy
  git -C vendor/serena add src/solidlsp/language_servers/pylsp_server.py test/decisions/test_p5a_mypy_decision.py
  git -C vendor/serena commit -m "feat(pylsp): enable pylsp-mypy via P5A_MYPY_DECISION"
  ```

### Task 3: Append a superseding 2026-04-26 row to PROGRESS.md decision log

**Files:** `docs/superpowers/plans/spike-results/PROGRESS.md`, `vendor/serena/src/serena/refactoring/python_strategy.py`

- [ ] **Step 1: Write failing test** — Create `tests/governance/test_progress_p5a_decision_synced.py`:
  ```python
  """Cross-artifact lock: PROGRESS.md §70 must reflect SHIP."""
  from __future__ import annotations
  from pathlib import Path

  PROGRESS = Path("docs/superpowers/plans/spike-results/PROGRESS.md").read_text("utf-8")


  def test_progress_md_marks_2026_04_24_row_superseded() -> None:
      # Append-only ledger: original row must remain, prefixed as superseded.
      assert "**Superseded by 2026-04-26 row below**" in PROGRESS
      assert "pylsp-mypy is dropped from the MVP active Python LSP set" in PROGRESS


  def test_progress_md_records_ship_outcome_with_rerun_measurements() -> None:
      assert "pylsp-mypy is shipped in the MVP active Python LSP set" in PROGRESS
      assert "stale_rate 0.00%" in PROGRESS
      assert "p95 2.668s" in PROGRESS


  def test_progress_md_quick_reference_row_reads_ship() -> None:
      assert "| P5a | B (ship pylsp-mypy with documented warning)" in PROGRESS
  ```

- [ ] **Step 2: Run test, verify fail** — From repo root:
  ```bash
  pytest tests/governance/test_progress_p5a_decision_synced.py -x -p no:randomly
  ```
  Expected: `test_progress_md_marks_2026_04_24_row_superseded` fails (no superseded marker yet); the SHIP-row test fails (current `PROGRESS.md:101` reads `| P5a | C (drop pylsp-mypy) |`).

- [ ] **Step 3: Implement** — In `docs/superpowers/plans/spike-results/PROGRESS.md`:
  - **Append-only:** in the existing §70 row (single physical line in `PROGRESS.md` at line 70), insert the literal string `**Superseded by 2026-04-26 row below** ` (note trailing space) immediately after the first `| ` of the second column, so the row begins `| 2026-04-24 | **Superseded by 2026-04-26 row below** **pylsp-mypy is dropped...`. All other content in the row is preserved verbatim. (Per PROGRESS.md convention §60+: rows are append-only; never delete prior decisions.)
  - **Insert a new 2026-04-26 row immediately below** the now-superseded 2026-04-24 row:
    ```
    | 2026-04-26 | **pylsp-mypy is shipped in the MVP active Python LSP set with documented cold-start warning.** Re-run of the P5a fixture under unchanged Q1 configuration (`live_mode: false` + `dmypy: true` + scalpel-injected per-step `didSave`) reversed both falsifier axes: stale_rate 8.33% -> stale_rate 0.00% (0/12 stale steps); p95 8.011s -> p95 2.668s (within the 1-3s outcome-B window). The cold-daemon outlier from the original run did not reproduce. **Decision:** ratify outcome B per `P5a.md:30`; enable `pylsp_mypy` in `PylspServer` initializationOptions (`enabled: true, live_mode: false, dmypy: true`); add CHANGELOG note that first didSave after long idle may exceed 1s. The +135 LoC `python_strategy.py`/`multi_server.py` synthetic-didSave plumbing originally budgeted by Q1 §7 remains unbuilt — pylsp's debounce + dmypy warm-path is sufficient under the re-run measurements. | P5a re-run evidence: stale_rate 0.00% < 5%; p95 2.668s within 1-3s; both falsifier axes failed simultaneously per `P5a.md:5-14`. | MVP scope (ship pylsp-mypy); `pylsp_server.py` initializationOptions block; `solidlsp.decisions.p5a_mypy` (canonical record); CHANGELOG note. |
    ```
  - Replace the §Spike-outcome-quick-reference row at line 101 reading `| P5a | C (drop pylsp-mypy) | -135 LoC vs. budgeted ...` with:
    ```
    | P5a | B (ship pylsp-mypy with documented warning) | 0 LoC `python_strategy.py`/`multi_server.py` synthetic-didSave plumbing (budgeted ~135 LoC under Q1 §7 — not needed under re-run measurements); +1 boolean toggle in `pylsp_server.py` initializationOptions plus `solidlsp.decisions.p5a_mypy` record (~30 LoC). +11 LoC `_pylsp_client.py` `diagnostics_by_uri` capture (re-usable for P3/P4/P6); +184 LoC P5a test bypasses wrapper via raw stdio JSON-RPC (no `notify_did_change_configuration` facade in SolidLanguageServer). Stale_rate **0.00%** (0/12 on re-run); **p95 = 2.668s** (within 1-3s outcome-B window). |
    ```
  - **Update misleading docstrings in `vendor/serena/src/serena/refactoring/python_strategy.py`** (Stage 2A/2B test wiring touch point — addresses spec-coverage row 7): replace lines 12–14 reading `- NO pylsp-mypy in SERVER_SET (Phase 0 P5a verdict C). / - NO synthetic per-step didSave (Q1 cascade — pylsp-mypy mitigation became redundant once mypy was dropped).` with `- pylsp-mypy ships as a *plugin inside pylsp-rope*, NOT a separate SERVER_SET entry (Phase 0 P5a re-run verdict B); SERVER_SET stays {pylsp-rope, basedpyright, ruff}. / - NO synthetic per-step didSave: the dmypy daemon's warm-path plus pylsp's didSave debounce satisfy the latency budget on re-run (Q1 mitigation redundant under outcome B).` Stage 1E tests `test_build_servers_returns_three_entries_no_mypy` and `test_strategy_does_not_inject_synthetic_did_save` continue to pass unchanged because pylsp-mypy is a plugin, not a server.

- [ ] **Step 4: Run test, verify pass** — From repo root:
  ```bash
  pytest tests/governance/test_progress_p5a_decision_synced.py -x -p no:randomly
  ```
  Then re-run Stage 1E test wiring to confirm the docstring change does not regress assertions:
  ```bash
  cd vendor/serena && uv run pytest test/spikes/test_stage_1e_t1_language_strategy_protocol.py test/spikes/test_stage_1e_t7_python_strategy_multi_server.py -x -p no:randomly
  ```
  Expected: governance file `3 passed`; Stage 1E selected tests all pass (no behaviour change — only docstring).

- [ ] **Step 5: Two commits (parent + submodule, separate)** — From repo root:
  ```bash
  git -C vendor/serena checkout feature/decision-p5a-mypy
  git -C vendor/serena add src/serena/refactoring/python_strategy.py
  git -C vendor/serena commit -m "docs(python_strategy): update verdict-C docstrings to verdict-B (plugin-mode SHIP)"
  git add docs/superpowers/plans/spike-results/PROGRESS.md tests/governance/test_progress_p5a_decision_synced.py
  git commit -m "docs(progress): supersede §70 with 2026-04-26 SHIP row (stale 0.00%, p95 2.668s)"
  ```

### Task 4: Add CHANGELOG warning for the cold-daemon caveat

**Files:** `CHANGELOG.md`, `tests/governance/test_changelog_p5a_warning.py`

- [ ] **Step 1: Write failing test** — Create `tests/governance/test_changelog_p5a_warning.py`:
  ```python
  """CHANGELOG must document the P5a cold-daemon caveat per outcome B."""
  from __future__ import annotations

  from pathlib import Path

  CHANGELOG = Path("CHANGELOG.md").read_text(encoding="utf-8")


  def test_changelog_has_unreleased_section() -> None:
      assert "## [Unreleased]" in CHANGELOG


  def test_changelog_documents_pylsp_mypy_cold_start_caveat() -> None:
      assert "pylsp-mypy" in CHANGELOG
      assert "live_mode: false" in CHANGELOG
      assert "dmypy: true" in CHANGELOG
      assert "first didSave after long idle" in CHANGELOG
  ```

- [ ] **Step 2: Run test, verify fail** — From repo root:
  ```bash
  pytest tests/governance/test_changelog_p5a_warning.py -x -p no:randomly
  ```
  Expected: `assert '## [Unreleased]' in CHANGELOG` fails (`grep "## \["` confirms only `## [0.1.0]` exists today).

- [ ] **Step 3: Implement** — Insert a new `## [Unreleased]` section between the existing line 4 (`The format follows...`) and line 6 (`## [0.1.0] — 2026-04-24`) of `CHANGELOG.md`. The literal block to insert:
  ```
  ## [Unreleased]

  ### Type-error coverage

  - **pylsp-mypy enabled** with `live_mode: false` + `dmypy: true` per P5a outcome B (stale_rate 0.00%, p95 2.668s on re-run). Expect occasional latency >1s on first didSave after long idle while the dmypy daemon warms; subsequent didSaves complete in ~1.25s. Reconciles `docs/superpowers/plans/spike-results/PROGRESS.md` decision-log §70.
  ```

- [ ] **Step 4: Run test, verify pass** — From repo root:
  ```bash
  pytest tests/governance/test_changelog_p5a_warning.py -x -p no:randomly
  ```
  Expected: `2 passed`.

- [ ] **Step 5: Commit (parent only)** — From repo root:
  ```bash
  git add CHANGELOG.md tests/governance/test_changelog_p5a_warning.py
  git commit -m "docs(changelog): document pylsp-mypy SHIP + cold-daemon caveat per P5a re-run"
  ```

### Task 5: Bump submodule pointer + final cross-artifact lock test

**Files:** repo root (parent submodule pointer), `tests/governance/test_p5a_artifacts_agree.py`

- [ ] **Step 1: Write failing test** — Create `tests/governance/test_p5a_artifacts_agree.py`:
  ```python
  """Single integration assertion: all three P5a artifacts agree on SHIP."""
  from __future__ import annotations

  import sys
  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]
  sys.path.insert(0, str(REPO_ROOT / "vendor" / "serena" / "src"))

  from solidlsp.decisions.p5a_mypy import P5A_MYPY_DECISION  # noqa: E402

  PROGRESS = (REPO_ROOT / "docs/superpowers/plans/spike-results/PROGRESS.md").read_text(
      encoding="utf-8"
  )
  PYLSP_SERVER = (
      REPO_ROOT / "vendor/serena/src/solidlsp/language_servers/pylsp_server.py"
  ).read_text(encoding="utf-8")


  def test_decision_record_says_ship() -> None:
      assert P5A_MYPY_DECISION.outcome == "SHIP"


  def test_progress_log_says_ship() -> None:
      assert "pylsp-mypy is shipped in the MVP active Python LSP set" in PROGRESS


  def test_pylsp_server_consumes_decision_record() -> None:
      assert "P5A_MYPY_DECISION.pylsp_initialization_options" in PYLSP_SERVER
      assert '"pylsp_mypy": {"enabled": False}' not in PYLSP_SERVER
  ```

- [ ] **Step 2: Run test, verify pass under working-tree state** — From repo root:
  ```bash
  pytest tests/governance/test_p5a_artifacts_agree.py -x -p no:randomly
  ```
  Expected: `3 passed.` — all three reads resolve against the working tree (`vendor/serena/src/...` files reflect Tasks 1–2 commits on `feature/decision-p5a-mypy`); the parent's pinned submodule SHA is irrelevant until step 3 commits the bump.

- [ ] **Step 3: Implement — submodule fast-forward + parent bump** — Per the canonical pattern in `PROGRESS.md:53,72`. The merge MUST hard-fail if not fast-forwardable (no silent fallback — that exact failure mode is what `WHAT-REMAINS.md:135` is trying to prevent):
  ```bash
  git -C vendor/serena checkout main
  git -C vendor/serena merge --ff-only feature/decision-p5a-mypy
  git add vendor/serena
  ```
  Expected: `git merge` succeeds (Task 1, 2, 3, 4 commits all sit on `feature/decision-p5a-mypy` ahead of `main`); `git status` now shows `vendor/serena` staged with a new submodule SHA.

- [ ] **Step 4: Run test, verify pass** — From repo root:
  ```bash
  pytest tests/governance/test_p5a_artifacts_agree.py tests/governance/test_progress_p5a_decision_synced.py tests/governance/test_changelog_p5a_warning.py -x -p no:randomly
  ```
  Expected: `8 passed` total across the three governance files (3 + 3 + 2).

- [ ] **Step 5: Commit (parent — submodule pointer + integration lock)** — From repo root:
  ```bash
  git add tests/governance/test_p5a_artifacts_agree.py vendor/serena
  git commit -m "feat(governance): lock P5a SHIP across decision record, PROGRESS.md, pylsp_server, CHANGELOG"
  ```
  Tagging is owned by the synthesizer/release flow (project CLAUDE.md "Tag a release after each significant feature" applies at integration time, not in-stream); this plan deliberately stops at the commit.

---

## Self-Review

- [ ] **Spec coverage** (`WHAT-REMAINS.md` §1, lines 46–55): rationale-tied-to-measurements (§Recommendation + Task 1 lock); PROGRESS.md update (Task 3 Step 3, append-only); minimal Python-strategy code change (Task 2 — single decision-record consumption); Stage 2A/2B test wiring assumption (Task 3 Step 3 docstring update in `python_strategy.py:12–14` — Stage 1E tests `test_build_servers_returns_three_entries_no_mypy` and `test_strategy_does_not_inject_synthetic_did_save` remain valid because pylsp-mypy is a plugin, not a SERVER_SET entry; Task 3 Step 4 re-runs them to verify).
- [ ] **Submodule git-flow:** every submodule commit (Tasks 1, 2, 3) lands on `feature/decision-p5a-mypy` first per `PROGRESS.md:72`; ff-merge to `main` happens only at Task 5 Step 3 with hard-fail (no `2>/dev/null || true`).
- [ ] **TDD cycle:** Task 1 frames the recommendation as `P5A_MYPY_DECISION.outcome == "SHIP"`, test-first.
- [ ] **No placeholders:** no "TBD" / "appropriate" / "similar to" / "handle edge cases" wording.
- [ ] **Type consistency:** pydantic-frozen model + `Literal["SHIP", "DROP"]`; `Any` only inside `pylsp_initialization_options` whose schema is owned by pylsp upstream.
- [ ] **Naming:** `axes_that_failed_falsifier_check` (per S1) replaces ambiguous `falsifier_axes_failed`; semantics documented in the module docstring.
- [ ] **Sizing:** small (5 tasks; ≤30 LoC production; ~95 LoC governance tests). No time estimates.
- [ ] **Author:** AI Hive(R); no "Claude" string; no emoji; no ASCII art (Mermaid-only convention; no diagram needed at this scope — linear 5-task pipeline).
- [ ] **Evidence:** referenced by `file:line`; keys: `P5a.md:5–14,30`, `pylsp_server.py:142–155`, `PROGRESS.md:53,72,101`, `python_strategy.py:12–14`, `WHAT-REMAINS.md:46–55,135`.

*Author: AI Hive(R)*
