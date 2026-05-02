---
title: Scalpel-vs-Serena Routing Audit
date: 2026-05-01
author: AI Hive(R)
status: live
scope: |
  Audit every prompt, trigger, hook, and config in the repo (and vendored engine)
  that could route the LLM to "Serena" instead of "o2-scalpel".
---

# Scalpel-vs-Serena Routing Audit — Consolidated Report

## TL;DR

The routing policy is correctly **machine-enforced** at the tool-docstring layer: 46/46 `Scalpel*Tool` classes carry the `PREFERRED:`/`FALLBACK:` opener, drift-CI gates that, and the v1.5-P3 spec is authoritative. **Where routing leaks today is at session-entry points the policy doesn't reach** — the engine MCP server greets every session with the literal string "Serena Instructions Manual", the engine's `pyproject.toml` console-script entrypoint is `serena` (which propagates into all 23 published `.mcp.json` files), the project `CLAUDE.md` is silent on tool routing, and only one of the 23 plugins is enabled by default in this dogfood repo.

The plugin trees themselves are clean (all 67 skill descriptions point at `scalpel_*` facades, all 23 hooks emit `scalpel: <lsp> ready`, all 23 READMEs market as "Scalpel for X"). No live doc actively prescribes Serena tools — at worst a few 2026-04-24 specialist briefs read as "use Serena tools as fallback" without a superseded banner.

| Severity | Count | Locus |
|---|---|---|
| HIGH | 2 | engine `initial_instructions` priming + entrypoint name |
| MEDIUM | 4 | settings.local.json, CLAUDE.md routing silence, install.md staleness, install.md binary name |
| LOW | 5 | 3 research-brief banners, CHANGELOG.md line 76, rename-facade naming inconsistency |

---

## Findings (consolidated)

### H1 — MCP servers prime every session with "Serena Instructions Manual"

**Source files (engine, in `vendor/serena/src/serena/`):**
- `tools/workflow_tools.py:37,62,70` — `initial_instructions` tool body
- `tools/config_tools.py:38` — config-tool follow-up
- `agent.py:904` — agent docstring
- `hooks.py:343` — SessionStart hook context
- `resources/config/prompt_templates/system_prompt.yml:6,60` — the literal CRITICAL bullet the LLM sees
- `resources/project.template.yml:86` — template comment

**Why it routes to Serena:** The MCP server `instructions` field is the very first thing the model sees on session start. It says "CRITICAL: Before starting to work on a coding task, call the `initial_instructions` tool to read the **'Serena Instructions Manual'**." This brands the entire toolset as Serena's before any tool docstring is read. The `PREFERRED:`/`FALLBACK:` opener on `Scalpel*Tool` docstrings is undermined because by the time the LLM inspects them it has already loaded a Serena-branded manual.

**Test that asserts the brand:** `test/serena/test_hooks.py:492` — `assert "Serena Instructions Manual" in context`. Must be updated when the string is renamed.

### H2 — `pyproject.toml` exposes `serena` as the console-script entrypoint

**Source:** `vendor/serena/pyproject.toml:75-78`:
```toml
[project.scripts]
o2-scalpel-newplugin = "serena.refactoring.cli_newplugin:main"
serena = "serena.cli:top_level"
serena-hooks = "serena.hooks:hook_commands"
```

**Why it routes to Serena:** Every published Scalpel plugin's `.mcp.json` ships `"args": ["--from", "git+...", "serena", "start-mcp-server", "--server-name", "scalpel-<lang>"]`. The literal string `"serena"` is at args index 2 in 23 of 23 plugins. Anyone reading `.mcp.json` to debug, anyone whose tooling logs argv, anyone who runs `uvx --from … serena --help` is told the tool is "Serena". This contradicts the rebrand at every install.

### M1 — `.claude/settings.local.json` enables only `o2-scalpel-python`

```json
"enabledPlugins": { "o2-scalpel-python@o2-scalpel": true }
```
For Markdown / Rust / any-other-language work in this dogfood repo, no Scalpel plugin is loaded — so the engine's generic primitives win without a Scalpel facade in sight. Inverts the intended routing in this repo.

### M2 — Project `CLAUDE.md` is silent on Scalpel-vs-Serena routing

The `PREFERRED:`/`FALLBACK:` convention exists only inside per-tool docstrings. There is zero project-level instruction telling the LLM to prefer Scalpel facades — combined with H1, the model has no counter-pressure to the engine's Serena-branded greeting.

### M3 — `docs/install.md` is anchored at v0.2.0 (5+ versions stale)

References `serena-mcp` binary, "marketplace publication is v1.1 work", and a 33-tool surface. The model is currently at v1.7+ with the marketplace published and 36 facades. First-time users read this doc and pattern-match the running server as "Serena MCP".

### M4 — `docs/install.md` references `vendor/serena/` despite the GH repo being renamed

The GitHub repo was renamed `o2alexanderfedin/serena → o2-scalpel-engine` on 2026-04-25, but the local submodule path remains `vendor/serena/` and install.md (lines 41, 60–61, 78, 149) directs users to it. Filesystem path is correct; the perceptual concern is the brand anchor.

### L1-L3 — Three 2026-04-24 research briefs read as "use Serena tools as fallback"

- `docs/research/2026-04-24-dx-facades-brief.md:136,204`
- `docs/research/2026-04-24-serena-architecture-brief.md:11,79,83,113`
- (third brief)

Pre-fork specialist research, superseded by `docs/superpowers/specs/2026-04-29-lsp-feature-coverage-spec.md` §5 — but no "superseded" banner. An LLM scanning `docs/` could over-index on these.

### L4 — `CHANGELOG.md:76` references `o2alexanderfedin/serena`

Should be `o2alexanderfedin/o2-scalpel-engine` per the 2026-04-25 rename.

### L5 — Rename-facade naming inconsistency across plugins

- `o2-scalpel-python`, `o2-scalpel-rust` use `scalpel_rename_symbol`
- `o2-scalpel-prolog` uses `scalpel_rename_predicate`
- All 17 other languages use `scalpel_rename`

Not a Serena leak; an autocomplete-prediction degradation. Engine-catalog data, not generator-template.

---

## What's working

- **`PREFERRED:`/`FALLBACK:` docstring convention** — 46/46 Scalpel tools carry the opener; drift-CI test at `vendor/serena/test/serena/tools/test_docstring_convention.py` enforces.
- **Marketplace branding** — every `.claude-plugin/marketplace.json` entry says "Scalpel refactor MCP server".
- **Plugin trees** — 67 skill descriptions, 23 READMEs, 23 SessionStart hooks, 23 plugin.json descriptions all consistently route to/announce Scalpel facades.
- **MCP server names** — `scalpel-rust`, `scalpel-python`, etc. The wire-level identity is correct.
- **Authoritative spec** — `docs/superpowers/specs/2026-04-29-lsp-feature-coverage-spec.md` §3, §5 codify the routing policy.

---

## Source audit reports

The four parallel audit subagents produced detailed findings at:
- [.planning/scalpel-vs-serena/01-configs.md](../../../.planning/scalpel-vs-serena/01-configs.md) — root configs
- [.planning/scalpel-vs-serena/02-plugins.md](../../../.planning/scalpel-vs-serena/02-plugins.md) — 23 plugin trees
- [.planning/scalpel-vs-serena/04-docs.md](../../../.planning/scalpel-vs-serena/04-docs.md) — docs/ tree
- (engine audit `03-engine.md` was running when the audit subagent quota resolved; its key findings are confirmed by direct grep — listed above as H1 and H2)

## Remediation plan

See [PLAN.md](./PLAN.md) for the executable fix plan with ordered tasks and verification.
