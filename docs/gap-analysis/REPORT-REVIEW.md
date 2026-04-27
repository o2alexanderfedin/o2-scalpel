# Navigator Review of REPORT-DRAFT-V1.md

## Verdict

**APPROVE-WITH-EDITS.** The draft is structurally sound, covers all 8 coordinator buckets (A–H mapped to §1–§6 + Cross-cutting + Out-of-scope), faithfully reports the 37-tool count, the 14/15 domain status, the 117/~694 test inventory, and the 810/9,460 LoC Stage 1H ratio. Sequencing matches the coordinator's order precisely. Tone is honest about deferrals (no false "shipped" claims for Stage 1H or Stage 2B). Length is **183 lines** — well under the 600 ceiling and below the ~400 target, which is fine. Two issues are material: (1) the P5a recommendation editorializes in the wrong direction relative to A§4 evidence and must be neutralized; (2) the inspect.getsource fix-path proposals are speculation beyond what D§2 supports and must be softened. The Stage 2B/1H "double-counting" concern is a non-issue. After ~5 mechanical edits this is publishable.

## Driver-flagged decisions — adjudicated

1. **Double-counting (Stage 2B / Stage 1H in §2 + §3):** **Not double-counting — keep as-is.** §2 is the state-of-the-union status table (one row per stage). §3 explains the gap behind the "partial" labels. This is honest layering: the table says *what status*, §3 says *what's actually deferred*. Concrete instruction: **No edit required**, but tighten the Stage 2B table cell from "naming differs from plan" to "naming/count differs; all 40 E2E pass" so the "behaviorally complete" framing is in the table itself.

2. **P5a editorialization direction:** **Driver picked the wrong direction — must be reversed or neutralized.** A§4 is unambiguous: the spike re-run produced `stale_rate 8.33%→0.00%` (zero stale across 12 trials) and `p95 8.011s→2.668s` (cold-start within budget). Those are *measurement-driven evidence in favor of SHIP*, not against it. The fact that "code reflects DROP" is an artifact of unsynchronized state, not a vote. The coordinator outline (Bucket F-1) framed this neutrally. Concrete instruction: **In §1, replace "probably ratify DROP since the code already reflects it" with: "the spike re-run evidence (0% stale, p95 within budget) leans toward ratifying SHIP and adding a small code change to enable mypy in the Python strategy; ratifying DROP would require explaining away the new measurement and is the path of least code change. Both are defensible — the project owner must call it."**

3. **inspect.getsource fix specificity:** **Driver speculated beyond D§2 — soften.** D§2 hypothesizes three causes (dynamic codegen / bytecode mismatch / decorator stacking) and points at `scalpel_facades.py:1002`. The draft's specific remediations (`functools.WRAPPER_ASSIGNMENTS`, `__wrapped_source__`) are **not in D** — they are the driver's guess. Concrete instruction: **In §2, replace the "Suggested fix path" sentence with: "Suggested investigation path (per D§2 hypothesis): trace the safety-call wrapper at `scalpel_facades.py:1002`; one root-cause fix likely clears all six. Specific remediation TBD — candidates include `functools.WRAPPER_ASSIGNMENTS`-aware source extraction or attaching an explicit source attribute on the decorator, but neither is verified."**

## Required edits (apply these mechanically)

- **E1: §1 P5a "Action implied" paragraph** — Replace the editorialized "probably ratify DROP since the code already reflects it" with the neutral framing in adjudication #2 above. Reason: A§4 evidence (stale_rate 0%, p95 2.668s) leans the other way; coordinator F-1 is neutral; driver overstepped.

- **E2: §2 "The 6 inspect.getsource flakes" subsection** — Soften the "Suggested fix path" sentence per adjudication #3. Reason: `functools.WRAPPER_ASSIGNMENTS` and `__wrapped_source__` are driver speculation; D§2 only hypothesizes generic causes.

- **E3: §2 status table, Stage 2B row** — Change cell text from "**partial — naming differs from plan**" to "**partial — naming/count differs; all 40 E2E pass**". Reason: makes the table itself convey "behaviorally complete".

- **E4: §2 status table, Stage 3 row Evidence column** — Currently says "tag `v0.2.0-stage-3-complete` (A§3, C§3)". Add submodule SHA `4ae3d99e` for T6+T7. Reason: A§3 lists this SHA explicitly as the truth-check anchor for the contested T6/T7 claims.

- **E5: TL;DR paragraph 2 (last bullet)** — Add the watch-items from B§4 as a parenthetical at the end: "(plus four watch-items: `lspee` 1.0 maturity, `gopls daemon` reuse, Anthropic native LSP-write, plugin-list API)". Reason: TL;DR currently elides ecosystem watch-items entirely; the **plugin-list API request to Anthropic** (B§4) is missing from the entire draft.

## Suggested edits (improve but not blocking)

- **S1: §3 Stage 1H paragraph** — "T8–T9 — 16 Rust assist-family integration tests" — verify breakdown against `stage-1h-results/PROGRESS.md:21–22` if v2 driver wants precision. Non-blocking.

- **S2: §4 ordering** — Re-order so the 4 PROGRESS.md items come first, then E1-py, then calcpy monolith — minor.

- **S3: §Cross-cutting risks #2 (Anthropic)** — Inline the three GitHub issue numbers (`#24249, #1315, #32502`) directly in the bullet for ease of reference. Already cited indirectly via B§3.

- **S4: §6 v2+ strategies** — Add Q13 fork/rename context (B§2): "(Q13 resolution permits Boostvolt-shaped plugin trees with attribution.)" Optional.

- **S5: §Cross-cutting risks** — Add a 6th bullet for the Anthropic plugin-list API request (B§4 watch-item): "Plugin-list API request filed with Anthropic — low-cost feature request for documented plugin discovery; tracked, no action."

## Things the draft got right (worth preserving)

- TL;DR opens with "**functionally complete through v0.3.0**" — matches coordinator headline exactly.
- Tool count math (8 + 6 + 23 = 37) is correct and cited (C§Summary).
- Stage 1H gap framed honestly with both numerator (810 LoC) and denominator (9,460 LoC).
- Sequencing matches coordinator's 1–7 order precisely (P5a → inspect.getsource → v0.2.0 follow-ups → Stage 1H continuation → v1.1 → v2+ → #1040).
- Sizing uses small/medium/large per project rule — **no time estimates anywhere**.
- No emoji decorations in section headers.
- No "Generated with Claude" footer; author = AI Hive(R) per CLAUDE.md.
- §Out-of-scope-by-design correctly cites B§7 with all 10 coordinator-G items.
- §Cross-cutting risks covers 5 of 6 coordinator-H items.
- D§2 file:line table reproduced faithfully (6 rows, line numbers match exactly).
- "All 40 E2E pass, 0 xfail" stated correctly in multiple places (matches C).
- Headline tool count called out explicitly under the table — good information design.

## Missing material the v2 should add

- **Plugin-list API request to Anthropic** (B§4 watch-items) — not in draft anywhere; add as Cross-cutting risk #6.
- **Q13 fork/rename resolution** (B§2) — Boostvolt MIT/attribution; Piebald clean-room. One-line context for §6.
- **14-step Python interpreter discovery** (C§7) — non-trivial shipped feature; could ground the "Python is a real strategy" claim. Optional.
- **CapabilityCatalog.hash() SHA-256 export** (B§1.6, C§8) — quality gate the design names; not in draft. Optional.
- **CHANGELOG.md citation** — coordinator implies B sourced this; cross-cite would strengthen TL;DR. Optional.

---

**Summary:** APPROVE-WITH-EDITS. **5 required edits, 5 suggested edits.**
