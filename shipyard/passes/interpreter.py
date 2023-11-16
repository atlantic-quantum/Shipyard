# pylint: disable=C0302
# Too many lines in module
"""
Interpreter:
Class for evaluating OpenQASM ASTs
"""

import functools
import operator
from contextlib import contextmanager

import numpy as np
from openpulse import ast

from ..call_stack import ActivationRecord, ARType, CallStack
from ..compiler_error import Error, ErrorCode, SemanticError
from ..logger import LOGGER
from ..mangle import Mangler
from ..setup.internal import Frame, SetupInternal
from ..visitors import GenericVisitor as QASMVisitor

# pylint: disable=W0221,R0904


def _maybe_annotated(method):  # pragma: no cover
    @functools.wraps(method)
    def annotated(self: "Interpreter", node: ast.Statement) -> None:
        for annotation in node.annotations:
            self.visit(annotation)
        return method(self, node)

    return annotated


# redefine IndexElement as it is not accessible from the openqasm3.ast
IndexElement = ast.DiscreteSet | list[ast.Expression | ast.RangeDefinition]


class Interpreter(QASMVisitor):
    """AST-visitor for evaluating OpenQASM code.

    Class maintains a call stack of activation records, which hold variable/literals
    information. Also maintains record of external functions, subroutines, and
    quantum gates.

    If subclassing, generally only the specialised ``visit_*`` methods need to be
    overridden.  These are derived from the base class, and use the name of the
    relevant :mod:`AST node <.ast>` verbatim after ``visit_``.

    Based on the openQASM3 Printer"""

    def __init__(
        self,
        setup: SetupInternal = None,
        external_funcs: dict = None,
        visit_loops: bool = True,
    ):
        self.call_stack = CallStack()
        self.setup = setup
        self.external_funcs = external_funcs
        self.calibration_scope = {}
        self.defcal_nodes = {}
        self.defcal_names = []
        self.subroutines = {}
        self.visit_loops = visit_loops

    def visit_Program(self, node: ast.Program) -> None:
        activation_record = ActivationRecord(
            name="main", ar_type=ARType.PROGRAM, nesting_level=1
        )
        with self.ar_context_manager(activation_record):
            for statement in node.statements:
                self.visit(statement)

    @_maybe_annotated
    def visit_Include(self, node: ast.Include) -> None:
        """Include statements should be resolved at this point"""
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_QubitDeclaration(self, node: ast.QubitDeclaration) -> None:
        """Qubit declarations not supported"""
        activation_record = self.call_stack.peek()
        if node.size is not None:
            size = self.visit(node.size)
            activation_record[node.qubit.name] = [f"${x}" for x in range(size)]

    def visit_SubroutineDefinition(self, node: ast.SubroutineDefinition) -> None:
        """Add subroutine to subroutines dict"""
        self.subroutines[node.name.name] = node

    @_maybe_annotated
    def visit_QuantumGateDefinition(self, node: ast.QuantumGateDefinition) -> None:
        """Not supporting quantum gate definitions"""
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_ExternDeclaration(self, node: ast.ExternDeclaration) -> None:
        """Pass over extern declarations"""

    def visit_Identifier(self, node: ast.Identifier) -> None:
        """Return the value associated with a given identifier"""
        try:
            activation_record = self.call_stack.down_stack(node.name)
            return activation_record[node.name]
        except KeyError as exc:
            raise SemanticError(
                ErrorCode.ID_NOT_FOUND,
                f"Identifier: {node.name} not found in call stack",
            ) from exc

    def visit_BooleanLiteral(self, node: ast.BooleanLiteral) -> bool:
        """Return the value of a boolean literal"""
        return node.value

    def visit_BinaryExpression(self, node: ast.BinaryExpression) -> None:
        """Evaluate and return the binary expression"""
        left = self.visit(node.lhs)
        right = self.visit(node.rhs)
        op = node.op
        return binary_ops[op.value](left, right)

    def visit_UnaryExpression(self, node: ast.UnaryExpression) -> None:
        """Evaluate and return the unary expression"""
        op = node.op
        return unary_ops[op.value](self.visit(node.expression))

    def visit_FloatLiteral(self, node: ast.FloatLiteral) -> None:
        """Return the value of a float literal"""
        return node.value

    def visit_ImaginaryLiteral(self, node: ast.ImaginaryLiteral) -> None:
        """Return the value of an imaginary literal"""
        return complex(0, node.value)

    def visit_DurationLiteral(self, node: ast.DurationLiteral) -> None:
        """Return the value of a duration literal"""
        return node.value

    def visit_IntegerLiteral(self, node: ast.IntegerLiteral) -> None:
        """Return the value of an integer literal"""
        return node.value

    def visit_ArrayLiteral(self, node: ast.ArrayLiteral) -> None:
        """Return the value of an array literal"""
        return np.array([self.visit(val) for val in node.values])

    def visit_IndexExpression(self, node: ast.IndexExpression) -> None:
        """Return the value of an index expression. Assumes the IndexExpression
        is a discrete set (ex. arr[{0, 1, 2}]), range (ex. arr[0:3:1]), or
        list of expressions (ex. arr[0:2, 4])"""
        activation_record = self.call_stack.down_stack(node.collection.name)
        if isinstance(node.index, ast.DiscreteSet):
            return activation_record[node.collection.name][self.visit(node.index)]
        if isinstance(node.index, ast.RangeDefinition):
            start, end, step = self.visit(node.index)
            return activation_record[node.collection.name][start:end:step]
        # assume list of expressions
        indices = [self.visit(index) for index in node.index]
        return activation_record[node.collection.name][indices]

    def visit_ReturnStatement(self, node: ast.ReturnStatement) -> None:
        """Return the value of a return statement"""
        return self.visit(node.expression)

    def visit_Concatenation(self, node: ast.Concatenation) -> None:
        """
        Concatenation node visitor:
            joins elements in OpenQASM concatenation statement

            example:
                qasm: 'a ++ b ++ c;'

        Args:
            node (ast.Concatenation): openQASM concatenation AST node
        """
        return np.concatenate([self.visit(node.lhs), self.visit(node.rhs)])

    def quantum_gate_helper(
        self, node: ast.QuantumMeasurementStatement | ast.QuantumReset | ast.QuantumGate
    ) -> None:
        """
        Helper function for QuantumGate, QuantumMeasurementStatement, and QuantumReset.
        Puts the calibration dictionary onto the stack and then adds a new activation
        record for the quantum gate, measurement, or reset. In the case of a
        QuantumGate, the function first adds the arguments to the activation record,
        then the statements in the measurement, reset, or gate body are visited.
        """
        curr_nesting = self.call_stack.peek().nesting_level
        outer_activation_record = ActivationRecord(
            name="calibration",
            ar_type=ARType.CALIBRATION,
            nesting_level=curr_nesting + 1,
        )
        outer_activation_record.members = self.calibration_scope
        with self.ar_context_manager(outer_activation_record):
            inner_activation_record = ActivationRecord(
                name="defcal", ar_type=ARType.DEFCAL, nesting_level=curr_nesting + 2
            )
            with self.ar_context_manager(inner_activation_record):
                signature = Mangler(node).signature()
                mangled_name = signature.match(self.defcal_names)[0]

                if isinstance(node, ast.QuantumGate):
                    if node.modifiers:
                        raise self.compile_out(node.modifiers)
                    args = [self.visit(arg) for arg in node.arguments]
                    node = self.defcal_nodes[mangled_name]
                    inner_activation_record = self.call_stack.peek()
                    for arg, val in zip(
                        node.arguments, args
                    ):  # ignores Integer arguments
                        if isinstance(arg, ast.ClassicalArgument):
                            inner_activation_record[arg.name.name] = val
                for statement in self.defcal_nodes[mangled_name].body:
                    if isinstance(statement, ast.ReturnStatement):
                        returnval = self.visit(statement)
                        return returnval
                    self.visit(statement)

    @_maybe_annotated
    def visit_QuantumGate(self, node: ast.QuantumGate) -> None:
        """
        QuantumGate node visitor:
            Visits and evaluates quantum gate call, at this point the gate operation
            should have a calibration definition (defcal).

            Example:
                qasm:
                    defcal x90 $0 {...}
                  >>x90 $0;
                ->  ^^^^^^^
        Args:
            node (ast.QuantumGate): openQASM QuantumGate AST node

        Optionally returns elements based on gate definition
        """
        self.quantum_gate_helper(node)

    @_maybe_annotated
    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement
    ) -> None:
        """
        QuantumMeasurementStatement node visitor:
            Visits and evaluates quantum measurement call, at this point the quantum
            measurement statement should have a calibration definition (defcal)

            Example:
                qasm:
                    defcal measure $0 -> bit {...}
                  >>b1 = measure $0;
                ->       ^^^^^^^^^^^
        Args:
            node (ast.QuantumMeasurementStatement): openQASM
            QuantumMeasurementStatement AST node
        Optionally allows for returns based on quantum measurement definition
        (gate definition)
        """
        match node.target:
            case ast.Identifier():
                name = node.target.name
                activation_record = self.call_stack.down_stack(name)
                activation_record[name] = self.quantum_gate_helper(node)
            case ast.IndexedIdentifier():
                activation_record = self.call_stack.down_stack(node.target.name.name)
                activation_record[node.target.name.name][
                    [self.visit(index) for index in node.target.indices[0]]
                ] = self.quantum_gate_helper(node)
            case _:
                self.quantum_gate_helper(node)

    @_maybe_annotated
    def visit_QuantumReset(self, node: ast.QuantumReset) -> None:
        """
        QuantumReset node visitor:
            Visits and evaluates quantum reset call, at this point the quantum reset
            should have a calibration definition (defcal)

            Example:
                qasm:
                    defcal reset $0 {...}
                  >>reset $0;
                ->  ^^^^^^^^^

        Args:
            node (ast.QuantumReset): openQASM QuantumReset AST node
        """
        self.quantum_gate_helper(node)

    def visit_QuantumMeasurement(self, node: ast.QuantumMeasurement) -> None:
        """
        QuantumMeasurement node visitor:
            Visits and evaluates quantum measurement call, at this point the quantum
            measurement statement should have a calibration definition (defcal). Differs
            from QuantumMeasurementStatement in that it does not allow for returns

            Example:
                qasm:
                    defcal measure $0 -> bit {...}
                  >>measure $0;
                    ^^^^^^^^^^^
        Args:
            node (ast.QuantumMeasurement): openQASM QuantumMeasurement AST node
        Optionally allows for returns based on quantum measurement definition
        (gate definition)
        """
        self.quantum_gate_helper(node)

    def visit_ExternArgument(self, node: ast.ExternArgument) -> None:
        """Passes extern argument call"""

    def visit_DiscreteSet(self, node: ast.DiscreteSet) -> None:
        """Returns a set of discrete values"""
        discrete_set = []
        for i in node.values:
            discrete_set.append(self.visit(i))
        return set(discrete_set)

    def visit_RangeDefinition(self, node: ast.RangeDefinition) -> None:
        """Returns tuple of (start,end,step) or default values"""
        start = self.visit(node.start) if node.start else 0
        end = self.visit(node.end) if node.end else None
        step = self.visit(node.step) if node.step else 1
        return (start, end, step)

    def visit_ExpressionStatement(self, node: ast.ExpressionStatement) -> None:
        """Visits expression statement"""
        return self.visit(node.expression)

    def generic_visit(self, node: ast.QASMNode) -> None:
        LOGGER.debug("Generic visit: %s", node)

    @_maybe_annotated
    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration) -> None:
        """Saves classical declaration to activation record"""
        activation_record = self.call_stack.peek()
        match node:
            case ast.ClassicalDeclaration(type=ast.PortType()):
                name = node.identifier.name
                # activation_record = self.call_stack.peek()
                activation_record[name] = self.setup.ports[name]
            case ast.ClassicalDeclaration(
                type=ast.FrameType(),
                init_expression=ast.FunctionCall(name=ast.Identifier("newframe")),
            ):
                call = node.init_expression
                assert isinstance(call, ast.FunctionCall)
                assert len(call.arguments) == 3
                port = call.arguments[0].name
                frequency = self.visit(call.arguments[1])
                phase = self.visit(call.arguments[2])
                frame = Frame(
                    name=node.identifier.name,
                    port=activation_record[port],
                    frequency=frequency,
                    phase=phase,
                )

                activation_record[frame.name] = frame
            case ast.ClassicalDeclaration(type=ast.ArrayType()):
                if node.init_expression is None:
                    shapes = [self.visit(dim) for dim in node.type.dimensions]
                    activation_record[node.identifier.name] = np.zeros(shape=shapes)
                else:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
            case ast.ClassicalDeclaration(type=ast.BitType()):
                if node.init_expression is None:
                    size = self.visit(node.type.size) or 1
                    activation_record[node.identifier.name] = np.zeros(shape=size)
                else:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
            case ast.ClassicalDeclaration(type=ast.WaveformType()):
                if node.init_expression is None:
                    activation_record[node.identifier.name] = None
                else:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
            case _:
                if node.init_expression is not None:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
                else:
                    activation_record[node.identifier.name] = None

    @_maybe_annotated
    def visit_IODeclaration(self, node: ast.IODeclaration) -> None:
        """IO Declaration should be resolved"""
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration) -> None:
        """Saves constant declaration to activation record"""
        activation_record = self.call_stack.peek()
        activation_record[node.identifier.name] = self.visit(node.init_expression)

    @_maybe_annotated
    def visit_CalibrationDefinition(self, node: ast.CalibrationDefinition) -> None:
        """
        CalibrationDefinition (defcal) node visitor:
            Saves defcal defintions to self.defcal_nodes dictionary with a
            mangled name. These mangled names are also saved to a list of
            defcal names (self.defcal_names)

        Args:
            node (ast.CalibrationDefinition): defcal node to visit
        """

        mangled_name = Mangler(node).signature().mangle()
        self.defcal_names.append(mangled_name)
        self.defcal_nodes[mangled_name] = node

    @_maybe_annotated
    def visit_CalibrationStatement(self, node: ast.CalibrationStatement) -> None:
        """
        CalibrationStatement node visitor:
            Evaluates each line in a calibration block. Updates the
            self.calibration_scope dictionary which maintains a
            dictionary of values/variables in calibration scope.

        Args:
            node (ast.CalibrationStatement): openQASM CalibrationStatement AST node
        """
        curr_nesting = self.call_stack.peek().nesting_level
        outer_activation_record = ActivationRecord(
            name="outer_calibration",
            ar_type=ARType.CALIBRATION,
            nesting_level=curr_nesting + 1,
        )
        outer_activation_record.members = self.calibration_scope
        with self.ar_context_manager(outer_activation_record):
            inner_activation_record = ActivationRecord(
                name="new_calibration",
                ar_type=ARType.CALIBRATION,
                nesting_level=curr_nesting + 2,
            )
            with self.ar_context_manager(inner_activation_record):
                for statement in node.body:
                    self.visit(statement)
                self.calibration_scope.update(self.call_stack.peek().members)

    def visit_QuantumArgument(self, node: ast.QuantumArgument) -> None:
        """Raises error"""
        self.visit(node.name)

    @_maybe_annotated
    def visit_BreakStatement(self, node: ast.BreakStatement) -> None:
        """Raises error"""
        raise NotImplementedError

    @_maybe_annotated
    def visit_ContinueStatement(self, node: ast.ContinueStatement) -> None:
        """Raises error"""
        raise NotImplementedError

    @_maybe_annotated
    def visit_EndStatement(self, node: ast.EndStatement) -> None:
        """Raises error"""
        raise NotImplementedError

    @_maybe_annotated
    def visit_WhileLoop(self, node: ast.WhileLoop) -> None:
        """
        WhileLoop node visitor:
            Prints out a while loop in SEQC format (which happens to be identical to
            openQASM format) All the statements in the block of the while loop are
            visited

            Example:
                qasm:
                    while (int i < 10) {...; i=i+1;}
                ->
                seqc:
                    while (cvar i < 10) {...; i=i+1;}

        Args:
            node (ast.WhileLoop): openQASM WhileLoop AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        if not self.visit_loops:
            return
        activation_record = ActivationRecord(
            name="while loop",
            ar_type=ARType.LOOP,
            nesting_level=self.call_stack.nesting_level + 1,
        )
        with self.ar_context_manager(activation_record):
            # todo break if while_condition is just True (i.e. infiinite loop)
            while self.visit(node.while_condition):
                for statement in node.block:
                    self.visit(statement)

    @_maybe_annotated
    def visit_ForInLoop(self, node: ast.ForInLoop) -> None:
        """
        ForInLoop node visitor:
            Evaluates iteration range of for loop and then evaluates the body of the
            for loop for each iteration.
        Args:
            node (ast.ForInLoop): openQASM ForInLoop AST node

        Raises:
            Error: ErrorCode.UNHANDLED
                If the SET iterated over by the ForInLoop is incorrectly defined or not
                created using a RangeDefinition
        """
        if not self.visit_loops:
            return
        name = node.identifier.name
        activation_record = ActivationRecord(
            name=f"for_loop_{self.call_stack.nesting_level+1}",
            ar_type=ARType.LOOP,
            nesting_level=self.call_stack.nesting_level + 1,
        )
        with self.ar_context_manager(activation_record):
            start, end, step = self.visit(node.set_declaration)
            if end is None:
                raise Error(
                    ErrorCode.UNHANDLED,
                    f"unsupported set declaration in for loop: {node.set_declaration}",
                )
            activation_record = self.call_stack.peek()
            activation_record[name] = start
            for i in range(start, end, step):
                activation_record[name] = i
                for statement in node.block:
                    self.visit(statement)

    def visit_DelayInstruction(self, node: ast.DelayInstruction) -> None:
        """Passes over delay instructions"""

    def visit_DurationOf(self, node: ast.DurationOf) -> None:
        """DurationOf function not implemented"""
        raise self.compile_out(node)

    def visit_SizeOf(self, node: ast.SizeOf) -> None:
        """SizeOf function not implemented"""
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_AliasStatement(self, node: ast.AliasStatement) -> None:
        """Saves alias statement to activation record, including name and value"""
        match node:
            case ast.AliasStatement(target=ast.Identifier(), value=ast.Concatenation()):
                activation_record = self.call_stack.peek()
                activation_record[node.target.name] = self.visit(node.value)
            case ast.AliasStatement(
                ast.Identifier(alias),
                ast.IndexExpression(ast.Identifier(name), [ast.RangeDefinition()]),
            ):
                start, end, step = self.visit_RangeDefinition(node.value.index[0])
                activation_record = self.call_stack.peek()
                activation_record[alias] = self.call_stack.down_stack(name)[name][
                    start:end:step
                ]
            case _:
                raise self.compile_out(node)

    def _visit_IndexElement(self, node: IndexElement) -> None:
        match node:
            case ast.DiscreteSet():
                return self.visit(node)
            case list():
                return [self.visit(index) for index in node]

    @_maybe_annotated
    def visit_ClassicalAssignment(self, node: ast.ClassicalAssignment) -> None:
        """Evaluate and save classical assignment to activation record"""
        match node:
            case ast.ClassicalAssignment(lvalue=ast.Identifier()):
                activation_record = self.call_stack.down_stack(node.lvalue.name)
                activation_record[node.lvalue.name] = self.visit(node.rvalue)
            case ast.ClassicalAssignment(lvalue=ast.IndexedIdentifier()):
                activation_record = self.call_stack.down_stack(node.lvalue.name.name)
                indices = [
                    self._visit_IndexElement(index) for index in node.lvalue.indices
                ]
                activation_record[node.lvalue.name.name][indices] = self.visit(
                    node.rvalue
                )
            case _:
                raise Error(
                    ErrorCode.UNHANDLED, f"unhandled classical assignment: {node}"
                )

    def evaluate_function(self, func_name: str, arg_vals: list):
        """Helper function to evaluate subroutine calls. Either from external
        functional definitions or from subroutines defined in the program.
        Adds arguments to the activation record and evaluates the body of the
        subroutine."""
        if func_name in self.external_funcs:
            return self.external_funcs[func_name](*arg_vals)
        if func_name in self.subroutines:
            activation_record = self.call_stack.peek()
            node = self.subroutines[func_name]
            for arg, val in zip(node.arguments, arg_vals):
                activation_record[arg.name.name] = val
            for statement in node.body:
                if isinstance(statement, ast.ReturnStatement):
                    return self.visit(statement)
                self.visit(statement)
        raise Error(ErrorCode.UNHANDLED, f"function {func_name} not found")

    def visit_FunctionCall(self, node: ast.FunctionCall) -> None:
        """
        FunctionCall node visitor:
            Evaluates function calls. Either from external functional definitions
            or from subroutines defined in the program.

        Args:
            node (ast.FunctionCall): openQASM FunctionCall AST node
        """
        curr_nesting = self.call_stack.peek().nesting_level
        activation_record = ActivationRecord(
            name=f"{node.name.name}",
            ar_type=ARType.SUBROUTINE,
            nesting_level=curr_nesting + 1,
        )
        with self.ar_context_manager(activation_record):
            match node:
                case ast.FunctionCall(name=ast.Identifier("play")) | ast.FunctionCall(
                    name=ast.Identifier("capture_v1")
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v2")
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v3")
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v1_spectrum")
                ):
                    self.visit_play(node)
                case ast.FunctionCall(
                    name=ast.Identifier("set_phase"),
                    arguments=[ast.Identifier(frame_name), _],
                ):
                    frame: Frame = self.call_stack.down_stack(frame_name)[frame_name]
                    phase_val = self.visit(node.arguments[1])
                    phase_val = (phase_val + np.pi) % (2 * np.pi) - np.pi
                    frame.set_phase(phase_val)
                case ast.FunctionCall(
                    name=ast.Identifier("shift_phase"),
                    arguments=[ast.Identifier(frame_name), _],
                ):
                    frame: Frame = self.call_stack.down_stack(frame_name)[frame_name]
                    phase_val = self.visit(node.arguments[1]) + frame.phase
                    phase_val = (phase_val + np.pi) % (2 * np.pi) - np.pi
                    frame.set_phase(phase_val)
                case ast.FunctionCall(
                    name=ast.Identifier("set_frequency"),
                    arguments=[ast.Identifier(frame_name), _],
                ):
                    frame: Frame = self.call_stack.down_stack(frame_name)[frame_name]
                    frame.set_frequency(self.visit(node.arguments[1]))
                case ast.FunctionCall(
                    name=ast.Identifier("shift_frequency"),
                    arguments=[ast.Identifier(frame_name), _],
                ):
                    frame: Frame = self.call_stack.down_stack(frame_name)[frame_name]
                    frame.shift_frequency(self.visit(node.arguments[1]))
                case ast.FunctionCall(name=ast.Identifier("executeTableEntry")):
                    pass
                case ast.FunctionCall(name=ast.Identifier("assignWaveIndex")):
                    pass
                case _:
                    args = [self.visit(arg) for arg in node.arguments]
                    return_val = self.evaluate_function(node.name.name, args)
                    return return_val

    def visit_play(self, node: ast.FunctionCall) -> None:
        """Passes over visit_play function (see PulseVisualizer)"""

    @contextmanager
    def ar_context_manager(
        self,
        activation_record: ActivationRecord,
    ):
        """
        Context manager for activation records / call stack,
        the activation record tracks ports and frames declared in the program
        to make sure frames can be replaced with appropriate channels

        Args:
            activation_record (ActivationRecord): activation record to activate
        """
        self.call_stack.push(activation_record)
        LOGGER.debug("ENTER: ACTIVATION RECORD %s", activation_record.name)
        LOGGER.debug(self.call_stack)
        try:
            yield
        finally:
            LOGGER.debug("LEAVE: ACTIVATION RECORD %s", activation_record.name)
            LOGGER.debug(self.call_stack)
            self.call_stack.pop()

    def compile_out(self, node: ast.QASMNode) -> Error:
        """
        Method for standartizing raising errors when Intepreter is asked to visit
        nodes that should be compiled out of the AST before the Interpreter is used.

        Args:
            node (ast.QASMNode):
                Should have been removed from the AST by prior compilation steps

        Returns:
            Error: should be raised immediately after this method returns
        """
        return Error(ErrorCode.COMPILE_OUT, f"{node}")


binary_ops = {
    1: operator.gt,
    2: operator.lt,
    3: operator.ge,
    4: operator.le,
    5: operator.eq,
    6: operator.ne,
    7: lambda x, y: x and y,
    8: lambda x, y: x or y,
    9: operator.or_,
    10: operator.xor,
    11: operator.and_,
    12: operator.lshift,
    13: operator.rshift,
    14: operator.add,
    15: operator.sub,
    16: operator.mul,
    17: operator.truediv,
    18: operator.mod,
    19: operator.pow,
}

unary_ops = {
    1: operator.__invert__,
    2: operator.not_,
    3: operator.__neg__,
}
