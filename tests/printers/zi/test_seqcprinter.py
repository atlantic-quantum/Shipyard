import io
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
import json
from openpulse import ast, parse
from zhinst.core import compile_seqc
from zhinst.toolkit import CommandTable

from shipyard.compiler import Compiler
from shipyard.call_stack import ActivationRecord, ARType
from shipyard.compiler_error import SEQCPrinterError
from shipyard.passes.core_splitter import CoreSplitter
from shipyard.passes.remove_unused import RemoveUnused
from shipyard.passes.semantic_analysis.semantic_analyzer import SemanticAnalyzer
from shipyard.printers.zi.seqcprinter import SEQCPrinter, dumps
from shipyard.setup.internal import SetupInternal


def compile_seqc_code(seqc_code: str):
    compile_seqc(seqc_code, "SHFSG4", [""], index=0, sequencer="SG")
    compile_seqc(seqc_code, "HDAWG8", ["PC"], index=0, samplerate=2.4e9)


def compile_seqc_code_qa(seqc_code: str):
    compile_seqc(seqc_code, "SHFQA4", [""], index=0)
    compile_seqc(seqc_code, "SHFQC", [""], index=0, sequencer="QA")


@pytest.fixture(name="basic_setup")
def fixture_basic_setup() -> SetupInternal:
    json_path = Path(__file__).parent.parent.parent / "setups/basic.json"
    return SetupInternal.from_json(json_path)


@pytest.fixture(name="seqc_printer")
def fixture_seqc_printer(basic_setup: SetupInternal) -> SEQCPrinter:
    return SEQCPrinter(io.StringIO(), basic_setup)


def test_basic(seqc_printer: SEQCPrinter):
    """
    Demonstrative test that:
        imports qasm program code from file
        and transpiles it to seqc code
    """
    qasm_path = Path(__file__).parent.parent.parent / "qasm/basic.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)

    seqc_printer.visit(qasm_ast)

    # compare generated code with expected result
    seqc_path = Path(__file__).parent.parent.parent / "seqc/basic.seqc"
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for genrated, target in zip(
        seqc_printer.stream.getvalue().split("\n"), seqc_code.split("\n")
    ):
        assert genrated == target

    compile_seqc_code(seqc_printer.stream.getvalue())


def files(folder: str) -> list[str]:
    base_path = Path(__file__).parent.parent.parent / folder
    plen = len(base_path.parts)
    FILES = list(base_path.glob(f"**/*.{folder}"))
    return [str(Path(*path.parts[plen:])) for path in FILES]


QASM_FILES = files("qasm")
SEQC_FILES = files("seqc")


def common_files() -> list[str]:
    files = []
    cut = -5
    for q_file in QASM_FILES:
        for s_file in SEQC_FILES:
            if q_file[:cut] == s_file[:cut]:
                files.append(q_file[:cut])
                break
    return files


COMMON_FILES = common_files()

FILE_NAMES_QA = ["measurements"]


@pytest.mark.parametrize("file_name", COMMON_FILES)
def test_files(seqc_printer: SEQCPrinter, file_name):
    """
    Demonstrative test that:
        imports qasm program code from file
        and transpiles it to seqc code
    """
    if file_name in FILE_NAMES_QA:
        pytest.xfail()
    qasm_path = Path(__file__).parent.parent.parent / f"qasm/{file_name}.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    seqc_printer.visit(qasm_ast)

    print(seqc_printer.stream.getvalue())

    # compare generated code with expected result
    seqc_path = Path(__file__).parent.parent.parent / f"seqc/{file_name}.seqc"
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for genrated, target in zip(
        seqc_printer.stream.getvalue().split("\n"), seqc_code.split("\n")
    ):
        assert genrated == target

    compile_seqc_code(seqc_printer.stream.getvalue())


@pytest.mark.parametrize("file_name", FILE_NAMES_QA)
def test_files_qa(file_name):
    """
    Demonstrative test that:
        imports qasm program code from file
        and transpiles it to seqc code
    """
    qasm_path = Path(__file__).parent.parent.parent / f"qasm/{file_name}.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)

    json_path = Path(__file__).parent.parent.parent / "setups/complex.json"
    complex_setup = SetupInternal.from_json(json_path)
    seqc_printer = SEQCPrinter(io.StringIO(), complex_setup)
    seqc_printer.visit(qasm_ast)

    # compare generated code with expected result
    seqc_path = Path(__file__).parent.parent.parent / f"seqc/{file_name}.seqc"
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for genrated, target in zip(
        seqc_printer.stream.getvalue().split("\n"), seqc_code.split("\n")
    ):
        assert genrated == target

    compile_seqc_code_qa(seqc_printer.stream.getvalue())


@pytest.mark.parametrize("file_name", SEQC_FILES)
def test_zi_core_compiler(file_name):
    if file_name in [
        "measurements.seqc",
        "cw_sweep.seqc",
        "input_testing.seqc",
    ]:
        pytest.xfail()
    seqc_path = Path(__file__).parent.parent.parent / f"seqc/{file_name}"
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    compile_seqc_code(seqc_code)


@pytest.mark.parametrize("file_name", FILE_NAMES_QA)
def test_zi_core_compiler_qa(file_name):
    seqc_path = Path(__file__).parent.parent.parent / f"seqc/{file_name}.seqc"
    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    compile_seqc_code_qa(seqc_code)


@pytest.mark.parametrize("file_name", COMMON_FILES)
def test_dump(basic_setup: SetupInternal, file_name):
    if file_name == "measurements":
        json_path = Path(__file__).parent.parent.parent / "setups/complex.json"
        basic_setup = SetupInternal.from_json(json_path)
    qasm_path = Path(__file__).parent.parent.parent / f"qasm/{file_name}.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    dumps(parse(qasm_code), setup=basic_setup)


def test_sp_visit_const_decl_node(seqc_printer: SEQCPrinter):
    seqc_printer.visit(
        ast.Program(
            statements=[
                ast.ConstantDeclaration(
                    type=ast.FloatType(),
                    identifier=ast.Identifier("i"),
                    init_expression=ast.FloatLiteral(1.1),
                )
            ]
        )
    )
    compile_seqc_code(seqc_printer.stream.getvalue())


def test_sp_visit_while_node(seqc_printer: SEQCPrinter, while_loop: ast.WhileLoop):
    seqc_printer.visit(while_loop)
    compile_seqc_code(seqc_printer.stream.getvalue())
    # todo more extensive while loop tests, especially different while conditions


def test_sp_visit_array_literal(seqc_printer: SEQCPrinter):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    seqc_printer.call_stack.push(activation_record=ar)
    seqc_printer.visit(
        ast.ClassicalDeclaration(
            ast.WaveformType(),
            ast.Identifier("wfm_literal"),
            ast.ArrayLiteral([ast.FloatLiteral(1.1), ast.FloatLiteral(2.3)]),
        )
    )
    compile_seqc_code(seqc_printer.stream.getvalue())


def test_compile_out_nodes(seqc_printer: SEQCPrinter):
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_Include(ast.Include("test_dummy"), None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_QuantumGateDefinition(
            ast.QuantumGateDefinition(ast.Identifier("reset"), [], [], []), None
        )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_ImaginaryLiteral(ast.ImaginaryLiteral(1.1), None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_DiscreteSet(None, None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_RangeDefinition(None, None)

    # with pytest.raises(SEQCPrinterError):
    #     seqc_printer.visit_IndexedIdentifier(
    #         ast.IndexedIdentifier(ast.Identifier("q"), []), None
    #     )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_QuantumGateModifier(None, None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_QuantumPhase(
            ast.QuantumPhase([], ast.FloatLiteral(1.1), []), None
        )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_IODeclaration(
            ast.IODeclaration(
                ast.IOKeyword.input, ast.FloatType(), ast.Identifier("q1")
            ),
            None,
        )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_QuantumArgument(None, None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_DurationOf(None, None)

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit_SizeOf(None, None)

    # with pytest.raises(SEQCPrinterError):
    #     seqc_printer.visit_AliasStatement(
    #         ast.AliasStatement(ast.Identifier("q2"), ast.Identifier("q1")), None
    #     )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.interpret = False
        seqc_printer.visit(
            ast.QuantumGate(
                modifiers=[
                    ast.QuantumGateModifier(modifier=ast.GateModifierName["inv"])
                ],
                name=ast.Identifier("x90"),
                arguments=[],
                qubits=[ast.Identifier("q")],
            )
        )
        seqc_printer.interpret = True

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.IndexedIdentifier(
                name=ast.Identifier("q"),
                indices=[
                    ast.DiscreteSet([ast.IntegerLiteral(1), ast.IntegerLiteral(2)])
                ],
            )
        )


def test_warning_nodes(seqc_printer: SEQCPrinter):
    with pytest.raises(Warning):
        seqc_printer.visit_Annotation(None, None)

    with pytest.raises(Warning):
        seqc_printer.visit_Pragma(None, None)


def test_slicing(seqc_printer: SEQCPrinter):
    qasm_code = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";
    cal {
      waveform w_gauss = gauss(640dt, 1.0, 320dt, 50dt);
      let w_rise = w_gauss[0:319];
    }
    """
    seqc_code = """wave w_gauss = gauss(640, 1.0, 320, 50);
wave w_rise = cut(w_gauss, 0, 319);\n"""
    seqc_printer.visit(parse(qasm_code))
    generated_code = seqc_printer.stream.getvalue()
    assert generated_code == seqc_code
    for genrated, target in zip(generated_code.split("\n"), seqc_code.split("\n")):
        assert genrated == target


def test_concatenating(seqc_printer: SEQCPrinter):
    qasm_code = """
    OPENQASM 3.0;
    defcalgrammar "openpulse";
    cal {
    port ch1;
    frame lab_frame = newframe(ch1, 0, 0);
    waveform w_gauss = gauss(640dt, 1.0, 320dt, 50dt);
    let w_rise = w_gauss[0:319];
    let w_fall = w_gauss[320:639];
    let w_pulse = w_rise ++ w_fall;
    }
    """
    seqc_code = """wave w_gauss = gauss(640, 1.0, 320, 50);
wave w_rise = cut(w_gauss, 0, 319);
wave w_fall = cut(w_gauss, 320, 639);
wave w_pulse = join(w_rise, w_fall);
"""
    seqc_printer.visit(parse(qasm_code))
    generated_code = seqc_printer.stream.getvalue()
    for genrated, target in zip(generated_code.split("\n"), seqc_code.split("\n")):
        assert genrated == target


@pytest.mark.parametrize(
    "node",
    [
        ast.BreakStatement(),
        ast.ContinueStatement(),
        ast.EndStatement(),
    ],
)
def test_no_equivalent_seqc_statement(seqc_printer: SEQCPrinter, node):
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(node)


@pytest.mark.parametrize(
    "set",
    [
        ast.Identifier("j"),
        ast.DiscreteSet([ast.IntegerLiteral(1), ast.IntegerLiteral(2)]),
    ],
)
def test_sp_visit_for_in_loop_node_set_decl_error(seqc_printer: SEQCPrinter, set):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    seqc_printer.call_stack.push(activation_record=ar)
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.ForInLoop(
                type=ast.IntType(),
                identifier=ast.Identifier("i"),
                set_declaration=set,
                block=[],
            )
        )


@pytest.mark.parametrize("start", [None, ast.Identifier("a"), ast.IntegerLiteral(2)])
@pytest.mark.parametrize("step", [None, ast.Identifier("c"), ast.IntegerLiteral(1)])
@pytest.mark.parametrize("end", [ast.Identifier("b"), ast.IntegerLiteral(10)])
def test_sp_visit_for_in_loop_node(seqc_printer: SEQCPrinter, start, step, end):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    ar["a"] = 2
    ar["b"] = 10
    ar["c"] = 1
    seqc_printer.call_stack.push(activation_record=ar)
    seqc_printer.visit(
        ast.ForInLoop(
            type=ast.IntType(),
            identifier=ast.Identifier("i"),
            set_declaration=ast.RangeDefinition(start, end, step),
            block=[],
        )
    )


@pytest.mark.parametrize(
    "start", [ast.FloatLiteral(3.2), None, ast.Identifier("a"), ast.IntegerLiteral(2)]
)
@pytest.mark.parametrize("step", [None, ast.Identifier("c"), ast.IntegerLiteral(1)])
def test_sp_visit_for_in_loop_node_end_error(seqc_printer: SEQCPrinter, start, step):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    ar["a"] = 2
    ar["b"] = 10
    ar["c"] = 1
    seqc_printer.call_stack.push(activation_record=ar)
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.ForInLoop(
                type=ast.IntType(),
                identifier=ast.Identifier("i"),
                set_declaration=ast.RangeDefinition(start, None, step),
                block=[],
            )
        )


def test_sp_visit_for_in_loop_node_end_error_step(seqc_printer: SEQCPrinter):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    ar["a"] = 2
    ar["b"] = 10
    ar["c"] = 1
    seqc_printer.call_stack.push(activation_record=ar)
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.ForInLoop(
                type=ast.IntType(),
                identifier=ast.Identifier("i"),
                set_declaration=ast.RangeDefinition(
                    ast.IntegerLiteral(3), ast.IntegerLiteral(6), ast.FloatLiteral(0.1)
                ),
                block=[],
            )
        )


@pytest.mark.parametrize("start", [None, ast.IntegerLiteral(2)])
@pytest.mark.parametrize("step", [None, ast.IntegerLiteral(1)])
def test_sp_visit_for_in_loop_node_compiles(seqc_printer: SEQCPrinter, start, step):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    seqc_printer.call_stack.push(activation_record=ar)
    seqc_printer.visit(
        ast.ForInLoop(
            type=ast.IntType(),
            identifier=ast.Identifier("i"),
            set_declaration=ast.RangeDefinition(start, ast.IntegerLiteral(10), step),
            block=[],
        )
    )
    compile_seqc_code(seqc_printer.stream.getvalue())


def test_sp_visit_defcal(
    seqc_printer: SEQCPrinter, defcal_definition: ast.CalibrationDefinition
):
    # todo add play/capture test(s), <- covered by measurements.qasm/seqc
    # but add deticated tests
    seqc_printer.visit(defcal_definition)
    compile_seqc_code(seqc_printer.stream.getvalue())


def test_sp_visit_delay(seqc_printer: SEQCPrinter):
    seqc_printer.visit(
        ast.DelayInstruction(
            ast.DurationLiteral(1.1, ast.TimeUnit.dt), ast.Identifier("q")
        )
    )
    compile_seqc_code(seqc_printer.stream.getvalue())


def test_sp_visit_box(seqc_printer: SEQCPrinter):
    seqc_printer.visit(ast.Box(duration=None, body=[ast.IntegerLiteral(1)]))

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.Box(
                duration=ast.DurationLiteral(1.0, ast.TimeUnit.dt),
                body=[ast.IntegerLiteral(1)],
            )
        )


def test_sp_extern_argument_implemented_error(seqc_printer: SEQCPrinter):
    with pytest.raises(NotImplementedError):
        seqc_printer.visit(
            ast.ExternArgument(ast.FloatType(), ast.AccessControl["readonly"])
        )

    with pytest.raises(NotImplementedError):
        seqc_printer.visit(
            ast.ExternArgument(ast.FloatType(), ast.AccessControl["mutable"])
        )


def test_sp_visit_classical_argument_implemented_error(seqc_printer: SEQCPrinter):
    with pytest.raises(NotImplementedError):
        seqc_printer.visit(
            ast.ClassicalArgument(
                ast.FloatType(), ast.Identifier("error"), ast.AccessControl["readonly"]
            )
        )

    with pytest.raises(NotImplementedError):
        seqc_printer.visit(
            ast.ClassicalArgument(
                ast.FloatType(), ast.Identifier("error"), ast.AccessControl["mutable"]
            )
        )


def test_sp_visit_alias_statement(seqc_printer: SEQCPrinter):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    ar["qs"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    seqc_printer.call_stack.push(activation_record=ar)
    seqc_printer.visit(
        ast.AliasStatement(
            ast.Identifier("q"),
            ast.IndexExpression(
                ast.Identifier("qs"),
                [
                    ast.RangeDefinition(
                        ast.IntegerLiteral(0), ast.IntegerLiteral(10), None
                    )
                ],
            ),
        )
    )

    seqc_printer.visit(
        ast.AliasStatement(
            target=ast.Identifier("q"),
            value=ast.Concatenation(
                ast.ArrayLiteral([ast.IntegerLiteral(1), ast.IntegerLiteral(2)]),
                ast.ArrayLiteral([ast.IntegerLiteral(3), ast.IntegerLiteral(4)]),
            ),
        )
    )

    with pytest.raises(SEQCPrinterError):
        seqc_printer.interpret = False
        seqc_printer.visit(
            ast.AliasStatement(
                target=ast.Identifier("q"),
                value=ast.IndexExpression(
                    ast.Identifier("qs"),
                    [ast.IntegerLiteral(1)],
                ),
            )
        )
        seqc_printer.interpret = True

    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.AliasStatement(
                target=ast.Identifier("q"),
                value=ast.IndexExpression(
                    ast.Identifier("qs"),
                    ast.DiscreteSet([ast.IntegerLiteral(1), ast.IntegerLiteral(2)]),
                ),
            )
        )


def test_sp_visit_quantum_barrier(seqc_printer: SEQCPrinter):
    seqc_printer.visit(ast.QuantumBarrier(qubits=[]))

    with pytest.raises(SEQCPrinterError):
        ar = ActivationRecord("test", ARType.LOOP, 0)
        ar["q"] = ast.QubitDeclaration(ast.Identifier("q"))
        seqc_printer.call_stack.push(activation_record=ar)
        seqc_printer.visit(ast.QuantumBarrier(qubits=[ast.Identifier("q")]))


def test_sp_visit_classical_assignment(seqc_printer: SEQCPrinter):
    ar = ActivationRecord("test", ARType.LOOP, 0)
    ar["a"] = 0
    seqc_printer.call_stack.push(activation_record=ar)
    seqc_printer.visit(
        ast.Program(
            [
                ast.ClassicalAssignment(
                    ast.Identifier("a"),
                    ast.AssignmentOperator["="],
                    ast.IntegerLiteral(1),
                )
            ]
        )
    )
    assert ar["a"] == 1

    seqc_printer.visit(
        ast.Program(
            [
                ast.ClassicalAssignment(
                    ast.Identifier("a"),
                    ast.AssignmentOperator["="],
                    ast.BinaryExpression(
                        ast.BinaryOperator["+"],
                        ast.IntegerLiteral(1),
                        ast.IntegerLiteral(2),
                    ),
                )
            ]
        )
    )
    assert ar["a"] == 3

    ar["q"] = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    seqc_printer.visit(
        ast.Program(
            [
                ast.ClassicalAssignment(
                    ast.IndexedIdentifier(
                        ast.Identifier("q"), [[ast.IntegerLiteral(1)]]
                    ),
                    ast.AssignmentOperator["="],
                    ast.IntegerLiteral(1),
                )
            ]
        )
    )
    assert ar["q"][1] == 1


def test_split():
    """
    Demonstrative test that:
        imports qasm program code from file
        and transpiles it to seqc code
    """
    qasm_path = Path(__file__).parent.parent.parent / "qasm/split.qasm"
    with open(qasm_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)

    json_path = Path(__file__).parent.parent.parent / "setups/split.json"
    complex_setup = SetupInternal.from_json(json_path)

    def split_port(port, target_file):
        transformed_ast = CoreSplitter(port).visit(deepcopy(qasm_ast))
        RemoveUnused().visit(transformed_ast)
        seqc_printer = SEQCPrinter(io.StringIO(), complex_setup)
        seqc_printer.visit(transformed_ast)

        with open(
            Path(__file__).parent.parent.parent / f"seqc/{target_file}.seqc",
            encoding="utf_8",
        ) as seqc_file:
            seqc_code = seqc_file.read()
            compile_seqc_code(seqc_code)

        for genrated, target in zip(
            seqc_printer.stream.getvalue().split("\n"), seqc_code.split("\n")
        ):
            assert genrated == target

    split_port("awg1_ch1", "split_awg1")
    split_port("awg2_ch1", "split_awg2")


def test_play_unhandled(seqc_printer: SEQCPrinter):
    with pytest.raises(SEQCPrinterError):
        seqc_printer.visit(
            ast.Program(
                [
                    ast.FunctionCall(ast.Identifier("play"), []),
                ]
            )
        )


def test_visit_ImaginaryLiteral(seqc_printer: SEQCPrinter):
    a = seqc_printer.visit(ast.ImaginaryLiteral(1.0))

    assert isinstance(a, complex)
    assert a == 1.0j


@pytest.mark.parametrize("port", ["ch1", "sg_ch1"])
@pytest.mark.parametrize("start_time", [32, 48, 64, 128])
@pytest.mark.parametrize("time_step", [16, 32, 48, 64, 128])
def test_play_ones(
    basic_setup: SetupInternal, start_time: int, time_step: int, port: str
):
    """
    Generate for loops, over playing the ones command, of various sizes and check
    that the generated code is correct i.e. it compiles to seqc,

    Args:
        basic_setup (Setup): describes the setup of the system
        start_time (int): start time in samples
        time_step (int): time step in samples
        port (str): port to play ones on, either ch1 (HDAWG) or sg_ch1 (SHFSG)
    """

    def loop_node_generator(ids: str, block: list[ast.QASMNode]) -> ast.ForInLoop:
        return ast.ForInLoop(
            ast.IntType(),
            ast.Identifier(ids),
            ast.RangeDefinition(None, ast.IntegerLiteral(10), None),
            block=block,
        )

    ones_node = ast.FunctionCall(
        ast.Identifier("play"),
        [
            ast.Identifier("my_frame"),
            ast.FunctionCall(
                ast.Identifier("ones"),
                [
                    ast.BinaryExpression(
                        ast.BinaryOperator["+"],
                        ast.IntegerLiteral(start_time),
                        ast.BinaryExpression(
                            ast.BinaryOperator["*"],
                            ast.Identifier("i"),
                            ast.IntegerLiteral(time_step),
                        ),
                    )
                ],
            ),
        ],
    )

    setup_nodes = [
        ast.ClassicalDeclaration(ast.PortType(), ast.Identifier(port)),
        ast.ClassicalDeclaration(
            ast.FrameType(),
            ast.Identifier("my_frame"),
            ast.FunctionCall(
                ast.Identifier("newframe"),
                [
                    ast.Identifier(port),
                    ast.IntegerLiteral(128),
                    ast.IntegerLiteral(1),
                ],
            ),
        ),
    ]
    loop_node = loop_node_generator("i", [ones_node])
    program_node = ast.Program([ast.CalibrationStatement(setup_nodes + [loop_node])])
    seqc_printer = SEQCPrinter(io.StringIO(), basic_setup)
    seqc_printer.visit(program_node)
    compile_seqc_code(seqc_printer.stream.getvalue())

    loop_node2 = loop_node_generator("i", [loop_node_generator("j", [ones_node])])
    program_node2 = ast.Program([ast.CalibrationStatement(setup_nodes + [loop_node2])])
    seqc_printer2 = SEQCPrinter(io.StringIO(), basic_setup)
    seqc_printer2.visit(program_node2)


def test_command_table_for_loop():
    """
    Test for just one command table and 1 HD core
    """
    qasm_path = (
        Path(__file__).parent.parent.parent / f"qasm/command_table/for_loop.qasm"
    )
    setup_path = Path(__file__).parent.parent.parent / "setups/complex.json"
    seqc_path = Path(__file__).parent.parent.parent / "qasm/command_table/for_loop.seqc"
    hdawg_schema_path = (
        Path(__file__).parent.parent.parent / "qasm/command_table/hdawg_schema.json"
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
        print(generated)
        assert generated == target
