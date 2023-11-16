from openpulse import ast

from .generic_transformer import GenericTransformer

# pylint: disable=C0103,W0613,R0904


class CopyTransformer(GenericTransformer):
    def visit_Program(self, node: ast.Program, context=None) -> ast.Program:
        """
        An entire OpenQASM 3 program represented by a list of top level statements
        """
        return ast.Program(
            self._visit_list(node.statements, self.visit), version=node.version
        )

    def visit_Annotation(self, node: ast.Annotation, context=None) -> ast.Annotation:
        """An annotation applied to a statment."""
        return ast.Annotation(keyword=node.keyword, command=node.command)

    # def visit_Statement(self, node: ast.Statement, context=None) -> ast.Statement:
    #     """A statement: anything that can appear on its own line"""
    #     return ast.Statement(self._visit_list(node.annotations, self.visit))

    def _visit_Statement(
        self, node: ast.Statement, context=None
    ) -> list[ast.Annotation]:
        """A statement: anything that can appear on its own line"""
        return self._visit_list(node.annotations, self.visit)

    def visit_Include(
        self, node: ast.Include, context=None
    ) -> ast.Include | list[ast.Statement]:
        """
        An include statement
        """
        return ast.Include(filename=node.filename)

    def visit_ExpressionStatement(
        self, node: ast.ExpressionStatement, context=None
    ) -> ast.ExpressionStatement:
        """A statement that contains a single expression"""
        return ast.ExpressionStatement(
            expression=self.visit(node.expression),
        )

    # Note that QubitDeclaration is not a valid QuantumStatement, because qubits
    # can only be declared in global scopes, not in gates.
    def visit_QubitDeclaration(
        self, node: ast.QubitDeclaration, context=None
    ) -> ast.QubitDeclaration:
        """
        Global qubit declaration

        Example::

            qubit q;
            qubit[4] q;

            q // <- qubit
            4 // <- size

        """
        return ast.QubitDeclaration(
            qubit=self.visit_Identifier(node.qubit),
            size=self.visit(node.size) if node.size else None,
        )

    def visit_QuantumGateDefinition(
        self, node: ast.QuantumGateDefinition, context=None
    ) -> ast.QuantumGateDefinition:
        """
        Define a new quantum gate

        Example::

            gate cx c, t {
                ctrl @ unitary(pi, 0, pi) c, t;
            }

        """
        return ast.QuantumGateDefinition(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit_Identifier),
            qubits=self._visit_list(node.qubits, self.visit_Identifier),
            body=self._visit_list(node.body, self.visit),
        )

    # def visit_QuantumStatement(
    #     self, node: ast.QuantumStatement, context=None
    # ) -> ast.QuantumStatement:
    #     """Statements that may appear inside a gate declaration"""
    #     return ast.QuantumStatement(self._visit_Statement(node))

    def _visit_QuantumStatement(
        self, node: ast.QuantumStatement, context=None
    ) -> list[ast.Annotation]:
        """Statements that may appear inside a gate declaration"""
        return self._visit_Statement(node)

    def visit_ExternDeclaration(
        self, node: ast.ExternDeclaration, context=None
    ) -> ast.ExternDeclaration:
        """
        A extern declaration

        Example::

            extern get_pauli(int[prec], context=None) -> bit[2 * n];

            get_pauli  // <- name
            int[prec]  // <- classical type
            bit[2 * n] // <- return type

        """
        return ast.ExternDeclaration(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit),
            return_type=self.visit(node.return_type) if node.return_type else None,
        )

    # def visit_Expression(self, node: ast.Expression, context=None) -> ast.Expression:
    #     """An expression: anything that returns a value"""
    #     return node

    def visit_Identifier(self, node: ast.Identifier, context=None) -> ast.Identifier:
        """
        An identifier

        Example::

            q1

        """
        return ast.Identifier(name=node.name)

    def visit_UnaryExpression(
        self, node: ast.UnaryExpression, context=None
    ) -> ast.UnaryExpression:
        """
        A unary expression

        Example::

            ~b
            !bool
            -i

        """
        return ast.UnaryExpression(op=node.op, expression=self.visit(node.expression))

    def visit_BinaryExpression(
        self, node: ast.BinaryExpression, context=None
    ) -> ast.BinaryExpression:
        """
        A binary expression

        Example::

            q1 || q2

        """
        return ast.BinaryExpression(
            op=node.op, lhs=self.visit(node.lhs), rhs=self.visit(node.rhs)
        )

    def visit_IntegerLiteral(
        self, node: ast.IntegerLiteral, context=None
    ) -> ast.IntegerLiteral:
        """
        An integer literal

        Example::

            1

        """
        return ast.IntegerLiteral(value=node.value)

    def visit_FloatLiteral(
        self, node: ast.FloatLiteral, context=None
    ) -> ast.FloatLiteral:
        """
        An real number literal

        Example::

            1.1

        """
        return ast.FloatLiteral(value=node.value)

    def visit_ImaginaryLiteral(
        self, node: ast.ImaginaryLiteral, context=None
    ) -> ast.ImaginaryLiteral:
        """
        An real number literal

        Example::

            1.1im

        """
        return ast.ImaginaryLiteral(value=node.value)

    def visit_BooleanLiteral(
        self, node: ast.BooleanLiteral, context=None
    ) -> ast.BooleanLiteral:
        """
        A boolean expression

        Example::

            true
            false

        """
        return ast.BooleanLiteral(value=node.value)

    def visit_BitstringLiteral(
        self, node: ast.BitstringLiteral, context=None
    ) -> ast.BitstringLiteral:
        """A literal bitstring value.  The ``value`` is the numerical value of the
        bitstring, and the ``width`` is the number of digits given."""
        return ast.BitstringLiteral(value=node.value, width=node.width)

    def visit_DurationLiteral(
        self, node: ast.DurationLiteral, context=None
    ) -> ast.DurationLiteral:
        """
        A duration literal

        Example::

            1.0ns

        """
        return ast.DurationLiteral(value=node.value, unit=node.unit)

    def visit_ArrayLiteral(
        self, node: ast.ArrayLiteral, context=None
    ) -> ast.ArrayLiteral:
        """Array literal, used to initialise declared arrays.

        For example::

            array[uint[8], 2] row = {1, 2};
            array[uint[8], 2, 2] my_array = {{1, 2}, {3, 4}};
            array[uint[8], 2, 2] my_array = {row, row};
        """
        return ast.ArrayLiteral(values=self._visit_list(node.values, self.visit))

    def visit_FunctionCall(
        self, node: ast.FunctionCall, context=None
    ) -> ast.FunctionCall:
        """
        A function call expression

        Example::

            foo(1)

            foo // <- name

        """
        return ast.FunctionCall(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit),
        )

    def visit_Cast(self, node: ast.Cast, context=None) -> ast.Cast:
        """
        A cast call expression

        Example::

            counts += int[1](b);

        """
        return ast.Cast(type=self.visit(node.type), argument=self.visit(node.argument))

    def visit_DiscreteSet(self, node: ast.DiscreteSet, context=None) -> ast.DiscreteSet:
        """
        A set of discrete values.  This can be used for the values in a ``for``
        loop, or to index certain values out of a register::

            for i in {1, 2, 3} {}
            let alias = qubits[{2, 3, 4}];
        """
        return ast.DiscreteSet(values=self._visit_list(node.values, self.visit))

    def visit_RangeDefinition(
        self, node: ast.RangeDefinition, context=None
    ) -> ast.RangeDefinition:
        """
        Range definition.

        Example::

            1:2
            1:1:10
            :
        """
        return ast.RangeDefinition(
            start=self.visit(node.start) if node.start else None,
            end=self.visit(node.end) if node.end else None,
            step=self.visit(node.step) if node.step else None,
        )

    IndexElement = ast.DiscreteSet | list[ast.Expression | ast.RangeDefinition]

    def _visit_IndexElement(self, node: IndexElement, context=None) -> IndexElement:
        if isinstance(node, list):
            return self._visit_list(node, self.visit)
        return self.visit(node)

    def visit_IndexExpression(
        self, node: ast.IndexExpression, context=None
    ) -> ast.IndexExpression:
        """
        An index expression.

        Example::

            q[1]
        """
        return ast.IndexExpression(
            collection=self.visit(node.collection),
            index=self._visit_IndexElement(node.index),
        )

    def visit_IndexedIdentifier(
        self, node: ast.IndexedIdentifier, context=None
    ) -> ast.IndexedIdentifier:
        """An indentifier with index operators, such that it can be used as an
        lvalue.  The list of indices is subsequent index brackets, so in::

            a[{1, 2, 3}][0:1, 0:1]

        the list of indices will have two elements.  The first will be a
        :class:`.DiscreteSet`, and the second will be a list of two
        :class:`.RangeDefinition`\\ s.
        """
        nnode = ast.IndexedIdentifier(
            name=self.visit_Identifier(node.name),
            indices=self._visit_list(node.indices, self._visit_IndexElement),
        )
        return nnode

    def visit_Concatenation(
        self, node: ast.Concatenation, context=None
    ) -> ast.Concatenation:
        """
        Concatenation of two registers, for example::

            a ++ b
            a[2:3] ++ a[0:1]
        """
        return ast.Concatenation(lhs=self.visit(node.lhs), rhs=self.visit(node.rhs))

    def visit_QuantumGate(self, node: ast.QuantumGate, context=None) -> ast.QuantumGate:
        """
        Invoking a quantum gate

        Example::
            cx[dur] 0, 1;

            or

            ctrl @ p(λ) a, b;

            ctrl @ // <- quantumGateModifier
            p // <- quantumGateName
            λ // <- argument
            a, b // <- qubit
        """
        return ast.QuantumGate(
            name=self.visit_Identifier(node.name),
            modifiers=self._visit_list(node.modifiers, self.visit_QuantumGateModifier),
            arguments=self._visit_list(node.arguments, self.visit),
            qubits=self._visit_list(node.qubits, self.visit),
            duration=self.visit(node.duration) if node.duration else None,
        )

    def visit_QuantumGateModifier(
        self, node: ast.QuantumGateModifier, context=None
    ) -> ast.QuantumGateModifier:
        """
        A quantum gate modifier

        Attributes:
            modifier: 'inv', 'pow', or 'ctrl'
            expression: only pow modifier has expression.

        Example::

            inv @
            pow(1/2)
            ctrl
        """
        return ast.QuantumGateModifier(
            modifier=node.modifier,
            argument=self.visit(node.argument) if node.argument else None,
        )

    def visit_QuantumPhase(
        self, node: ast.QuantumPhase, context=None
    ) -> ast.QuantumPhase:
        """
        A quantum phase instruction

        Example::

            ctrl @ gphase(λ) a;

            ctrl @ // <- quantumGateModifier
            λ // <- argument
            a // <- qubit

        """
        return ast.QuantumPhase(
            modifiers=self._visit_list(node.modifiers, self.visit_QuantumGateModifier),
            argument=self.visit(node.argument),
            qubits=self._visit_list(node.qubits, self.visit),
        )

    # Not a full expression because it can only be used in limited contexts.
    def visit_QuantumMeasurement(
        self, node: ast.QuantumMeasurement, context=None
    ) -> ast.QuantumMeasurement:
        """
        A quantum measurement instruction

        Example::

            measure q;
        """
        return ast.QuantumMeasurement(
            qubit=self.visit(node.qubit),
        )

    # Note that this is not a QuantumStatement because it involves access to
    # classical bits.
    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement, context=None
    ) -> ast.QuantumMeasurementStatement:
        """Stand-alone statement of a quantum measurement, potentially assigning the
        result to a classical variable.  This is not the only statement that
        `measure` can appear in (it can also be in classical declaration statements
        and returns)."""
        return ast.QuantumMeasurementStatement(
            measure=self.visit_QuantumMeasurement(node.measure),
            target=self.visit(node.target) if node.target else None,
        )

    def visit_QuantumBarrier(
        self, node: ast.QuantumBarrier, context=None
    ) -> ast.QuantumBarrier:
        """
        A quantum barrier instruction

        Example::

            barrier q;
        """
        return ast.QuantumBarrier(
            qubits=self._visit_list(node.qubits, self.visit),
        )

    def visit_QuantumReset(
        self, node: ast.QuantumReset, context=None
    ) -> ast.QuantumReset:
        """
        A reset instruction.

        Example::

            reset q;
        """
        return ast.QuantumReset(
            qubits=self.visit(node.qubits),
        )

    def visit_ClassicalArgument(
        self, node: ast.ClassicalArgument, context=None
    ) -> ast.ClassicalArgument:
        """
        Classical argument for a gate or subroutine declaration
        """
        return ast.ClassicalArgument(
            type=self.visit(node.type),
            name=self.visit_Identifier(node.name),
            access=self.visit(node.access) if node.access else None,
        )

    def visit_ExternArgument(
        self, node: ast.ExternArgument, context=None
    ) -> ast.ExternArgument:
        """Classical argument for an extern declaration."""
        return ast.ExternArgument(
            type=self.visit(node.type),
            access=self.visit(node.access) if node.access else None,
        )

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration, context=None
    ) -> ast.ClassicalDeclaration:
        """
        Classical variable declaration

        Example::

            bit c;
        """
        return ast.ClassicalDeclaration(
            type=self.visit(node.type),
            identifier=self.visit_Identifier(node.identifier),
            init_expression=self.visit(node.init_expression)
            if node.init_expression
            else None,
        )

    def visit_IODeclaration(
        self, node: ast.IODeclaration, context=None
    ) -> ast.IODeclaration:
        """
        Input/output variable declaration

        Exampe::

            input angle[16] theta;
            output bit select;
        """
        return ast.IODeclaration(
            type=self.visit(node.type),
            identifier=self.visit_Identifier(node.identifier),
            io_identifier=node.io_identifier,
        )

    def visit_ConstantDeclaration(
        self, node: ast.ConstantDeclaration, context=None
    ) -> ast.ConstantDeclaration:
        """
        Constant declaration

        Example::

            const int[16] n = 10;
        """
        return ast.ConstantDeclaration(
            type=self.visit(node.type),
            identifier=self.visit_Identifier(node.identifier),
            init_expression=self.visit(node.init_expression),
        )

    # def visit_ClassicalType(
    #     self, node: ast.ClassicalType, context=None
    # ) -> ast.ClassicalType:
    #     """
    #     Base class for classical type
    #     """
    #     return node

    def visit_IntType(self, node: ast.IntType, context=None) -> ast.IntType:
        """
        Node representing a classical ``int`` (signed integer) type, with an
        optional precision.

        Example:

            int[8]
            int[16]
        """
        return ast.IntType(size=self.visit(node.size) if node.size else None)

    def visit_UintType(self, node: ast.UintType, context=None) -> ast.UintType:
        """
        Node representing a classical ``uint`` (unsigned integer) type, with an
        optional precision.

        Example:

            uint[8]
            uint[16]
        """
        return ast.UintType(size=self.visit(node.size) if node.size else None)

    def visit_FloatType(self, node: ast.FloatType, context=None) -> ast.FloatType:
        """
        Node representing the classical ``float`` type, with the particular IEEE-754
        floating-point size optionally specified.

        Example:

            float[16]
            float[64]
        """
        return ast.FloatType(size=self.visit(node.size) if node.size else None)

    def visit_ComplexType(self, node: ast.ComplexType, context=None) -> ast.ComplexType:
        """
        Complex ClassicalType. Its real and imaginary parts are based on other
        classical types.

        Example::

            complex[float]
            complex[float[32]]
        """
        return ast.ComplexType(
            base_type=self.visit(node.base_type) if node.base_type else None
        )

    def visit_AngleType(self, node: ast.AngleType, context=None) -> ast.AngleType:
        """
        Node representing the classical ``angle`` type, with an optional precision.

        Example::

            angle[8]
            angle[16]
        """
        return ast.AngleType(size=self.visit(node.size) if node.size else None)

    def visit_BitType(self, node: ast.BitType, context=None) -> ast.BitType:
        """
        Node representing the classical ``bit`` type, with an optional size.

        Example::

            bit[8]
            creg[8]
        """
        return ast.BitType(size=self.visit(node.size) if node.size else None)

    def visit_BoolType(self, node: ast.BoolType, context=None) -> ast.BoolType:
        """
        Leaf node representing the Boolean classical type.
        """
        return ast.BoolType()

    def visit_ArrayType(self, node: ast.ArrayType, context=None) -> ast.ArrayType:
        """Type of arrays that include allocation of the storage.

        This is generally any array declared as a standard statement, but not
        arrays declared by being arguments to subroutines.
        """
        return ast.ArrayType(
            base_type=self.visit(node.base_type),
            dimensions=self._visit_list(node.dimensions, self.visit),
        )

    def visit_ArrayReferenceType(
        self, node: ast.ArrayReferenceType, context=None
    ) -> ast.ArrayReferenceType:
        """Type of arrays that are a reference to an array with allocated storage.

        This is generally any array declared as a subroutine argument.  The
        dimensions can be either a list of expressions (one for each dimension), or
        a single expression, which is the number of dimensions.

        For example::

            // `a` will have dimensions `[IntegerLiteral(2)]` (with a list), because
            // it is a 1D array, with a length of 2.
            def f(const array[uint[8], 2] a) {}
            // `b` will have dimension `IntegerLiteral(3)` (no list), because it is
            // a 3D array, but we don't know the lengths of its dimensions.
            def f(const array[uint[8], #dim=3] b) {}
        """
        return ast.ArrayReferenceType(
            base_type=self.visit(node.base_type),
            dimensions=self._visit_list(node.dimensions, self.visit)
            if isinstance(node.dimensions, list)
            else self.visit(node.dimensions),
        )

    def visit_DurationType(
        self, node: ast.DurationType, context=None
    ) -> ast.DurationType:
        """
        Leaf node representing the ``duration`` type.
        """
        return ast.DurationType()

    def visit_StretchType(self, node: ast.StretchType, context=None) -> ast.StretchType:
        """
        Leaf node representing the ``stretch`` type.
        """
        return ast.StretchType()

    def visit_CalibrationGrammarDeclaration(
        self, node: ast.CalibrationGrammarDeclaration, context=None
    ) -> ast.CalibrationGrammarDeclaration:
        """
        Calibration grammar declaration

        Example::

            defcalgrammar "openpulse";
        """
        return ast.CalibrationGrammarDeclaration(node.name)

    def visit_CalibrationStatement(
        self, node: ast.CalibrationStatement, context=None
    ) -> ast.CalibrationStatement:
        """An inline ``cal`` statement for embedded pulse-grammar interactions.

        Example::

            cal {
                shift_phase(drive($0), theta);
            }
        """
        return ast.CalibrationStatement(body=self._visit_list(node.body, self.visit))

    def visit_CalibrationBlock(
        self, node: ast.CalibrationBlock, context=None
    ) -> ast.CalibrationBlock:
        return ast.CalibrationBlock(body=self._visit_list(node.body, self.visit))

    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition, context=None
    ) -> ast.CalibrationDefinition:
        """
        Calibration definition

        Example::

            defcal rz(angle[20] theta) q {
                shift_phase drive(q), -theta;
            }
        """
        return ast.CalibrationDefinition(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit),
            qubits=self._visit_list(node.qubits, self.visit),
            body=self._visit_list(node.body, self.visit),
            return_type=self.visit(node.return_type) if node.return_type else None,
        )

    def visit_SubroutineDefinition(
        self, node: ast.SubroutineDefinition, context=None
    ) -> ast.SubroutineDefinition:
        """
        Subroutine definition

        Example::

            def measure(qubit q, context=None) -> bit {
                s q;
                h q;
                return measure q;
            }
        """
        return ast.SubroutineDefinition(
            name=self.visit_Identifier(node.name),
            arguments=self._visit_list(node.arguments, self.visit),
            body=self._visit_list(node.body, self.visit),
            return_type=self.visit(node.return_type) if node.return_type else None,
        )

    def visit_QuantumArgument(
        self, node: ast.QuantumArgument, context=None
    ) -> ast.QuantumArgument:
        """
        Quantum argument for a subroutine declaration
        """
        return ast.QuantumArgument(
            name=self.visit_Identifier(node.name),
            size=self.visit(node.size) if node.size else None,
        )

    def visit_ReturnStatement(
        self, node: ast.ReturnStatement, context=None
    ) -> ast.ReturnStatement:
        """
        Classical or quantum return statement

        Example::

            return measure q;

            return a + b

        """
        return ast.ReturnStatement(
            expression=self.visit(node.expression) if node.expression else None,
        )

    def visit_BreakStatement(
        self, node: ast.BreakStatement, context=None
    ) -> ast.BreakStatement:
        """
        Break statement

        Example::

            break;
        """
        return ast.BreakStatement()

    def visit_ContinueStatement(
        self, node: ast.ContinueStatement, context=None
    ) -> ast.ContinueStatement:
        """
        Continue statement

        Example::

            continue;
        """
        return ast.ContinueStatement()

    def visit_EndStatement(
        self, node: ast.EndStatement, context=None
    ) -> ast.EndStatement:
        """
        End statement

        Example::

            end;
        """
        return ast.EndStatement()

    def visit_BranchingStatement(
        self, node: ast.BranchingStatement, context=None
    ) -> ast.Statement:
        """
        Branch (``if``) statement

        Example::

            if (temp == 1) {
                ry(-pi / 2) scratch[0];
            } else continue;
        """
        return ast.BranchingStatement(
            condition=self.visit(node.condition),
            if_block=self._visit_list(node.if_block, self.visit),
            else_block=self._visit_list(node.else_block, self.visit),
        )

    def visit_WhileLoop(self, node: ast.WhileLoop, context=None) -> ast.WhileLoop:
        """
        While loop

        Example::

            while(~success) {
                reset magic;
                ry(pi / 4) magic;
                success = distill(magic, scratch);
            }
        """
        return ast.WhileLoop(
            while_condition=self.visit(node.while_condition),
            block=self._visit_list(node.block, self.visit),
        )

    def visit_ForInLoop(self, node: ast.ForInLoop, context=None) -> ast.ForInLoop:
        """
        For in loop

        Example::

            for i in [0: 2] {
                majority a[i], b[i + 1], a[i + 1];
            }
        """
        return ast.ForInLoop(
            type=self.visit(node.type),
            identifier=self.visit_Identifier(node.identifier),
            set_declaration=self.visit(node.set_declaration),
            block=self._visit_list(node.block, self.visit),
        )

    def visit_DelayInstruction(
        self, node: ast.DelayInstruction, context=None
    ) -> ast.DelayInstruction:
        """
        Delay instruction

        Example::

            delay[start_stretch] $0;
        """
        return ast.DelayInstruction(
            duration=self.visit(node.duration),
            qubits=self._visit_list(node.qubits, self.visit),
        )

    def visit_Box(self, node: ast.Box, context=None) -> ast.Box:
        """
        Timing box

        Example::

            box [maxdur] {
                delay[start_stretch] $0;
                x $0;
            }
        """
        return ast.Box(
            duration=self.visit(node.duration) if node.duration else None,
            body=self._visit_list(node.body, self.visit),
        )

    def visit_DurationOf(self, node: ast.DurationOf, context=None) -> ast.DurationOf:
        """
        Duration Of

        Example::

            durationof({x $0;})
        """
        return ast.DurationOf(
            target=self._visit_list(node.target, self.visit),
        )

    def visit_SizeOf(self, node: ast.SizeOf, context=None) -> ast.SizeOf:
        """``sizeof`` an array's dimensions."""
        return ast.SizeOf(
            target=self.visit(node.target),
            index=self.visit(node.index) if node.index else None,
        )

    def visit_AliasStatement(
        self, node: ast.AliasStatement, context=None
    ) -> ast.AliasStatement:
        """
        Alias statement

        Example::

            let a = qubits[0];

        """
        return ast.AliasStatement(
            target=self.visit_Identifier(node.target),
            value=self.visit(node.value),
        )

    def visit_ClassicalAssignment(
        self, node: ast.ClassicalAssignment, context=None
    ) -> ast.ClassicalAssignment:
        """
        Classical assignment

        Example::

            a[0] = 1;
        """
        return ast.ClassicalAssignment(
            op=node.op,
            lvalue=self.visit(node.lvalue),
            rvalue=self.visit(node.rvalue),
        )

    def visit_Pragma(self, node: ast.Pragma, context=None) -> ast.Pragma:
        """
        Pragma
        Example::

            #pragma val1 val2 val3
        """
        return ast.Pragma(node.command)

    def visit_WaveformType(
        self, node: ast.WaveformType, context=None
    ) -> ast.WaveformType:
        return ast.WaveformType()

    def visit_PortType(self, node: ast.PortType, context=None) -> ast.PortType:
        return ast.PortType()

    def visit_FrameType(self, node: ast.FrameType, context=None) -> ast.FrameType:
        return ast.FrameType()
