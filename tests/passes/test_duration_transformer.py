import pytest
from openpulse import ast

from shipyard.passes.duration_transformer import DurationTransformer

duration_nodes_and_samples = [
    (ast.DurationLiteral(40, ast.TimeUnit.dt), 40),
    (ast.DurationLiteral(10, ast.TimeUnit.ns), 20),
    (ast.DurationLiteral(5, ast.TimeUnit.us), 10_000),
    (ast.DurationLiteral(2, ast.TimeUnit.ms), 4_000_000),
    (ast.DurationLiteral(1, ast.TimeUnit.s), 2_000_000_000),
]


@pytest.mark.parametrize("node, expected", duration_nodes_and_samples)
def test_duration_transformer_literal(node: ast.DurationLiteral, expected: int):
    duration_transformer = DurationTransformer()
    new_node = duration_transformer.visit(node)
    assert new_node.unit == ast.TimeUnit.dt
    assert new_node.value == expected


@pytest.mark.parametrize("node, expected", duration_nodes_and_samples)
def test_duration_transformer_const(node, expected):
    duration_transformer = DurationTransformer()
    const_node = ast.ConstantDeclaration(
        ast.DurationType, ast.Identifier("some_time"), init_expression=node
    )
    new_const_node = duration_transformer.visit(const_node)
    assert new_const_node.init_expression.unit == ast.TimeUnit.dt
    assert new_const_node.init_expression.value == expected


@pytest.mark.parametrize("node, expected", duration_nodes_and_samples)
def test_duration_transformer_different_sample_rate(node, expected):
    duration_transformer = DurationTransformer(sample_rate=2.4e9)
    new_node = duration_transformer.visit(node)
    assert new_node.unit == ast.TimeUnit.dt
    if node.unit.name != "dt":
        print(expected * 1.2)
        assert new_node.value == int(expected * 1.2)
    else:
        assert new_node.value == expected
