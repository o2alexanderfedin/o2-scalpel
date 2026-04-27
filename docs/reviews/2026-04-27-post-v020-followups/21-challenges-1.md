# Challenges to Draft 1 — Pair-Programming Round 1
**Date**: 2026-04-27
**Tester**: Synthesizer B
**Target**: 20-draft-1.md

## Summary

Draft 1 is structurally strong: it captures the 3 critical findings from the synthesis input, organizes 9 important issues by category, and preserves the cross-cutting patterns from the coordinator. It correctly elevated the "two unexecuted atomic plans + P5a doc contradiction = ONE problem" cross-finding insight. However, several specialist findings are missed or muted, severities are off in two places, one self-flagged claim has weak sourcing, and the "What's NOT Wrong" defensive section recommended by the synthesis input is missing entirely. Total: 12 challenges (3 critical / 6 important / 3 minor).

## Critical challenges (Draft 2 MUST address these)

### CH-C1: Missing "What's NOT Wrong" / defensive section
- **Type**: Missing (structural)
- **Draft 1 location**: §Out-of-Scope is present but the explicit "What's NOT Wrong" defensive section is not.
- **Source contradicting**: `11-synthesis-input.md:102-106` recommends the section explicitly: "Touched-area pyright is 0/0/0 / L01-L05 closure annotations in WHAT-REMAINS.md verified accurate / new docs/dev/host-rustc-shim.md is accurate / gitStatus M-flags on spike-result files are stale (working tree is clean)." S1 §Pyright state confirms 0/0/0 on touched files; S4 confirms host-rustc-shim.md accurate; S1 §Test fixtures touched but not reverted line 60 confirms M-flag staleness.
- **Falsifiable claim**: "The synthesis input prescribes a 'What's NOT Wrong' section enumerating 4 specific defensive items; Draft 1 omits all four."
- **Required change**: Add a "What's NOT Wrong (defensive)" section between §Out-of-Scope and §Open Questions enumerating the four items above. Without it, a casual reader cannot tell the closure mostly stands and may overweight the criticals.

### CH-C2: C3 (skip-pattern drift) severity is overstated as Critical
- **Type**: Overstated severity
- **Draft 1 location**: §Critical Issues C3 (lines 48-58) — labeled Critical with self-disclaimer in the "Note on severity" block.
- **Source contradicting**: S3 §Recommendations Important #7 (`03-test-coverage.md:188`) classifies it as **Important**. Coordinator Theme 7 (`10-coordinator-thread.md:77`) labels it **IMPORTANT**. Synthesis input item 11 (`11-synthesis-input.md:34`) is in the **IMPORTANT** block. No specialist tagged this Critical.
- **Falsifiable claim**: "Three independent sources (S3, coordinator, synthesis input) all classify the 13-facade strip-the-skip pattern as Important, not Critical. Draft 1's elevation to Critical is unsourced and lacks evidence that the skips currently mask any real failure."
- **Required change**: Demote C3 to Important (move under §Important Issues alongside I4-I6, possibly as I4'). Keep the cross-cutting-theme observation intact, but the severity label must match source consensus. The "I am elevating" note can stay as a side comment if the synthesizer believes it, but the headline classification must follow specialists.

### CH-C3: Pattern 4 ("No-leaf-was-audited for L01") is over-promoted as a cross-cutting pattern
- **Type**: Misattributed / Overstated
- **Draft 1 location**: §Cross-Cutting Patterns Pattern 4 (lines 156-157).
- **Source contradicting**: This is **cross-finding insight 5** in `10-coordinator-thread.md:127-128`, which the coordinator phrases as "no specialist audited L01 tests" — a process observation, not a "cross-cutting pattern" that the report has surfaced. Synthesis input does NOT list it as a cross-cutting theme. Calling it "Pattern 4" alongside three substantive code/process patterns inflates its weight.
- **Falsifiable claim**: "The L01-not-audited observation is a coordinator scope note (cross-finding insight 5), not a cross-cutting pattern across multiple specialists. Promoting it to 'Pattern 4' alongside the TRIZ separation pattern, the unexecuted-atomic-plans pattern, and the verification-by-existence pattern misrepresents its weight."
- **Required change**: Either (a) demote to a one-line note in §Out-of-Scope ("L01 was not deeply audited; flag for re-verification if basedpyright dynamic-cap claim is challenged"), or (b) keep but re-label as "Process scope note" rather than "Pattern 4" so it doesn't read as a fourth peer pattern.

## Important challenges (Draft 2 should address)

### CH-I1: M3 CHANGELOG tag list is incorrect (7 vs 6 tags)
- **Type**: Wrong
- **Draft 1 location**: §Minor Issues M3 (line 120) — "7 tags out of date" then lists six tag names: `v0.1.0-mvp`, `v0.2.0-critical-path-complete`, `v0.2.0-stage-3-complete`, `v0.3.0-facade-application-complete`, `stage-v0.2.0-followup-01-…-complete`, `stage-v0.2.0-followups-complete`.
- **Source contradicting**: S4 §CHANGELOG (`04-doc-currency.md:30`) lists the same six tag names and also says "~7 tags". Synthesis input #15 reads "7 tags out of date" with the same six names. The arithmetic is off — either the count should be 6 (current list) or one tag is missing (the synthesis input does not name a 7th).
- **Falsifiable claim**: "Draft 1's M3 says '7 tags' but enumerates 6 tag names. Either count is wrong or one tag name is missing. Counting the bare list in `git tag` would resolve this — `v0.2.0-stage-3-facades-complete` is a candidate 7th not yet enumerated (per S2 plan-table line 33)."
- **Required change**: Either drop "7" to "6" or add the 7th tag (likely `v0.2.0-stage-3-facades-complete` per S2 line 33). Be precise.

### CH-I2: I3 fixture footgun cites wrong line for the legacy caller
- **Type**: Missing evidence (Draft 1 self-flagged)
- **Draft 1 location**: §Important I3 (lines 75-78) — claims `test_smoke_python_codeaction.py:22` is the one legacy caller.
- **Source contradicting**: S1 Important #3 (`01-code-review.md:32`) says the legacy caller exists but does not cite a specific line in `test_smoke_python_codeaction.py`. Synthesis input #7 (`11-synthesis-input.md:26`) also names `test_smoke_python_codeaction.py:22` but with no specialist line backing the `:22`.
- **Falsifiable claim**: "The `test_smoke_python_codeaction.py:22` line number is not actually verified in any specialist finding — it appears in the synthesis input as a passed-through assertion without a confirming specialist citation."
- **Required change**: Either (a) verify the line number against the file and cite it as Wave-3-confirmed, or (b) drop the `:22` and say "the one legacy caller in `test_smoke_python_codeaction.py` (line not verified at synthesis time)."

### CH-I3: M5 "13/24 → 33/34" drift cites wrong banner line
- **Type**: Missing evidence (Draft 1 self-flagged)
- **Draft 1 location**: §Minor M5 (line 122) — references `mvp-scope-report.md:17`.
- **Source contradicting**: S4 §mvp-scope-report (`04-doc-currency.md:47`) cites `mvp-scope-report.md:17` for "13 always-on / ~11 deferred-loading". Verifiable. But Draft 1 says "8+25=33 always-on" while S4 line 7 says "8 + 25 = 34" and §mvp-scope-report headline says "33/34 drift" — internal contradiction.
- **Falsifiable claim**: "Draft 1 says 8+25=33 always-on tools; S4 explicitly says 8+25=34 in two places. The arithmetic is wrong (8+25=33 mathematically, but S4's count is 34 — implying S4 either has a wrong addend or counts an extra tool)."
- **Required change**: Verify the actual count (8 primitives + 25 facades vs README banner) and reconcile with S4's stated "34". Pick one number and cite the source clearly.

### CH-I4: Missing — L02 plan parallelism wording-shift call-out
- **Type**: Missing
- **Draft 1 location**: M2 covers L03 SoT-vs-tuple drift but does NOT cover L03 parallelism threshold wording-shift.
- **Source contradicting**: S4 §Per-leaf plan files L03 (`04-doc-currency.md:106`) flags: "Plan parallelism threshold: `parallel_elapsed < serial_total * 0.7` (line 208). Per WHAT-REMAINS, the implementation refers to 'Amdahl-aware parallelism budget' — wording shift, may or may not reflect the same threshold; not verified." This is a falsifiable plan-vs-impl drift not in Draft 1.
- **Falsifiable claim**: "S4 explicitly flags an unverified threshold drift between L03 plan (`*0.7` literal) and impl ('Amdahl-aware budget' wording). Draft 1 omits this."
- **Required change**: Either fold into M2 as a sub-bullet ("L03 also has unverified parallelism-threshold wording drift per S4 line 106") or add as a separate Minor item.

### CH-I5: Missing — Cold-start ordering / fault-injection test gap (S3 Missing test categories)
- **Type**: Missing / Understated
- **Draft 1 location**: Test gaps section covers I4 (booted-RA), I5 (xpassed), I6 (mutation), and C3 (strip-the-skip). Misses S3's broader "Missing test categories" enumeration.
- **Source contradicting**: S3 §Missing test categories (`03-test-coverage.md:161-172`) lists 8 categories: concurrency/race, cold-start ordering, cross-language multi-server, perf regression guards, error-path/fault-injection, property-based, negative tests for new gates, coverage instrumentation. Draft 1 absorbs only the negative-test (I6) and cross-language (mentions in Out-of-Scope as v1.1). The other 6 categories vanish.
- **Falsifiable claim**: "S3 enumerated 8 missing test categories; Draft 1 only carries 1-2 of them, dropping concurrency/race, cold-start ordering, perf-regression guards, error-path/fault-injection, hypothesis property-based, and coverage instrumentation."
- **Required change**: Add a single "Test depth gaps (carried forward)" bullet under §Minor or under §Out-of-Scope explicitly enumerating the 6 missed categories with a one-liner each. They are deferrable but should be named so they don't silently drop off the radar.

### CH-I6: Missing — pyright-info-hint policy assertion in §What's NOT Wrong
- **Type**: Missing
- **Draft 1 location**: Not present.
- **Source contradicting**: S1 §Pyright state line 56 explicitly says "No ★ pyright info hints in the touched files (clean per the project's 'all errors must be fixed' rule)." This is a load-bearing closure claim per the user's CLAUDE.md memory `feedback_pyright_diagnostics.md` ("Pyright info-level hints (★) treated as fix-required").
- **Falsifiable claim**: "S1 explicitly verified zero ★ pyright info hints in touched files, which is the user-defined 'fix-required' bar. Draft 1's executive summary mentions '0/0/0 pyright on all touched files' but does not surface the ★ check, which is the project's stricter convention."
- **Required change**: In the §What's NOT Wrong section (per CH-C1), add explicit ★-info-hint clean-bill-of-health line. This matters because the user's diagnostic-discipline memory is invoked.

## Minor challenges (nice to address)

### CH-M1: I9 path is incomplete — sites are in `test/spikes/`, not the suggested file basenames
- **Type**: Wrong (minor — inferable but technically wrong)
- **Draft 1 location**: §Important I9 (line 110) — lists 6 file basenames without the `test/spikes/` prefix.
- **Source contradicting**: S2 §C (`02-plan-coverage.md:82`) and synthesis input #4 give the actual paths under `vendor/serena/test/spikes/`. A grep against just the basenames would miss them.
- **Required change**: Prefix with `vendor/serena/test/spikes/` for grep-ability. Same fix in §Recommended Execution Order step 3.

### CH-M2: Cross-link to specialist evidence in C2 is incomplete
- **Type**: Missing evidence
- **Draft 1 location**: §C2 (lines 38-46).
- **Source contradicting**: C2 cites S2 §B + S4 §Spike-result + S3 indirect but does not cite specific S4 line ranges. S4 §Spike-result re-runs lines 145-160 are the source-of-truth. Coordinator Theme 1 (`10-coordinator-thread.md:23-29`) is the converging-signals citation.
- **Required change**: Add line-range citations: "S4 `04-doc-currency.md:145-160`; coordinator Theme 1 `10-coordinator-thread.md:23-29`."

### CH-M3: §Recommended Execution Order should call out parallelization explicit per-step
- **Type**: Structural
- **Draft 1 location**: §Recommended Execution Order (lines 161-177). Final paragraph says "Steps 4-9 are independent of each other and can be parallelized via map/reduce" — true but vague.
- **Source contradicting**: CLAUDE.md project conventions explicitly call out map/reduce + parallelism limits. Coordinator's prioritized agenda items 1-13 are sequential prose with no explicit parallelism markers either.
- **Required change**: Re-label steps 4-9 as "Wave 2 (parallelizable)" vs steps 1-3 as "Wave 1 (sequential)" with a one-line note on dependency edges. Makes the execution plan actionable for a multi-agent run.

## Acknowledgments — what Draft 1 got right

- Correctly identified the "P5a triple-convergence" insight from coordinator cross-finding insight 1, and packaged C2 as one issue with three faces rather than three separate findings. This is the strongest synthesis move in the draft.
- Cross-cutting Pattern 1 (TRIZ separation violation tying together I1+I2+I3) is well-grounded in coordinator cross-finding insight 4 — well-attributed.
- Pattern 3 (verification-by-existence vs verification-by-test-green) sharply names a real methodology gap and recommends a concrete convention fix.
- Open Question Q3 (wire-vs-delete for I2 dead helpers) correctly surfaces the YAGNI-vs-completeness call as needing human input rather than guessing.
- Effort sizing throughout uses the project's S/M/L convention (per CLAUDE.md "Time" rule); no time estimates anywhere.
- Out-of-Scope section is comprehensive and correctly punts Stage 1H continuation, v11-milestone, v2-language-strategies, the 75 pre-existing pyright errors, and the long-horizon items.

## Suggested Draft 2 priorities

1. **Add the §What's NOT Wrong defensive section** (CH-C1) — it's the single biggest structural omission and the synthesis input prescribes it explicitly. Include the ★-info-hint line per CH-I6.
2. **Demote C3 from Critical to Important** (CH-C2) — three independent sources contradict the Critical label; keep the substance, fix the severity.
3. **Reframe Pattern 4** (CH-C3) — either drop or re-label as "process scope note" so it doesn't sit alongside the substantive patterns.
4. **Verify the questionable line numbers** (CH-I2, CH-I3) and reconcile the 33-vs-34 arithmetic in M5; fix the "7 tags vs 6 names" count in M3 (CH-I1).
5. **Surface the missed S3 test-depth categories** (CH-I5) and the L03 threshold wording-shift drift (CH-I4) so they don't silently drop off the radar.
