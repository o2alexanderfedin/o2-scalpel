---
title: Scalpel-vs-Serena Routing Fixes — Executable Plan
date: 2026-05-01
author: AI Hive(R)
status: in-progress
input: ./REPORT.md
---

# Executable Plan: Close Scalpel-vs-Serena Routing Leaks

## TRIZ contradiction & resolution

**Contradiction:** Renaming every "Serena" → "Scalpel" risks (a) breaking fork-merge with `oraios/serena` upstream, (b) breaking existing user installs that invoke `uvx … serena …`, and (c) breaking `test_hooks.py:492`. Leaving "Serena" everywhere keeps the LLM mis-routed.

**Resolution (segmentation):** *Rename what the LLM reads at session start, leave what only the build system / fork-internal code reads.*
- Session-start prompts, manual title, system-prompt template → **rename** (LLM-facing).
- Console-script entrypoint → **add `scalpel` alias, keep `serena`** (build-system, back-compat).
- Internal Python identifiers (`serena.cli`, `serena_home_dir`, `is_serena_tool`) → **leave** (no LLM exposure).
- `vendor/serena/` submodule path, `.serena/` config dir → **defer** (large blast radius, LLM-routing benefit is perceptual only).

## Phase A — Repo-level fixes (this repo, immediate)

| # | Action | File | Closes |
|---|---|---|---|
| A1 | Add §"Tool routing (Scalpel vs Serena primitives)" to project CLAUDE.md | `CLAUDE.md` | M2 |
| A2 | Enable `o2-scalpel-rust` and `o2-scalpel-markdown` in dogfood settings | `.claude/settings.local.json` | M1 |
| A3 | Fix stale repo name | `CHANGELOG.md:76` | L4 |
| A4 | Add "superseded" status banners | `docs/research/2026-04-24-dx-facades-brief.md`, `docs/research/2026-04-24-serena-architecture-brief.md` | L1, L2 |
| A5 | Add stale-version banner to install.md | `docs/install.md` | M3 (partial) |

## Phase B — Engine-side fixes (vendor/serena/ submodule)

| # | Action | File | Closes |
|---|---|---|---|
| B1 | Rename "Serena Instructions Manual" → "Scalpel Tool Manual" | 7 source files (workflow_tools.py, config_tools.py, hooks.py, agent.py, system_prompt.yml, project.template.yml) | H1 |
| B2 | Update test assertion to match new string | `test/serena/test_hooks.py:492` | H1 (test) |
| B3 | Update 4 fixture `.serena/project.yml` files (comments only — search/replace) | `test/resources/repos/{python,clojure,elixir,swift}/test_repo/.serena/project.yml:87` | H1 (fixtures) |
| B4 | Append routing guidance to system_prompt.yml | `src/serena/resources/config/prompt_templates/system_prompt.yml` | M2 (engine-side) |
| B5 | Add `scalpel` script alias in pyproject.toml (keep `serena`) | `vendor/serena/pyproject.toml:75-78` | H2 (alias) |
| B6 | Verify drift-CI test still passes | run `pytest test/serena/tools/test_docstring_convention.py` | regression check |
| B7 | Commit + push submodule, update parent submodule pointer | `vendor/serena` + parent | shipping |

## Phase C — Deferred (out of scope for this PR)

- Regenerate all 23 `.mcp.json` to use `scalpel` alias instead of `serena`. Defer until B5 is published and `uvx --from … scalpel start-mcp-server` is verified working from a fresh checkout. Not blocking — `serena` keeps working.
- Refresh `docs/install.md` to v1.7+ (M3 full fix). Own follow-up; touches lots of stale content.
- Rename submodule `vendor/serena/` → `vendor/o2-scalpel-engine/`. Touches ~50 sites; LLM-routing benefit is perceptual only post-Phase-A/B; large surface.
- L5 rename-facade consistency cleanup. Engine-catalog data, separate task.

## Verification (per phase)

**Phase A:**
- `git diff CLAUDE.md` shows the new "Tool routing" section before "graphify".
- `cat .claude/settings.local.json` has 3 enabled plugins.
- `grep -n "o2alexanderfedin/serena" CHANGELOG.md` returns no hits (or only inside frozen historical lines we wrote in the past — verify line 76 specifically).
- `head -5 docs/research/2026-04-24-dx-facades-brief.md` shows the superseded banner.
- `head -10 docs/install.md` shows the stale-version banner.

**Phase B:**
- `grep -rin "Serena Instructions Manual" vendor/serena/src/` → 0 hits.
- `grep -rin "Scalpel Tool Manual" vendor/serena/src/` → ≥7 hits.
- `grep -rin "Serena Instructions Manual" vendor/serena/test/` → 0 hits in code (fixture YAML comments may remain — those are non-functional).
- `pytest vendor/serena/test/serena/test_hooks.py::TestSessionStartActivateProjectHook` passes.
- `pytest vendor/serena/test/serena/tools/test_docstring_convention.py` passes (no regression on PREFERRED:/FALLBACK:).
- `grep "^scalpel" vendor/serena/pyproject.toml` shows the new alias under `[project.scripts]`.
- `cd vendor/serena && uv tool install -e . && scalpel --help` (or `uvx --from . scalpel --help`) prints the same help as `serena --help`.

## Commit policy

One commit per phase milestone:
1. Phase A complete (5 files in main repo).
2. Phase B complete (engine submodule, then submodule-pointer bump in parent).

Each commit message documents what changed and quotes the leak ID(s) it closes (H1/H2/M1/...).
