#!/bin/sh
# SessionStart hook for o2-scalpel-ocaml - verifies LSP server is reachable.
set -eu

if ! command -v ocamllsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "ocamllsp" >&2
  printf 'Install hint: %s\n' "opam install ocaml-lsp-server  # requires opam + an active switch" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "ocamllsp" "ocaml"
