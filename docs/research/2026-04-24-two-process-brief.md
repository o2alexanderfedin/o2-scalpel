# Two-LSP-Process Problem — Resolution Research

Specialist A3 — established solutions for running two LSP servers against one workspace simultaneously (scalpel MCP + Claude Code's umbrella LSP).

---

## Q1 — Multi-client support per language server

| Server          | Built-in multi-client / daemon?                                                                                                     | Transport options                          | Maturity  | Verdict for shared instance |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------- | --------------------------- |
| **rust-analyzer** | **No.** No daemon, no multi-client, no TCP/socket transport. Stdio only. Persistent on-disk cache is open feature request since 2020 (issue [#4712](https://github.com/rust-lang/rust-analyzer/issues/4712), labeled `S-unactionable`, `E-hard`). Per-instance cold-start of std + deps every spawn. | stdio                                      | mature    | **Impossible today.**       |
| **gopls**         | **Yes.** `gopls -remote=auto` is a documented daemon that "starts a single machine-wide process that manages multiple workspace views across projects" (golang/go [#78668](https://github.com/golang/go/issues/78668)). LSP side already handles multi-workspace via `DidChangeWorkspaceFolders`. *Caveat:* `gopls mcp` mode locks `os.Getwd()` at startup — the multi-workspace MCP-over-daemon work is open. | stdio + `-listen` socket / shared daemon  | mature    | **Yes, well-supported.**    |
| **clangd**        | **Partial.** `--index-file=` lets multiple clangd instances point at the same pre-built static index ([clangd indexing docs](https://clangd.llvm.org/design/indexing)). No daemon mode for live state, but **remote index** server allows centralized index serving multiple clients. Background `.cache/clangd/index/` is per-instance. | stdio + remote-index gRPC                  | mature    | **Index sharing only.**     |
| **pyright / basedpyright** | **No** daemon / multi-client. Spawn is fast (sub-second) and memory modest (~300 MB). | stdio | mature | **Don't bother sharing.**   |
| **pylsp**         | No daemon. Stdio only.                                                                                                             | stdio                                      | mature    | Don't bother sharing.       |
| **ty / pyrefly**  | No daemon (early-stage Astral / Meta type-checkers).                                                                              | stdio                                      | early     | N/A                         |

`tower-lsp` and `lsp-server` are *single-client* server frameworks (one stream-pair per process). Neither library exposes multi-client support — multiplexing must be added externally.

---

## Q2 — Off-the-shelf LSP proxies / multiplexers

GitHub search for `lsp multiplexer` / `lsp proxy` returns ~15 projects. Most are **server-aggregation** multiplexers (one client → many servers), **not** the **client-aggregation** multiplexer (many clients → one server) we need.

| Tool                                                                                  | Direction                          | Stars | Lang   | Maturity      | Notes |
| ------------------------------------------------------------------------------------- | ---------------------------------- | ----- | ------ | ------------- | ----- |
| [`thefrontside/lspx`](https://github.com/thefrontside/lspx)                           | Many servers → one client          | 113   | TS     | active        | Wrong direction. |
| [`garyo/lsp-multiplexer`](https://github.com/garyo/lsp-multiplexer)                   | Many servers → one client          | 12    | Python | experimental  | Wrong direction. |
| [`joaotavora/lsplex`](https://github.com/joaotavora/lsplex)                           | Eglot-focused proxy                | 16    | C++    | **archived 2025-12**, "doesn't really do anything useful yet" | Dead. |
| [`ifiokjr/lspee`](https://github.com/ifiokjr/lspee)                                   | **Many clients → one server (per-workspace pool, idle eviction)** — agents-focused, NDJSON-over-Unix-socket, Rust | 0    | Rust   | pre-release, no tags | **Architecturally exactly right. Not production-ready.** |
| [`K-dash/typemux-cc`](https://github.com/K-dash/typemux-cc)                           | Claude Code plugin: routes Python type-checker requests to per-`.venv` backend pool | 9 | Rust | early but functional | Python-only, scope different (per-venv routing, not per-workspace sharing). |
| [`LuciusChen/lsp-mux`](https://github.com/LuciusChen/lsp-mux), `lsp-composer`, `alligator` | server-aggregation, Emacs-flavored | <5   | mixed  | toy           | Wrong direction. |

JetBrains / VS Code **do not** share LSP across processes. VS Code's [LSIF (Language Server Index Format)](https://microsoft.github.io/language-server-protocol/overviews/lsif/overview/) serializes navigation indexes (defs/refs) for read-only consumption — useful as inspiration but not a live-LSP substitute.

**Conclusion:** there is **no production-grade, polyglot, many-clients-to-one-LSP-server multiplexer**. `lspee` is the closest shape but green-field.

---

## Q3 — Index-only sharing (no live multiplex)

| Server          | Disk-cache / index-share trick                                                                | Helps avoid 2× indexing? | Risk |
| --------------- | --------------------------------------------------------------------------------------------- | ------------------------ | ---- |
| **rust-analyzer** | None today — no on-disk index. `cargo.targetDir` shares `target/` build artifacts across instances. | No (only saves cargo build). | **Lock contention** if both run `cargo check` — confirmed by the [config docs](https://rust-analyzer.github.io/book/configuration.html) that `cargo.targetDir` exists *precisely* to avoid Cargo.lock contention with the IDE's own builds. Two rust-analyzers writing to the same dir reintroduces the problem. |
| **clangd**        | `clangd-indexer` pre-builds a static index → both instances `--index-file=path.idx`. Or run a **remote-index server**. | **Yes, mostly.** Static portion is shared; per-edit live index still per-instance. | Low. |
| **gopls**         | Module/build cache (`GOMODCACHE`, `GOCACHE`) already shared by default at `$HOME` level.       | Partly.                  | Low. |
| **pyright**       | Cheap to spawn — not worth optimizing.                                                        | N/A                       | N/A  |

Rust is the worst case: **no disk-share avenue exists in 2026**. Both processes pay the full 4–8 GB / 3–10-min cold-start tax.

---

## Q4 — Acceptable degradation strategies (when sharing impossible)

For Rust specifically, since neither (Q1) nor (Q3) yield a fix:

1. **Lazy-spawn on first call** — already proposed in scalpel design; defers cost until the agent actually needs precision.
2. **Idle-shutdown** — kill scalpel's rust-analyzer after N minutes idle; respawn on next call (8-min cold-start is the penalty). Good for long Q&A sessions where LSP isn't repeatedly hit.
3. **Reduced-capability spawn** — pass `cargo.buildScripts.enable=false`, `procMacro.enable=false`, `checkOnSave.enable=false`, `cargo.allTargets=false`. Cuts memory ~40% and skips proc-macro expansion. Lossy: misses macro-generated symbols (a real concern in 227-crate workspaces).
4. **Per-call ephemeral spawn** — kill after each request. Effectively unusable for rust-analyzer (cold start dominates), tolerable for pyright.
5. **Separate `cargo.targetDir`** for scalpel's RA from CC's RA — pays 2× disk but **avoids lock contention** (mandatory if both are live).
6. **Detect-and-skip** — if `CLAUDE_PROJECT_DIR` matches and CC's LSP is already attached (per [issue #50224](https://github.com/anthropics/claude-code/issues/50224) showing per-session LSP), scalpel can route reads through CC's tools and only spawn its own RA when scalpel-specific writes need stale-free analysis.

---

## Q5 — Anthropic native-LSP-write roadmap signal

- Claude Code shipped **read-only LSP** (`go-to-def`, `references`, `diagnostics`, `hover`) in **v2.0.74** (announced Dec 2025 per HN [thread 46355165](https://news.ycombinator.com/item?id=46355165)).
- Issue [anthropics/claude-code#32502](https://github.com/anthropics/claude-code/issues/32502) explicitly requests `textDocument/rename`, `codeAction`, `typeHierarchy`, `signatureHelp` — **marked `stale`**, no assignee, no ETA.
- Active LSP bugs ([#50224 worktree leak](https://github.com/anthropics/claude-code/issues/50224), [#50271 pyright cache](https://github.com/anthropics/claude-code/issues/50271), [#42013 hang](https://github.com/anthropics/claude-code/issues/42013)) suggest Anthropic is **fixing v1 LSP-read**, not yet building LSP-write. HN commentary calls the feature "still fairly jank" and "under-resourced."
- Realistic horizon: **6–18 months** before LSP-write (rename / code-action) lands and is stable enough to obsolete scalpel's structural-edit niche. The two-process tax is **not short-lived enough to ignore**.

---

## Recommendation

**Primary: Strategy-pattern per-language, with rust-analyzer treated as the worst-case outlier.**

| Language     | Strategy                                                                                                                                                                                                              |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rust**     | Lazy-spawn on first scalpel call, **separate `cargo.targetDir=target/scalpel-ra`** to avoid lock contention with CC, idle-shutdown after 10 min, reduced-capability flags off (`procMacro=true` is non-negotiable on macro-heavy codebases). Accept the 4–8 GB tax while active. |
| **Go**       | Connect to `gopls -remote=auto` daemon if running; otherwise spawn fresh. Eliminates 2× cost when the user already has a daemon. (Watch golang/go#78668 for MCP-multi-workspace fix.)                                |
| **C/C++**    | Pre-run `clangd-indexer` once, point both clangds at the same `--index-file`. Eliminates 2× indexing; live state still doubles but is small.                                                                          |
| **Python**   | No optimization — pyright spawn is ~300 MB / <1 s. Don't bother. (Optionally adopt `typemux-cc` model if `.venv` confusion appears.)                                                                                  |
| **Other**    | Lazy + idle-shutdown defaults.                                                                                                                                                                                        |

**Honest assessment:** **Known-leaky workaround, not a clean solution.** A polyglot many-clients-to-one-server multiplexer doesn't exist in maintained form; `lspee` is the right shape but pre-1.0. Building our own is out of scope for scalpel — capability negotiation, per-client `didOpen` ref-counting, `workspace/configuration` divergence, and progress-token collisions are subtle multi-month work.

**For Rust on a 227-crate workspace:** the two-process tax is real (~6–8 GB extra RAM, ~5 min extra cold-start). The only 2026 mitigations are *lazy + idle-shutdown + separate `targetDir`*. Acceptable on 32–64 GB dev machines, **not** on 16 GB laptops — expose `scalpel.lsp.rust.lazy=true` (default) so small-machine users can opt out and rely on CC's LSP for reads.

When Anthropic ships LSP-write (likely 2026 H2 / 2027 H1), scalpel's RA can retire. Until then, lazy-spawn + segregated targetDir + idle-shutdown is the defensible answer.

---

### Sources

- [rust-analyzer #4712 — Persistent caches](https://github.com/rust-lang/rust-analyzer/issues/4712)
- [rust-analyzer config docs](https://rust-analyzer.github.io/book/configuration.html)
- [golang/go #78668 — gopls MCP multi-workspace daemon](https://github.com/golang/go/issues/78668)
- [clangd indexing design](https://clangd.llvm.org/design/indexing)
- [thefrontside/lspx](https://github.com/thefrontside/lspx)
- [ifiokjr/lspee](https://github.com/ifiokjr/lspee)
- [K-dash/typemux-cc](https://github.com/K-dash/typemux-cc)
- [joaotavora/lsplex](https://github.com/joaotavora/lsplex) (archived)
- [garyo/lsp-multiplexer](https://github.com/garyo/lsp-multiplexer)
- [anthropics/claude-code #32502 — Expand LSP tool methods](https://github.com/anthropics/claude-code/issues/32502)
- [anthropics/claude-code #50224 — LSP diagnostics leak across worktrees](https://github.com/anthropics/claude-code/issues/50224)
- [anthropics/claude-code #50271 — pyright cross-module cache](https://github.com/anthropics/claude-code/issues/50271)
- [HN: Claude Code gets native LSP support](https://news.ycombinator.com/item?id=46355165)
