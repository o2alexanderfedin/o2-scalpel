# v2.0 facade ceiling roadmap — 4 candidate slots

**Status:** Item D close (v1.9.3). Audit-only — no facades shipped.
**Demand gate:** each candidate facade requires **3 independent user requests**
to admit. Until the gate is met, the slot stays open and the v1.9.3 inventory
test (`vendor/serena/test/spikes/test_v19_d_facade_inventory.py`) keeps the
current 46-tool ceiling pinned.

## Inventory baseline

As of `v1.9.3-facade-ceiling-audit`:

- **34 ergonomic facades** (refactor / generation / re-shape operations)
- **12 primitives + operators** (`scalpel_apply_capability`, `*_rollback`,
  `*_compose`, `*_install_lsp_servers`, `*_workspace_health`, etc.)
- **= 46 total** Scalpel-prefixed MCP tools

The v2.0 ergonomic-facade target is **40**, leaving **4 slots** for
demand-gated additions.

## Candidate slot 1 — `scalpel_inline_temp`

**Operation.** Inline a single local variable at every reference inside
its enclosing function. Distinct from the existing `scalpel_inline`
which targets a function/method definition; `inline_temp` operates on
a let-binding in Rust or an assignment in Python.

**LSP backing.** Rust-analyzer ships `assist.refactor.inline.local`;
rope provides `rope.refactor.inline.InlineVariable`. Both are stable
in their respective LSPs.

**Demand evidence required.** 3 user reports of "I want to inline a
specific variable, not the whole function." Common in Rust pattern
removal and Python ownership/lifetime simplification.

**Effort estimate.** Small — leverages the existing
`apply_action_and_checkpoint` helper for Rust dispatch and the
v1.9.1 `move_global` pattern for the rope path. ~150 LoC + tests.

## Candidate slot 2 — `scalpel_remove_dead_code`

**Operation.** Delete unreachable branches, dead `if False:` blocks,
and unused private symbols flagged by the LSP's diagnostics layer.
Closes a class of cleanup tasks currently routed through
`scalpel_fix_lints` + manual review.

**LSP backing.** Pyright surfaces `reportUnreachable` diagnostics with
matching code-actions; rust-analyzer offers `assist.refactor.rewrite.removeUnreachableCode`.
Both gated by the dynamic-capability registry.

**Demand evidence required.** 3 user reports asking for a one-shot
"prune what the type-checker says is dead." Distinct from
`fix_lints` because dead-code removal is whole-block delete, not
in-place lint fix.

**Effort estimate.** Small — pyright + rust-analyzer code-action
dispatch with a `target_kind` action filter analogous to
`scalpel_generate_from_undefined`. ~120 LoC + tests.

## Candidate slot 3 — `scalpel_swap_arguments`

**Operation.** Reorder a function's parameters across its definition
*and* every call site, using rope's `ChangeSignature` ArgumentReorderer
(Python) or rust-analyzer's `assist.refactor.rewrite.swap_arguments`.

**LSP backing.** Rope already exposes `ArgumentReorderer` (the v1.6
`change_signature` bridge uses it for parameter renames). Rust-analyzer
caps reorder to two-argument swaps in stable but the assist surface
is enumerated.

**Demand evidence required.** 3 user reports describing a multi-arg
reorder that today requires manual rename + textual replace.

**Effort estimate.** Medium — extends the rope bridge's
`change_signature` surface with a typed reorder spec; adds a Rust
arm via the assist dispatcher. ~200 LoC + tests.

## Candidate slot 4 — `scalpel_convert_to_classmethod`

**Operation.** Convert a Python regular `def` into `@classmethod`,
rewriting the first arg to `cls` and updating every call site that
references the receiver.

**LSP backing.** Rope provides `rope.refactor.method_object.MethodToFunction`
(distinct from the v1.6 `convert_to_method_object`). The decorator
rewrite layer is bridge-side AST manipulation similar to
`convert_to_async`.

**Demand evidence required.** 3 user reports asking for the
classmethod conversion specifically (not "make this a free function"
which `convert_to_method_object`'s reverse handles, nor
`convert_to_async`).

**Effort estimate.** Small-to-medium — bridge AST rewrite for the
decorator + first-arg rename, plus rope-driven importer rewrite. ~180 LoC
+ tests.

## Admission procedure

When a candidate clears the 3-user-request gate:

1. Append the canonical snake-case tool name to `EXPECTED_TOOLS` in
   `test/spikes/test_v19_d_facade_inventory.py`.
2. Reference the user-request evidence in the commit message (PR links,
   issue numbers, or quoted user transcripts — whatever proves demand).
3. Implement against the LSP-backing pattern noted above; add the
   `routing_aliases: ClassVar[tuple[str, ...]]` per the v1.9 Phase 4
   convention (see `vendor/serena/test/spikes/test_routing_benchmark.py`).
4. Run `test/spikes/test_routing_benchmark.py` to verify the new facade
   doesn't regress the 1.000 routing-accuracy baseline; add a benchmark
   trial with three paraphrases for the new operation.
5. Update this roadmap doc — strike the candidate's slot, increment the
   ergonomic-facade count, and (if the v2.0 ceiling is reached) close
   the roadmap with a v3.0 forward link.

## Why a gate

The v1.6 `stub-facade-fix` audit found that **4 of 44** facades had
silent contract drift between docstring and implementation. The gate
exists to prevent the inverse failure mode: speculative facades shipped
without a clear caller — these accumulate maintenance cost
(routing-benchmark trials, drift-CI docstring policing, capability
catalog entries) without proportional value. 3 user requests is a
deliberately low bar that still filters out the "neat in theory"
additions.

## Gate-check log

| Date | Slot | Evidence count | Decision |
|------|------|----------------|----------|
| 2026-04-29 | All 4 (initial) | 0 / 3 each | Roadmap filed; no admissions. |
| 2026-04-30 | All 4 (post-v1.9.x ship) | 0 / 3 each | Re-checked at v1.9.3 hand-back. No new requests since the roadmap was filed. All 4 slots remain open. The 46-tool inventory test stays in force. |

Future gate-checks: append a row each time a release-cycle hand-back
considers admitting a candidate. Once a slot crosses the 3-request
threshold, replace its row with the admission commit SHA + a forward
link to the implementing PR.
