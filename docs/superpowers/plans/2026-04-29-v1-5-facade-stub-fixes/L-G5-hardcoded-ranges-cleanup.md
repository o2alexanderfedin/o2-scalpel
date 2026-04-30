# Leaf L-G5 — Hardcoded `(0,0)→(0,0)` cleanup (residual sites)

**Goal.** Sweep up the `(0,0)→(0,0)` LSP range pattern in any sites NOT already closed by Wave 2 fix leaves. After Wave 2 lands, the residual set should be:

| Site | Closed by | Status entering G5 |
|---|---|---|
| `_split_rust` (L330-335) | L-G3a | ✓ closed |
| `_split_python` is symbolic | n/a (uses rope.refactor.move) | ✓ never had this bug |
| `imports_organize` (L991-995) | L-G4-9 (uses `compute_file_range`) | ✓ closed |
| `fix_lints` (L2228-2232) | L-G4-8 (uses `compute_file_range`) | ✓ closed |
| `inline` fallback (L627) | L-G4-7 (resolves via name_path / references) | ✓ closed |
| `_java_generate_dispatch` (L3011-3019) | L-G6 ME-6 sub-task | ✓ closed |

**This leaf becomes a verifier-only no-code-change leaf if all of the above land cleanly.** That's the desired outcome — Wave 2 sweeps the bug at the source. G5 exists as a safety net: if any of the above leaves left a `(0,0)→(0,0)` literal in code, this leaf catches and removes it. The grep regression below is the gate.

If during Wave 2 execution any leaf scopes-down its range fix (e.g. G4-8 lands `rules` honor but defers the file-range cleanup), G5 picks up that residue here.

**Source spec.** § HI-13 (lines 111-113).

**Author.** AI Hive®.

## Files to modify (potentially)

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit any residual `(0,0)→(0,0)` site | 0-30 |
| `vendor/serena/test/spikes/test_v1_5_g5_no_hardcoded_zero_range.py` | NEW — grep-style regression test that the source contains zero `start={"line":0,"character":0}, end={"line":0,"character":0}` literal pairs in production code paths | ~80 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g5_no_hardcoded_zero_range.py`:

```python
"""v1.5 G5 — regression guard against (0,0)→(0,0) LSP range literals.

Asserts that scalpel_facades.py contains no `start={"line":0,"character":0},
end={"line":0,"character":0}` adjacency in production code paths (test
fixtures and docstrings excepted).

This is the catch-net for HI-13. By the time G5 runs, Wave 2 leaves
should have closed every site listed in the spec; this test verifies
that claim and fails loudly if any literal slipped through.
"""
from __future__ import annotations

import re
from pathlib import Path

FACADE = Path(__file__).resolve().parents[2] / "src" / "serena" / "tools" / "scalpel_facades.py"

# Two near-adjacent zero positions form the bug pattern. We scan for the
# literal that appears in `merge_code_actions(...)` calls.
_PATTERN = re.compile(
    r'start\s*=\s*\{\s*"line"\s*:\s*0\s*,\s*"character"\s*:\s*0\s*\}'
    r'\s*,\s*'
    r'end\s*=\s*\{\s*"line"\s*:\s*0\s*,\s*"character"\s*:\s*0\s*\}',
    re.MULTILINE | re.DOTALL,
)


def test_no_hardcoded_zero_range_in_facades():
    text = FACADE.read_text(encoding="utf-8")
    # Strip docstrings and #-comments to avoid false-positives (the spec
    # citations and our own commit-message drafts may legitimately quote
    # the bad pattern). For test simplicity, drop triple-quoted blocks
    # and #-line comments.
    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", text)
    no_comments = re.sub(r"^\s*#.*$", "", no_docstrings, flags=re.MULTILINE)
    matches = _PATTERN.findall(no_comments)
    assert matches == [], (
        f"Found {len(matches)} hardcoded (0,0)→(0,0) range(s); "
        f"replace with compute_file_range or a real symbol range:\n{matches}"
    )
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g5_no_hardcoded_zero_range.py -x`. After Wave 2 lands cleanly, this test should already PASS — at which point G5 is just landing the regression guard. If Wave 2 left any site, the test FAILS and G5 fixes the residue.

## Implementation steps

1. **Run the test.** If it PASSES, no code change needed — proceed directly to step 4 (commit just the test).
2. **If FAILS:** identify each residual site and replace with `compute_file_range(file)` (for whole-file ranges) or `coord.find_symbol_range(...)` (for symbol-scoped ranges).
3. **Re-run tests** until green.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g5_no_hardcoded_zero_range.py -x

# Ensure no Wave-2-touched test was regressed:
uv run pytest vendor/serena/test/spikes/test_stage_2a_t6_imports_organize.py \
                vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py \
                vendor/serena/test/spikes/test_stage_2a_t4_inline.py -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
test(facade-ranges): regression guard against hardcoded (0,0)→(0,0) ranges (HI-13)

Catch-net for HI-13. After Wave 2 (G3a, G4-7/8/9, G6 ME-6) closed every
spec-cited site, this test asserts no literal (0,0) adjacency remains
in scalpel_facades.py production paths. Future regressions surface
loudly via this test.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** the regex misses a unicode-spacing variant. Mitigation: pre-compile is `\s*` permissive.
- **Risk:** a legitimate empty-file edge case lands a (0,0)→(0,0) — `compute_file_range` already returns this for an empty file but only when called via the helper, not as a literal. The grep won't fire on `compute_file_range(...)` returns; it only fires on the literal pattern.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G4-7, L-G4-8, L-G4-9 (Wave 2 leaves that close the residual sites).
- **Soft:** L-G6 (Java fallback site closed there).
- **Blocks:** none — terminal regression guard.

---

**Author:** AI Hive®.
