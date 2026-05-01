#!/bin/sh
# SessionStart hook for o2-scalpel-clojure - verifies LSP server is reachable.
set -eu

if ! command -v clojure-lsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "clojure-lsp" >&2
  printf 'Install hint: %s\n' "brew install clojure-lsp/brew/clojure-lsp-native  # macOS; binary at github.com/clojure-lsp/clojure-lsp/releases" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "clojure-lsp" "clojure"
