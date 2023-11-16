from pathlib import Path

import pytest
from numpy.random import rand, randint
from openpulse import ast, parse

from shipyard.compiler_error import SemanticError
from shipyard.mangle import Mangler
from shipyard.passes.include_statements import IncludeAnalyzer
from shipyard.passes.semantic_analysis import symbols
from shipyard.passes.semantic_analysis.scoped_symbol_table import (
    CalScopedSymbolTable,
    ScopedSymbolTable,
)
from shipyard.passes.semantic_analysis.semantic_analyzer import (
    ScopeContext,
    SemanticAnalyzer,
)


def test_end_to_end():
    """
    Demonstrative test that:
        imports qasm program code from file
        parses the code to an Abstract Syntax Tree (AST)
        performs semantic analysis on the porgram
    """
    path = Path(__file__).parent.parent.parent / "qasm/complex.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)

    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)


def qasm_files() -> list[str]:
    base_path = Path(__file__).parent.parent.parent / "qasm"
    plen = len(base_path.parts)
    QASM_FILES = list(base_path.glob("**/*.qasm"))
    return [str(Path(*path.parts[plen:])) for path in QASM_FILES]


QASM_FILES = qasm_files()


@pytest.mark.parametrize("file", QASM_FILES)
def test_files_parse(file):
    path = Path(__file__).parent.parent.parent / f"qasm/{file}"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    parse(qasm_code)


SKIP_FILES_SA = [
    "remove_unused/undeclared.qasm",
    "include_files/duplicate_error.qasm",
    "include_files/include_dne.qasm",
    "used_in_measurements/full_waveform.qasm",
]


@pytest.mark.parametrize("file", QASM_FILES)
def test_files_sa(file):
    if file in SKIP_FILES_SA:
        pytest.xfail()
    path = Path(__file__).parent.parent.parent / f"qasm/{file}"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    qasm_ast = parse(qasm_code)
    IncludeAnalyzer(path).visit(qasm_ast)
    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)


@pytest.fixture(name="semantic_analyzer")
def fixture_semantic_analyzer() -> SemanticAnalyzer:
    return SemanticAnalyzer()


def test_init_semantic_analyzer(semantic_analyzer: SemanticAnalyzer):
    assert semantic_analyzer.current_scope is None
    assert semantic_analyzer._calibration_scope is None
    assert semantic_analyzer.scope_context is None
    semantic_analyzer.scope_context = ScopeContext.GLOBAL
    assert isinstance(semantic_analyzer.calibration_scope, CalScopedSymbolTable)


def test_sa_visit_program(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(ast.Program([]))
    assert isinstance(semantic_analyzer.current_scope, ScopedSymbolTable)
    assert semantic_analyzer.scope_context == ScopeContext.GLOBAL


def test_sa_visit_extern_declaration(
    semantic_analyzer: SemanticAnalyzer, extern_declaration: ast.ExternDeclaration
):
    semantic_analyzer.visit(ast.Program([extern_declaration]))
    assert "test_extern" in semantic_analyzer.current_scope.keys()
    assert isinstance(
        semantic_analyzer.current_scope.lookup("test_extern"),
        symbols.ExternSymbol,
    )


def test_sa_visit_subroutine_definition(
    semantic_analyzer: SemanticAnalyzer, subroutine_definition: ast.SubroutineDefinition
):
    semantic_analyzer.visit(ast.Program([subroutine_definition]))
    assert "test_subroutine" in semantic_analyzer.current_scope.keys()
    subroutine_symbol = semantic_analyzer.current_scope.lookup("test_subroutine")
    assert isinstance(subroutine_symbol, symbols.SubroutineSymbol)
    for param, arg in zip(subroutine_symbol.params, subroutine_definition.arguments):
        assert param.name == arg.name.name
    assert subroutine_symbol.return_type == "FLOAT"


def test_sa_visit_quantum_gate_definition(
    semantic_analyzer: SemanticAnalyzer,
    quantum_gate_definition: ast.QuantumGateDefinition,
):
    semantic_analyzer.visit(ast.Program([quantum_gate_definition]))
    assert "test_gate" in semantic_analyzer.current_scope.keys()
    gate_symbol = semantic_analyzer.current_scope.lookup("test_gate")
    assert isinstance(gate_symbol, symbols.GateSymbol)
    assert gate_symbol.qubits[0].name == quantum_gate_definition.qubits[0].name
    assert gate_symbol.params[0].name == quantum_gate_definition.arguments[0].name


def test_sa_visit_classical_declaration(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program(
            [
                ast.ClassicalDeclaration(
                    type=ast.BoolType(), identifier=ast.Identifier("test_c_decl")
                )
            ]
        )
    )
    assert "test_c_decl" in semantic_analyzer.current_scope.keys()
    decl_symbol = semantic_analyzer.current_scope.lookup("test_c_decl")
    assert isinstance(decl_symbol, symbols.ClassicalSymbol)
    assert decl_symbol.kind == symbols.bool_type.name


def test_sa_visit_classical_declaration_array(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program(
            [
                ast.ClassicalDeclaration(
                    type=ast.ArrayType(
                        base_type=ast.FloatType, dimensions=[ast.IntegerLiteral(10)]
                    ),
                    identifier=ast.Identifier("test_array_decl"),
                )
            ]
        )
    )
    assert "test_array_decl" in semantic_analyzer.current_scope.keys()
    decl_symbol = semantic_analyzer.current_scope.lookup("test_array_decl")
    assert isinstance(decl_symbol, symbols.ClassicalSymbol)
    assert decl_symbol.kind == "ARRAY"


def test_sa_visit_constant_declaration(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program(
            [
                ast.ConstantDeclaration(
                    type=ast.BoolType(),
                    identifier=ast.Identifier("test_const_decl"),
                    init_expression=ast.BooleanLiteral(True),
                )
            ]
        )
    )
    assert "test_const_decl" in semantic_analyzer.current_scope.keys()
    decl_symbol = semantic_analyzer.current_scope.lookup("test_const_decl")
    assert isinstance(decl_symbol, symbols.ConstantSymbol)
    assert decl_symbol.kind == symbols.bool_type.name


def test_sa_visit_qubit_declaration(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program([ast.QubitDeclaration(ast.Identifier("qubit"))])
    )
    assert "qubit" in semantic_analyzer.current_scope.keys()
    decl_symbol = semantic_analyzer.current_scope.lookup("qubit")
    assert isinstance(decl_symbol, symbols.QuantumSymbol)
    assert decl_symbol.kind == symbols.qubit_type.name


def test_sa_visit_io_declaration(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program(
            [
                ast.IODeclaration(
                    io_identifier=ast.IOKeyword.input,
                    type=ast.FloatType(),
                    identifier=ast.Identifier("input"),
                ),
                ast.IODeclaration(
                    io_identifier=ast.IOKeyword.output,
                    type=ast.BitType(),
                    identifier=ast.Identifier("output"),
                ),
            ]
        )
    )
    assert "input" in semantic_analyzer.current_scope.keys()
    in_decl_symbol = semantic_analyzer.current_scope.lookup("input")
    assert isinstance(in_decl_symbol, symbols.IOSymbol)
    assert in_decl_symbol.kind == symbols.float_type.name
    assert "output" in semantic_analyzer.current_scope.keys()
    out_decl_symbol = semantic_analyzer.current_scope.lookup("output")
    assert isinstance(out_decl_symbol, symbols.IOSymbol)
    assert out_decl_symbol.kind == symbols.bit_type.name


def test_sa_visit_identifier(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.Program(
            [
                ast.ConstantDeclaration(
                    type=ast.BoolType(),
                    identifier=ast.Identifier("declared_constant"),
                    init_expression=ast.BooleanLiteral(True),
                ),
            ]
        )
    )
    # visit identifer does nothing on identifer that have been declared
    semantic_analyzer.visit(ast.Identifier("declared_constant"))

    # SemanticError is rased on undeclared identifiers
    with pytest.raises(SemanticError):
        semantic_analyzer.visit(ast.Identifier("not_declared"))

    # physical qubits do (currently not have to be declared
    semantic_analyzer.visit(ast.Identifier("$1"))


def test_sa_visit_calibration_statement(
    semantic_analyzer: SemanticAnalyzer, cal_statement: ast.CalibrationStatement
):
    semantic_analyzer.visit(ast.Program([cal_statement]))

    assert "port1" in semantic_analyzer.calibration_scope.keys()
    port_symbol = semantic_analyzer.calibration_scope.lookup("port1")
    assert isinstance(port_symbol, symbols.ClassicalSymbol)
    assert port_symbol.kind == symbols.port_type.name

    assert "frame1" in semantic_analyzer.calibration_scope.keys()
    frame_symbol = semantic_analyzer.calibration_scope.lookup("frame1")
    assert isinstance(frame_symbol, symbols.ClassicalSymbol)
    assert frame_symbol.kind == symbols.frame_type.name


def test_sa_visit_calibration_definition(
    semantic_analyzer: SemanticAnalyzer,
    defcal_definition: ast.CalibrationDefinition,
):
    semantic_analyzer.visit(ast.Program([defcal_definition]))
    defcal_name = Mangler(defcal_definition).signature().mangle()
    assert defcal_name in semantic_analyzer.calibration_scope.keys()
    defcal_symbol = semantic_analyzer.calibration_scope.lookup(defcal_name)
    assert isinstance(defcal_symbol, symbols.DefcalSymbol)
    assert defcal_symbol.return_type == symbols.bit_type.name
    assert defcal_symbol.params[0].name == defcal_definition.arguments[0].name.name
    assert defcal_symbol.qubits[0].name == defcal_definition.qubits[0].name


def test_sa_visit_calibration_definition_with_literal(
    semantic_analyzer: SemanticAnalyzer,
    defcal_definition: ast.CalibrationDefinition,
):
    defcal_definition.arguments.append(ast.IntegerLiteral(23))
    semantic_analyzer.visit(ast.Program([defcal_definition]))
    defcal_name = Mangler(defcal_definition).signature().mangle()
    assert defcal_name in semantic_analyzer.calibration_scope.keys()
    defcal_symbol = semantic_analyzer.calibration_scope.lookup(defcal_name)
    assert isinstance(defcal_symbol, symbols.DefcalSymbol)
    assert defcal_symbol.return_type == symbols.bit_type.name
    assert defcal_symbol.params[0].name == defcal_definition.arguments[0].name.name
    assert int(defcal_symbol.params[1].name) == defcal_definition.arguments[1].value
    assert defcal_symbol.qubits[0].name == defcal_definition.qubits[0].name


def test_sa_visit_quantum_gate(
    semantic_analyzer: SemanticAnalyzer,
    defcal_definition: ast.CalibrationDefinition,
    quantum_gate: ast.QuantumGate,
):
    semantic_analyzer.visit(ast.Program([defcal_definition, quantum_gate]))


def test_as_visit_quantum_gate_error(
    semantic_analyzer: SemanticAnalyzer, quantum_gate: ast.QuantumGate
):
    with pytest.raises(SemanticError):
        semantic_analyzer.visit(ast.Program([quantum_gate]))


def test_sa_visit_forinloop(
    semantic_analyzer: SemanticAnalyzer, range_definition: ast.RangeDefinition
):
    for_in_node = ast.ForInLoop(
        type=ast.IntType(),
        identifier=ast.Identifier("i"),
        set_declaration=range_definition,
        block=[],
    )
    semantic_analyzer.visit(ast.Program([for_in_node]))


def test_sa_visit_branching_statement(
    semantic_analyzer: SemanticAnalyzer,
    branching_statement: ast.BranchingStatement,
):
    semantic_analyzer.visit(ast.Program([branching_statement]))


def test_sa_visit_while_loop(
    semantic_analyzer: SemanticAnalyzer,
    while_loop: ast.WhileLoop,
):
    semantic_analyzer.visit(ast.Program([while_loop]))


def test_sa_visit_box(semantic_analyzer: SemanticAnalyzer, box: ast.Box):
    semantic_analyzer.visit(ast.Program([box]))


def test_sa_visit_unary_expression(semantic_analyzer: SemanticAnalyzer):
    semantic_analyzer.visit(
        ast.UnaryExpression(ast.UnaryOperator["!"], ast.BooleanLiteral(False))
    )
    semantic_analyzer.visit(
        ast.UnaryExpression(ast.UnaryOperator["~"], ast.BooleanLiteral(False))
    )
    semantic_analyzer.visit(
        ast.UnaryExpression(ast.UnaryOperator["-"], ast.IntegerLiteral(10))
    )
    with pytest.raises(AssertionError):
        semantic_analyzer.visit(ast.UnaryExpression("^", ast.BooleanLiteral(False)))


binary_operators = "> < >= <= == != && || | ^ & << >> + - * / % **".split(" ")


@pytest.mark.parametrize("operator", binary_operators)
def test_sa_visit_binary_expression(semantic_analyzer: SemanticAnalyzer, operator):
    semantic_analyzer.visit(
        ast.BinaryExpression(
            op=ast.BinaryOperator[operator],
            lhs=ast.BooleanLiteral(False),
            rhs=ast.BooleanLiteral(True),
        )
    )


def test_sa_visit_binary_expression_not_binary_operator(
    semantic_analyzer: SemanticAnalyzer,
):
    with pytest.raises(AssertionError):
        semantic_analyzer.visit(
            ast.BinaryExpression(
                op="not_binary_operator",
                lhs=ast.BooleanLiteral(False),
                rhs=ast.BooleanLiteral(True),
            )
        )


def test_sa_visit_function_call(
    semantic_analyzer: SemanticAnalyzer, subroutine_definition: ast.SubroutineDefinition
):
    call_node = ast.FunctionCall(
        name=ast.Identifier("test_subroutine"),
        arguments=[ast.FloatLiteral(1.1), ast.Identifier("$1")],
    )
    semantic_analyzer.visit(ast.Program([subroutine_definition, call_node]))


def test_sa_visit_cast(semantic_analyzer: SemanticAnalyzer):
    cast_node = ast.Cast(type=ast.IntType(), argument=ast.FloatLiteral(1.1))
    semantic_analyzer.visit(ast.Program([cast_node]))


def test_sa_visit_index_expression(
    semantic_analyzer: SemanticAnalyzer,
    discrete_set: ast.DiscreteSet,
    range_definition: ast.RangeDefinition,
):
    index_exp_node_literal = ast.IndexExpression(
        collection=ast.Identifier("q"), index=[ast.IntegerLiteral(1)]
    )
    index_exp_node_set = ast.IndexExpression(
        collection=ast.Identifier("q"), index=discrete_set
    )
    index_exp_node_range = ast.IndexExpression(
        collection=ast.Identifier("q"), index=[range_definition]
    )

    semantic_analyzer.visit(
        ast.Program(
            [
                ast.QubitDeclaration(ast.Identifier("q"), size=ast.IntegerLiteral(10)),
                index_exp_node_literal,
                index_exp_node_set,
                index_exp_node_range,
            ]
        )
    )


def test_sa_visit_discrete_set(
    semantic_analyzer: SemanticAnalyzer, discrete_set: ast.DiscreteSet
):
    semantic_analyzer.visit(ast.Program([discrete_set]))


def test_sa_visit_range_definition(
    semantic_analyzer: SemanticAnalyzer, range_definition: ast.RangeDefinition
):
    semantic_analyzer.visit(ast.Program([range_definition]))


def test_sa_visit_concatenation(semantic_analyzer: SemanticAnalyzer):
    concatenation = ast.Concatenation(
        lhs=ast.ArrayLiteral([ast.FloatLiteral(3.2), ast.FloatLiteral(1.2)]),
        rhs=ast.ArrayLiteral([ast.FloatLiteral(2.2), ast.FloatLiteral(4.2)]),
    )
    semantic_analyzer.visit(ast.Program([concatenation]))


def test_sa_visit_bitstring_literal():
    bs_node = ast.BitstringLiteral(7, 4)
    assert SemanticAnalyzer().visit_BitstringLiteral(bs_node).name == '"0111"'


def test_sa_visit_int_literal():
    for _ in range(100):
        rand_int = randint(-10000, 10000)
        int_node = ast.IntegerLiteral(rand_int)
        int_symbol = SemanticAnalyzer().visit_IntegerLiteral(int_node)
        assert int_symbol.name == f"{rand_int}"
        assert int_symbol.kind == "INT"


def test_sa_visit_float_literal_literal():
    for _ in range(100):
        r_number = rand()
        f_node = ast.FloatLiteral(r_number)
        f_symbol = SemanticAnalyzer().visit_FloatLiteral(f_node)
        assert f_symbol.name == f"{r_number}"
        assert f_symbol.kind == "FLOAT"


def test_sa_visit_imaginary_literal():
    for _ in range(100):
        r_number = rand()
        f_node = ast.ImaginaryLiteral(r_number)
        f_symbol = SemanticAnalyzer().visit_ImaginaryLiteral(f_node)
        assert f_symbol.name == f"{r_number}im"
        assert f_symbol.kind == "IMAGINARY"


def test_sa_visit_boolean_literal():
    true_symbol = SemanticAnalyzer().visit_BooleanLiteral(ast.BooleanLiteral(True))
    assert true_symbol.name == "true"
    assert true_symbol.kind == "BOOL"
    false_symbol = SemanticAnalyzer().visit_BooleanLiteral(ast.BooleanLiteral(False))
    assert false_symbol.name == "false"
    assert false_symbol.kind == "BOOL"


@pytest.mark.parametrize("time_unit", ["ns", "us", "ms", "s", "dt"])
def test_sa_visit_duration_literal(time_unit: str):
    r_number = rand()
    d_node = ast.DurationLiteral(r_number, ast.TimeUnit[time_unit])
    d_symbol = SemanticAnalyzer().visit_DurationLiteral(d_node)
    assert d_symbol.name == f"{r_number}{time_unit}"
    assert d_symbol.kind == "DURATION"


def test_double_declaration(semantic_analyzer: SemanticAnalyzer):
    with pytest.raises(SemanticError):
        semantic_analyzer.visit(
            ast.Program(
                [
                    ast.QubitDeclaration(ast.Identifier("qubit")),
                    ast.QubitDeclaration(ast.Identifier("qubit")),
                ]
            )
        )


def test_ensure_in_global(semantic_analyzer: SemanticAnalyzer):
    dummy_node = ast.Identifier("dummy_node")
    semantic_analyzer.scope_context = ScopeContext.GLOBAL
    semantic_analyzer.ensure_in_global_scope(dummy_node)


@pytest.mark.parametrize(
    "context", [ScopeContext.DEFCAL, ScopeContext.LOCAL, ScopeContext.SUBROUTINE]
)
def test_ensure_in_global_error(
    semantic_analyzer: SemanticAnalyzer, context: ScopeContext
):
    dummy_node = ast.Identifier("dummy_node")
    semantic_analyzer.scope_context = context
    with pytest.raises(SemanticError):
        semantic_analyzer.ensure_in_global_scope(dummy_node)


# def test_scope_context_manager():
#     assert False


# def test_local_context_manger():
#     assert False
