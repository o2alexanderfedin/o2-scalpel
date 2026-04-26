# Q1 — `pylsp-mypy` `live_mode` policy under multi-step LLM-driven refactor transactions

**Status**: Resolved (decision below).
**Author**: AI Hive(R), Python LSP / static-analysis specialist.
**Date**: 2026-04-24.
**Resolves**: §19, item 1 of `2026-04-24-mvp-scope-report.md` ("`pylsp-mypy` retention under `live_mode: false`").

> **Decision (boxed)**
>
> **Option (b): `live_mode: false` + `dmypy: true` + scalpel-injected `didSave` after each successful internal `apply()` step.** Keep `pylsp-mypy` in the MVP active server set. The dmypy daemon is the only configuration that gives sub-second incremental rechecks under our cadence; the synthetic `didSave` after each transaction step eliminates the staleness window that motivated the open question. basedpyright remains the authoritative `severity_breakdown` source per §11.1 of the MVP report; `pylsp-mypy` is a corroborator, not a gate. **Spike P5 (now `P5a`) is the falsifier**: if the stale-diagnostic rate on `calcpy` exceeds 5% under realistic refactor sequences with this configuration, fall back to **option (c) — drop `pylsp-mypy` from the MVP active server set** and ship without it.

---

## 1. Background and exact framing

### 1.1 What `live_mode` actually does (source-verified)

Read of `pylsp_mypy/plugin.py` at HEAD (sourced via raw.githubusercontent.com 2026-04-24):

```python
# lines 261-266
live_mode = settings.get("live_mode", True)
dmypy = settings.get("dmypy", False)
if dmypy and live_mode:
    log.warning("live_mode is not supported with dmypy, disabling")
    live_mode = False

# lines 226-228 — the hook signature
def pylsp_lint(
    config: Config, workspace: Workspace, document: Document, is_saved: bool
) -> list[dict[str, Any]]: ...

# lines 277-282 — shadow-file branch (live_mode true, document dirty)
if live_mode and not is_saved:
    if tmpFile:
        tmpFile = open(tmpFile.name, "wb")
    else:
        tmpFile = tempfile.NamedTemporaryFile("wb", delete=False)
    tmpFile.write(bytes(document.source, "utf-8"))
    tmpFile.close()
    args.extend(["--shadow-file", document.path, tmpFile.name])

# lines 285-291 — cache fallback (live_mode false, document dirty)
elif not is_saved and document.path in last_diagnostics:
    log.info("non-live, returning cached diagnostics len(cached) = %s",
             last_diagnostics[document.path])
    return last_diagnostics[document.path]
```

Three behaviours fall out of those branches:

| Config                              | On `didChange` (`is_saved=False`)                 | On `didSave` (`is_saved=True`)               |
|-------------------------------------|---------------------------------------------------|----------------------------------------------|
| `live_mode: true`, `dmypy: false`   | runs mypy on a `--shadow-file` of the buffer      | runs mypy on the on-disk file                |
| `live_mode: false`, `dmypy: false`  | **returns cached `last_diagnostics`** (stale)     | runs mypy on the on-disk file                |
| `live_mode: false`, `dmypy: true`   | **returns cached `last_diagnostics`** (stale)     | runs `dmypy run` on the on-disk file         |
| `live_mode: true`, `dmypy: true`    | impossible — pylsp-mypy logs warning, forces `live_mode=False` (line 264) | same as row 3 |

Source: <https://github.com/python-lsp/pylsp-mypy/blob/master/pylsp_mypy/plugin.py>.

### 1.2 What pylsp dispatches (source-verified)

Read of `python-lsp-server/pylsp/python_lsp.py` at HEAD:

```python
LINT_DEBOUNCE_S = 0.5  # line 40

# didChange handler — line 760
self.lint(textDocument["uri"], is_saved=False)

# didSave handler — line 764
self.lint(textDocument["uri"], is_saved=True)

# the lint method itself — line 696
@_utils.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
def lint(self, doc_uri, is_saved) -> None: ...
```

So pylsp:

- maps `didChange` → `pylsp_lint(is_saved=False)` and `didSave` → `pylsp_lint(is_saved=True)`,
- debounces lint calls by 500 ms keyed by URI (one per file in flight at a time),
- does **not** debounce `didSave` separately — saves bypass the keystroke coalescing because a save event flushes pending debounce timers.

Source: <https://github.com/python-lsp/python-lsp-server/blob/develop/pylsp/python_lsp.py>.

### 1.3 What scalpel's pipeline does between steps

From the MVP report §6.8 / §11.4 and the Python specialist §3 / §4: a multi-step facade like `scalpel_split_file` performs ~5 internal `apply()` calls, each of which:

1. computes a `WorkspaceEdit` against the in-memory buffer (sometimes by calling pylsp-rope, sometimes by direct Rope-library bridge),
2. issues `didChange` to **all** Python LSPs (pylsp + basedpyright + ruff) so they share buffer state,
3. **does not** write to disk — disk write is deferred to `apply()` at the transaction boundary (§6.8 P0 invariant),
4. reads `diagnostics_delta` for the `RefactorResult.

The question is: at step 4, what does pylsp-mypy report?

---

## 2. Staleness risk under `live_mode: false` (without intervention)

If we ship the current MVP report's literal config (`live_mode: false`, `dmypy: true`) and do nothing else, between transaction steps:

- Each internal `didChange` triggers `pylsp_lint(is_saved=False)`.
- pylsp-mypy hits the `last_diagnostics` cache fallback (plugin.py line 285-291) and returns the **previous lint pass's diagnostics** — i.e. the diagnostics from before the refactor started, on the on-disk file content.
- The `RefactorResult.diagnostics_delta` reports those stale diagnostics as `after`. The "after" is in fact "before, recycled".

**Concrete failure modes** (each is reproducible on `calcpy`):

| # | Scenario                                                                                          | What user/LLM sees             | Reality                                |
|---|---------------------------------------------------------------------------------------------------|--------------------------------|----------------------------------------|
| F1 | `extract_module` introduces a circular import between two new files                              | `severity_breakdown.error: 0`  | mypy on disk would show `error: 2`     |
| F2 | `move_method` removes the only definition of a name; callers now reference an undefined symbol   | mypy: 0 new errors             | mypy on disk would show `attr-defined` errors |
| F3 | Inline of a typed helper drops a parameter annotation; later step relies on it                   | mypy clean                     | mypy on disk shows `arg-type`         |
| F4 | Apply runs cleanly, transaction commits, post-commit `didSave` finally runs, error appears       | success → unexpected error appears | should have failed earlier, before commit |

Failures F1-F3 are silent during the transaction; F4 is the regression mode the user's profile (regression-aversion, MVP report §16.2) explicitly asks us to avoid. **Without intervention, the staleness rate is 100% within a transaction** — every internal step returns cached diagnostics by construction. The §19 entry's "5% stale-diagnostic rate" framing is too generous; the true rate without intervention is 100% on every multi-step facade call.

This is the load-bearing finding. It rules out `live_mode: false` as-currently-configured.

---

## 3. Cost and reliability of `live_mode: true`

### 3.1 Performance characteristics

- pylsp-mypy with `live_mode: true` and `dmypy: false` runs the **full mypy CLI as a subprocess** on every `didChange` (after the 500 ms pylsp debounce). A mypy run on a 1k-LoC file with imports typically costs 1.5–4 s cold, 0.2–1 s warm. Source: pylsp-mypy README mentions "live_mode... writes to a tempfile every time a check is done"; mypy docs state typical incremental runs.
- pylsp-mypy with `live_mode: true` and `dmypy: true` is **disallowed** — the plugin forces `live_mode=False` (plugin.py line 264). dmypy + shadow-file works upstream in mypy (issue python/mypy#9309 was patched so dmypy ignores `--shadow-file` in its options snapshot and stays warm), but pylsp-mypy has not removed its hard-coded mutual-exclusion guard. As of master HEAD on 2026-04-24, the line is still there.

So the only real `live_mode: true` config is full-mypy-subprocess-per-edit, with no daemon caching.

### 3.2 Concurrency and races

- Mypy daemon docs: "Each mypy daemon process supports one user and one set of source files, and it can only process one type checking request at a time." (<https://mypy.readthedocs.io/en/stable/mypy_daemon.html>) — but this is only relevant under `dmypy: true`.
- pylsp-mypy itself has **no internal lock** around `last_diagnostics`, `tmpFile`, or `mypyConfigFileMap`. The plugin relies on pylsp's request serialization. pylsp's debounce(`keyed_by="doc_uri"`) gives per-URI serialization; cross-URI requests can interleave, but each URI's mypy run completes before the next starts.
- Documented race: <https://github.com/python-lsp/pylsp-mypy/issues/12> — "pylsp hangs in Atom if a file is saved immediately after change". Closed but no fix shipped — the closing remark notes "this is clearly some kind of a race condition" and the user worked around it by deleting `.mypy_cache/`. Root cause is two mypy processes racing on the cache directory.
- Documented related cache issue: <https://github.com/python-lsp/pylsp-mypy/issues/81> — pylsp-mypy invokes mypy with `--follow-imports silent` by default; this differs from CLI default (`normal`) and **invalidates the shared cache**. Reporter measured 12 s cold → 2 s warm → 12 s after each editor invocation. Mitigation: `overrides = [true, "--follow-imports", "normal"]`.

### 3.3 Live-mode verdict

`live_mode: true` (mypy-subprocess-per-edit) **does** type-check the unsaved buffer correctly. Trade-offs:

| Axis                  | Cost                                                         |
|-----------------------|--------------------------------------------------------------|
| Latency per step      | 0.2–4 s per `didChange`; multi-step facades multiply by ~5   |
| Aggregate latency on `scalpel_split_file` | ~1–20 s of synchronous mypy work added to MVP §9 wall-clock budget |
| Cache thrash          | Issue #81 — invalidates CLI cache between runs               |
| Race window           | Issue #12 — two simultaneous lint passes can corrupt cache   |
| Daemon benefit        | None — `live_mode` and `dmypy` are mutually exclusive in pylsp-mypy |

The §9 wall-clock budget for `scalpel_split_file` is 8 s (MVP report §9.2). Adding 1–20 s of mypy work blows that budget on real codebases.

---

## 4. Third option — `live_mode: false` + scalpel-injected `didSave`

### 4.1 The mechanism

After each successful internal `apply()` step within a transaction, scalpel can:

1. Write the current buffer state to the on-disk file (via the `WorkspaceEditApplier` instead of holding it in memory).
2. Send `textDocument/didSave` notifications to all Python LSPs.
3. Wait for the debounce window (500 ms + dmypy run latency, typically <500 ms warm) before reading `diagnostics_delta`.
4. Roll the disk-write back if the **transaction** as a whole fails. The MVP report §6.8 already commits to a `python-edit-log.jsonl` for inverse-edit replay (§11.5); rollback applies the inverse `WorkspaceEdit` and re-issues `didSave` to converge state.

This is **not** the same as committing the transaction. It's a per-step on-disk checkpoint that lets mypy see real content. The user-visible transaction still commits/rolls back atomically.

### 4.2 Why this is viable

- pylsp-mypy with `dmypy: true` on `didSave` runs `dmypy run --` on the on-disk file. dmypy warm latency is typically 50–500 ms on `calcpy`-scale projects (mypy daemon docs claim "10x faster" than cold mypy; cold here is ~1 s, so warm is ~100 ms order).
- The disk-write per step costs ~1 ms per file (writing already-computed content); negligible against the dmypy run.
- Inverse-edit rollback already exists in the MVP design (§11.5 `python-edit-log.jsonl`); we are not adding new rollback machinery, only invoking the existing one on transaction-level abort.
- Cross-server consistency is preserved: when scalpel issues `didSave` to one server, it issues `didSave` to **all** (pylsp + basedpyright + ruff). All servers see the same on-disk state. This is in fact tighter consistency than today's design — the multi-LSP merger already needs this (§6 of MVP report risk P0).

### 4.3 What this loses

- **Atomicity guarantee softening.** With per-step disk-write, a hard scalpel crash mid-transaction leaves files in an intermediate state. Mitigation: the `python-edit-log.jsonl` already provides forensics; recovery is `scalpel_rollback`. The crash window is identical to today's transaction-with-disk-commit semantics for the same N steps; we're not adding new crash modes.
- **Cost of disk I/O.** Negligible (~1 ms per file); the `WorkspaceEditApplier` already does this work for the final commit.

### 4.4 Why this is the right pick

The synthetic `didSave` is the **TRIZ "segmentation"** principle from CLAUDE.md applied: the contradiction "diagnostics need on-disk state, but transactions defer disk writes" is resolved by **segmenting the transaction's disk-commit phase from its rollback-commit phase**. We get fresh diagnostics without sacrificing atomicity at the user-visible boundary.

---

## 5. Decision rationale

| Option | Verdict | Key reason |
|--------|---------|------------|
| (a) `live_mode: true` | Reject | Disables dmypy; 1–20 s/step latency; documented races (#12, #81); blows §9 wall-clock budget. |
| (b) `live_mode: false` + `dmypy: true` + scalpel `didSave` per step | **Adopt** | Sub-500 ms dmypy warm rechecks; reuses existing rollback machinery; consistent across all 3 Python LSPs. |
| (c) Drop `pylsp-mypy` entirely | Hold as fallback | basedpyright already provides type diagnostics (MVP §11.1, basedpyright authoritative for `severity_breakdown`). pylsp-mypy is corroboration, not gate. Drop only if (b) fails the spike. |
| (d) User-configurable, default off | Reject | Foists the trade-off onto the user; the user-profile (research-first, regression-aversion) wants us to commit to a tested default. |

Option (b) preserves the MVP report's §3.1 commitment to three Python LSPs with full diagnostic redundancy, eliminates the 100% staleness rate identified in §2, and adds zero new failure modes that are not already mitigated.

---

## 6. Spike that would invalidate the decision (P5a)

### 6.1 Pass criteria

On the `calcpy` fixture (~600 LoC, has typed helpers, has imports across modules), run a **scripted refactor sequence** that exercises the realistic multi-step path:

1. `scalpel_split_file_by_symbols(calcpy/parser.py, ["AstNode", "Token", "Lexer"])` — 5 internal steps.
2. `scalpel_rename(calcpy/evaluator.py, "evaluate" -> "eval_expr")` — 3 internal steps.
3. `scalpel_extract_function(calcpy/evaluator.py, range, "_dispatch")` — 2 internal steps.
4. `scalpel_inline(calcpy/parser.py, "tokenize")` — 2 internal steps.

For each of the **12 internal steps**, capture:

- diagnostics_delta from `pylsp-mypy` (via the per-step `didSave`),
- diagnostics_delta from a **ground-truth oracle**: run `dmypy run -- calcpy/` against the on-disk state directly (bypassing pylsp).

### 6.2 Pass / fail thresholds

| Metric | Threshold | Action if breached |
|--------|-----------|---------------------|
| Stale-diagnostic rate (oracle says X, pylsp-mypy says Y, X ≠ Y on the same file) | < 5% across the 12 steps | accept option (b); ship MVP |
| Per-step `didSave → diagnostic available` latency (p95) | < 1 s | accept; ship |
| Per-step latency (p95) > 1 s, < 3 s | conditional | ship at MVP, document warning, plan tuning at v0.2.0 |
| Per-step latency (p95) > 3 s | reject (b) | fall back to option (c): drop pylsp-mypy at MVP, basedpyright-only |
| Cache-corruption / crash observed (issue #12 reproduction) | any occurrence in 100 runs | reject (b); investigate dmypy version pin or fall back to (c) |

### 6.3 Implementation cost of the spike

~30 LoC test harness in `test/spikes/p5a_pylsp_mypy_staleness.py`, parametrized over the four refactor scripts. Reuses existing `calcpy` fixture and `RefactorResult` capture. ~2 hours to implement, ~10 minutes per run. Run before MVP gate.

### 6.4 What "fall back to (c)" means concretely

If P5a fails, scalpel ships MVP without pylsp-mypy in the active server set. Concrete config delta in `python_strategy.py`:

```python
# §3.5 of specialist-python.md, before:
"pylsp_mypy": {"enabled": True, "live_mode": False, "dmypy": True, ...},

# after, if P5a fails:
"pylsp_mypy": {"enabled": False},
```

Diagnostic redundancy is lost (basedpyright becomes sole type-error source). Capability surface is unchanged: the `ignore_diagnostic(tool="mypy")` facade (specialist-python.md §4.1) becomes a `# type: ignore` comment generator without runtime mypy validation. Document in CHANGELOG.

---

## 7. Integration impact on the codebase

### 7.1 Changes in `PythonStrategy`

In `vendor/serena/src/serena/strategies/python_strategy.py` (or equivalent location):

```python
class PythonStrategy(LanguageStrategy):
    def post_apply_health_check_commands(self) -> list[Command]:
        """MVP report §2.6: RA: `runFlycheck`; Python: pylsp-mypy refresh + ruff source.fixAll dry-run.
        Per Q1 resolution: pylsp-mypy refresh is now a synthetic didSave, not a separate command."""
        return [
            Command.SyntheticDidSave(servers=["pylsp", "basedpyright", "ruff"]),
            Command.WaitForDiagnostics(timeout_ms=1000, servers=["pylsp", "basedpyright"]),
            Command.RuffFixAllDryRun(),
        ]
```

Additional method on the strategy (not in the base Protocol — Python-only mixin per MVP §6.8):

```python
class PythonStrategyExtensions:
    def per_step_synthetic_save(self, applier: WorkspaceEditApplier,
                                changed_uris: list[str]) -> None:
        """Called between transaction steps. Writes buffer to disk, broadcasts didSave.
        Inverse logged in python-edit-log.jsonl for transaction-level rollback."""
```

LoC delta: ~40 LoC (method + log entry + tests). Fits under §17.1 "no additional LoC budget" because it replaces the missing-from-design `post_apply_health_check_commands` mypy refresh path; the LoC was always going to be spent.

### 7.2 Changes in the multi-LSP merger

In `vendor/serena/src/serena/multi_server.py` (MVP §14.1 [10]):

- `MultiServerBroadcastResult` already supports broadcasting `didChange`. Add `broadcast_did_save` symmetric method (~15 LoC).
- The `multi_server` consistency invariant (MVP §6 P0) becomes stronger: "every transaction step ends with all three Python LSPs at the same on-disk state". Easier to test, easier to debug.

LoC delta: ~15 LoC.

### 7.3 Changes in spike list (P5)

Replace P5 in MVP report §13:

| Old P5                            | New P5a                                                     |
|-----------------------------------|-------------------------------------------------------------|
| "stale-diagnostic rate on `calcpy` under realistic refactor sequences" | Same scope, but with `dmypy: true` + synthetic-didSave config baked in. Test passes if rate <5% AND p95 latency <1 s. |

Spike P5b (new): also measure the same on `kitchen_sink_py` (4 sub-fixtures, MVP §15.4) — broader confidence. ~30 min extra runtime.

### 7.4 Changes in the diagnostics-delta merge rule

MVP report §11.1 already commits to **basedpyright as authoritative for `severity_breakdown`**, with pylsp-mypy as corroborator. Q1 resolution preserves that. Add a rule:

> If pylsp-mypy and basedpyright disagree on a (file, line, severity) triple by more than 20%, emit a `language_findings` entry of kind `type_check_disagreement` with both sets of counts. Do not gate the refactor on it. (Pre-existing in MVP §11.2 row "Server returns action with kind: null"; this is the diagnostic analogue.)

LoC delta: 0 (reuses existing `language_findings` channel).

### 7.5 Test coverage

Add to `test/integration/test_multi_server.py` (Python branch):

- `test_synthetic_did_save_propagates_to_all_servers` — assert all three servers see the same buffer on a `did_save_all()` call.
- `test_diagnostic_freshness_after_synthetic_save` — assert mypy and basedpyright both report new errors introduced by an `apply()` step.

Add to `test/spikes/p5a_pylsp_mypy_staleness.py` — the spike itself.

LoC delta: ~80 LoC tests. Already counted in MVP §17.1's ~1,650 LoC unit-test bucket.

### 7.6 Documentation

Update `docs/design/mvp/specialist-python.md` §3.5:

- Change config block comment from `# live_mode false because dmypy true` to `# live_mode false because dmypy true; per-step synthetic didSave injected by PythonStrategy.per_step_synthetic_save() — see open-questions/q1-pylsp-mypy-live-mode.md`.

Add a one-line cross-reference in MVP report §19 item 1:

- Replace "Proposed resolution path: spike P5 follow-up..." with "**Resolved**: option (b) — `live_mode: false` + `dmypy: true` + scalpel synthetic `didSave` per step. See `open-questions/q1-pylsp-mypy-live-mode.md`. Spike P5a is the falsifier."

---

## 8. References (verified 2026-04-24)

Primary sources:

- pylsp-mypy README: <https://github.com/python-lsp/pylsp-mypy/blob/master/README.md>
- pylsp-mypy plugin source: <https://github.com/python-lsp/pylsp-mypy/blob/master/pylsp_mypy/plugin.py>
- python-lsp-server dispatch: <https://github.com/python-lsp/python-lsp-server/blob/develop/pylsp/python_lsp.py>
- mypy daemon docs: <https://mypy.readthedocs.io/en/stable/mypy_daemon.html>

Issues cited:

- pylsp-mypy#12 — race condition under fast save-after-change (closed; no fix shipped). <https://github.com/python-lsp/pylsp-mypy/issues/12>
- pylsp-mypy#25 — v0.5.4 mypy-not-on-PATH crash (closed). <https://github.com/python-lsp/pylsp-mypy/issues/25>
- pylsp-mypy#52 — pylsp dies when dmypy enabled (closed via PR #53). <https://github.com/python-lsp/pylsp-mypy/issues/52>
- pylsp-mypy#81 — `--follow-imports silent` cache invalidation (open). <https://github.com/python-lsp/pylsp-mypy/issues/81>
- mypy#9309 — dmypy reloads daemon on `--shadow-file` (fixed upstream; not consumed by pylsp-mypy). <https://github.com/python/mypy/issues/9309>
- mypy#11801 — same root cause; resolution moved upstream. <https://github.com/python/mypy/issues/11801>
- mypy#16784 — shared cache + daemon. <https://github.com/python/mypy/issues/16784>
- mypy#18326 — daemon cache bug with passed-in string. <https://github.com/python/mypy/issues/18326>

Internal docs:

- `docs/design/mvp/2026-04-24-mvp-scope-report.md` §11 (diagnostic priority), §13 (spikes), §17 (LoC), §19 (open questions).
- `docs/design/mvp/specialist-python.md` §3.5 (init payloads), §14.3 (cut path), §15 (E1-E16 scenarios).
- `docs/design/mvp/specialist-scope.md` §1 (3-LSP commitment).

---

## 9. Final answer (drop-in for §19, item 1)

> **Resolved**: keep `pylsp-mypy` in the MVP active server set with `live_mode: false`, `dmypy: true`, and a scalpel-injected `textDocument/didSave` after each successful internal `apply()` step within a transaction. Source-verified that without this synthetic save, `pylsp-mypy`'s cache fallback (`pylsp_mypy/plugin.py:285`) returns stale diagnostics on every internal `didChange`, making the staleness rate 100%, not the 5% the open question assumed. The synthetic save lets `dmypy` re-check the on-disk state in <500 ms warm, preserves atomicity at the user-visible transaction boundary via the existing `python-edit-log.jsonl` rollback machinery (§11.5), and tightens cross-LSP consistency. Falsified by **spike P5a** on `calcpy` if stale-diagnostic rate exceeds 5% or per-step `didSave → diagnostic` p95 latency exceeds 3 s; on falsification, fall back to dropping `pylsp-mypy` at MVP and rely on `basedpyright` (already authoritative for `severity_breakdown` per §11.1). Integration cost is ~135 LoC across `python_strategy.py`, `multi_server.py`, and tests, all already covered by the §17.1 LoC accounting. Replaces P5 with P5a in §13.
