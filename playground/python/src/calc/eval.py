"""Expression evaluator for the calc playground.

Two facade targets live here:

1. ``scalpel_extract``: the expression ``a + b`` inside ``evaluate`` is the
   extract candidate.  The E2E test extracts it into a helper ``add_values``.

2. ``scalpel_imports_organize``: the imports below are intentionally
   disorganized (stdlib mixed with local, unsorted) so the E2E test can
   exercise ``scalpel_imports_organize``.
"""

from __future__ import annotations

# disorganized imports — scalpel_imports_organize target
from calc.ast import Sub
import sys
from calc.ast import Add, Num, Expr


def evaluate(expr: Expr) -> int:
    """Evaluate an Expr tree and return its integer value.

    The ``a + b`` expression inside the Add branch is the
    ``scalpel_extract`` target: the E2E test extracts it into
    a helper function ``add_values(a, b)``.
    """
    if isinstance(expr, Num):
        return expr.value
    if isinstance(expr, Add):
        a = evaluate(expr.left)
        b = evaluate(expr.right)
        # extract candidate: pull `a + b` into helper `add_values`
        return a + b
    if isinstance(expr, Sub):
        return evaluate(expr.left) - evaluate(expr.right)
    raise TypeError(f"unknown expr type: {type(expr)!r}")


def _unused_sys_ref() -> str:
    """Reference sys to keep the import alive for the organize-imports test."""
    return sys.version
