import functools
from contextlib import contextmanager

from openpulse import ast

from ..call_stack import ActivationRecord, ARType, CallStack
from ..logger import LOGGER
from ..setup.internal import SetupInternal
from ..visitors import GenericTransformer
from ..visitors import GenericVisitor as QASMVisitor
from .interpreter import Interpreter


def _maybe_annotated(method):
    @functools.wraps(method)
    def annotated(self: "Interpreter", node: ast.Statement) -> None:
        for annotation in node.annotations:
            self.visit(annotation)
        return method(self, node)

    return annotated


def _visit_interpreter(method):
    @functools.wraps(method)
    def interpreter_visit(self: "DetermineMaxDelay", node: ast.Statement) -> None:
        self.interpreter.visit(node)
        return method(self, node)

    return interpreter_visit


class DetermineMaxDelay(QASMVisitor):
    """
    Class for collecting the delays in the measure defintions and determining the
    maximum of these delays
    """

    def __init__(
        self,
        node: ast.Program | None = None,
        setup: SetupInternal = None,
        exteranl_funcs: dict = None,
    ) -> None:
        super().__init__()
        self.delays = []  # list of all the delay values
        self.setup = setup
        self.call_stack = CallStack()
        self.interpreter = Interpreter(
            setup=setup, external_funcs=exteranl_funcs, visit_loops=False
        )
        self.interpreter.call_stack = self.call_stack
        if node:
            self.visit(node)

    def visit_Program(self, node: ast.Program) -> None:
        activation_record = ActivationRecord(
            name="main", ar_type=ARType.PROGRAM, nesting_level=1
        )
        with self.ar_context_manager(activation_record):
            for statement in node.statements:
                self.visit(statement)

    @_visit_interpreter
    @_maybe_annotated
    def visit_CalibrationStatement(self, node: ast.CalibrationStatement) -> None:
        pass

    @_visit_interpreter
    @_maybe_annotated
    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration) -> None:
        pass

    @_visit_interpreter
    @_maybe_annotated
    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration) -> None:
        pass

    @_visit_interpreter
    @_maybe_annotated
    def visit_SubroutineDefinition(self, node: ast.SubroutineDefinition) -> None:
        pass

    # @_visit_interpreter
    @_maybe_annotated
    def visit_ForInLoop(self, node: ast.ForInLoop) -> None:
        pass

    @_visit_interpreter
    def visit_CalibrationDefinition(self, node: ast.CalibrationDefinition) -> None:
        """
        CalibrationDefinition (defcal) node visitor:
            Adds the interpreters calibration scope to the call stack. If the defcal
            Statment is a measure statement, the visitor searches for the delay
            instructions and adds them to the list of delays.

        Args:
            node (ast.CalibrationDefinition): defcal node to visit
        """
        if node.name.name == "measure":
            outer_activation_record = ActivationRecord(
                name="calibration",
                ar_type=ARType.CALIBRATION,
                nesting_level=self.call_stack.nesting_level + 1,
            )
            outer_activation_record.members = self.interpreter.calibration_scope
            with self.ar_context_manager(outer_activation_record):
                inner_activation_record = ActivationRecord(
                    name="defcal",
                    ar_type=ARType.DEFCAL,
                    nesting_level=self.call_stack.nesting_level + 1,
                )
                with self.ar_context_manager(inner_activation_record):
                    for statement in node.body:
                        if isinstance(statement, ast.DelayInstruction):
                            self.delays.append(
                                self.interpreter.visit(statement.duration)
                            )

    def result(self) -> float:
        """
        Returns the maximum delay in the program
        """
        return max(self.delays) if self.delays else None

    @contextmanager
    def ar_context_manager(
        self,
        activation_record: ActivationRecord,
    ):
        """
        Context manager for activation records / call stack,
        the activation record tracks ports and frames declared in the program
        to make sure frames can be replaced with approprate channels

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


class DelaysInMeasure(GenericTransformer):
    """
    Class for transforming the delay instructions in measure definitions
    to the maximum found by the _DetermineMaxDelay class. Should be run
    after DurationTransformer so that all durations are in same unit.
    """

    def __init__(
        self,
        node: ast.Program | None = None,
        setup: SetupInternal = None,
        exteranl_funcs: dict = None,
    ) -> None:
        super().__init__()
        self.setup = setup
        self.max_delay = DetermineMaxDelay(node, setup, exteranl_funcs).result()
        self.flag = False  # flag for transforming a delay instruction
        if node and self.max_delay is not None:
            self.visit(node)

    def visit_DelayInstruction(
        self, node: ast.DelayInstruction
    ) -> ast.DelayInstruction:
        """
        DelayInstruction node visitor:
            Transforms DelayInstruction to the maximum delay

        Args:
            node (ast.DelayInstruction): delay node to visit
        """
        if self.flag:
            return ast.DelayInstruction(
                duration=ast.DurationLiteral(
                    value=self.max_delay,
                    unit=ast.TimeUnit.dt,
                ),
                qubits=node.qubits,
            )
        else:
            self.visit(node)

    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition
    ) -> ast.CalibrationDefinition:
        """
        CalibrationDefinition (defcal) node visitor:
            If the CalibrationDefintion is a measure definition, set the flag to
            true to allow for the transformation of the delay instructions in the
            body of the CalibrationDefinition

        Args:
            node (ast.CalibrationDefinition): defcal node to visit
        """
        if node.name.name == "measure":
            for i, statement in enumerate(node.body):
                match statement:
                    case ast.DelayInstruction():
                        self.flag = True
                        node.body[i] = self.visit(statement)
                        self.flag = False
                    case _:
                        pass
        return node
