# Stage 1J — Plugin/Skill Generator — PROGRESS Ledger

Plan: [`../2026-04-25-stage-1j-plugin-skill-generator.md`](../2026-04-25-stage-1j-plugin-skill-generator.md)
Submodule branch: `feature/stage-1j-plugin-skill-generator` (off `main` @ `1ba3f9b1`)
Parent branch: `feature/stage-1j-plugin-skill-generator` (off `develop` @ `8ed625d`)

| Task | Title | Submodule SHA | Outcome | Follow-ups |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + `_FakeStrategy` fixture | df9c270e | OK — 2/2 green | — |
| T1 | Pydantic schemas (PluginManifest, SkillFrontmatter, MarketplaceManifest) | edd5de0c | OK — 5/5 green | HttpUrl→str+regex (plan deviation, Pyright cleanliness) |
| T2 | `_render_plugin_json` | aeeb08b0 | OK — 3/3 green | — |
| T3 | `_render_mcp_json` | f4f30ad3 | OK — 3/3 green | — |
| T4 | `_render_marketplace_json` | 1feffb9a | OK — 3/3 green | — |
| T5 | `_render_skill_for_facade` | fc8a5e90 | OK — 5/5 green | — |
| T6 | `_render_readme` | c0b6fd04 | OK — 5/5 green | — |
| T7 | `_render_session_start_hook` | 5c9ec82c | OK — 5/5 green | — |
| T8 | `PluginGenerator.emit` composition | 66251d7b | OK — 7/7 green | — |
| T9 | CLI entry `o2-scalpel-newplugin` | _pending_ | _pending_ | — |
| T10 | Golden-file snapshots (rust + python) | _pending_ | _pending_ | — |
| T11 | Stage 1I refactor (`make generate-plugins`) | _pending_ | _pending_ | — |
| T12 | E2E hook + uvx install + tools/list verify | _pending_ | _pending_ | — |
| T13 | ff-merge submodule + parent merge + tag | _pending_ | _pending_ | — |
| 1J | **Stage 1J complete** | _pending_ | _pending_ | — |
