"""Deterministic AST mutation engine.

Applies one small, realistic bug at a time to a Python module: the kind of
mistake a careless refactor (human or agent) plausibly introduces — a
boundary flipped, an operator swapped, a condition negated, an operand
order reversed, an off-by-one constant. Mutation is purely syntactic and
deterministic: the same source always yields the same numbered list of
candidate mutations in the same order, so `apply_mutation(source, i)` is
reproducible across machines and runs.
"""
from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from typing import Callable, Iterator, List, Tuple

NodeVisitor = Callable[[ast.AST], None]


class Rule:
    name: str = "rule"

    def matches(self, node: ast.AST) -> bool:
        raise NotImplementedError

    def variants(self, node: ast.AST) -> List[Tuple[str, NodeVisitor]]:
        """Return (variant_name, apply_in_place) pairs for this node."""
        raise NotImplementedError


class ComparisonOperatorSwap(Rule):
    name = "comparison_operator_swap"
    _swaps = {
        ast.Lt: ast.LtE, ast.LtE: ast.Lt,
        ast.Gt: ast.GtE, ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
    }

    def matches(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in self._swaps

    def variants(self, node: ast.Compare):
        new_op = self._swaps[type(node.ops[0])]

        def apply(n: ast.Compare = node, op=new_op):
            n.ops[0] = op()

        return [(f"{type(node.ops[0]).__name__}->{new_op.__name__}", apply)]


class ComparisonOperandSwap(Rule):
    name = "comparison_operand_swap"

    def matches(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Compare) and len(node.ops) == 1

    def variants(self, node: ast.Compare):
        def apply(n: ast.Compare = node):
            n.left, n.comparators[0] = n.comparators[0], n.left

        return [("swap_operands", apply)]


class ArithmeticOperatorSwap(Rule):
    name = "arithmetic_operator_swap"
    _swaps = {
        ast.Add: ast.Sub, ast.Sub: ast.Add,
        ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult,
    }

    def matches(self, node: ast.AST) -> bool:
        return isinstance(node, ast.BinOp) and type(node.op) in self._swaps

    def variants(self, node: ast.BinOp):
        new_op = self._swaps[type(node.op)]

        def apply(n: ast.BinOp = node, op=new_op):
            n.op = op()

        return [(f"{type(node.op).__name__}->{new_op.__name__}", apply)]


class BooleanOperatorSwap(Rule):
    name = "boolean_operator_swap"
    _swaps = {ast.And: ast.Or, ast.Or: ast.And}

    def matches(self, node: ast.AST) -> bool:
        return isinstance(node, ast.BoolOp) and type(node.op) in self._swaps

    def variants(self, node: ast.BoolOp):
        new_op = self._swaps[type(node.op)]

        def apply(n: ast.BoolOp = node, op=new_op):
            n.op = op()

        return [(f"{type(node.op).__name__}->{new_op.__name__}", apply)]


class ConstantOffByOne(Rule):
    name = "constant_off_by_one"

    def matches(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Constant)
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        )

    def variants(self, node: ast.Constant):
        def make(delta: int):
            def apply(n: ast.Constant = node, d: int = delta):
                n.value = n.value + d
            return apply

        return [("plus_one", make(1)), ("minus_one", make(-1))]


class ConditionNegation(Rule):
    name = "condition_negation"

    def matches(self, node: ast.AST) -> bool:
        return isinstance(node, (ast.If, ast.While))

    def variants(self, node):
        def apply(n=node):
            if isinstance(n.test, ast.UnaryOp) and isinstance(n.test.op, ast.Not):
                n.test = n.test.operand
            else:
                n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)

        return [("negate_test", apply)]


RULES: List[Rule] = [
    ComparisonOperatorSwap(),
    ComparisonOperandSwap(),
    ArithmeticOperatorSwap(),
    BooleanOperatorSwap(),
    ConstantOffByOne(),
    ConditionNegation(),
]


@dataclass
class Mutation:
    index: int
    kind: str
    variant: str
    lineno: int
    col_offset: int
    description: str


def _candidates(tree: ast.AST) -> Iterator[Tuple[Rule, str, ast.AST, NodeVisitor]]:
    for node in ast.walk(tree):
        for rule in RULES:
            if rule.matches(node):
                for variant_name, apply_fn in rule.variants(node):
                    yield rule, variant_name, node, apply_fn


def enumerate_mutations(source: str) -> List[Mutation]:
    """List every mutation this engine could apply to `source`, in the
    fixed deterministic order it would apply them."""
    tree = ast.parse(source)
    mutations = []
    for idx, (rule, variant_name, node, _apply) in enumerate(_candidates(tree)):
        mutations.append(
            Mutation(
                index=idx,
                kind=rule.name,
                variant=variant_name,
                lineno=getattr(node, "lineno", -1),
                col_offset=getattr(node, "col_offset", -1),
                description=f"{rule.name}:{variant_name} @ line {getattr(node, 'lineno', '?')}",
            )
        )
    return mutations


def apply_mutation(source: str, index: int) -> str:
    """Return the mutated source with mutation `index` applied (and no
    other mutation). Re-parses fresh so the original AST is untouched."""
    tree = ast.parse(source)
    for idx, (_rule, _variant, node, apply_fn) in enumerate(_candidates(tree)):
        if idx == index:
            apply_fn(node)
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
    raise ValueError(f"no mutation at index {index} (only {idx + 1} available)")


def diff(original: str, mutated: str, filename: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            mutated.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )
