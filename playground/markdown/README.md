# Markdown Playground — o2-scalpel E2E fixture workspace

This is the baseline Markdown workspace used by the o2-scalpel Markdown E2E
test suite (v1.3-D+).

> **DO NOT hand-edit these source files without updating the E2E
> assertions.** The test suite asserts on specific heading names, file paths,
> and link targets that match the baseline exactly. If you change the
> baseline, update the corresponding test in
> `vendor/serena/test/e2e/test_e2e_playground_markdown.py` in the same
> commit.
>
> The E2E suite refactors a **clone** of this directory (via
> `playground_markdown_root` fixture), never this source-controlled copy.

---

## Documents

| File | Purpose |
|------|---------|
| `INDEX.md` | Wiki-root with cross-file `[[wiki-links]]` (cross-file rename target). |
| `docs/index.md` | Main entry doc with references to other docs. |
| `docs/api.md` | Has heading "Authentication" (rename target) + multi-section content (split target). |
| `docs/tutorial.md` | Has "Getting Started" section to extract into its own file. |
| `docs/links.md` | Disorganized link list (organize target). |

---

## Facade targets at a glance

| Facade | File | Target |
|--------|------|--------|
| `scalpel_rename_heading` | `docs/api.md` | heading `Authentication` → `Auth`; cross-file `[[Authentication]]` in `INDEX.md` updated too |
| `scalpel_split_doc` | `docs/api.md` | split along H2 headings into sibling files |
| `scalpel_extract_section` | `docs/tutorial.md` | extract "Getting Started" section into `getting-started.md` |
| `scalpel_organize_links` | `docs/links.md` | sort + dedup disorganized wiki-links and markdown links |

---

## How the E2E suite uses this workspace

1. The pytest fixture `playground_markdown_root` calls `shutil.copytree` to
   clone the entire workspace into `pytest`'s `tmp_path` directory.

2. The test invokes a facade (e.g. `scalpel_rename_heading`) against the
   **clone** — never against this source-controlled directory.

3. After the refactor, the test asserts that files changed, that the
   applied payload carries `"applied": true`, and optionally verifies
   that cross-file links were updated correctly.
