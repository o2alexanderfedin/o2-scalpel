# License & Rename Feasibility — Boostvolt + Piebald

Date: 2026-04-24. Scope: can o2.services fork+rename `boostvolt/claude-code-lsps` and `Piebald-AI/claude-code-lsps` analogously to Serena?

---

## Boostvolt

### License: MIT

Confirmed: `vendor/claude-code-lsps-boostvolt/LICENSE.md` is verbatim MIT, `Copyright (c) 2025 Jan Kott`. Upstream `gh repo view --json licenseInfo` returns `{"key":"mit"}`.

### What MIT permits
Fork, modify, rename, redistribute (source or binary), sublicense, relicense the combined work (including proprietary), commercial use — all yes. The MIT notice + copyright must travel with the MIT-licensed portions. No explicit patent grant (a known MIT weakness vs Apache-2.0; rarely blocking for plugin manifests). Only mandatory obligation: preserve the copyright + permission notice in "all copies or substantial portions."

### Required attribution

Add to the renamed fork's `LICENSE` (or `LICENSES/MIT-boostvolt.txt`) — verbatim from upstream:

```
Portions of this work are derived from claude-code-lsps
(https://github.com/boostvolt/claude-code-lsps).

MIT License
Copyright (c) 2025 Jan Kott

[full MIT text — preserved verbatim from upstream LICENSE.md]
```

In the README, one credit line:

> Originally based on [claude-code-lsps](https://github.com/boostvolt/claude-code-lsps) by Jan Kott (MIT). Renamed and extended by O2.services.

### Trademark / branding

- "boostvolt" = GitHub handle of Jan Kott (individual). Not surfaced as a registered mark in USPTO/EUIPO TESS. Risk: low. Action: don't use "boostvolt" in our product name; don't imply endorsement.
- "Claude" and "Claude Code" are Anthropic marks. Do **not** put them in our renamed product name. Use a neutral name (`o2-lsp-marketplace`, `scalpel-lsps`).
- The string "claude-code-lsps" is descriptive and shared by both upstreams; forking it confers no mark on us.

### Verdict — Boostvolt: **GREEN**, proceed.

---

## Piebald

### License: NONE FOUND

Verified four ways:
- No `LICENSE`/`COPYING`/`NOTICE` at any depth in the local clone. Root has only `README.md`, `CLAUDE.md`, `.gitignore`, plugin dirs.
- `gh repo view Piebald-AI/claude-code-lsps --json licenseInfo` → `"licenseInfo": null`.
- `.claude-plugin/marketplace.json` has no top-level `license` field.
- Per-plugin `plugin.json` files do contain `"license": "MIT"` / `"Apache-2.0"` — but these describe the **underlying LSP binary** (clangd, rust-analyzer, etc.), not Piebald's own scaffolding code.

Owner per `marketplace.json`: **Piebald LLC** (`support@piebald.ai`) — a commercial entity actively promoting a paid product ("Piebald, the ultimate agentic AI developer experience").

### What "no license" legally means

Per GitHub's official documentation:

> "You're under no obligation to choose a license. However, without a license, the default copyright laws apply, meaning that you retain all rights to your source code and **no one may reproduce, distribute, or create derivative works from your work**."
>
> Source: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

Implications:
1. Default = "all rights reserved" by Piebald LLC.
2. Forking on github.com **is** permitted by GitHub TOS §D.5, which grants every user a license to fork and view public content **on the GitHub platform**.
3. Republishing the fork outside GitHub, renaming it, distributing via any other channel, or relicensing it is **NOT** permitted without express permission.
4. No reliable "implicit license" doctrine. Courts have inferred narrow licenses for the act of submitting PRs, which doesn't help redistribution.
5. The `"license": "MIT"` fields inside per-plugin `plugin.json` describe the **third-party LSP binaries** (clangd, rust-analyzer, etc.), not Piebald's manifest code itself.

### Trademark
- "Piebald" is a registered trade name for **Piebald LLC** (commercial product at piebald.ai). Even if we had a redistribution license, we would have to scrub all "Piebald" branding (logos, wordmark SVG, screenshots, discord/X links currently embedded in `README.md`).
- "Piebald-AI" is the GitHub org. Risk of trademark conflict: medium-high if we keep any branding. Risk if we strip it cleanly: low, but we still need a license to redistribute the underlying content.

### Options

| Option | Allowed? | Notes |
|---|---|---|
| Keep upstream as read-only submodule for private analysis | Yes (GitHub TOS) | No redistribution. |
| Fork on GitHub for private use | Yes | Same. |
| Rename + redistribute publicly | **No** | Requires explicit license. |
| Copy individual `plugin.json` entries verbatim into our marketplace | **No** | Still Piebald's copyrighted text. |
| Re-derive equivalent manifests clean-room from upstream LSP docs + Boostvolt's MIT template | Yes | Set of LSP servers is factual; `command`/`args`/`extensionToLanguage` is mechanical. Avoid copy-paste of Piebald's prose, descriptions, README, scripts. |
| Open a licensing inquiry issue and wait | Yes, in parallel | Zero cost. Best case: MIT/Apache added. Worst case: silence → fall back to clean-room. |

### Verdict — Piebald: **RED for redistribution, YELLOW for inspiration**

Do not rename and ship. Do open a licensing inquiry. In parallel, treat Piebald as a *catalog reference* — the list of supported languages and the choice of LSP binaries is uncopyrightable factual information; only the textual expression is protected.

---

## Practical recommendation for o2.scalpel design

1. **Boostvolt fork — proceed.** Rename to `o2-lsp-marketplace` (or similar non-Anthropic, non-Piebald name). Include the MIT attribution above in `LICENSE`. Add a `NOTICE` paragraph in README. Continue using as a submodule and ship publicly.
2. **Piebald fork — do NOT redistribute.** Keep the current submodule **only for private analysis** (allowed under GitHub TOS). Do not include it in any public release artifact, npm/cargo/pip package, or distributed marketplace JSON. Do not push our renamed copy to a public registry.
3. **Plan B for Piebald content** — for any LSP server that exists in Piebald but not Boostvolt (e.g. `ada-language-server`, `phpactor`, `texlab`, `metals`, `julia-lsp`, `kotlin-lsp`, `lean4-*`, `omnisharp`, `solidity-language-server`, `svelte`, `vue-volar`, `vtsls`), **clean-room re-author** the manifest using Boostvolt's MIT structure as the template and the upstream LSP project's own docs as the data source. Track each re-authored file with a commit message like `feat(lsp): add ada-language-server plugin (clean-room, no Piebald content)`.
4. **File a licensing inquiry** against `Piebald-AI/claude-code-lsps` (draft below). If they grant MIT/Apache-2.0, switch to direct fork + attribution. Track the issue ID; revisit before each public release.
5. **Submodule hygiene** — until Piebald licensing is resolved, mark `vendor/claude-code-lsps-piebald` in our repo's `README` as "private analysis only — not distributed" and exclude it from any release tarball/sdist.

---

## Draft licensing-inquiry issue for Piebald

Title: **Please add a LICENSE file**

Body:

> Hi Piebald team — thanks for publishing claude-code-lsps; the breadth of LSP coverage is great.
>
> We noticed the repository does not currently include a LICENSE file, and `gh repo view` reports no detected license. Per [GitHub's licensing docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), this defaults to "all rights reserved", which makes it difficult for downstream projects (including ours, an open-source C++ to Rust transpiler tooling project) to depend on or extend the marketplace.
>
> Would you consider adding a permissive license such as MIT or Apache-2.0? We'd be glad to open a PR adding the file if you tell us your preference. If MIT works, the canonical text would be:
>
> ```
> MIT License
> Copyright (c) 2025 Piebald LLC
> ...
> ```
>
> Either way, thank you for the work — and a clear license would let the community contribute back additional language plugins.

---

## Disclaimer

Engineering analysis by a non-lawyer reviewing public license texts and GitHub's published policies. **Not legal advice.** Before any commercial release of o2.scalpel that bundles or redistributes either upstream, have counsel review (a) the MIT attribution chain for Boostvolt, (b) the licensing status of any Piebald-derived content, and (c) the trademark posture of the renamed product (especially "Claude", "Claude Code", "Anthropic").
