# Challenger Review of v1

**Date**: 2026-04-29
**Reviewer**: AI Hive® (challenger pass)
**Spec under review**: `2026-04-29-lsp-feature-coverage-spec.md` (DRAFT v1)

---

## Acceptance criteria

- **AC-1**: Decision is unambiguous; doesn't split-the-difference between defenders and gap auditors. A clear directional verdict for each disputed point.
- **AC-2**: Phase 1 specifies HOW `preferred_facade` gets populated — concrete file, factory call site, baseline regen procedure, drift-CI interaction.
- **AC-3**: Phase 2's Java facades are concrete (kind strings, args, return envelope), not "TBD."
- **AC-4**: Phase 3 Serena/Scalpel coexistence has a defined disambiguation convention plus a backwards-compat story.
- **AC-5**: All cited line numbers in the research notes verify against the actual files.
- **AC-6**: Each phase declares falsifiable exit criteria distinct from "tests green."
- **AC-7**: Hedging language ("we could", "might", "consider") is absent from normative sections; appears only in §8 risks/open questions.
- **AC-8**: YAGNI — nothing in the spec is added that is not strictly needed to fix one of the three empirically-broken items.
- **AC-9**: The drafter's own open question (benchmark gating) is at least flagged as a known unresolved item, even if not answered.
- **AC-10**: Cross-LSP kind-drift risk is explicitly acknowledged for any "extend existing facade to language X" claim.

## Verification per AC

| # | AC | Verdict | Note |
|---|----|---------|------|
| 1 | Unambiguous decision | PASS | §1 "not split the difference but fix what is empirically broken before adding what is speculatively useful"; §2 lists concrete phases with effort/risk |
| 2 | How `preferred_facade` gets populated | PASS | §3.2 names the file (`capabilities.py`), the constant (`KIND_TO_FACADE`), and §3.3 the baseline + drift-CI step |
| 3 | Java facades concrete | PARTIAL | `scalpel_generate_constructor` and `scalpel_override_methods` have signatures and docstrings; `scalpel_extract` Java-arm extension is one paragraph (§4.2.1) with no example call |
| 4 | Phase 3 disambiguation defined | PASS | §5.2.1 `PREFERRED:` opener + §5.2.2 `expose_serena_symbol_tools=True` default for backwards-compat |
| 5 | Cited line numbers verify | PASS | Spot-checked: capabilities.py:84 (`preferred_facade: str \| None = None`), :319 (`preferred_facade=None`), baseline file has 72 lines containing `"preferred_facade"` of which 72 are `null` — all match research-note claims |
| 6 | Falsifiable exit criteria | PASS | §3.4 manual smoke trace + drift-CI green; §4.4 catalog rows non-null for 3 jdtls kinds; §5.4 flag-off MCP surface excludes 4 named tools |
| 7 | No hedging in normative sections | PARTIAL | §3–§5 are crisp; §8 risks correctly hedge; but §7 mermaid diagram says "Iterate docstrings, do not add more facades" — that's prescriptive in a diagram while the surrounding text leaves the gate undefined |
| 8 | YAGNI | PARTIAL | Phase 3 §5.2.2's `expose_serena_symbol_tools` flag is added before any user has reported routing collision in the wild; could be docstring-only |
| 9 | Benchmark question flagged | PASS | §8 Risks first bullet states it explicitly and ties to Phase 1's exit criteria |
| 10 | Cross-LSP kind drift acknowledged | PASS | §4.3 explicitly cites the rust-analyzer-vs-rope kind divergence and gates §4.2.1 behind dynamic capability registry |

---

## MUST FIX before v2

### MF-1: Phase-2 `scalpel_extract` Java extension hides a real ambiguity
**Location**: §4.2.1
**Issue**: The spec says "the existing `ScalpelExtractTool` gains a `language="java"` dispatch arm." But that tool's `target` literal at `scalpel_facades.py:375–377` is `"variable" | "function" | "constant" | "static" | "type_alias" | "module"`. Java has no `module` and a different notion of `static` (static-context extraction is a jdtls-specific kind). The spec does not say which `target` values are valid for `language="java"`, so the Java arm risks silent dispatch failure for invalid combinations.
**Recommended fix**: Add a per-language target-validity matrix to §4.2.1 — at minimum specify which `target` values map to which jdtls kinds, and what the facade returns for an invalid combo (presumably the same `CAPABILITY_NOT_AVAILABLE` envelope the dynamic registry already emits).

### MF-2: Phase-1 `KIND_TO_FACADE` is one-to-one but the table's `refactor.extract.function` row is structurally many-to-one
**Location**: §3.2 table rows 1, 7
**Issue**: Both rust-analyzer's `refactor.extract.function` and pylsp-rope's `refactor.extract.function` map to `scalpel_extract`. That is correct — but the table is keyed by `(server, kind)` only implicitly. If a future server emits `refactor.extract.function` and we want it routed to a different facade, the implied key is silently ambiguous. §8 risks-bullet-2 acknowledges this as "edge cases" but the contract table itself does not.
**Recommended fix**: State explicitly that `KIND_TO_FACADE` is keyed on `(source_server, kind)` (a tuple), not on `kind` alone. Update §3.3 unit-test wording so the assertion checks the tuple key, not just the kind string.

### MF-3: Phase-2 jdtls fixture is "small (a 5-class sample project)" but no path is named
**Location**: §8 Risks bullet 3
**Issue**: The risk acknowledges the fixture must exist but does not say where it lives or what naming convention to use. The project memory (`project_v0_2_0_review_fixes_batch`) mentions `calcrs_e2e/` for Rust and `calcpy/` for Python — Java needs an analogous directory but the spec leaves it implicit.
**Recommended fix**: Name the fixture path concretely: e.g. `vendor/serena/test/e2e/fixtures/calcjava_e2e/` with a 5-class sample mirroring the Rust pattern. Either ship it in Phase 2 or explicitly list the e2e test among the Phase-2 deferred items (and update §4.4 exit criteria to say "unit tests only; e2e deferred to Phase 2.5").

### MF-4: §5.2.2 hide-flag is YAGNI as currently scoped
**Location**: §5.2.2
**Issue**: The spec adds an `expose_serena_symbol_tools=True` config knob with default `True`, then describes it as backwards-compat. But there is no demonstrated case of an LLM mis-routing `rename_symbol` vs `scalpel_rename` in production traces. Adding a flag with no off-state user is exactly the speculative-bloat pattern the conservative defender warns against (`conservative-defender.md:152–164`).
**Recommended fix**: Either (a) cite at least one observed mis-routing trace as motivation for the flag, or (b) drop §5.2.2 from Phase 3 and rely on §5.2.1 `PREFERRED:` docstrings alone. If kept, downgrade it from a config field to an env-var-only experimental knob so it doesn't enter the public contract until validated.

### MF-5: Open question 1 contradicts the spec contract
**Location**: §8 open question 1 vs §3.2 table schema
**Issue**: §3.2 commits to `preferred_facade=<facade_name>` (singular string). §8 open question 1 asks "should `preferred_facade` accept a list?" If the answer is yes, §3.2's contract is wrong. v1 cannot leave a contradiction this load-bearing as an open question — pick one.
**Recommended fix**: Resolve the question now. Recommended: keep singular for v1.5 (matches existing schema at `capabilities.py:84` which is `str | None`), document the ambiguous-kind case as a Phase-1.5 follow-up if Phase-1 measurement shows it matters. Move the open question to "explicitly deferred."

---

## SHOULD CONSIDER

### SC-1: Phase 1 should ship the benchmark fixture, not just suggest it
The drafter's own §8 risk-bullet-1 says "Phase 1 should land with a small benchmark fixture (5–10 prompts × 3 trials per language)." But §3.4 exit criteria do not include the fixture — they only require drift-CI + unit test + manual smoke. If the benchmark is the gate for Phase 2, it must be a Phase-1 deliverable, not a Phase-1 wishlist item. See open-question verdict below.

### SC-2: §4.2.1 strategy-table-only extension is lower risk than 4.2.2/4.2.3 — split it
Open question 3 already raises this. It would shrink Phase 2's scope to two new tools + one strategy-table edit and let the third tool ship in Phase 2.5 once benchmark data exists.

### SC-3: §5.2.1 `PREFERRED:` opener — specify the regex
Docstring conventions only work if drift-CI can enforce them. Add a Phase-3 unit test that scans every `scalpel_*` facade docstring for `^PREFERRED: ` (or equivalent) and fails CI if missing. Otherwise the convention drifts the moment a contributor forgets it.

### SC-4: Phase 3 should explicitly state whether Serena upstream tools get a `FALLBACK:` token
The asymmetry — Scalpel says PREFERRED, Serena says nothing — is fine, but stating it in §5.2.1 ("Serena upstream tools intentionally keep neutral docstrings; the absence of a PREFERRED token is the signal") would make the convention machine-checkable.

### SC-5: §6 "What we explicitly DO NOT do" is good — extend to MCP-tool-count budget
Add a numerical ceiling: "v1.5 ships at 36 facades (33 + 3 Java); v2.0 budget is 40, with each addition requiring three independent user requests per the Phase-1 demand rule." Otherwise the "no facade additions" rule decays without a counter.

---

## Open-question verdict

**Drafter's question**: Should Phase 2 be gated on a Phase 1 benchmark exit criterion?

**Verdict: HYBRID.**

Ship Phase 2 in parallel with the benchmark fixture, but require the benchmark BEFORE Phase 4 (any further per-language facade expansion). Reasoning:

1. **Phase 2 is small and self-contained** (3 jdtls facades, ~6 file touches, dynamic-capability gate already protects against silent failures). Gating it behind a benchmark that nobody has built yet creates a chicken-and-egg: the benchmark's signal-to-noise is low until at least one language has named coverage to compare against. Pure-fallback Java with no named tools is the wrong baseline.

2. **The benchmark IS feasible without live Claude inference**. A 5-prompt × 3-trial fixture per language can be a static JSON file mapping `(natural_language_prompt, expected_tool_name)` evaluated by a deterministic scorer over the existing tool docstrings — closest-match by embedding distance, or even simpler keyword overlap. The harness exists in spirit in the existing drift-CI tests. This is one new test module, not a Claude API integration.

3. **Phase 4+ horizontal expansion** (Go, TypeScript, C#, C++ facade waves) is where the bloat risk is real. A. notes ~40–77 file touches per facade × 9 languages = 360–693 file touches if Phase 4 is unconstrained. The benchmark MUST gate that decision.

Concrete commitment for v2 of the spec:
- §3.4 exit criteria add: "Phase 1 ships a benchmark fixture at `vendor/serena/test/spikes/data/routing_benchmark.json` with 5 prompts × 3 trials × 2 languages (rust + python), plus a deterministic scorer in `test/spikes/test_routing_benchmark.py`."
- §4 ships in parallel.
- A new §4.5 "Phase 4 gating" section says: "No language-N facade waves until benchmark accuracy on Phase-2 jdtls kinds reaches ≥ 85%, where 85% is the empirically-measured Phase-1 baseline for rust-analyzer + pylsp-rope facades."

This preserves Phase 2 momentum, makes the benchmark a real artifact rather than a wishlist bullet, and pins the gate where the bloat actually lives.

---

## Verdict

**APPROVE_WITH_FIXES**

Spec is structurally sound, the three-phase decomposition follows signal-to-effort correctly, the cited line numbers verify (capabilities.py:84/319, baseline 72/72 null), and the open question is honestly flagged. Five MUST-FIX items are local to specific sections — none invalidate the overall plan. With MF-1 through MF-5 addressed and HYBRID benchmark gating wired into §3.4 + new §4.5, this becomes v2-ready.

Word count: ~1,100.
