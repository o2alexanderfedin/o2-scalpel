"""Baseline tests for playground/python — must pass on unmodified source.

These tests serve two purposes:
1. Verify the playground is a healthy baseline before any E2E refactoring.
2. Provide a post-refactor smoke signal: the E2E suite optionally re-runs
   ``python -m pytest tests/`` after applying facades and asserts exit 0.

DO NOT modify these tests without updating the E2E assertions in
``vendor/serena/test/e2e/test_e2e_playground_python.py``.
"""

from __future__ import annotations

import pytest

from calc.ast import Add, Num, Sub
from calc.eval import evaluate
from calc.parser import parse_expr
from lints.core import report, sum_helper


# ---------------------------------------------------------------------------
# calc.ast
# ---------------------------------------------------------------------------


class TestAstNodes:
    def test_num_holds_value(self) -> None:
        node = Num(42)
        assert node.value == 42

    def test_add_holds_children(self) -> None:
        node = Add(Num(1), Num(2))
        assert node.left == Num(1)
        assert node.right == Num(2)

    def test_sub_holds_children(self) -> None:
        node = Sub(Num(5), Num(3))
        assert node.left == Num(5)
        assert node.right == Num(3)

    def test_num_frozen_dataclass(self) -> None:
        node = Num(7)
        with pytest.raises(Exception):
            node.value = 9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# calc.parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_parse_integer_literal(self) -> None:
        result = parse_expr("5")
        assert result == Num(5)

    def test_parse_addition(self) -> None:
        result = parse_expr("1+2")
        assert result == Add(Num(1), Num(2))

    def test_parse_subtraction(self) -> None:
        result = parse_expr("5-3")
        assert result == Sub(Num(5), Num(3))

    def test_parse_with_spaces(self) -> None:
        result = parse_expr(" 3 + 4 ")
        assert result == Add(Num(3), Num(4))


# ---------------------------------------------------------------------------
# calc.eval
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_evaluate_literal(self) -> None:
        assert evaluate(Num(7)) == 7

    def test_evaluate_addition(self) -> None:
        assert evaluate(Add(Num(1), Num(2))) == 3

    def test_evaluate_subtraction(self) -> None:
        assert evaluate(Sub(Num(5), Num(3))) == 2

    def test_evaluate_nested(self) -> None:
        # (1 + 2) + 3 = 6
        assert evaluate(Add(Add(Num(1), Num(2)), Num(3))) == 6

    def test_parse_and_evaluate_roundtrip(self) -> None:
        assert evaluate(parse_expr("3+4")) == 7


# ---------------------------------------------------------------------------
# lints.core
# ---------------------------------------------------------------------------


class TestLintsCore:
    def test_report_sums_items(self) -> None:
        assert report([1, 2, 3]) == 6

    def test_report_empty(self) -> None:
        assert report([]) == 0

    def test_sum_helper_directly(self) -> None:
        assert sum_helper([10, 20]) == 30
