from pathlib import Path

import pytest
from openpulse import ast

from shipyard.compiler import Compiler
from shipyard.compiler_error import SemanticError, SetupError
from shipyard.passes import ResolveIODeclaration


@pytest.fixture(name="io_resolver")
def fixture_seqc_printer() -> ResolveIODeclaration:
    return ResolveIODeclaration({"test_dummy": 1})


def test_inputs_general():
    """
    All inputs are declared in the input dictionary
    """
    source = Path(__file__).parent.parent
    qasm_path = source / "qasm/io_resolution/input_testing.qasm"
    setup_path = source / "setups/basic.json"
    seqc_path = source / "seqc/input_testing.seqc"

    compiler = Compiler(qasm_path, setup_path)

    input_dict = {
        "n_shots": 6,
        "time_delta": 2e-5,
        "c": complex(1.1, 2.2),
        "f": 3.0,
        "b": True,
        "bi": 0,
        "u": 3,
        "second_bi": [0, 0],
    }
    compiler.compile(input_dict)

    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 1, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target


def test_missing_inputs():
    """
    Some inputs are missing from the input dictionary
    """
    qasm_path = Path(__file__).parent.parent / "qasm/io_resolution/input_testing.qasm"
    setup_path = Path(__file__).parent.parent / "setups/basic.json"

    compiler = Compiler(qasm_path, setup_path)

    input_dict = {
        "time_delta": 2e-5,
        "c": complex(1.1, 2.2),
        "f": 3.0,
        "b": True,
        "bi": [0, 0],
        "u": 3,
    }
    with pytest.raises(SetupError):
        compiler.compile(input_dict)


def test_output_error():
    """
    Output type is initiated, should throw an error
    """
    qasm_path = Path(__file__).parent.parent / "qasm/io_resolution/output_error.qasm"
    setup_path = Path(__file__).parent.parent / "setups/basic.json"

    compiler = Compiler(qasm_path, setup_path)

    input_dict = {
        "time_delta": 2e-5,
        "c": complex(1.1, 2.2),
        "f": 3.0,
        "b": True,
        "bi": [0, 0],
        "u": 3,
    }
    with pytest.raises(SemanticError):
        compiler.compile(input_dict)


def test_inputs_not_supported(io_resolver: ResolveIODeclaration):
    """
    Test unsupported input types: complex, angle, stretch
    """
    with pytest.raises(SemanticError):
        io_resolver.visit_IODeclaration(
            ast.IODeclaration(
                io_identifier=ast.IOKeyword.input,
                identifier=ast.Identifier(name="test_dummy"),
                type=ast.ComplexType(base_type=ast.FloatType()),
            )
        )

    with pytest.raises(SemanticError):
        io_resolver.visit_IODeclaration(
            ast.IODeclaration(
                io_identifier=ast.IOKeyword.input,
                identifier=ast.Identifier(name="test_dummy"),
                type=ast.StretchType(),
            )
        )

    with pytest.raises(SemanticError):
        io_resolver.visit_IODeclaration(
            ast.IODeclaration(
                io_identifier=ast.IOKeyword.input,
                identifier=ast.Identifier(name="test_dummy"),
                type=ast.AngleType(),
            )
        )
