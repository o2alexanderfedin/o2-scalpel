# Stage 1I — Plugin Package (Generator-Driven) — PROGRESS Ledger

Plan: [`../2026-04-24-stage-1i-plugin-package.md`](../2026-04-24-stage-1i-plugin-package.md)
Parent branch: `feature/stage-1i-plugin-package`
Generator dependency: Stage 1J `o2-scalpel-newplugin` CLI @ `eddba6c579aab28bac37e708bd2124b35ea8753b`

| Task | Title | Parent SHA | Outcome | Follow-ups |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + generator verify | c094223 | OK — generator @ eddba6c5; serena-mcp entry absent (Stage 1J follow-up) | T6 smoke will skip until `serena.cli:mcp_entry` lands. |
| T1 | Run generator → o2-scalpel-rust/ | c094223 (no diff) | OK — re-emitted via `--force`; byte-identical to golden + already-tracked Stage 1J commit | Stage 1J already committed identical bytes; no new commit needed. |
| T2 | Run generator → o2-scalpel-python/ | c094223 (no diff) | OK — re-emitted via `--force`; matches committed Stage 1J Python tree | Golden snapshot at `vendor/serena/test/spikes/golden/o2-scalpel-python/` is stale (split_file description / facade list); Stage 1J fixture refresh follow-up. |
| T3 | Header banner injection (6 files) | 6956d6f | OK — 4 JSON `_generator` keys + 2 Markdown comment headers; idempotent | — |
| T4 | Top-level marketplace.json | _pending_ | _pending_ | — |
| T5 | README regen + Makefile target | _pending_ | _pending_ | — |
| T6 | uvx smoke driver + pytest wrapper | _pending_ | _pending_ | — |
| T7 | Hook chmod +x check + ledger close + tag | _pending_ | _pending_ | — |
