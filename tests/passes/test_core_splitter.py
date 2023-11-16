from copy import deepcopy
from pathlib import Path

import pytest
from openpulse import ast, parse
from openpulse.printer import dumps

from shipyard.compiler_error import TransformError
from shipyard.passes.core_splitter import CoreSplitter, ports_for_core
from shipyard.passes.remove_unused import RemoveUnused
from shipyard.setup.internal import SetupInternal


def test_split_basic():
    """ """
    qasm_path = Path(__file__).parent.parent / "qasm/split.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    def split_port(port, target_file):
        transformed_ast = CoreSplitter(port).visit(deepcopy(qasm_ast))
        RemoveUnused().visit(transformed_ast)
        with open(
            Path(__file__).parent.parent / f"qasm/{target_file}.qasm", encoding="utf_8"
        ) as qasm_file:
            post_split = qasm_file.read()

        # print(dumps(transformed_ast))

        for genrated, target in zip(
            dumps(transformed_ast).split("\n"), post_split.split("\n")
        ):
            assert genrated == target

    split_port("awg1_ch1", "post_split_1")
    split_port("awg2_ch1", "post_split_2")


def test_ports_for_core():
    json_path = Path(__file__).parent.parent / "setups/complex.json"
    complex_setup = SetupInternal.from_json(json_path)

    assert set(["dac0"]) == ports_for_core(complex_setup, "hdawg1", 1)
    assert set(["dac1"]) == ports_for_core(complex_setup, "hdawg1", 2)
    assert set(["dac2"]) == ports_for_core(complex_setup, "hdawg1", 3)
    assert set(["dac3", "adc0"]) == ports_for_core(complex_setup, "shfqa1", 1)


@pytest.fixture(name="frame")
def fixture_frame():
    return ast.ClassicalDeclaration(
        ast.FrameType(),
        ast.Identifier("frame1"),
        ast.FunctionCall(
            name=ast.Identifier("newframe"),
            arguments=[
                ast.Identifier("ch1"),
                ast.FloatLiteral(1.1),
                ast.FloatLiteral(0.4),
            ],
        ),
    )


def test_frame_declaration(frame):
    assert CoreSplitter(set(["ch1"])).visit(frame) == frame
    assert CoreSplitter(set(["ch2"])).visit(frame) is None

    with pytest.raises(TransformError):
        frame2 = ast.ClassicalDeclaration(ast.FrameType(), ast.Identifier("frame2"))
        CoreSplitter(set(["ch1"])).visit(frame2)


def test_port_declaration():
    ch1 = ast.ClassicalDeclaration(ast.PortType(), ast.Identifier("ch1"))

    assert CoreSplitter(set(["ch1"])).visit(ch1) == ch1
    assert CoreSplitter(set(["ch2"])).visit(ch1) is None


def test_other_declaration():
    core_splitter = CoreSplitter(set(["ch1"]))

    node = ast.ClassicalDeclaration(ast.IntType(), ast.Identifier("some_int"))
    assert core_splitter.visit(node) == node


@pytest.mark.parametrize("call", ["play", "capture_v2"])
def test_play_capture_call(frame, call):
    play_call = ast.FunctionCall(
        name=ast.Identifier(call),
        arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
    )

    calibration = ast.CalibrationStatement(
        body=[
            ast.ClassicalDeclaration(ast.PortType(), ast.Identifier("ch1")),
            frame,
            play_call,
        ]
    )

    cal1 = deepcopy(calibration)
    ncal1 = CoreSplitter(set(["ch1"])).visit(cal1)
    assert ncal1.body[2] == play_call

    cal2 = deepcopy(calibration)
    ncal2 = CoreSplitter(set(["ch2"])).visit(cal2)
    assert not ncal2.body


def test_other_function_call():
    other_call = ast.FunctionCall(name=ast.Identifier("other"), arguments=[])
    assert CoreSplitter(set(["ch1"])).visit(other_call) == other_call


def test_expression_statement(frame):
    play_call = ast.FunctionCall(
        name=ast.Identifier("play"),
        arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
    )
    calibration = ast.CalibrationStatement(
        body=[
            ast.ClassicalDeclaration(ast.PortType(), ast.Identifier("ch1")),
            frame,
            ast.ExpressionStatement(play_call),
        ]
    )

    cal1 = deepcopy(calibration)
    ncal1 = CoreSplitter(set(["ch1"])).visit(cal1)
    assert ncal1.body[2] == ast.ExpressionStatement(play_call)

    cal2 = deepcopy(calibration)
    ncal2 = CoreSplitter(set(["ch2"])).visit(cal2)
    assert not ncal2.body


def test_defcal(frame):
    defcal = ast.CalibrationDefinition(
        name=ast.Identifier("dcal"),
        arguments=[],
        qubits=[],
        return_type=None,
        body=[
            ast.FunctionCall(
                name=ast.Identifier("play"),
                arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
            )
        ],
    )
    calibration = ast.CalibrationStatement(
        body=[
            ast.ClassicalDeclaration(ast.PortType(), ast.Identifier("ch1")),
            frame,
        ]
    )
    program = ast.Program(statements=[calibration, defcal])

    prog1 = deepcopy(program)
    nprog1 = CoreSplitter(set(["ch1"])).visit(prog1)
    assert nprog1.statements[1] == defcal

    prog2 = deepcopy(program)
    nprog2 = CoreSplitter(set(["ch2"])).visit(prog2)
    assert len(nprog2.statements) == 1
