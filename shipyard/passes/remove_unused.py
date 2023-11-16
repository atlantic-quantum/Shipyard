"""
Module for a QASMTransformer that removes unused nodes from an openQASM AST
"""

from openpulse import ast

from ..logger import LOGGER
from ..mangle import Mangler
from ..visitors import GenericTransformer
from ..visitors import GenericVisitor as QASMVisitor


class _DetermineUnused(QASMVisitor):
    """
    QASMVisitor that visits every node in an openQASM AST and
    determines what quantaties are declared and if any quantaties are declared
    but unused.

    Usage (Note: it is prefered to use RemoveUnused instead):
        qasm_ast: ast.Program

        deter_unused = _DetermineUnused(qasm_ast)
        unused, declared = deter_unused.results()

        or

        deter_unused = _DetermineUnused()
        deter_unused.visit(qasm_ast)
        unused, declared = deter_unused.results()

    """

    def __init__(self, node: ast.Program | None = None) -> None:
        super().__init__()
        self.declared: set[str] = set()
        self.unused: set[str] = set()
        if node:
            self.visit(node)

    # pylint: disable=C0103
    # (snake_case naming style)

    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration):
        """
        ClassicalDeclaration node visitor
            Adds name of declared classical variables to a set of declared quantities
            and to a set of unsued quantaties

            then visits the type and init_expression nodes of declaration

        Args:
            node (ast.ClassicalDeclaration): openQASM classical declaration node
        """
        self.unused.add(node.identifier.name)
        self.declared.add(node.identifier.name)
        LOGGER.debug(
            "DECLARED: ClassicalDeclaration %s with identifier %s",
            node.type.__class__.__name__,
            node.identifier.name,
        )
        self.visit(node.type)
        if node.init_expression:
            self.visit(node.init_expression)

    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration):
        """
        ConstantDeclaration node visitor
            Adds name of declared classical constant to a set of declared quantities
            and to a set of unsued quantaties

            then visits the type and init_expression nodes of declaration

        Args:
            node (ast.ConstantDeclaration): openQASM constant declaration node
        """
        self.unused.add(node.identifier.name)
        self.declared.add(node.identifier.name)
        LOGGER.debug(
            "DECLARED: ConstantDeclaration with identifier %s", node.identifier.name
        )
        self.visit(node.type)
        self.visit(node.init_expression)

    def visit_SubroutineDefinition(self, node: ast.SubroutineDefinition):
        """
        SubroutineDefinition node visitor
            Adds name of declared subroutines to a set of declared quantities
            and to a set of unused quantities.

            then visits the arguments and body nodes of the definition.

        Args:
            node (ast.SubroutineDefinition): openQASM subroutine definition node
        """
        self.unused.add(node.name.name)
        self.declared.add(node.name.name)
        LOGGER.debug(
            "DECLARED: SubroutineDefinition with identifier %s", node.name.name
        )
        for arg in node.arguments:
            self.visit(arg)
        for statement in node.body:
            self.visit(statement)

    def visit_CalibrationDefinition(self, node: ast.CalibrationDefinition):
        """
        CalibrationDefinition (defcal) node visitor
            Adds a mangled name of the declared calibration definition
            to a set of declared quantities and to a set of unused quantities.

            then visits the arguments, qubits and body nodes of the definition.

        Args:
            node (ast.CalibrationDefinition): openQASM defcal node
        """
        mangled_name = Mangler(node).signature().mangle()
        self.unused.add(mangled_name)
        self.declared.add(mangled_name)
        LOGGER.debug(
            "DECLARED: CalibrationDefinition with Identifier: %s, mangled: %s",
            node.name.name,
            mangled_name,
        )
        for arg in node.arguments:
            self.visit(arg)
        for qubit in node.qubits:
            self.visit(qubit)
        for statement in node.body:
            self.visit(statement)

    def visit_QuantumGate(self, node: ast.QuantumGate):
        """
        QuantumGate node visitor
            Removes a mangled string matching the gate call from the set of unused
            quantaties.

        Args:
            node (ast.QuantumGate): openQASM quantum gate node
        """
        matches = Mangler(node).signature().match(self.unused)
        if matches:
            self.unused.discard(matches[0])
            LOGGER.debug(
                "USED: QuantumGate: %s, mangled: %s", node.name.name, matches[0]
            )
        for arg in node.arguments:
            self.visit(arg)

    def visit_QuantumMeasurement(self, node: ast.QuantumMeasurement):
        """
        QuantumMeasurement node visitor
            Removes a mangled string matching the measure call from the set of unused
            quantaties.

        Args:
            node (ast.QuantumMeasurement): openQASM quantum measurement node
        """
        matches = Mangler(node).signature().match(self.unused)
        if matches:
            self.unused.discard(matches[0])
            LOGGER.debug(
                "USED: : QuantumMeasurement: %s, mangled: %s", node.qubit, matches[0]
            )

    def visit_QuantumReset(self, node: ast.QuantumReset):
        """
        QuantumReset node visitor
            Removes a mangled string matching the reset call from the set of unused
            quantaties.

        Args:
            node (ast.QuantumReset): openQASM quantum reset node
        """
        matches = Mangler(node).signature().match(self.unused)
        if matches:
            self.unused.discard(matches[0])
            LOGGER.debug(
                "USED: : QuantumReset: %s, mangled: %s", node.qubits, matches[0]
            )

    def visit_Identifier(self, node: ast.Identifier):
        """
        Identifier node visitor
            Removes a string matching identifier name from the set of unused
            quantaties.

        Args:
            node (ast.Identifier): openQASM identifier node
        """
        self.unused.discard(node.name)
        LOGGER.debug("USED: Identifier %s", node.name)

    # pylint: enable=C0103
    # (snake_case naming style)

    def result(self) -> tuple[set[str], set[str]]:
        """
        Method for retrieving the sets of declared and unused quantites in a single call

        Returns:
            tuple[set[str], set[str]]: tuple of sets of unused and declared quantites
        """
        return self.unused, self.declared


class RemoveUnused(GenericTransformer):
    """
    QASMTransformer that removed unused and undeclared nodes from an openQASM AST.

    Usage:
        qasm_ast: ast.Program
        RemoveUnused(qasm_ast) <- transforms qasm ast

    Note:
        May have to be run multiple times to have intended effect.
    """

    def __init__(self, node: ast.Program | None = None) -> None:
        super().__init__()
        self.unused: set[str] = None
        self.declared: set[str] = None
        self.remove_assignment: set[str] = set()
        if node:
            self.visit(node)

    def visit(self, node: ast.QASMNode, context=None) -> ast.QASMNode:
        if not self.unused and not self.declared:
            self.unused, self.declared = _DetermineUnused(node).result()
            LOGGER.debug("UPDATED: RemovedUnused with unused: %s", self.unused)
            LOGGER.debug("UPDATED: RemovedUnused with declared: %s", self.declared)
        return super().visit(node, context)

    # pylint: disable=C0103
    # (snake_case naming style)

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration
    ) -> ast.ClassicalDeclaration:
        """
        ClassicalDeclaration node visitor:
            Removes the node if it is not used within the openQASM program the node
            is part of.

            Example:
                in: int i = 1;
                    int j = 2;
                    i;  // <- this line uses 'i'
                out:
                    int i = 1;
                    i;

        Args:
            node (ast.ClassicalDeclaration): openQASM classical declaration node

        Returns:
            ast.ClassicalDeclaration:
                if the node is used in the program else returns None
        """
        if node.identifier.name not in self.unused:
            return node
        LOGGER.debug(
            "REMOVED: unused ClassicalDeclaration node: %s", node.identifier.name
        )
        return None

    def visit_ConstantDeclaration(
        self, node: ast.ConstantDeclaration
    ) -> ast.ConstantDeclaration:
        """
        ClassicalDeclaration node visitor:
            Removes the node if it is not used within the openQASM program the node
            is part of.

            Example:
                in: const int i = 1;
                    const int j = 2;
                    i;  // <- this line uses 'i'
                out:
                    const int i = 1;
                    i;

        Args:
            node (ast.ConstantDeclaration): openQASM constant declaration node

        Returns:
            ast.ConstantDeclaration:
                if the node is used in the program else returns None
        """
        if node.identifier.name not in self.unused:
            return node
        LOGGER.debug(
            "REMOVED: unused ConstantDeclaration node: %s", node.identifier.name
        )
        return None

    def visit_SubroutineDefinition(
        self, node: ast.SubroutineDefinition
    ) -> ast.SubroutineDefinition:
        """
        SubroutineDefinition node visitor:
            Removes the subroutine definition node if it is not used within the openQASM
            program the node is part of.

            Example:
                in: def used_func() {...};
                    def unused_func() {...};
                    used_func();  // <- this line uses 'used_func'
                out:
                    def used_func() {...};
                    used_func();

        Args:
            node (ast.SubroutineDefinition): openQASM subroutine definition node

        Returns:
            ast.SubroutineDefinition:
                if the node is used in the program else returns None
        """
        node.body = self._visit_list(node.body, self.visit)
        if node.name.name not in self.unused:
            return node
        LOGGER.debug("REMOVED: unused SubroutineDefinition node: %s", node)
        return None

    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition
    ) -> ast.CalibrationDefinition:
        """
        CalibrationDefinition (defcal) node visitor:
            Visits the statements within the body of the defcal statments.

            Removes the calibration definition (defcal) node if it is not used within
            the openQASM program the node is part of.

            If the the defcal statement is used and it has a return value, checks
            if the return statement has been removed from the body of the defcal
            statements and adds the defcal signature to statements that assignment
            should be removed from.

            If the defcal statement is a measure statement, it will be written
            regardless of whether it is used or not.

            Example 1:
                in: defcal used_gate $0 {...};
                    defcal unused_gate $0 {...};
                    used_gate $0;  // <- this line uses 'used_gate'
                out:
                    defcal used_func $0 {...};
                    used_gate $1;

            Example 2:
                in: defcal used_measure $0 -> bit {
                        play(frame1, ...);
                        play(frame0, ...);
                        return capture_v2(frame0, ...);
                    }
                    bit measured_bit;
                    measured_bit = used_measure $0;
                out:
                    defcal used_measure $0 {
                        play(frame1, ...);
                    }
                    used_measure $0;


        Args:
            node (ast.CalibrationDefinition): openQASM defcal node

        Returns:
            ast.CalibrationDefinition:
                if the node is used in the program else returns None
        """
        node.body = self._visit_list(node.body, self.visit)
        if (
            not Mangler(node).signature().match(self.unused)
            and node.body
            or node.name.name == "measure"
        ):
            if node.return_type:
                has_return = False
                for stmt in node.body:
                    has_return = isinstance(stmt, ast.ReturnStatement) or has_return
                if not has_return:
                    node.return_type = None
                    self.remove_assignment.add(Mangler(node).signature().mangle())
                    LOGGER.debug(
                        "ADDED: defcal defintion to remove_assignment: %s", node
                    )
            return node
        LOGGER.debug("REMOVED: unused CalibrationDefinition node: %s", node)
        return None

    def visit_QuantumGate(self, node: ast.QuantumGate) -> ast.QuantumGate:
        """
        QuantumGate node visitor:
            Removes the quantum gate node if it is not declared within the openQASM
            program the node is part of.

            Example:
                in: defcal declared_gate $0 {...};
                    declared_gate $0;
                    undeclared_gate $0; // <- defcal for this gate is not declared
                out:
                    defcal declared_gate $0 {...};
                    declared_gate $0;

        Args:
            node (ast.QuantumGate): openQASM quantum gate node

        Returns:
            ast.QuantumGate:
                if the node is used in the program else returns None
        """
        declared = Mangler(node).signature().match(self.declared)
        LOGGER.debug("DECLARED Gates: %s", declared)
        if declared:
            return node
        LOGGER.debug("REMOVED: Undeclared QuantumGate node: %s", node)
        return None

    def visit_QuantumMeasurement(
        self, node: ast.QuantumMeasurement
    ) -> ast.QuantumMeasurement:
        """
        QuantumMeasurement node visitor:
            Removes the quantum measurement node if it is not declared within the
            openQASM program the node is part of.

            Example:
                in: defcal measure $0 {...};
                    measure $0;
                    measure $1; // <- defcal for this gate is not declared
                out:
                    defcal measure $0 {...};
                    measure $0;

        Args:
            node (ast.QuantumMeasurement): openQASM quantum measurement node.

        Returns:
            ast.QuantumMeasurement:
                if the node is used in the program else returns None.
        """
        declared = Mangler(node).signature().match(self.declared)
        LOGGER.debug("DECLARED Measurements: %s", declared)
        if declared:
            return node
        LOGGER.debug("REMOVED: Undeclared QuantumMeasurement node: %s", node)
        return None

    def visit_QuantumReset(self, node: ast.QuantumReset) -> ast.QuantumReset:
        """
        QuantumReset node visitor:
            Removes the quantum reset node if it is not declared within the
            openQASM program the node is part of.

            Example:
                in: defcal reset $0 {...};
                    reset $0;
                    reset $1; // <- defcal for this gate is not declared
                out:
                    defcal reset $0 {...};
                    reset $0;

        Args:
            node (ast.QuantumReset): openQASM quantum reset node.

        Returns:
            ast.QuantumReset:
                if the node is used in the program else returns None.
        """
        declared = Mangler(node).signature().match(self.declared)
        LOGGER.debug("DECLARED Resets: %s", declared)
        if declared:
            return node
        LOGGER.debug("REMOVED: Undeclared QuantumReset node: %s", node)
        return None

    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement
    ) -> ast.QuantumMeasurementStatement:
        """
        QuantumMeasurementStatement node visitor:
            If the QuantumMeasurement node of the MeasurementStatement is removed
            also remove the MeasurementStatement.

            If the mangled measurement call signature is in the remove_assignment list
            remove the target from the node.

            Example 1:
                in:
                    defcal measure $0 {...};
                    bit meas_bit_0;
                    bit meas_bit_1; <- a 2nd pass will then also remove this declaration
                    meas_bit_0 = measure $0;
                                 __________ <- removed as defcal is not declared
                    meas_bit_1 = measure $1;
                    |---------------------| <- meas is removed so entire stmt is removed

                out:
                    defcal measure $0 {...};
                    bit meas_bit_0;
                    meas_bit_0 = measure $0;

            Example 2:
                in: remove_assignment = [_ZN7measure_PN0_QN0_$0_R]

                    bit meas_bit_0;
                    meas_bit_0 = measure $0;

                out:
                    measure $0;

        Args:
            node (ast.QuantumMeasurementStatement):
                openQASM quantum measurement statement node.

        Returns:
            ast.QuantumMeasurementStatement:
                if the node is used in the program else returns None.
        """
        mangler = Mangler(node.measure)
        mangler.return_type = ""
        if mangler.signature().mangle() in self.remove_assignment:
            node.target = None
        if self.visit(node.measure):
            return node
        LOGGER.debug("REMOVED: Unused QuantumMeasurementStatement node: %s", node)
        return None

    # pylint: enable=C0103
    # (snake_case naming style)
