from pathlib import Path

import pytest
from openpulse import ast, parse
from openpulse.printer import dumps

from shipyard.passes.remove_unused import RemoveUnused, _DetermineUnused


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/remove_unused/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


FILES = [
    "classical_declaration",
    "const_declaration",
    "subroutine",
    "defcal",
    "undeclared",
    "measurements",
    "resets",
]

list_declared = [
    {"used", "unused"},
    {"used", "unused"},
    {"used", "used_function", "unused_function"},
    {
        "used",
        "ch1",
        "lab_frame",
        "w_gauss",
        "_ZN9used_gate_PN1_INT_QN1_$0_R",
        "_ZN11unused_gate_PN1_INT_QN1_$0_R",
    },
    {
        "used",
        "ch1",
        "lab_frame",
        "w_gauss",
        "_ZN13declared_gate_PN1_INT_QN1_$0_R",
    },
    {
        "ch1",
        "tx_frame",
        "rx_frame",
        "w_gauss",
        "_ZN7measure_PN0_QN1_$0_RBIT",
        "measured_bit_0",
        "measured_bit_1",
    },
    {"_ZN5reset_PN0_QN1_$0_R"},
]

list_unused = [
    {"unused"},
    {"unused"},
    {"unused_function"},
    {"_ZN11unused_gate_PN1_INT_QN1_$0_R"},
    set(),
    set(),
    set(),
]


@pytest.mark.parametrize(
    "file, declared, unused", zip(FILES, list_declared, list_unused)
)
def test_determine_unused(file, declared, unused):
    deter_unused = _DetermineUnused()
    deter_unused.visit(load_ast(file))

    assert deter_unused.declared == declared
    assert deter_unused.unused == unused


@pytest.mark.parametrize("file", FILES)
def test_remove_unused(file: str):
    removed_ast = load_ast(file)
    RemoveUnused(removed_ast)
    RemoveUnused(removed_ast)
    expected_ast = load_ast(f"processed/{file}")

    for generated, target in zip(
        dumps(removed_ast).split("\n"), dumps(expected_ast).split("\n")
    ):
        assert generated == target
