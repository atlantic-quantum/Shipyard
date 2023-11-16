"""pytest fixtures for openQASM AST nodes"""

import pytest
from openpulse import ast

# @pytest.fixture(name="empty_program")
# def fixture_empty_program() -> ast.Program:
#     return ast.Program([])


@pytest.fixture(name="extern_declaration")
def fixture_extern_declaration() -> ast.ExternDeclaration:
    return ast.ExternDeclaration(
        name=ast.Identifier("test_extern"),
        arguments=[ast.ExternArgument(ast.FloatType())],
        return_type=ast.BitType,
    )


@pytest.fixture(name="subroutine_definition")
def fixture_subroutine_definition() -> ast.SubroutineDefinition:
    return ast.SubroutineDefinition(
        name=ast.Identifier("test_subroutine"),
        arguments=[
            ast.ClassicalArgument(
                ast.FloatType(), ast.Identifier("classical_argument")
            ),
            ast.QuantumArgument(ast.Identifier("quantum_argument")),
        ],
        body=[ast.Statement()],
        return_type=ast.FloatType(),
    )


@pytest.fixture(name="quantum_gate_definition")
def fixture_quantum_gate_definition() -> ast.QuantumGateDefinition:
    return ast.QuantumGateDefinition(
        name=ast.Identifier("test_gate"),
        arguments=[ast.Identifier("argument")],
        qubits=[ast.Identifier("qubit")],
        body=[ast.Statement()],
    )


@pytest.fixture(name="cal_statement")
def fixture_cal_statement() -> ast.CalibrationStatement:
    return ast.CalibrationStatement(
        [
            ast.ClassicalDeclaration(
                type=ast.PortType(), identifier=ast.Identifier("port1")
            ),
            ast.ClassicalDeclaration(
                type=ast.FrameType(),
                identifier=ast.Identifier("frame1"),
                init_expression=ast.FunctionCall(
                    name=ast.Identifier("newframe"), arguments=[]
                ),
            ),
        ]
    )


@pytest.fixture(name="defcal_definition")
def fixture_defcal_definition() -> ast.CalibrationDefinition:
    return ast.CalibrationDefinition(
        name=ast.Identifier("test_defcal"),
        arguments=[
            ast.ClassicalArgument(
                ast.FloatType(), ast.Identifier("classical_argument")
            ),
        ],
        qubits=[ast.Identifier("qubit")],
        body=[ast.Statement()],
        return_type=ast.BitType(),
    )


@pytest.fixture(name="quantum_gate")
def fixture_quantum_gate() -> ast.QuantumGate:
    return ast.QuantumGate(
        modifiers=[],
        name=ast.Identifier("test_defcal"),
        arguments=[ast.FloatLiteral(1)],
        qubits=[ast.Identifier("$1")],
    )


@pytest.fixture(name="range_definition")
def fixture_range_definition() -> ast.RangeDefinition:
    return ast.RangeDefinition(
        start=ast.IntegerLiteral(0),
        end=ast.IntegerLiteral(10),
        step=ast.IntegerLiteral(1),
    )


@pytest.fixture(name="discrete_set")
def fixture_discrete_set() -> ast.DiscreteSet:
    return ast.DiscreteSet([ast.FloatLiteral(3.2), ast.FloatLiteral(1.2)])


@pytest.fixture(name="branching_statement")
def fixture_branching_statement() -> ast.BranchingStatement:
    return ast.BranchingStatement(
        condition=ast.BooleanLiteral(True),
        if_block=[ast.Statement()],
        else_block=[ast.Statement()],
    )


@pytest.fixture(name="while_loop")
def fixture_while_loop() -> ast.WhileLoop:
    return ast.WhileLoop(
        while_condition=ast.BooleanLiteral(True), block=[ast.Statement()]
    )


@pytest.fixture(name="box")
def fixture_box() -> ast.Box:
    return ast.Box(
        duration=ast.DurationLiteral(1.0, ast.TimeUnit.ns), body=[ast.Statement()]
    )
