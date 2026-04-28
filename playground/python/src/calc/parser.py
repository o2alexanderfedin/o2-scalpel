"""Expression parser for the calc playground.

``parse_expr`` is the ``scalpel_rename`` target: the E2E test renames it
to ``parse_expression`` across the workspace.
"""

from __future__ import annotations

from calc.ast import Add, Expr, Num, Sub


def parse_expr(text: str) -> Expr:
    """Parse a simple arithmetic expression string into an Expr tree.

    Supports ``+`` and ``-`` binary operators and integer literals.
    This is the rename target for ``scalpel_rename``: the E2E test
    renames ``parse_expr`` → ``parse_expression`` across the workspace.
    """
    s = text.strip()
    for op_char, ctor in (("+", Add), ("-", Sub)):
        idx = s.rfind(op_char)
        if idx > 0:
            return ctor(parse_expr(s[:idx]), parse_expr(s[idx + 1:]))
    return Num(int(s))
