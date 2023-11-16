from pathlib import Path

import pytest
from openpulse import ast, parse
from openpulse.printer import dumps

from shipyard.passes.delays_in_measure import DelaysInMeasure, DetermineMaxDelay
from shipyard.passes.duration_transformer import DurationTransformer
from shipyard.setup.internal import SetupInternal

FILES = ["one_delay", "two_delays", "two_variable_delays"]

list_delays = [
    [6],
    [6, 10],
    [8, 4],
]

list_max_delay = [
    6,
    10,
    8,
]


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/delays_in_measure/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


def load_setup() -> SetupInternal:
    json_path = Path(__file__).parent.parent / "setups/complex.json"
    return SetupInternal.from_json(json_path)


@pytest.mark.parametrize(
    "file, delays, max_delay", zip(FILES, list_delays, list_max_delay)
)
def test_determine_max_delay(file, delays, max_delay):
    prog = load_ast(file)
    DurationTransformer().visit(prog)
    deter_max_delay = DetermineMaxDelay(setup=load_setup())
    deter_max_delay.visit(prog)

    assert deter_max_delay.delays == delays
    assert deter_max_delay.result() == max_delay


@pytest.mark.parametrize("file", FILES)
def test_delays_in_measure(file: str):
    loaded_ast = load_ast(file)
    DurationTransformer().visit(loaded_ast)
    DelaysInMeasure(loaded_ast, setup=load_setup())
    expected_ast = load_ast(f"processed/{file}")
    DurationTransformer().visit(expected_ast)

    for generated, target in zip(
        dumps(loaded_ast).split("\n"), dumps(expected_ast).split("\n")
    ):
        assert generated == target
