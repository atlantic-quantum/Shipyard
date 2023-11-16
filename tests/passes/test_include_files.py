import io
from pathlib import Path

import pytest
from openpulse import ast, parse

from shipyard.compiler import Compiler
from shipyard.compiler_error import SemanticError, TransformError
from shipyard.printers.zi.seqcprinter import SEQCPrinter
from shipyard.setup.internal import SetupInternal


@pytest.fixture(name="basic_setup")
def fixture_basic_setup() -> SetupInternal:
    json_path = Path(__file__).parent.parent / "setups/basic.json"
    return SetupInternal.from_json(json_path)


@pytest.fixture(name="seqc_printer")
def fixture_seqc_printer(basic_setup: SetupInternal) -> SEQCPrinter:
    return SEQCPrinter(io.StringIO(), basic_setup)


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


def test_ramsey_nested_include(seqc_printer: SEQCPrinter, file="ramsey_nested"):
    """
    Test for nested include files (one qasm on inc) for ramsey experiment
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "qasm/include_files/setup.json"
    seqc_path = Path(__file__).parent.parent / "qasm/include_files/ramsey_seqc.seqc"
    compiler = Compiler(qasm_path, setup_path)
    compiler.compile()
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 1, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target


def test_include_dne(seqc_printer: SEQCPrinter, file="include_dne"):
    """
    Test for include file that does not exist/ not in path
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "qasm/include_files/setup.json"

    with pytest.raises(TransformError):
        compiler = Compiler(qasm_path, setup_path)
        compiler.compile()


def test_ramsey_two_includes(seqc_printer: SEQCPrinter, file="ramsey_two_includes"):
    """
    Test for multiple include files (one qasm on inc) for ramsey experiment
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "qasm/include_files/setup.json"
    seqc_path = Path(__file__).parent.parent / "qasm/include_files/ramsey_seqc.seqc"

    compiler = Compiler(qasm_path, setup_path)
    compiler.compile()
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 1, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target


def test_duplicate_error(seqc_printer: SEQCPrinter, file="duplicate_error"):
    """
    Test for duplicate include files (also catches include files that contain overlap
    in declarations and definitions)
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "qasm/include_files/setup.json"

    with pytest.raises(SemanticError):
        compiler = Compiler(qasm_path, setup_path)
        compiler.compile()


def test_complex_path(seqc_printer: SEQCPrinter, file="complex_path"):
    """
    Test for more complex/absolute path include statements for ramsey experiment
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/include_files/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "qasm/include_files/setup.json"
    seqc_path = Path(__file__).parent.parent / "qasm/include_files/ramsey_seqc.seqc"

    compiler = Compiler(qasm_path, setup_path)
    compiler.compile()
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 1, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target
