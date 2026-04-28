"""AST node types for the calc expression evaluator.

This module is the ``scalpel_split_file`` target: the E2E test splits
``Expr``, ``Num``, and ``Add`` into separate sibling files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


# --- scalpel_split_file target: split each cluster into its own file -------


@dataclass(frozen=True)
class Num:
    """Integer literal AST node."""

    value: int


@dataclass(frozen=True)
class Add:
    """Binary addition AST node."""

    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Sub:
    """Binary subtraction AST node."""

    left: "Expr"
    right: "Expr"


Expr = Union[Num, Add, Sub]
