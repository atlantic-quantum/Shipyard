import numpy as np
import pytest
from openpulse import ast

from shipyard.compiler_error import SEQCPrinterError
from shipyard.printers.zi import waveform_functions
from shipyard.printers.zi.sample_waveform import sample_waveform

TYPES_TO_NODES = {
    "int": ast.IntegerLiteral,
    "float": ast.FloatLiteral,
}

FUNCTIONS_AND_ARGUMENTS = [
    ("zeros", [("int", 100)]),
    ("ones", [("int", 100)]),
    ("sine", [("int", 100), ("float", 0.9), ("float", 0.1), ("int", 5)]),
    ("cosine", [("int", 100), ("float", 0.9), ("float", 0.1), ("int", 5)]),
    ("sinc", [("int", 100), ("float", 0.9), ("float", 0.1), ("float", 0.8)]),
    ("ramp", [("int", 100), ("float", -0.75), ("float", 0.1)]),
    ("sawtooth", [("int", 100), ("float", 0.9), ("float", 0.1), ("int", 5)]),
    ("triangle", [("int", 100), ("float", 0.9), ("float", 0.1), ("int", 5)]),
    ("gauss", [("int", 100), ("float", 0.9), ("int", 50), ("float", 55)]),
    ("drag", [("int", 100), ("float", 0.9), ("int", 50), ("float", 55)]),
    ("blackman", [("int", 100), ("float", 0.9), ("float", 0.45)]),
    ("hamming", [("int", 100), ("float", 0.9)]),
    ("hann", [("int", 100), ("float", 0.9)]),
    ("rect", [("int", 100), ("float", 0.9)]),
    ("chirp", [("int", 100), ("float", 0.9), ("float", 1e6), ("float", 3e6)]),
    (
        "chirp",
        [("int", 100), ("float", 0.9), ("float", 1e6), ("float", 3e6), ("float", 1.5)],
    ),
    (
        "rrc",
        [("int", 100), ("float", 0.9), ("int", 55), ("float", 0.25), ("float", 1)],
    ),
    (
        "rrc",
        [("int", 100), ("float", 0.9), ("int", 45), ("float", 0.25), ("float", 1)],
    ),
]


@pytest.mark.parametrize("func, arguments", FUNCTIONS_AND_ARGUMENTS)
def test_sample_waveform(func: str, arguments: list[tuple[str, int | float]]):
    node = ast.FunctionCall(
        ast.Identifier(func),
        arguments=[TYPES_TO_NODES[ttype](value) for (ttype, value) in arguments],
    )
    wfm_func = waveform_functions.__dict__[func]
    wfm = wfm_func(*[value for (_, value) in arguments])

    assert np.all(sample_waveform(node) == wfm)
    assert wfm.shape == (100,)


def test_binary_expression():
    node = ast.BinaryExpression(
        op=ast.BinaryOperator["*"],
        lhs=ast.FunctionCall(
            ast.Identifier("ones"), arguments=[ast.IntegerLiteral(100)]
        ),
        rhs=ast.FloatLiteral(0.9),
    )
    wfm = sample_waveform(node)
    assert np.all(wfm == np.ones(100) * 0.9)


def test_unknown_function_error():
    with pytest.raises(SEQCPrinterError):
        sample_waveform(ast.FunctionCall(ast.Identifier("unknown"), arguments=[]))


def test_unhanded_node_error():
    with pytest.raises(SEQCPrinterError):
        sample_waveform(
            ast.UnaryExpression(ast.UnaryOperator["-"], ast.IntegerLiteral(1))
        )
