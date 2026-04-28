"""Lint-pattern fixture for ``scalpel_inline``.

``report`` calls ``sum_helper`` exactly once.  The E2E test inlines
``sum_helper`` at its single call site, collapsing the two functions into
one.  After inlining, ``sum_helper`` is removed and ``report``'s body
becomes ``sum(items)`` directly.
"""

from __future__ import annotations

from typing import Sequence


def report(items: Sequence[int]) -> int:
    """Return the sum of *items* by delegating to ``sum_helper``.

    ``sum_helper`` is the inline target: after ``scalpel_inline``, this
    function's body becomes ``sum(items)`` directly.
    """
    return sum_helper(items)


def sum_helper(items: Sequence[int]) -> int:
    """Single-use helper — the inline candidate.

    Called only by ``report``; the E2E test inlines it there and removes
    this definition.
    """
    return sum(items)
