import io
import json
from pathlib import Path

import pytest
from openpulse import ast, parse
from zhinst.toolkit import CommandTable

from shipyard.compiler import Compiler
from shipyard.compiler_error import SemanticError
from shipyard.printers.zi.seqcprinter import SEQCPrinter
from shipyard.setup.internal import SetupInternal


@pytest.fixture(name="basic_setup")
def fixture_basic_setup() -> SetupInternal:
    json_path = Path(__file__).parent.parent / "setups/complex.json"
    return SetupInternal.from_json(json_path)


@pytest.fixture(name="seqc_printer")
def fixture_seqc_printer(basic_setup: SetupInternal) -> SEQCPrinter:
    return SEQCPrinter(io.StringIO(), basic_setup)


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/command_table/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


def test_insert_commandtable(seqc_printer: SEQCPrinter, file="basic_ct"):
    """
    Test for  just one command table and 1 HD core
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/command_table/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"
    seqc_path = Path(__file__).parent.parent / "qasm/command_table/basic_ct.seqc"
    hdawg_schema_path = (
        Path(__file__).parent.parent / "qasm/command_table/hdawg_schema.json"
    )

    hdawg_schema = {}
    with open(hdawg_schema_path, encoding="utf_8") as f:
        hdawg_schema = json.load(f)
    hdawg_schema = dict(hdawg_schema)
    ct = CommandTable(hdawg_schema)
    ct.table[0].waveform.index = 0
    ct.table[0].waveform.length = 64
    ct_dict = {("hdawg1", 2, "HD"): ct}
    compiler = Compiler(qasm_path, setup_path)

    compiler.compile(command_tables=ct_dict)

    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 2, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target


def test_insert_commandtable_2(seqc_printer: SEQCPrinter, file="two_cores"):
    """
    Test for just one command table and 1 HD core
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/command_table/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"
    seqc_path = Path(__file__).parent.parent / "qasm/command_table/two_cores.seqc"
    hdawg_schema_path = (
        Path(__file__).parent.parent / "qasm/command_table/hdawg_schema.json"
    )

    hdawg_schema = {}
    with open(hdawg_schema_path, encoding="utf_8") as f:
        hdawg_schema = json.load(f)
    hdawg_schema = dict(hdawg_schema)
    ct_1 = CommandTable(hdawg_schema)
    ct_1.table[0].waveform.index = 0
    ct_1.table[0].waveform.length = 64
    ct_2 = CommandTable(hdawg_schema)
    ct_2.table[0].waveform.index = 1
    ct_2.table[0].waveform.length = 64
    ct_2.table[1].waveform.index = 2
    ct_2.table[1].waveform.length = 96
    ct_dict = {
        ("hdawg1", 1, "HD"): ct_1,
        ("hdawg1", 2, "HD"): ct_2,
    }  # changed from 2,2 to 1,2
    compiler = Compiler(qasm_path, setup_path)

    compiler.compile(command_tables=ct_dict)

    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for generated, target in zip(
        compiler.split_compiled[("hdawg1", 2, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert generated == target
