from dataclasses import is_dataclass
from inspect import Parameter, signature
from pathlib import Path

import pytest
from openpulse import ast
from openpulse.parser import parse
from openpulse.printer import dumps

from shipyard.visitors.copy_transformer import CopyTransformer
from shipyard.visitors.generic_transformer import GenericTransformer
from shipyard.visitors.generic_visitor import GenericVisitor


def instanciate_dataclass(dataclass: ast.QASMNode):
    def _handle_parameter(param):
        if param.annotation.split("[")[0] == "Optional":
            return None
        if param.annotation == "Expression":
            return ast.IntegerLiteral(value=1)
        if param.annotation == "Statement":
            return ast.QASMNode()
        if is_dataclass(ast.__dict__.get(param.annotation, None)):
            return instanciate_dataclass(ast.__dict__[param.annotation])
        if param.annotation.split("[")[0] == "List":
            new_param = Parameter(
                name=param.name,
                kind=param.kind,
                annotation=param.annotation.split("[", 1)[1][:-1],
            )
            return [_handle_parameter(new_param)]
        if param.annotation.split("[")[0] == "Union":
            new_param = Parameter(
                name=param.name,
                kind=param.kind,
                annotation=param.annotation.split("[")[1].split(",")[0],
            )
            return _handle_parameter(new_param)
        if param.annotation == "str":
            return "test"
        if param.annotation == "int":
            return 1
        if param.annotation == "float":
            return 1.0
        if param.annotation == "bool":
            return True
        if param.annotation == "BinaryOperator":
            return ast.BinaryOperator["+"]
        if param.annotation == "UnaryOperator":
            return ast.UnaryOperator["-"]
        if param.annotation == "AssignmentOperator":
            return ast.AssignmentOperator["="]
        if param.annotation == "IndexElement":
            return instanciate_dataclass(ast.DiscreteSet)
        if param.annotation == "TimeUnit":
            return ast.TimeUnit["ns"]
        if param.annotation == "IOKeyword":
            return ast.IOKeyword["input"]
        if param.annotation == "GateModifierName":
            return ast.GateModifierName["ctrl"]
        raise NotImplementedError

    sig = signature(dataclass)
    params = sig.parameters
    values = {key: _handle_parameter(params[key]) for key in params.keys()}
    try:
        return dataclass(**values)
    except TypeError:
        print(dataclass)


QASM_NODE_NAMES = [
    key for key in ast.__dict__.keys() if is_dataclass(ast.__dict__[key])
]

QASM_NODES = [
    instanciate_dataclass(ast.__dict__[key])
    for key in ast.__dict__.keys()
    if is_dataclass(ast.__dict__[key])
]


@pytest.mark.parametrize("node", QASM_NODES, ids=QASM_NODE_NAMES)
def test_generic_visitor_node_visit(node):
    try:
        GenericVisitor().visit(node)
    except Exception as e:
        print(node)
        raise e


@pytest.mark.parametrize("node", QASM_NODES, ids=QASM_NODE_NAMES)
def test_generic_transformer_node_visit(node):
    try:
        transformed_node = GenericTransformer().visit(node)
        assert node is transformed_node
    except Exception as e:
        print(node)
        raise e


@pytest.mark.parametrize("node", QASM_NODES, ids=QASM_NODE_NAMES)
def test_copy_transformer_node_visit(node):
    if type(node) in [
        ast.Span,
        ast.ClassicalType,
        ast.Expression,
        ast.Statement,
        ast.QASMNode,
        ast.QuantumStatement,
    ]:
        pytest.xfail()
    try:
        new_node = CopyTransformer().visit(node)
        assert node is not new_node
        assert node == new_node
    except Exception as e:
        print(node)
        raise e


def files(folder: str) -> tuple[list[Path], list[str]]:
    base_path = Path(__file__).parent.parent / folder
    FILES = list(base_path.glob(f"**/*.{folder}"))
    return FILES, [path.name for path in FILES]


QASM_FILES, QASM_NAMES = files("qasm")


@pytest.mark.parametrize("qasm_path", QASM_FILES, ids=QASM_NAMES)
def test_generic_visitor_file_visit(qasm_path: Path):
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)
    copy_ast = CopyTransformer().visit(qasm_ast)

    original = dumps(qasm_ast)
    copied = dumps(copy_ast)
    assert original == copied
