from pathlib import Path

import numpy as np
import pytest
from openpulse import ast, parse

from shipyard.awg_core.awg_core import CoreType
from shipyard.call_stack import ActivationRecord, ARType
from shipyard.compiler import Compiler
from shipyard.compiler_error import Error
from shipyard.duration import Duration, TimeUnits
from shipyard.mangle import Mangler
from shipyard.passes.duration_transformer import DurationTransformer
from shipyard.passes.interpreter import Interpreter
from shipyard.passes.resolve_io_declaration import ResolveIODeclaration
from shipyard.passes.semantic_analysis.semantic_analyzer import SemanticAnalyzer
from shipyard.printers.zi import waveform_functions
from shipyard.setup.internal import Frame, Instrument, Port, SetupInternal


def test_QubitDeclaration():
    interp = Interpreter()
    qd_node = ast.QubitDeclaration(
        qubit=ast.Identifier("dummy"),
        size=ast.IntegerLiteral(value=2),
    )
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    interp.call_stack.push(activation_record)
    interp.visit_QubitDeclaration(qd_node)
    assert interp.call_stack.peek()["dummy"] == ["$0", "$1"]


def test_visit_SubroutineDefinition():
    interp = Interpreter()

    sr_node = ast.SubroutineDefinition(
        name=ast.Identifier("dummy"),
        arguments=[],
        return_type=ast.IntegerLiteral(value=1),
        body=["fake body for subroutine"],
    )
    interp.visit_SubroutineDefinition(sr_node)
    assert interp.subroutines["dummy"] == sr_node


def test_visit_Identifier():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = 1
    interp.call_stack.push(activation_record)
    i_node = ast.Identifier("a")
    assert interp.visit_Identifier(i_node) == 1


@pytest.mark.parametrize(
    "operator, expected, lvalue, rvalue",
    [
        (ast.BinaryOperator["+"], 3, 2, 1),
        (ast.BinaryOperator["-"], 1, 2, 1),
        (ast.BinaryOperator["*"], 2, 2, 1),
        (ast.BinaryOperator["/"], 2, 2, 1),
        (ast.BinaryOperator[">"], True, 2, 1),
        (ast.BinaryOperator[">"], False, 1, 1),
        (ast.BinaryOperator["<"], True, 1, 2),
        (ast.BinaryOperator["<"], False, 1, 1),
        (ast.BinaryOperator[">="], True, 2, 1),
        (ast.BinaryOperator[">="], True, 1, 1),
        (ast.BinaryOperator[">="], False, 1, 2),
        (ast.BinaryOperator["<="], False, 2, 1),
        (ast.BinaryOperator["=="], False, 2, 1),
        (ast.BinaryOperator["!="], True, 2, 1),
        (ast.BinaryOperator["!="], False, 1, 1),
        # (ast.BinaryOperator["&&"], True, False, True),
        # (ast.BinaryOperator["||"], 2, 2, 1),
        (ast.BinaryOperator["|"], 3, 2, 1),
        (ast.BinaryOperator["^"], 3, 2, 1),
        (ast.BinaryOperator["&"], 0, 2, 1),
        (ast.BinaryOperator["<<"], 16, 4, 2),
        (ast.BinaryOperator[">>"], 1, 4, 2),
        (ast.BinaryOperator["%"], 3, 7, 4),
        (ast.BinaryOperator["**"], 9, 3, 2),
    ],
)
def test_visit_BinaryExpression_numerical(
    operator: ast.BinaryOperator, expected, lvalue, rvalue
):
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = rvalue
    interp.call_stack.push(activation_record)
    i_node = ast.Identifier("a")
    int_node = ast.IntegerLiteral(value=lvalue)
    be_node_plus = ast.BinaryExpression(op=operator, lhs=int_node, rhs=i_node)
    assert interp.visit_BinaryExpression(be_node_plus) == expected


@pytest.mark.parametrize(
    "operator, expected, lvalue, rvalue",
    [
        (ast.BinaryOperator["&&"], False, False, True),
        (ast.BinaryOperator["&&"], True, True, True),
        (ast.BinaryOperator["||"], True, True, False),
        (ast.BinaryOperator["||"], False, False, False),
    ],
)
def test_visit_BinaryExpression_booleans(
    operator: ast.BinaryOperator, expected, lvalue, rvalue
):
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = rvalue
    interp.call_stack.push(activation_record)
    i_node = ast.Identifier("a")
    int_node = ast.BooleanLiteral(value=lvalue)
    be_node_plus = ast.BinaryExpression(op=operator, lhs=int_node, rhs=i_node)
    assert interp.visit_BinaryExpression(be_node_plus) == expected


@pytest.mark.parametrize(
    "operator, expected, val",
    [
        (ast.UnaryOperator["-"], -2, 2),
        (ast.UnaryOperator["!"], False, True),
        (ast.UnaryOperator["!"], True, False),
        (ast.UnaryOperator["~"], -5, 4),
    ],
)
def test_visit_UnaryExpression(operator: ast.UnaryOperator, expected, val):
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = val
    interp.call_stack.push(activation_record)
    i_node = ast.Identifier("a")
    u_node = ast.UnaryExpression(op=operator, expression=i_node)
    assert interp.visit_UnaryExpression(u_node) == expected


def test_visit_FloatLiteral():
    fl_node = ast.FloatLiteral(value=1.1)
    assert Interpreter().visit_FloatLiteral(fl_node) == 1.1


def test_visit_ImaginaryLiteral():
    il_node = ast.ImaginaryLiteral(value=3.0)
    assert Interpreter().visit_ImaginaryLiteral(il_node) == complex(0, 3.0)
    assert Interpreter().visit_ImaginaryLiteral(il_node) == 0 + 3.0j


def test_visit_DurationLiteral():
    d_node = ast.DurationLiteral(value=63.2, unit="s")
    assert Interpreter().visit_DurationLiteral(d_node) == 63.2


def test_IntegerLiteral():
    int_node = ast.IntegerLiteral(value=22)
    assert Interpreter().visit_IntegerLiteral(int_node) == 22


def test_ArrayLiteral():
    # all the values in the array
    first = ast.IntegerLiteral(value=1)
    second = ast.IntegerLiteral(value=2)
    third = ast.IntegerLiteral(value=3)
    fourth = ast.IntegerLiteral(value=4)
    arr_node_1 = ast.ArrayLiteral(
        values=[
            ast.ArrayLiteral(values=[first, second]),
            ast.ArrayLiteral(values=[third, fourth]),
        ]
    )
    arr_node_2 = ast.ArrayLiteral(
        values=[ast.ArrayLiteral(values=[first, second, third, fourth])]
    )
    assert np.all(
        Interpreter().visit_ArrayLiteral(arr_node_1) == np.array([[1, 2], [3, 4]])
    )
    assert np.all(
        Interpreter().visit_ArrayLiteral(arr_node_2) == np.array([[1, 2, 3, 4]])
    )


def test_visit_IndexExpression():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = np.array([1, 2, 3, 4])
    interp.call_stack.push(activation_record)
    i_node = ast.Identifier(name="a")
    int_node = ast.IntegerLiteral(value=1)
    ie_node = ast.IndexExpression(collection=i_node, index=[int_node])
    ie_node2 = ast.IndexExpression(
        collection=i_node, index=[int_node, ast.IntegerLiteral(value=2)]
    )
    ie_node3 = ast.IndexExpression(
        collection=i_node,
        index=ast.RangeDefinition(
            start=ast.IntegerLiteral(value=1),
            end=ast.IntegerLiteral(value=4),
            step=None,
        ),
    )
    assert interp.visit_IndexExpression(ie_node) == 2
    assert np.all(interp.visit_IndexExpression(ie_node2) == [2, 3])
    assert np.all(interp.visit_IndexExpression(ie_node3) == [2, 3, 4])


def test_visit_Concatenation():
    arr_1 = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=1), ast.IntegerLiteral(value=2)]
    )
    arr_2 = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=3), ast.IntegerLiteral(value=4)]
    )
    con_node = ast.Concatenation(lhs=arr_1, rhs=arr_2)
    assert np.all(Interpreter().visit_Concatenation(con_node) == np.array([1, 2, 3, 4]))


def test_visit_QuantumGate():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = Path(__file__).parent.parent / "qasm/interpreter/quantumgate.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"passing": 2, "last_int": 5}
    assert pv.defcal_names == ["_ZN5dummy_PN1_INT_QN1_$0_R"]
    assert "_ZN5dummy_PN1_INT_QN1_$0_R" in pv.defcal_nodes.keys()

    with pytest.raises(Error):
        qgate = ast.QuantumGate(
            modifiers=[ast.QuantumGateModifier(ast.GateModifierName["inv"])],
            name=ast.Identifier("dummy"),
            arguments=[ast.IntegerLiteral(1)],
            qubits=[ast.Identifier("$0")],
        )

        signature = Mangler(qgate).signature()
        pv.defcal_names.append(signature.mangle())

        pv.visit(qgate)

    pv.call_stack.pop()


def test_visit_QuantumMeasurement():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = Path(__file__).parent.parent / "qasm/interpreter/quantummeasure.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"dummy_var": 3}
    assert pv.defcal_names == ["_ZN7measure_PN0_QN1_$0_R"]
    assert "_ZN7measure_PN0_QN1_$0_R" in pv.defcal_nodes.keys()
    pv.call_stack.pop()


def test_visit_QuantumMeasurementStatement():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = (
        Path(__file__).parent.parent / "qasm/interpreter/quantummeasurestatement.qasm"
    )
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert np.all(pv.call_stack.peek().members["bit_reg"] == np.array([3, 0]))
    assert np.all(pv.call_stack.peek().members["b"] == 3)
    assert pv.defcal_names == ["_ZN7measure_PN0_QN1_$0_RINT"]
    assert "_ZN7measure_PN0_QN1_$0_RINT" in pv.defcal_nodes.keys()
    pv.call_stack.pop()


def test_visit_QuantumReset():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = Path(__file__).parent.parent / "qasm/interpreter/quantumreset.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"dummy_var": 3}
    assert pv.defcal_names == ["_ZN5reset_PN0_QN1_$0_R"]
    assert "_ZN5reset_PN0_QN1_$0_R" in pv.defcal_nodes.keys()
    pv.call_stack.pop()


# def test_visit_ClassicalArgument():
#     interp = Interpreter()
#     activation_record = ActivationRecord(
#             name="main", ar_type=ARType.PROGRAM, nesting_level=1
#     )
#     activation_record.members["a"] = 1
#     interp.call_stack.push(activation_record)
#     ca_node =ast.ClassicalArgument(type=ast.ClassicalType(), name=ast.Identifier("a"))
#     assert interp.visit_ClassicalArgument(ca_node) == 1
#     interp.call_stack.pop()


@pytest.mark.parametrize(
    "init, expected",
    [
        (ast.IntegerLiteral(value=1), 1),
        (ast.FloatLiteral(value=1.1), 1.1),
        (ast.DurationLiteral(value=2.1, unit="s"), 2.1),
        (ast.ImaginaryLiteral(value=3.0), complex(0, 3.0)),
        (
            ast.BinaryExpression(
                op=ast.BinaryOperator["+"],
                lhs=ast.IntegerLiteral(value=1),
                rhs=ast.IntegerLiteral(value=2),
            ),
            3,
        ),
    ],
)
def test_visit_ConstantDeclaration(init, expected):
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    interp.call_stack.push(activation_record)
    cd_node = ast.ConstantDeclaration(
        type=ast.ClassicalType(),
        identifier=ast.Identifier("a"),
        init_expression=init,
    )
    interp.visit_ConstantDeclaration(cd_node)

    assert interp.call_stack.peek().members["a"] == expected
    interp.call_stack.pop()


def test_visit_ConstantDeclaration_identifier():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = 1
    interp.call_stack.push(activation_record)
    cd_node = ast.ConstantDeclaration(
        type=ast.ClassicalType(),
        identifier=ast.Identifier("b"),
        init_expression=ast.Identifier("a"),
    )
    interp.visit_ConstantDeclaration(cd_node)
    assert interp.call_stack.peek().members["b"] == 1
    interp.call_stack.pop()


def test_visit_ConstantDeclaration_array():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    interp.call_stack.push(activation_record)
    arr_node = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=1), ast.IntegerLiteral(value=2)]
    )
    cd_node = ast.ConstantDeclaration(
        type=ast.ClassicalType(),
        identifier=ast.Identifier("a"),
        init_expression=arr_node,
    )
    interp.visit_ConstantDeclaration(cd_node)
    assert np.all(interp.call_stack.peek().members["a"] == np.array([1, 2]))
    interp.call_stack.pop()


def test_visit_CalibrationDefinition():
    interp = Interpreter()

    cal_node = ast.CalibrationDefinition(
        name=ast.Identifier("dummy"),
        arguments=[],
        qubits=[ast.Identifier("$0")],
        return_type=ast.IntegerLiteral(value=1),
        body="fake body for calibration",
    )
    interp.visit_CalibrationDefinition(cal_node)
    assert (
        interp.defcal_nodes["_ZN5dummy_PN0_QN1_$0_R1"].body
        == "fake body for calibration"
    )
    assert interp.defcal_nodes["_ZN5dummy_PN0_QN1_$0_R1"].qubits[0].name == "$0"


def test_visit_CalibrationStatement():
    cal_node = ast.CalibrationStatement(
        body=[
            ast.ConstantDeclaration(
                type=ast.ClassicalType(),
                identifier=ast.Identifier("a"),
                init_expression=ast.BinaryExpression(
                    op=ast.BinaryOperator["+"],
                    lhs=ast.IntegerLiteral(value=1),
                    rhs=ast.IntegerLiteral(value=2),
                ),
            ),
            ast.ConstantDeclaration(
                type=ast.ClassicalType(),
                identifier=ast.Identifier("b"),
                init_expression=ast.IntegerLiteral(value=1),
            ),
        ]
    )
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    interp.call_stack.push(activation_record)
    interp.visit_CalibrationStatement(cal_node)
    assert interp.calibration_scope == {"a": 3, "b": 1}


def test_visit_WhileLoop():
    interpreter = Interpreter()
    ar = ActivationRecord(name="main", ar_type=ARType.PROGRAM, nesting_level=1)
    ar["i"] = 0
    qasm_str = """OPENQASM 3.0;
    int i = 0;
    while (i < 10) {
        i = i + 1;
    }
    """
    qasm_ast = parse(qasm_str)
    interpreter.call_stack.push(ar)
    interpreter.visit(qasm_ast.statements[1])
    assert ar["i"] == 10


def test_visit_ForInLoop():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = Path(__file__).parent.parent / "qasm/interpreter/forloop.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"n_shots": 3, "n_steps": 2, "counter": 6}
    pv.call_stack.pop()


def test_visit_AliasStatement():
    arr_1 = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=1), ast.IntegerLiteral(value=2)]
    )
    arr_2 = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=3), ast.IntegerLiteral(value=4)]
    )
    con_node = ast.Concatenation(lhs=arr_1, rhs=arr_2)
    al_node = ast.AliasStatement(target=ast.Identifier("a"), value=con_node)

    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    interp.call_stack.push(activation_record)
    interp.visit_AliasStatement(al_node)
    assert np.all(interp.call_stack.peek().members["a"] == np.array([1, 2, 3, 4]))


def test_visit_AliasStatement_identifier():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["my_arr"] = np.array([1, 2])
    interp.call_stack.push(activation_record)
    arr_2 = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=3), ast.IntegerLiteral(value=4)]
    )
    con_node = ast.Concatenation(lhs=ast.Identifier("my_arr"), rhs=arr_2)
    al_node = ast.AliasStatement(target=ast.Identifier("a"), value=con_node)
    interp.visit_AliasStatement(al_node)
    assert np.all(interp.call_stack.peek().members["a"] == np.array([1, 2, 3, 4]))


def test_visit_RangeDefinition():
    interp = Interpreter()
    rd_node = ast.RangeDefinition(
        start=ast.IntegerLiteral(value=1),
        end=ast.IntegerLiteral(value=10),
        step=ast.IntegerLiteral(value=2),
    )
    start, stop, step = interp.visit_RangeDefinition(rd_node)
    assert start == 1
    assert stop == 10
    assert step == 2


def test_visit_DiscreteSet():
    interp = Interpreter()
    ds_node = ast.DiscreteSet(
        values=[ast.IntegerLiteral(value=1), ast.IntegerLiteral(value=2)]
    )
    values = interp.visit_DiscreteSet(ds_node)
    assert values == {2, 1}


@pytest.mark.parametrize(
    "rval, original, expected",
    [
        (ast.IntegerLiteral(value=1), 2, 1),
        (ast.FloatLiteral(value=1.1), 2.1, 1.1),
        (ast.DurationLiteral(value=2.1, unit="s"), 3.1, 2.1),
        (ast.ImaginaryLiteral(value=3.0), 4.0, 3.0j),
        (
            ast.BinaryExpression(
                op=ast.BinaryOperator["+"],
                lhs=ast.IntegerLiteral(value=1),
                rhs=ast.IntegerLiteral(value=2),
            ),
            2,
            3,
        ),
    ],
)
def test_visit_ClassicalAssignment(rval, original, expected):
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members = {"a": original}
    interp.call_stack.push(activation_record)
    int_node = ast.ClassicalAssignment(
        op=ast.AssignmentOperator["="],
        lvalue=ast.Identifier("a"),
        rvalue=rval,
    )

    interp.visit_ClassicalAssignment(int_node)
    assert interp.call_stack.peek().members["a"] == expected


def test_visit_ClassicalAssignment_identifier():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = 1
    activation_record.members["b"] = 2
    interp.call_stack.push(activation_record)
    int_node = ast.ClassicalAssignment(
        op=ast.AssignmentOperator["="],
        lvalue=ast.Identifier("a"),
        rvalue=ast.Identifier("b"),
    )
    interp.visit_ClassicalAssignment(int_node)
    assert interp.call_stack.peek().members["a"] == 2
    assert interp.call_stack.peek().members["b"] == 2


def test_ClassicalAssignment_array():
    interp = Interpreter()
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    activation_record.members["a"] = np.array([3, 4])
    arr_node = ast.ArrayLiteral(
        values=[ast.IntegerLiteral(value=1), ast.IntegerLiteral(value=2)]
    )
    interp.call_stack.push(activation_record)
    ca_node = ast.ClassicalAssignment(
        op=ast.AssignmentOperator["="],
        lvalue=ast.Identifier("a"),
        rvalue=arr_node,
    )
    interp.visit_ClassicalAssignment(ca_node)
    assert np.all(interp.call_stack.peek().members["a"] == np.array([1, 2]))
    interp.call_stack.pop()


# def test_visit_Annotation():
#     with warnings.catch_warnings(record=True) as w:
#         an_node = ast.Annotation(keyword="dummy")
#         Interpreter().visit_Annotation(an_node)
#         assert len(w) == 1

# def test_visit_Pragma():
#     with warnings.catch_warnings(record=True) as w:
#         pr_node = ast.Pragma(command="dummy")
#         Interpreter().visit_Pragma(pr_node)
#         assert len(w) == 1


def test_visit_FunctionCall():
    setup_path = Path(__file__).parent.parent / "setups/basic.json"
    qasm_path = (
        Path(__file__).parent.parent / "qasm/interpreter/nested_subroutines.qasm"
    )
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"dummy": 16}
    pv.call_stack.pop()


def test_visit_FunctionCall_phase_and_freq():
    setup_path = Path(__file__).parent.parent / "setups/complex.json"
    qasm_path = Path(__file__).parent.parent / "qasm/interpreter/phase_freq.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = Interpreter(SetupInternal.from_json(setup_path), waveform_functions.__dict__)
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"f1": 3000.0, "f2": 4000.0, "p1": 1.0}
    assert pv.calibration_scope == {
        "dac1": Port(
            name="dac1",
            instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
            core=Port.Core(type=CoreType.HD, index=2, channels=[1]),
        ),
        "dac0": Port(
            name="dac0",
            instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
            core=Port.Core(type=CoreType.HD, index=1, channels=[1]),
        ),
        "spec_frame": Frame(
            name="spec_frame",
            port=Port(
                name="dac1",
                instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
                core=Port.Core(type=CoreType.HD, index=2, channels=[1]),
            ),
            frequency=5000.0,
            phase=2.0,
            time=Duration(time=0.0, unit=TimeUnits.dt),
        ),
        "tx_frame_0": Frame(
            name="tx_frame_0",
            port=Port(
                name="dac0",
                instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
                core=Port.Core(type=CoreType.HD, index=1, channels=[1]),
            ),
            frequency=3000.0,
            phase=1.5,
            time=Duration(time=0.0, unit=TimeUnits.dt),
        ),
    }
    pv.call_stack.pop()


def test_compile_out_errors():
    interp = Interpreter()

    with pytest.raises(Error):
        interp.visit_Include(ast.Include("file.qasm"))

    with pytest.raises(Error):
        interp.visit_QuantumGateDefinition(
            ast.QuantumGateDefinition("dummy", [], [], [])
        )

    with pytest.raises(Error):
        interp.visit_IODeclaration(
            ast.IODeclaration(
                ast.IOKeyword["input"], ast.AngleType(), ast.Identifier("a")
            )
        )

    with pytest.raises(Error):
        interp.visit_DurationOf(ast.DurationOf([ast.Identifier("a")]))

    with pytest.raises(Error):
        interp.visit_SizeOf(ast.SizeOf(ast.Identifier("a")))


def test_visit_ClassicalDeclaration_no_init():
    interp = Interpreter()
    program = ast.Program(
        [ast.ClassicalDeclaration(ast.FloatType(), ast.Identifier("a"))]
    )
    interp.visit(program)


def test_visit_QuantumArgument():
    interp = Interpreter()
    program = ast.Program(
        [
            ast.ClassicalDeclaration(
                ast.FloatType(), ast.Identifier("a"), ast.IntegerLiteral(1)
            ),
            ast.QuantumArgument(ast.Identifier("a")),
        ]
    )
    interp.visit(program)


def test_not_implemented_error():
    interp = Interpreter()

    with pytest.raises(NotImplementedError):
        interp.visit_BreakStatement(ast.BreakStatement())

    with pytest.raises(NotImplementedError):
        interp.visit_ContinueStatement(ast.ContinueStatement())

    with pytest.raises(NotImplementedError):
        interp.visit_EndStatement(ast.EndStatement())
