"""
QASMTransformer that transforms a multi-port qasm program into
a qasm program for specific target ports.
"""
from contextlib import contextmanager

from openpulse import ast

from ..compiler_error import ErrorCode, TransformError
from ..logger import LOGGER
from ..setup.internal import SetupInternal
from ..utilities import ScopeContext
from ..visitors import CopyTransformer as QASMTransformer


def ports_for_core(setup: SetupInternal, instrument: str, core_index: int):
    """
    Gives all ports that are assocated with
    a specific core index of a specific instrument within a setup
    """
    return set(
        port_name
        for port_name, port in setup.ports.items()
        if (port.instrument.name == instrument and port.core.index == core_index)
    )


class CoreSplitter(QASMTransformer):
    """
    QASMTransformer that transforms a qasm program for multiple ports
    into a qasm program for a target ports

    Args:
        target_ports (set[str]): a set of target ports to transform the program to.
    """

    def __init__(self, target_ports: set[str]) -> None:
        if isinstance(target_ports, str):
            target_ports = set([target_ports])
        self.target_ports = target_ports
        self.context: ScopeContext = None
        self.frames = set()

    # pylint: disable=C0103
    # snake_case naming

    def visit_Program(self, node: ast.Program) -> ast.Program:
        """
        Program (defcal) node transformer:
            Enters GLOBAL context and visits the program node
            Exits GLOBAL context before returning the node

        Args:
            node (ast.Program): openQASM program to process

        Returns:
            ast.Program: same node
        """
        with self.scope_manager(ScopeContext.GLOBAL):
            statements = self._visit_list(node.statements, self.visit)
        return ast.Program(statements=statements, version=node.version)

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration
    ) -> ast.ClassicalDeclaration:
        """
        Classi calDeclaration node transformer:
            a) Frame declarations:
                If the port of a standard frame declaration is a target port:
                    Add frame to list of used frames and return the node.
                Else:
                    Remove the node
                If the frame declaration is not of the expected syntax i.e.
                    frame some_frame = newframe(port, frequency, phase)
                Raise Transform error

            b) Port Declaration
                IF the port is not one of the target ports -> remove the node

            c) Other declarations
                return the node


        Args:
            node (ast.ClassicalDeclaration): openQASM classical declaration to process

        Raises:
            TransformError:
                if a frame declaration does not match the expected format i.e.
                frame some_frame = newframe(port, frequency, phase)

        Returns:
            ast.ClassicalDeclaration: same node if it is not removed, else None.
        """
        match node:
            case ast.ClassicalDeclaration(
                type=ast.FrameType(),
                identifier=frame_id,
                init_expression=ast.FunctionCall(
                    name=ast.Identifier("newframe"),
                    arguments=[port_arg, _, _],
                ),
            ):
                if port_arg.name in self.target_ports:
                    self.frames.add(frame_id.name)
                    return super().visit_ClassicalDeclaration(node)
                LOGGER.debug(
                    "REMOVED: Declared frame: %s, that does not use a target port: %s",
                    frame_id.name,
                    self.target_ports,
                )
                return None
            case ast.ClassicalDeclaration(type=ast.FrameType()):
                raise TransformError(ErrorCode.UNHANDLED, "Unhandled frame declaration")
            case ast.ClassicalDeclaration(type=ast.PortType(), identifier=port):
                if port.name in self.target_ports:
                    return super().visit_ClassicalDeclaration(node)
                LOGGER.debug(
                    "REMOVED: Declared port: %s, that is not target port: %s",
                    port.name,
                    self.target_ports,
                )
                return None
            case _:
                return super().visit_ClassicalDeclaration(node)

    def visit_FunctionCall(self, node: ast.FunctionCall) -> ast.FunctionCall:
        """
        FunctionCall node transformer:
            If a play/capture_v2 function call is performed on a frame that uses the
            target AWG core it is passed on, else the node is removed.
            Other function calls are passed on

            Example:
                target: ch1

                in:
                    frame1 = newframe(ch1, ...)
                    frame2 = newframe(ch2, ...) <- removed by visit_ClassicalDeclaration

                    play(frame1, ...)
                    play(frame2, ...) <- this FunctionCall node will be removed

                    other_function_call(...)

                out:
                    frame1 = newframe(ch1, ...)
                    play(frame1, ...)

                    other_function_call(...)

        Args:
            node (ast.FunctionCall): openQASM function call node to process

        Returns:
            ast.FunctionCall: same node if it is passed on, else None.
        """
        match node:
            case ast.FunctionCall(
                name=ast.Identifier(
                    "play"
                    | "capture_v1"
                    | "capture_v2"
                    | "capture_v3"
                    | "capture_v1_spectrum"
                    | "set_frequency"
                    | "shift_frequency"
                    | "set_phase"
                    | "shift_phase"
                ),
                arguments=[frame_arg, _],
            ):
                if frame_arg.name in self.frames:
                    return super().visit_FunctionCall(node)
                LOGGER.debug(
                    "REMOVED: Function call %s that is not using frame for target %s",
                    node,
                    self.target_ports,
                )
                return None
            case _:
                return super().visit_FunctionCall(node)

    def visit_ExpressionStatement(
        self, node: ast.ExpressionStatement
    ) -> ast.ExpressionStatement:
        """
        ExpressionStatement node transformer:
            ExpressionStatements are wrappers around other expressions. If other
            methods of this transformer remove the expression of the ExpressionStatement
            this visitor also removes the ExpressionStatement wrapping it
            (as ExpressionStatements with expression=None are not allowed.)

        Args:
            node (ast.ExpressionStatement): openQASM expression statement to process

        Returns:
            ast.ExpressionStatement: same node if not removed, else None
        """
        expression = self.visit(node.expression)
        if expression is not None:
            return super().visit_ExpressionStatement(node)
        LOGGER.debug("REMOVED: Empty ExpressionStatement %s", node)
        return None

    def visit_CalibrationStatement(
        self, node: ast.CalibrationStatement
    ) -> ast.CalibrationStatement:
        """
        CalibrationStatement node transformer:
            Enters DEFCAL context and visits the calibration statement node
            Exits DEFCAL context before returning the node

        Args:
            node (ast.CalibrationStatement): openQASM calibration statement to process

        Returns:
            ast.CalibrationStatement: same node
        """
        with self.scope_manager(ScopeContext.DEFCAL):
            body = self._visit_list(node.body, self.visit)
        return ast.CalibrationStatement(body=body)

    def visit_SubroutineDefinition(
        self, node=ast.SubroutineDefinition
    ) -> ast.SubroutineDefinition:
        """
        SubroutineDefinition node transformer:
            Enters SUBROUTINE context and visits the Subroutine definition node
            Exits SUBROUTINE context before returning the node

        Args:
            node (ast.SubroutineDefinition): openQASM subroutine definition to process

        Returns:
            ast.SubroutineDefinition: same node
        """
        with self.scope_manager(ScopeContext.SUBROUTINE):
            body = self._visit_list(node.body, self.visit)
        return ast.SubroutineDefinition(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit),
            body=body,
            return_type=self.visit(node.return_type) if node.return_type else None,
        )

    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition
    ) -> ast.CalibrationDefinition:
        """
        CalibrationDefinition (defcal) node transformer:
            Enters DEFCAL context and visits the calibration definition node
            Then Exits DEFCAL context
            If all statements within the body of a defcal statements are removed
            this visitor also removes that defcal statements


        Args:
            node (ast.CalibrationDefinition): openQASM defcal node to process

        Returns:
            ast.CalibrationDefinition:
                same node if it has any statements within its body
        """
        with self.scope_manager(ScopeContext.DEFCAL):
            body = self._visit_list(node.body, self.visit)
        if body:
            return ast.CalibrationDefinition(
                name=self.visit_Identifier(node.name),
                arguments=self._visit_list(node.arguments, self.visit),
                qubits=self._visit_list(node.qubits, self.visit),
                return_type=self.visit(node.return_type) if node.return_type else None,
                body=body,
            )
        LOGGER.debug("REMOVED: Empty CalibrationDefinition (defcal) %s", node)
        return None

    def visit_ReturnStatement(self, node: ast.ReturnStatement) -> ast.ReturnStatement:
        """
        ReturnStatement node transformer:
            If the expression of the return statement is removed then the return
            statement itself is also removed.

        Args:
            node (ast.ReturnStatement): openQASM return statement to process

        Returns:
            ast.ReturnStatement: same node if not removed, else None
        """
        expression = self.visit(node.expression)
        if expression:
            return ast.ReturnStatement(expression=expression)
        LOGGER.debug("REMOVED: Empty ReturnStatement %s", node)
        return None

    def visit_DelayInstruction(self, node: ast.DelayInstruction):
        """
        DelayInstruction node transformer:
            If the dealy instruction is performed on a frame not using a target port
            it is removed.

        Args:
            node (ast.DelayInstruction): openQASM play instructions to process

        Returns:
            ast.DelayInstruction: same node if not removed, else None
        """
        if self.context == ScopeContext.DEFCAL:
            if node.qubits[0].name in self.frames:
                return super().visit_DelayInstruction(node)
            LOGGER.debug("REMOVED: Unused DelayInstruction %s", node)
            return None
        return super().visit_DelayInstruction(node)

    # pylint: enable=C0103

    @contextmanager
    def scope_manager(self, context: ScopeContext):
        """
        Context manager for the scope of the qasm program.
        on entering the manager sets the context to the input context.
        restores the previous context on exiting the manager

        Args:
            context (ScopeContext): context to set while within the manager.
        """
        old_context = self.context
        try:
            self.context = context
            yield
        finally:
            self.context = old_context
