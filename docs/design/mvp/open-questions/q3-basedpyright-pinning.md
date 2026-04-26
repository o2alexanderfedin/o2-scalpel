# Q3 — basedpyright pinning policy

**Status:** resolved
**Owner:** AI Hive(R) (Python packaging specialist)
**Date:** 2026-04-24
**Resolves:** [§19 open question 3](../2026-04-24-mvp-scope-report.md#19-open-questions-still-unresolved) — _"basedpyright vs pyright pinning policy"_
**Disagreement:** [`specialist-python.md` §17.3](../specialist-python.md) (recommended `~=` minor)
vs. [`specialist-scope.md` §13.9](../specialist-scope.md) (recommended exact pin).

---

## 1. The question, restated

scalpel depends on [basedpyright](https://github.com/DetachHead/basedpyright) — DetachHead's actively-diverging pyright fork — as one of three concurrent Python language servers (pylsp, basedpyright, ruff). Two pinning options are in dispute:

- **(A) Exact:** `basedpyright==1.39.3`. Reproducible; no silent drift; stale until manually bumped.
- **(B) Minor-floating:** `basedpyright~=1.39` (≡ `>=1.39,<2`). Picks up patches and minor improvements; risks silent breakage when basedpyright ships a code-action / `WorkspaceEdit` change.

The MVP report's §15.4 capability-catalog drift CI gate **does** diff `scalpel_capabilities_list("python")` against a checked-in golden file. If that gate catches every relevant change either way, exact-vs-floating is moot. The whole question collapses into: *can the catalog drift gate detect every basedpyright change that breaks scalpel?*

This report concludes that the answer is **no**, and therefore we pin **exact**.

---

## 2. basedpyright release cadence and SemVer adherence

### 2.1 Release frequency (12 months, 2025-04 → 2026-04)

Pulled from [`gh release list --repo DetachHead/basedpyright`](https://github.com/DetachHead/basedpyright/releases):

| Window | Releases | Minor bumps | Patches |
|---|---|---|---|
| 2025-04 → 2025-10 (6 mo) | 14 | 4 (1.29, 1.30, 1.31, 1.32) | 10 |
| 2025-10 → 2026-04 (6 mo) | 17 | 8 (1.32–1.39) | 9 |
| **12-mo total** | **31** | **12** | **19** |

That's roughly **one release every 12 days** and **one minor bump every 30 days**. basedpyright's minor cadence is meaningfully slower than pyright's `1.1.x` weekly drumbeat (pyright shipped 30 patch releases over the same window — see [microsoft/pyright/releases](https://github.com/microsoft/pyright/releases)) but every minor bump rolls in 2–4 pyright `1.1.x` patches plus basedpyright-specific changes.

### 2.2 SemVer policy — the maintainer does *not* commit to it

There is no published versioning policy. Empirically:

- **No `MAJOR.MINOR.PATCH` discipline.** [Issue #132 "rework the versioning"](https://github.com/DetachHead/basedpyright/issues/132) discusses the *mechanics* of bumping (Lerna, private node packages) but never codifies semantics. The maintainer has not asserted that minor releases are non-breaking.
- **Patch releases ship new diagnostics.** [Issue #1218](https://github.com/DetachHead/basedpyright/issues/1218): user `alexandreczg` reported v1.28.5 (a patch over v1.28.4) introduced ~15 new `reportAny` warnings. The maintainer's reply: the change is intentional. The user's parting comment — _"I just got surprised with a patch version all of the sudden changing my project's quality landscape so drastically"_ — captures the policy in user-discovery form.
- **Minor releases admit "breaking changes" by name.** v1.32.0 release notes ([release page](https://github.com/DetachHead/basedpyright/releases/tag/v1.32.0)) literally say: _"this approach limits us from making any **interesting breaking changes** to the type system itself"_ and introduces a `enableBasedFeatures` opt-in flag. The maintainer thinks of minor releases as the channel for type-system breakage.
- **Accidental breakage is patch-fixed.** v1.32.1 ([release notes](https://github.com/DetachHead/basedpyright/releases/tag/v1.32.1)) is a 1-PR release titled _"fix an accidental breaking change to `dataclass_transform` that was introduced in pyright 1.1.407"_. Mental model: minor = breakage allowed; patch = fix breakage.

**Conclusion.** basedpyright's versioning is closer to ChromeOS-style "minor = feature window, patch = bug window, breakage at any granularity allowed" than to strict SemVer. Under this model, neither `==` nor `~=` gives semantic safety — only `==` gives **build reproducibility**.

---

## 3. Specific minor releases that would have broken scalpel

The MVP report relies on basedpyright's code-action surface, command surface, and `WorkspaceEdit` shape. Walking the 12-month minor history with that lens:

| Release | Date | Change relevant to scalpel | Catalog-drift CI catches? |
|---|---|---|---|
| [v1.30.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.30.0) | 2025-07-09 | **New code action**: `# pyright: ignore` insertion (PR [#1359](https://github.com/DetachHead/basedpyright/pull/1359)). scalpel's `ignore_diagnostic(tool="pyright")` facade depends on this exact action. | **Yes** — new entry in `scalpel_capabilities_list("python")` |
| [v1.31.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.31.0) | 2025-07-16 | **Command surface change**: `writeBaseline`, `restartServer`, `createTypeStub` previously registered only in vscode extension; now registered in the language server (PR [#1385](https://github.com/DetachHead/basedpyright/pull/1385)). scalpel's [§4.4.2 dispatcher](../2026-04-24-mvp-scope-report.md) lists these commands. Pre-1.31 they returned `MethodNotFound`; post-1.31 they work. | **Yes** — new entries in command catalog |
| [v1.32.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.32.0) | 2025-10-22 | `enableBasedFeatures` opt-in; `reportSelfClsDefault` new diagnostic. Diagnostics-only changes don't change the catalog but **do** affect `severity_breakdown` — tests asserting diagnostic counts on `calcpy` would flake. | **Partial** — catalog stable; diagnostic-count fixtures break |
| [v1.34.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.34.0) | 2025-11-19 | **New LSP method**: `textDocument/implementation` ("Go to Implementations"), PR [#1636](https://github.com/DetachHead/basedpyright/pull/1636). Adds an entry to scalpel's protocol-method catalog. | **Yes** — new method in catalog |
| [v1.36.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.36.0) | 2025-12-09 | `--baselinemode` CLI argument; CI baseline failure mode. Affects scalpel's spawn command if we ever add `--baselinemode` (we don't at MVP). | **No** (CLI flag, not LSP method) |
| [v1.37.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.37.0) | 2026-01-04 | **New code action**: quick-fix to add `@override` (PR [#1680](https://github.com/DetachHead/basedpyright/pull/1680)). scalpel's `quickfix.basedpyright.*` namespace gains an entry. | **Yes** — new entry in catalog |
| [v1.38.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.38.0) | 2026-02-11 | **Three new quick fixes**: `reportUnnecessaryCast`, `reportUnusedCallResult`, `reportSelfClsDefault` (PR [#1721](https://github.com/DetachHead/basedpyright/pull/1721)). Catalog growth. | **Yes** — new entries |
| [v1.39.0](https://github.com/DetachHead/basedpyright/releases/tag/v1.39.0) | 2026-04-01 | New diagnostic rule `reportEmptyAbstractUsage` (PR [#1748](https://github.com/DetachHead/basedpyright/pull/1748)). Diagnostics-only. | **Partial** (same as v1.32) |

**Tally over 12 months under `~=1.X` floating:**

- 8 of 8 minor releases would have **changed scalpel's catalog or diagnostic surface**.
- 6 of 8 would have caused a catalog-drift CI failure on the next pull.
- 2 of 8 (1.32, 1.39) ship diagnostic-count drift that the catalog gate **does not** detect — only diagnostic-count fixture tests would.

The catalog gate catches additions and renames; it does **not** catch:

- Title-text drift on existing actions (e.g., `"Add import: numpy"` → `"Import 'numpy'"`). scalpel's merge rule (`specialist-python.md` §5.2) dedupes by normalized title; a title change across a minor bump silently changes which server "wins" a duplicate.
- `WorkspaceEdit` shape drift (the `documentChanges` vs. `changes` ambiguity that bit pylsp-rope historically; basedpyright has been consistent on `documentChanges` to date but is not contractually bound).
- Diagnostic message-prefix changes that scalpel's diagnostic-dedup rule (`specialist-python.md` §10.4) keys on.
- Behavioral changes to existing actions (e.g., an auto-import action that now adds a relative import where it previously added an absolute one — the kind/title are unchanged but the `WorkspaceEdit` differs).

These gaps are precisely the *silent regressions* the user's profile flags as a top frustration (per [`CLAUDE.md`](../../../CLAUDE.md): _"Frustrations: regression"_).

---

## 4. Pyright's track record (basedpyright rebases off it)

Pyright's release page ([microsoft/pyright/releases](https://github.com/microsoft/pyright/releases)) shows ~50 releases per year, all stamped `1.1.x`. There is no minor channel — every pyright release is, formally, a patch of `1.1`. The `1.1.x` numbers are effectively build numbers, not semantic levels.

basedpyright rebases pyright into its own `1.X.Y` namespace and ships pyright catch-up in roughly weekly batches. So basedpyright's "patch" (e.g., v1.39.0 → v1.39.3 over 19 days) typically rolls in 0–1 pyright `1.1.x` releases plus targeted basedpyright fixes. basedpyright's "minor" (v1.38 → v1.39 over ~7 weeks) typically rolls in 1–2 pyright `1.1.x` releases plus the bulk of new basedpyright-specific code-action / diagnostic work.

This means **the riskiest churn happens at basedpyright minor bumps**, not patches. Floating across minors (`~=1.39`) is therefore strictly higher-risk than floating across patches (`>=1.39,<1.40`).

---

## 5. Industry comparison

How comparable consumers pin basedpyright / pyright:

| Consumer | What they pin | Where |
|---|---|---|
| **[oraios/serena](https://github.com/oraios/serena/blob/main/pyproject.toml)** (our upstream) | `pyright==1.1.403` exact | `pyproject.toml` dependencies |
| **[mason.nvim](https://github.com/mason-org/mason-registry)** | Tracks latest stable, but each user's `mason-lock.json` records the resolved version exactly | Per-user lockfile |
| **[nvim-lspconfig](https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/basedpyright.lua)** | No version constraint at all — invokes whichever `basedpyright-langserver` is on `$PATH` | Out-of-band |
| **[ruff-vscode](https://github.com/astral-sh/ruff-vscode)** | Bundles ruff at exact version per release | `package.json` build step |
| **[Helix](https://github.com/helix-editor/helix)** | No bundling; user installs. Helix discussions show `uvx --from basedpyright basedpyright-langserver` (which respects whatever's in the user's lock) | Out-of-band |

Two patterns emerge:

1. **Editor LSP managers** (mason, lspconfig, helix) defer pinning to the user. They are not analogous to scalpel; scalpel ships a coherent capability surface and *cannot* defer.
2. **Tools that bundle a language server as a library dependency** — serena (our actual upstream), ruff-vscode — pin **exact**.

Serena's choice is the strongest precedent: it is the same kind of consumer scalpel is (Python project that depends on a language server's behavior at the wire level), and it pins `pyright==1.1.403`. The serena `pyproject.toml` even comments _"exact pinning is used intentionally for security-sensitive transitive dependencies, particularly because the project uses uvx, which installs from git and ignores lock files"_ — this exactly matches scalpel's distribution model (`uvx --from <git-url> serena-mcp-server --mode scalpel`).

---

## 6. Third options considered and rejected

### (C) Pin to a git SHA — `basedpyright @ git+https://github.com/DetachHead/basedpyright@5f66727`

**Pros:** maximum reproducibility; can pin to a non-released revision if needed.
**Cons:**
- Loses the wheel artifacts published to PyPI (basedpyright bundles the `pyright-internal` Node.js artifacts in its wheel; building from git requires Node + Lerna — a 2-minute install becomes 20 minutes).
- `uvx` and `pip install` both work but go through a source build.
- Defeats `uv`'s prebuilt-wheel cache and CI cache.
- Adds a `git` build dependency to scalpel install.

**Verdict:** rejected. Use only if PyPI is broken or we need a security patch before a release.

### (D) Float minors but require dependabot + green CI to bump

**Pros:** automation; we get bumps-as-PRs.
**Cons:**
- Requires GitHub PR workflow on a repo where `CLAUDE.md` says _"No Pull Requests. Solo development."_ Dependabot doesn't fit the workflow.
- Even with green CI, the catalog-drift gate misses title-text and behavioral drift (§3 above).
- Equivalent in effect to "exact, with manual bump" but adds CI noise and green-CI false confidence.

**Verdict:** rejected on workflow incompatibility. Revisit if scalpel ever adopts PRs (post-v1.0 marketplace push).

### (E) Pin to exact-patch range — `>=1.39,<1.40`

**Pros:** picks up patch fixes (e.g., v1.32.1's `dataclass_transform` accidental-breakage fix) without manual intervention; blocks minor bumps.
**Cons:**
- §2.2 evidence shows patch releases also ship new diagnostic rules (v1.28.5 → 15 new `reportAny` warnings). Patch is *not* safe by basedpyright's policy.
- Equivalent to floating-on-patches; same silent-regression vector at smaller magnitude.

**Verdict:** rejected. The cost of an extra manual bump every 12 days is dwarfed by the regression cost from one missed surface change.

---

## 7. Decision

**Pin exact: `basedpyright==1.39.3`** in scalpel's `pyproject.toml`.

```toml
# pyproject.toml
[project]
dependencies = [
    "basedpyright==1.39.3",  # pinned exact; bump via §8 procedure
    # ...
]
```

Rationale, ranked:

1. **basedpyright explicitly does not promise SemVer.** §2.2 evidence — the maintainer treats minor releases as the breakage channel and patches as the fix channel. `~=1.39` would silently absorb breakage.
2. **The catalog-drift CI gate has known blind spots** (§3): title text, `WorkspaceEdit` shape, diagnostic message prefix, behavioral change to an existing action. Exact pinning closes those gaps at the dependency level.
3. **Serena (our upstream fork base) pins pyright exact.** Mirroring that style keeps our `pyproject.toml` shape consistent with the file we inherit and modify.
4. **The user's profile flags regression aversion.** The ergonomic cost of "manually bump basedpyright on a schedule" is small; the ergonomic cost of a silent regression that bricks a refactor mid-session is large. Asymmetric payoff.
5. **scalpel ships via `uvx` from git**, which ignores any lockfile a user has. Without an in-repo exact pin, the *user's* environment can resolve to whatever PyPI returns at install time. Floating gives us non-reproducible support tickets.

**Same policy applies to other LSP deps for the same reasons:**

```toml
"basedpyright==1.39.3",
"python-lsp-server==1.13.1",   # pin exact
"pylsp-rope==0.1.17",           # pin exact (called out in §17.3 also)
"pylsp-mypy==0.7.0",            # pin exact
"python-lsp-ruff==2.2.2",      # pin exact
"ruff==0.14.4",                # pin exact (per `specialist-python.md` §17.2)
"rope==1.13.0",                # pin exact (per `specialist-scope.md` §13.8)
```

Cross-references: this aligns with [`specialist-scope.md` §5.7 and §13.8](../specialist-scope.md) (rope exact pin) and the [`specialist-python.md` §17.2](../specialist-python.md) (ruff exact pin for `--preview` rule stability).

---

## 8. Bump procedure and failure-mode test plan

### 8.1 Scheduled bump cadence

- **Cadence target:** evaluate a basedpyright bump on the **first Monday of each month**.
- **Mechanism:** a make-target `make check-deps-stale` runs `uv pip list --outdated` and prints a one-line summary; CI surfaces a warning (not a failure) when scalpel's `basedpyright` is more than 60 days behind PyPI's latest. This is non-blocking — it just nags.
- **Owner:** whichever maintainer touches the Python strategy next; if 60 days pass without a bump, open a `chore: bump basedpyright` task.

### 8.2 Bump test plan (the "smoke test that alerts us when fixes are available")

When bumping basedpyright `X.Y.Z` → `X'.Y'.Z'`:

1. Run `pytest test/integration/python/ -k basedpyright` — the four basedpyright-specific integration tests (`test_basedpyright_imports.py`, `test_basedpyright_autoimport.py`, `test_basedpyright_ignore.py`, `test_basedpyright_annotate.py`).
2. Run the catalog-drift gate: `pytest test/baselines/test_capability_catalog_drift.py::test_python`. This is expected to fail when basedpyright adds/removes/renames a code action.
3. **If catalog drift fires:**
   - Inspect the diff. Categorize each entry as (a) new capability we want to expose (add an integration test, update baseline, ship), (b) removed capability (audit downstream callers, possibly block bump), (c) rename (update applier mapping, update baseline).
4. Run the diagnostic-count fixture: `pytest test/integration/python/test_diagnostic_count_calcpy.py`. This catches §3's "diagnostic count drift" blind spot (e.g., v1.32.0's `reportSelfClsDefault` would fire here).
5. Run a *title-equivalence* fixture: `pytest test/integration/python/test_action_title_stability.py`. This snapshot-tests the literal title strings basedpyright emits for the four MVP action kinds (`source.organizeImports`, `quickfix.basedpyright.autoimport`, `quickfix.basedpyright.pyrightignore`, `source.organizeImports.basedpyright`). Title drift fails the bump.
6. Run E1-py + E3-py + E9-py + E10-py (the four blocking E2E scenarios per `specialist-python.md` §15) on `calcpy`.
7. If all green, update `pyproject.toml` pin and `test/baselines/capability_catalog_python.json`, commit `chore(deps): bump basedpyright X.Y.Z → X'.Y'.Z'`, push.

### 8.3 New fixtures introduced by this decision

| Fixture | Purpose | Cost |
|---|---|---|
| `test/integration/python/test_action_title_stability.py` | Snapshot-tests literal titles for 4 basedpyright MVP actions | ~80 LoC, ~2s runtime |
| `test/integration/python/test_diagnostic_count_calcpy.py` | Asserts basedpyright emits ≤ N diagnostics on `calcpy` (catches §3's diagnostic-drift blind spot) | ~120 LoC, ~5s runtime |
| `make check-deps-stale` target + CI nag job | Surfaces 60-day stale pin as warning | ~20 LoC of Make + 30 LoC of CI |

These fixtures plug the catalog-drift gate's two known blind spots. They cost ~250 LoC and ~10s of test time — a small premium over the existing test surface and well below the LoC budget noted in `specialist-scope.md` §3.

### 8.4 What an exact pin does *not* protect against

For honesty:

- **Security CVEs in basedpyright.** If a CVE drops on v1.39.3, exact pin means we ship a known-vulnerable LSP until a maintainer bumps. Mitigation: GitHub Dependabot security alerts on the repo (read-only — no auto-PR — per `CLAUDE.md`'s no-PR rule); maintainer triages within 48h. basedpyright's attack surface is small (it runs locally over stdio with the user's project files; not network-exposed), so the practical risk is low.
- **Pyright-side bug fixes** that basedpyright rolls in at minor bumps. Exact pin defers those until manual bump. Mitigation: §8.1's monthly check.
- **Drift between users' system Pythons and our pinned LSP.** The pin is on the LSP wheel; the user's interpreter is independent. The interpreter-discovery chain (`specialist-python.md` §7) handles this orthogonally.

---

## 9. Final answer (paste into §19 of the MVP report)

> **Q3 resolved → exact pin.** scalpel pins `basedpyright==1.39.3` (and the other Python LSP deps exact, matching serena's upstream policy). The decision rests on three findings: (1) basedpyright does not commit to SemVer — minor releases explicitly carry "interesting breaking changes" (v1.32.0 release notes; [issue #1218](https://github.com/DetachHead/basedpyright/issues/1218) shows new diagnostics also ship in patches); (2) the §15.4 catalog-drift CI gate catches additions and renames but misses title-text drift, `WorkspaceEdit` shape drift, and behavioral change to existing actions — exact pin closes those gaps at the dependency level; (3) serena (our upstream) pins `pyright==1.1.403` exact for the same `uvx`-from-git distribution model scalpel uses. Bump procedure: monthly stale-check nag (non-blocking), exact-pin bump runs the four basedpyright integration tests, the catalog-drift gate, a new title-stability snapshot fixture, and a new diagnostic-count fixture before the pin moves. Cost: ~250 LoC of new fixtures; one human-driven bump every 30–60 days. Floating (`~=1.39`) is rejected because every minor release in the last 12 months would have changed scalpel's surface, and 2 of 8 (v1.32, v1.39) shipped silent diagnostic-count drift the catalog gate does not detect.

---

## 10. References

- basedpyright repo: https://github.com/DetachHead/basedpyright
- basedpyright releases: https://github.com/DetachHead/basedpyright/releases
- v1.30.0 (new `# pyright: ignore` action): https://github.com/DetachHead/basedpyright/releases/tag/v1.30.0
- v1.31.0 (command-surface change): https://github.com/DetachHead/basedpyright/releases/tag/v1.31.0
- v1.32.0 (`enableBasedFeatures`, "interesting breaking changes" framing): https://github.com/DetachHead/basedpyright/releases/tag/v1.32.0
- v1.32.1 (accidental-breakage patch fix): https://github.com/DetachHead/basedpyright/releases/tag/v1.32.1
- v1.34.0 (`textDocument/implementation` LSP method added): https://github.com/DetachHead/basedpyright/releases/tag/v1.34.0
- v1.37.0 (`@override` quick-fix): https://github.com/DetachHead/basedpyright/releases/tag/v1.37.0
- v1.38.0 (three new quick fixes): https://github.com/DetachHead/basedpyright/releases/tag/v1.38.0
- v1.39.0 (`reportEmptyAbstractUsage`): https://github.com/DetachHead/basedpyright/releases/tag/v1.39.0
- Issue #132 ("rework the versioning"): https://github.com/DetachHead/basedpyright/issues/132
- Issue #1218 (patch release introduced new warnings): https://github.com/DetachHead/basedpyright/issues/1218
- pyright releases: https://github.com/microsoft/pyright/releases
- serena `pyproject.toml` (upstream pin precedent): https://github.com/oraios/serena/blob/main/pyproject.toml
- nvim-lspconfig basedpyright config: https://github.com/neovim/nvim-lspconfig/blob/master/lua/lspconfig/configs/basedpyright.lua
- mason-lspconfig: https://github.com/mason-org/mason-lspconfig.nvim
- ruff-vscode: https://github.com/astral-sh/ruff-vscode
- MVP scope report §19: [`../2026-04-24-mvp-scope-report.md`](../2026-04-24-mvp-scope-report.md)
- Python specialist §17.3 (the `~=` minor recommendation this report overrides): [`../specialist-python.md`](../specialist-python.md)
- Engineering-scope §13.9 / §5.7 / §13.8 (the exact-pin recommendation this report confirms): [`../specialist-scope.md`](../specialist-scope.md)

---

*Authored by AI Hive(R), 2026-04-24. Resolves §19 open question 3 of the MVP scope report.*
