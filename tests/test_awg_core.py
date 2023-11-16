import io

import pytest
from openpulse import ast

from shipyard.awg_core import (
    CORE_TYPE_TO_CLASS,
    AWGCore,
    CoreType,
    HDCore,
    QACore,
    SGCore,
)
from shipyard.awg_core.awg_core import WFMDatatype
from shipyard.printers.zi.seqcprinter import PrinterState, SEQCPrinter


def test_awg_core_init():
    qa_core = CORE_TYPE_TO_CLASS[CoreType.QA]
    assert qa_core.n_channels == 2
    assert qa_core.datatype == WFMDatatype.COMPLEX

    sg_core = CORE_TYPE_TO_CLASS[CoreType.SG]
    assert sg_core.n_channels == 1
    assert sg_core.datatype == WFMDatatype.REAL

    hd_core = CORE_TYPE_TO_CLASS[CoreType.HD]
    assert hd_core.n_channels == 2
    assert hd_core.datatype == WFMDatatype.REAL


def play_nodes():
    return [
        ast.BinaryExpression(
            ast.BinaryOperator["+"],
            ast.Identifier("wave_real"),
            ast.BinaryExpression(
                ast.BinaryOperator["*"],
                ast.Identifier("ii"),
                ast.Identifier("wave_imag"),
            ),
        ),
        ast.BinaryExpression(
            ast.BinaryOperator["*"],
            ast.Identifier("ii"),
            ast.Identifier("wave_imag"),
        ),
        ast.Identifier("wave_real"),
    ]


PLAY_NODES = play_nodes()

PLAY_EXPECTED = [
    "playWave(1, 2, wave_real, 1, 2, wave_imag)",
    "playWave(1, 2, 0 * wave_imag, 1, 2, wave_imag)",
]


@pytest.fixture(name="seqc_printer")
def fixture_seqc_printer() -> SEQCPrinter:
    return SEQCPrinter(io.StringIO(), None)


@pytest.mark.parametrize(
    "node, expected",
    [
        (node, expected)
        for (node, expected) in zip(
            PLAY_NODES, PLAY_EXPECTED + ["playWave(1, 2, wave_real)"]
        )
    ],
)
def test_sg_core_visit_play(
    node: ast.QASMNode, expected: str, seqc_printer: SEQCPrinter
):
    sg_core = CORE_TYPE_TO_CLASS[CoreType.SG]
    sg_core.play(node, seqc_printer, PrinterState())
    seqc_printer.stream.getvalue() == expected


@pytest.mark.parametrize(
    "node, expected",
    [
        (node, expected)
        for (node, expected) in zip(
            PLAY_NODES, PLAY_EXPECTED + ["playWave(1, wave_real)"]
        )
    ],
)
def test_hd_core_visit_play(
    node: ast.QASMNode, expected: str, seqc_printer: SEQCPrinter
):
    hd_core = CORE_TYPE_TO_CLASS[CoreType.HD]
    hd_core.play(node, seqc_printer, PrinterState())
    seqc_printer.stream.getvalue() == expected


def test_awg_core_abc_not_implemented():
    with pytest.raises(NotImplementedError):
        AWGCore.play(None, None, None)

    with pytest.raises(NotImplementedError):
        AWGCore.capture_v3(None, None, None)

    with pytest.raises(NotImplementedError):
        AWGCore.shift_frequency(None, None, None)

    with pytest.raises(NotImplementedError):
        AWGCore.shift_phase(None, None, None)

    with pytest.raises(NotImplementedError):
        AWGCore.set_frequency(None, None, None)

    with pytest.raises(NotImplementedError):
        AWGCore.set_phase(None, None, None)


def test_qa_core_value_errors():
    with pytest.raises(ValueError):
        QACore.play(None, None, None)

    with pytest.raises(ValueError):
        QACore.shift_frequency(None, None, None)

    with pytest.raises(ValueError):
        QACore.set_phase(None, None, None)

    with pytest.raises(ValueError):
        QACore.shift_phase(None, None, None)


def test_hd_core_value_errors():
    with pytest.raises(ValueError):
        HDCore.capture_v3(None, None, None)

    with pytest.raises(ValueError):
        HDCore.set_frequency(None, None, None)

    with pytest.raises(ValueError):
        HDCore.shift_frequency(None, None, None)


def test_sg_core_value_errors():
    with pytest.raises(ValueError):
        SGCore.capture_v3(None, None, None)

    with pytest.raises(ValueError):
        SGCore.shift_frequency(None, None, None)


@pytest.mark.parametrize(
    "coretype, expected",
    [
        (CoreType.SG, "setSinePhase(1.1)"),
        (CoreType.HD, "setSinePhase(0, 1.1)\nsetSinePhase(1, 1.1)"),
    ],
)
def test_set_phase(coretype: CoreType, expected: str, seqc_printer: SEQCPrinter):
    node = ast.FunctionCall(
        ast.Identifier("set_phase"),
        arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
    )
    CORE_TYPE_TO_CLASS[coretype].set_phase(node, seqc_printer, PrinterState())
    seqc_printer.stream.getvalue() == expected

    with pytest.raises(NotImplementedError):
        CORE_TYPE_TO_CLASS[coretype].set_phase(
            ast.QASMNode(), seqc_printer, PrinterState()
        )


@pytest.mark.parametrize(
    "coretype, expected",
    [
        (CoreType.SG, "incrementSinePhase(1.1)"),
        (CoreType.HD, "incrementSinePhase(0, 1.1)\nincrementSinePhase(1, 1.1)"),
    ],
)
def test_shift_phase(coretype: CoreType, expected: str, seqc_printer: SEQCPrinter):
    node = ast.FunctionCall(
        ast.Identifier("shift_phase"),
        arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
    )
    CORE_TYPE_TO_CLASS[coretype].shift_phase(node, seqc_printer, PrinterState())
    seqc_printer.stream.getvalue() == expected

    with pytest.raises(NotImplementedError):
        CORE_TYPE_TO_CLASS[coretype].shift_phase(
            ast.QASMNode(), seqc_printer, PrinterState()
        )


@pytest.mark.parametrize(
    "coretype, expected",
    [
        (CoreType.SG, "setOscFreq(0, 1.1)"),
        (CoreType.QA, "setOscFreq(0, 1.1)"),
    ],
)
def test_set_frequency(coretype: CoreType, expected: str, seqc_printer: SEQCPrinter):
    # todo specific oscillator
    node = ast.FunctionCall(
        ast.Identifier("set_frequency"),
        arguments=[ast.Identifier("frame1"), ast.FloatLiteral(1.1)],
    )
    CORE_TYPE_TO_CLASS[coretype].set_frequency(node, seqc_printer, PrinterState())
    seqc_printer.stream.getvalue() == expected

    with pytest.raises(NotImplementedError):
        CORE_TYPE_TO_CLASS[coretype].set_frequency(
            ast.QASMNode(), seqc_printer, PrinterState()
        )
