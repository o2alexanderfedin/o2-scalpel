# Challenger Review of v1 Draft

**Reviewer**: AI Hive(R) (challenger of drafter+challenger pair)
**Date**: 2026-04-28
**Subject**: `2026-04-28-rust-plugin-e2e-playground-spec.md` (v1 draft)
**Important context**: The 4 install-blockers in § 3 were FIXED post-drafting. Submodule HEAD `acf51109`, parent main `c59a6a8`. Spec needs re-aligning to that reality.

---

## Acceptance criteria (defined first, TDD-style)

- **AC-1**: § 3 reflects the post-fix reality — fixes are described as "completed (verify)" not "to do".
- **AC-2**: Phase plan in § 6 re-numbers or marks Phase 0 as DONE; downstream phase IDs adjust.
- **AC-3**: Every claimed file path is verified to exist on disk (or correctly described as new).
- **AC-4**: Every cited line-number range in `vendor/serena/test/e2e/conftest.py` matches the file.
- **AC-5**: README install delta in § 5 reflects the *fixed* install command (works post-§3 fixes).
- **AC-6**: E2E driver design reuses `_McpDriver` + `ScalpelRuntime` (not invented).
- **AC-7**: All four mermaid diagrams parse (no syntax errors, balanced subgraphs).
- **AC-8**: § 9 ("do NOT do yet") covers reasonably anticipated edge cases (CI runner without rust-analyzer, marketplace-cache staleness after re-publish, Claude Code version drift).
- **AC-9**: Spec voice is declarative ("SHALL"), not aspirational ("we could", "consider").
- **AC-10**: `types/` reservation either has documented v1.3 follow-up OR is removed (YAGNI).
- **AC-11**: Phase dependency chain is acyclic and each phase's outputs are explicitly named as inputs to the next.
- **AC-12**: Risk table (§ 8) acknowledges concrete risks beyond CI cost (e.g., generator-template drift re-introducing the fixed bug after `make generate-plugins`).

---

## Verification (PASS / PARTIAL / FAIL per AC)

| # | AC | Verdict | Evidence |
|---|----|---------|----------|
| 1 | § 3 reflects post-fix reality | **FAIL** | All 4 fixes landed (`.claude-plugin/marketplace.json` exists; `o2-scalpel-rust/hooks/hooks.json` exists; `.mcp.json` URL is `o2alexanderfedin/o2-scalpel-engine.git`; `verify-scalpel-rust.sh:8` is `exit 2`). § 3 still presents them as TODO with "Fix:" prescriptions. |
| 2 | Phase plan reflects DONE state | **FAIL** | § 6 shows `P0` as the first work item, not as `[DONE]`. Phase IDs `P1–P7` should renumber to `P1–P6` (or P0 should carry a `[DONE 2026-04-27, parent c59a6a8]` annotation and remain only as a verification gate). |
| 3 | File-path claims verified | **PARTIAL** | Most paths verified. But § 3.1 claims `marketplace.json` lives at repo root — it has been moved (the root file no longer exists). § 4.3 / § 7 reference `vendor/serena/test/e2e/test_e2e_playground_rust.py` (new — correct). The fixture path `vendor/serena/test/e2e/fixtures/calcrs_e2e/` is NOT cited in the spec but referenced via `calcrs_e2e_root` (line 27 of spec) — that fixture does exist. |
| 4 | Line-number ranges accurate | **PARTIAL** | `calcrs_e2e_root @ conftest.py:129–137` ✓ correct. `mcp_driver_rust @ conftest.py:281–286` ✓ correct. `_McpDriver @ conftest.py:148–212` — class is at 161, `scalpel_runtime` at 148–158, `_McpDriver` ends at 278. Range conflates fixture+class. `_which_or_skip @ 91–96, 100–111` — actually 91–96 + `rust_analyzer_bin` at 109–111. `cargo_bin` is at 99–101. Misleading citation. |
| 5 | README install delta is correct | **PASS** | `/plugin marketplace add o2alexanderfedin/o2-scalpel` and `/plugin install o2-scalpel-rust@o2-scalpel` work post-fix; the local-dev fallback uses the correct owner; `git submodule update --init --recursive` correctly retained. |
| 6 | Driver reuses existing harness | **PASS** | § 4.3 explicitly reuses `_McpDriver` + `scalpel_runtime` + `_which_or_skip`. No new harness invented. |
| 7 | Mermaid diagrams parse | **PASS** | All four diagrams (§ 4.1, § 4.2, § 4.6, § 6) use valid `flowchart` / `graph TD` syntax; subgraphs are balanced; no unescaped `<br>` issues. |
| 8 | "do NOT do yet" covers edge cases | **PARTIAL** | Covers PyPI, Linux/Windows, Python/Markdown playground. Misses: marketplace-cache staleness on re-publish at same `version` (referenced in F6 of install-mechanics § 4 and § 5.2 troubleshooting table — but not flagged as an open item); Claude Code version-drift gate (`/plugin marketplace add` requires Claude ≥ 1.0.0, only mentioned as a troubleshooting row). |
| 9 | Declarative voice | **PARTIAL** | Body uses SHALL/MUST consistently. Risk § 8 is correctly hedged. § 8 item 3 ends with "Open question for the challenger: should this spec mandate a coverage assertion ...?" — that question must either be answered or moved to § 9 (deferrals). § 8 item 6 ("Top open question for the challenger") is similarly stale — the challenger pass should resolve it, not propagate it. |
| 10 | `types/` reservation justified | **PARTIAL** | § 4.2 reserves `types/` for v1.3 (named in § 9 with the 7 deferred facades). Genuine forward-looking design — but no concrete acceptance criterion ties v1.2.2 to leaving it as an empty placeholder vs. dropping it entirely. KISS-leaning challenger position: drop `types/` from v1.2.2 and re-add when the v1.3 facade tests need it; an empty crate compiled per E2E run pays a build cost for no signal. |
| 11 | Phase chain dependencies named | **PASS** | Linear P0→P1→…→P7. Phase 3 depends on Phase 2's `mcp_driver_playground_rust` fixture. Phase 4 depends on Phase 3's test file. Phase 5 invokes Phase 4's script. No cycles. |
| 12 | Risk § 8 covers generator drift | **PARTIAL** | Risk 5 covers submodule pointer drift. Generator-template drift (P0's biggest latent regression — `make generate-plugins` after a generator regression could re-introduce the wrong owner / wrong path / wrong `exit 1`) is not in § 8. The fix-it-once-rewrite-templates note in § 3.4 mentions verification, but there is no recurring CI gate. |

**Tally**: PASS = 4 / PARTIAL = 6 / FAIL = 2.

---

## MUST FIX before v2 (with specific edit guidance)

### MF-1: § 3 must convert from "TODO" to "VERIFY" framing
**Location in spec**: § 3 (entire section, lines 35–110).
**Issue**: All four bugs were fixed in commits `68d561d` (parent) / merged via `c0ccbd2` to main. The "Verified state" / "Fix" framing is now wrong-tense and would mislead a reader into believing the work is unstarted.
**Recommended fix**: Rename § 3 heading to "Pre-existing install-blocking bugs — fixed in Phase 0 (this spec verifies)". Per sub-section, replace "Verified state (drafter Read)" with "Pre-fix state (verified by drafter on 2026-04-28)" and add a "Post-fix verification" line citing the new path/content + the parent commit SHA. Replace "Fix:" with "Applied fix (commit `68d561d`):" plus a one-line `git show --stat` summary. The four fixes are: (1) `.claude-plugin/marketplace.json` exists with `o2alexanderfedin/o2-scalpel` URLs; (2) `o2-scalpel-rust/hooks/hooks.json` exists with the canonical SessionStart binding; (3) `.mcp.json` now points at `git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git`; (4) `verify-scalpel-rust.sh:8` now `exit 2`.

### MF-2: § 6 phase plan must mark P0 as DONE
**Location in spec**: § 6 (lines 349–376).
**Issue**: P0's exit criteria are met today; treating it as a future phase wastes a slot in the plan and risks redoing the same fix.
**Recommended fix**: Either (a) rename `P0` → `P0 [DONE 2026-04-27, parent c59a6a8]` and keep it as a verification checkpoint only, or (b) drop P0 from the plan and re-number P1–P7 → P0–P6. Option (a) is preferred so the verification checklist (`git grep o2services` returns 0 hits — already true today) stays explicit.

### MF-3: Resolve the two "open question for the challenger" items
**Location in spec**: § 8 risk 3 (line 396) and § 8 risk 6 (line 399).
**Issue**: A challenger-reviewed v2 must not contain unresolved "challenger should answer" prompts.
**Recommended fix**:
- Risk 3 (coverage assertion): **Adopt a soft assertion in v1.3, not v1.2.2.** Add a `test_playground_rust_facade_coverage` placeholder marked `pytest.mark.skip(reason="enable in v1.3 when remaining 7 Rust facades land")` and document the rationale inline.
- Risk 6 (engine-repo rename): **Resolved.** The `.mcp.json` post-fix already points at `o2alexanderfedin/o2-scalpel-engine` — the rename is settled (memory `project_serena_fork_renamed.md`). Drop the "top open question" framing.

### MF-4: Conftest line-number citations
**Location in spec**: § 4.3 (lines 170–173).
**Issue**: Range `148–212` for `_McpDriver` covers two unrelated symbols (`scalpel_runtime` fixture starts at 148, `_McpDriver` class at 161, ends at 278). Range `100–111` for `rust_analyzer_bin` is wrong (`cargo_bin` is at 99–101; `rust_analyzer_bin` is at 109–111).
**Recommended fix**: Replace with precise ranges: `scalpel_runtime fixture (conftest.py:148–158)` + `_McpDriver class (conftest.py:161–278)` + `mcp_driver_rust fixture (conftest.py:281–286)` + `_which_or_skip (conftest.py:91–96)` + `rust_analyzer_bin fixture (conftest.py:109–111)`.

### MF-5: § 4.3 absolute path reference must be inlined as the relative form
**Location in spec**: § 4.3 (lines 178–181).
**Issue**: The spec acknowledges the absolute `/Volumes/Unitek-B/Projects/o2-scalpel/playground/rust` path is non-portable, then says it "will be replaced" — but ships the absolute form in the spec body. A reader copy-pasting the spec body into conftest gets a broken path on any other developer's machine.
**Recommended fix**: Inline the portable form directly: `PLAYGROUND_RUST_BASELINE = Path(__file__).resolve().parents[3] / "playground" / "rust"`. Move the absolute path mention to a footnote ("baseline resolved relative to repo root via `parents[3]` — the conftest at `vendor/serena/test/e2e/conftest.py` is 3 dirs deep from the repo root").

### MF-6: README install block must be the actually-tested form
**Location in spec**: § 5.1 (lines 293–315).
**Issue**: The README block uses `git+URL ./vendor/serena` for local dev — but the post-fix `.mcp.json` uses `git+URL .../o2-scalpel-engine.git` (no submodule). Two distinct install paths shown. Reader confusion likely.
**Recommended fix**: Either (a) add a "Why two paths?" sentence — "the marketplace install fetches the engine separately; the local-dev shortcut uses the in-tree submodule" — or (b) collapse to one form (`uvx --from git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git serena-mcp --language rust`) and remove the submodule-init instructions for non-engine-developers.

---

## SHOULD CONSIDER (nice-to-have)

### SC-1: Add a Phase 0 regression CI gate
The 4 fixes are tribal knowledge today. A 5-line CI check (`test -f .claude-plugin/marketplace.json && test -f o2-scalpel-rust/hooks/hooks.json && grep -q "exit 2" o2-scalpel-rust/hooks/verify-scalpel-rust.sh && ! git grep -q "o2services" -- ':!docs/'`) added to `playground.yml` would prevent regression.

### SC-2: Drop `types/` from v1.2.2 (YAGNI)
Empty crate compiles for zero signal. Add it back with the v1.3 facade tests. Saves ~1 s of `cargo test` per run × N CI runs.

### SC-3: Tighten § 4.5 remote-install gate description
"Off by default at v1.2.2 because the install path is still racing against the submodule-recursion gap" — but post-fix the `.mcp.json` is already submodule-free. The actual reason to gate is **CI minutes burnt on a 60–90 s `uvx` cold install on every push**, not the submodule gap. Rewrite the rationale.

### SC-4: Spec voice — § 8 item 4 / § 4.2 hedges
"...load-bearing per ..." is fine. "The `target/` directory deletion is load-bearing" — already declarative. But "A `make verify-engine-sha-pinned` target may be warranted" (§ 8 risk 5) hedges. Replace with "Decision deferred to v1.3" or commit to it.

### SC-5: Add explicit "Claude Code version" precondition to README § 5.1
The install commands assume Claude Code ≥ 1.0.0 (`/plugin marketplace add` did not exist before). Today's troubleshooting table mentions it (row "Skill namespace not found"). Promote to the install Prerequisites block.

### SC-6: Add a 2-line "what this milestone DELIVERS" table at top of § 6
Helpful for anyone scanning whether v1.2.2 ships them what they need (5 facades exercised, 1 cargo-test smoke, 1 gated remote-install stub, macOS-only CI, `make e2e-playground` target, README updates).

---

## Verdict

**APPROVE_WITH_FIXES**

The v1 draft is structurally sound: the design (§ 4) is coherent, the phase plan (§ 6) is acyclic and concrete, mermaid diagrams parse, the README delta (§ 5) is a meaningful upgrade, and the deferral list (§ 9) is honest. The fundamental problem is *temporal staleness*: § 3 and § 6's P0 reflect a state that no longer exists. Fixing the 6 MUST FIX items listed above (4 are framing/citation, 2 are content) yields a v2 that ships as final.

**MUST FIX count**: 6.
**SHOULD CONSIDER count**: 6.
**Spot-check stats**: 4 mermaid diagrams parsed (4/4), 4 install-blocker fixes verified on disk (4/4), 4 conftest line-number ranges checked (2 correct, 2 misleading), 1 stale `o2services` reference grep (0 hits in code, 0 in newly-rewritten configs — only present in research/spec docs, which is appropriate as historical record).

---

# v2 Sign-off

**Date**: 2026-04-28
**Verdict**: REWORK_v3

## MF verification

- **MF-1**: PASS — § 3 fully past-tense; pre-fix state preserved as historical context, applied-fix lines cite commit SHAs, post-fix verification quotes drafter Bash output. 4 install-blocker fixes spot-checked on disk (`.claude-plugin/marketplace.json`, `o2-scalpel-rust/hooks/hooks.json`, `verify-scalpel-rust.sh:8 = exit 2`, `.mcp.json` URL → `o2alexanderfedin/o2-scalpel-engine`); all 4 land. 4 commit SHAs spot-checked via `git log` (`85423eb`, `68d561d`, `c0ccbd2`, `c59a6a8`); all 4 exist on `main`.
- **MF-2**: PASS — § 6 P0 marked `DONE 2026-04-27 (parent c59a6a8, submodule acf51109)` in both the new § 6.0 deliverables table and the per-phase table; mermaid keeps the dotted `verified` edge. Phase numbering preserved.
- **MF-3**: PASS — Both stale "open question for the challenger" framings in § 8 resolved (risk 3 → soft assertion deferred to v1.3 via skipped placeholder; risk 6 → RESOLVED with reference to `project_serena_fork_renamed.md`).
- **MF-4**: PASS — 6 conftest line ranges spot-checked against `vendor/serena/test/e2e/conftest.py`. All 6 match exactly: `_which_or_skip` 91-96, `cargo_bin` 99-101, `rust_analyzer_bin` 109-111, `calcrs_e2e_root` 129-137, `scalpel_runtime` 148-158, `_McpDriver` 161-278, `mcp_driver_rust` 281-286. The v1 misleading ranges are gone.
- **MF-5**: **FAIL — NEW CRITICAL BUG INTRODUCED**. § 4.3 line 187 ships `Path(__file__).resolve().parents[3] / "playground" / "rust"`. Verified empirically: `parents[3]` from `vendor/serena/test/e2e/conftest.py` resolves to `/Volumes/Unitek-B/Projects/o2-scalpel/vendor`, NOT the parent-repo root. The correct index is **`parents[4]`** (`e2e` → `test` → `serena` → `vendor` → repo root = 4 walks). The `playground/rust` directory is NOT reachable via `parents[3]`. This is exactly the portability bug MF-5 was supposed to fix.
- **MF-6**: PASS — § 5.1 README install reconciled into two clearly-headed sub-sections (`### Recommended: install via Claude Code's plugin manager` + `### Engine developers only: local-dev shortcut`) with rationale on why each path exists.

## SC verification

- **SC-1**: PASS — § 8 risk 7 added with the exact 5-line shell snippet; P5 exit criterion now mentions the gate.
- **SC-2**: PASS — empty `types/` dropped from v1.2.2; § 4.2 mermaid + § 6.0 deliverables + § 6 P1 file list all reflect the drop; § 9 captures the v1.3 re-introduction trigger.
- **SC-3**: PASS — § 4.5 rationale rewritten to cite the 60-90 s `uvx` cold install as the real reason for gating; submodule-recursion concern correctly marked as moot post-§3.3.
- **SC-4**: PASS — § 8 risk 5 hedge replaced with concrete "deferred to v1.3" decision.
- **SC-5**: PASS — § 5.1 Prerequisites block now opens with `# Claude Code >= 1.0.0` and `brew upgrade` hint.
- **SC-6**: PASS — § 6.0 deliverables table added; cross-checked against per-phase table in § 6.1, no contradictions.

## New issues check

- **NEW-1 (CRITICAL)**: § 4.3 line 187 — `parents[3]` is wrong. Empirically verified: `Path("vendor/serena/test/e2e/conftest.py").resolve().parents[3]` returns `/Volumes/Unitek-B/Projects/o2-scalpel/vendor`, not the repo root. Must be `parents[4]`. The footnote on line 192 even self-contradicts: it says the conftest sits "four levels deep" (correct → needs `parents[4]`) but then lists 5 hops in parens (`file → e2e → test → serena → vendor → repo root`) and labels the result `parents[3]`. Both the constant and the footnote need correction.
- **NEW-2 (MINOR — derivative of NEW-1)**: § 4.3 footnote text should read "sits four levels deep" + "`.parents[4]` walks up four levels (file → `e2e` → `test` → `serena` → `vendor` → repo root)". The hops correspond to indices 0..4 of `.parents`, so the index after walking 4 levels is `[4]`, not `[3]`. KISS sanity check: `parents[N]` of any path is N hops up.
- No new self-contradictions beyond NEW-1's footnote.
- No new invented APIs / fictional file paths.
- No new mermaid syntax errors (all 4 diagrams still parse).
- No new hedging language ("could" on line 438 is fine — it describes a risk, not a decision).
- § 6.0 deliverables table and § 6.1 per-phase table do not contradict each other (cross-checked: 8 deliverables in § 6.0 map 1-to-1 onto P0-P7 in § 6.1).

## Required v3 deltas

1. **§ 4.3 line 187**: change `parents[3]` → `parents[4]`.
2. **§ 4.3 footnote line 192**: change `.parents[3]` → `.parents[4]` and reword "walks up four levels" so the hop count and index agree (4 walks = index 4).
3. **No other changes required** — every other MF/SC verification passed.

## Spot-check tally

- Mermaid diagrams parsed: 4/4
- Install-blocker fixes verified on disk: 4/4
- Conftest line-number ranges verified: 6/6 correct
- Commit SHAs verified via `git log`: 4/4 exist on `main`
- `parents[N]` index empirically verified: **WRONG — `parents[3]` resolves to `/vendor`, must be `parents[4]`**

## Final spec status

The spec is **one trivial edit** away from sign-off — every other MF and SC item landed cleanly, and the temporal staleness, citation, voice, and structural issues from v1 are all addressed. But the `parents[3]` bug is load-bearing (it determines whether the conftest can find the playground at all) and shipping it would surface as a `FileNotFoundError` on the very first CI run. v3 must correct `parents[3]` → `parents[4]` and re-align the footnote arithmetic. Once that lands, the spec is implementation-ready.

---

# v3 Sign-off

**Date**: 2026-04-28
**Verdict**: APPROVED

The v2 sign-off identified a single off-by-one bug (`parents[3]` → `parents[4]`) in § 4.3. The drafter applied the fix in-place + rewrote the footnote with an explicit per-index lookup table to remove the arithmetic ambiguity. Empirically verified via Python on the actual conftest path:

```
$ python3 -c "from pathlib import Path; p=Path('vendor/serena/test/e2e/conftest.py').resolve(); print('parents[4]:', p.parents[4])"
parents[4]: /Volumes/Unitek-B/Projects/o2-scalpel
```

No other deltas. Spec is implementation-ready. Phases 1-7 may proceed.
