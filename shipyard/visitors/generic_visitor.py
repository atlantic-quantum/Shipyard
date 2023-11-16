from openpulse import ast
from openqasm3.visitor import QASMVisitor

# pylint: disable=C0103,W0613,R0904


class GenericVisitor(QASMVisitor):
    def _visit_list(
        self, nodes: list[ast.QASMNode], visit_function: callable, context=None
    ):
        [visit_function(node) for node in nodes]

    def visit_Program(self, node: ast.Program, context=None):
        """
        An entire OpenQASM 3 program represented by a list of top level statements
        """
        self._visit_list(node.statements, self.visit)

    def visit_Annotation(self, node: ast.Annotation, context=None):
        """An annotation applied to a statment."""

    def visit_Statement(self, node: ast.Statement, context=None):
        """A statement: anything that can appear on its own line"""
        self._visit_list(node.annotations, self.visit)

    def visit_Include(
        self, node: ast.Include, context=None
    ) -> ast.Include | list[ast.Statement]:
        """
        An include statement
        """
        self.visit_Statement(node)

    def visit_ExpressionStatement(self, node: ast.ExpressionStatement, context=None):
        """A statement that contains a single expression"""
        self.visit_Statement(node)
        self.visit(node.expression)

    # Note that QubitDeclaration is not a valid QuantumStatement, because qubits
    # can only be declared in global scopes, not in gates.
    def visit_QubitDeclaration(self, node: ast.QubitDeclaration, context=None):
        """
        Global qubit declaration

        Example::

            qubit q;
            qubit[4] q;

            q // <- qubit
            4 // <- size

        """
        self.visit_Statement(node)
        self.visit_Identifier(node.qubit)
        if node.size:
            self.visit(node.size)

    def visit_QuantumGateDefinition(
        self, node: ast.QuantumGateDefinition, context=None
    ):
        """
        Define a new quantum gate

        Example::

            gate cx c, t {
                ctrl @ unitary(pi, 0, pi) c, t;
            }

        """
        self.visit_Statement(node)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit_Identifier)
        self._visit_list(node.qubits, self.visit_Identifier)
        self._visit_list(node.body, self.visit)

    def visit_QuantumStatement(self, node: ast.QuantumStatement, context=None):
        """Statements that may appear inside a gate declaration"""
        self.visit_Statement(node)

    def visit_ExternDeclaration(self, node: ast.ExternDeclaration, context=None):
        """
        A extern declaration

        Example::

            extern get_pauli(int[prec], context=None) -> bit[2 * n];

            get_pauli  // <- name
            int[prec]  // <- classical type
            bit[2 * n] // <- return type

        """
        self.visit_Statement(node)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit)
        if node.return_type:
            self.visit(node.return_type)

    def visit_Expression(self, node: ast.Expression, context=None):
        """An expression: anything that returns a value"""

    def visit_Identifier(self, node: ast.Identifier, context=None):
        """
        An identifier

        Example::

            q1

        """
        self.visit_Expression(node)

    def visit_UnaryExpression(self, node: ast.UnaryExpression, context=None):
        """
        A unary expression

        Example::

            ~b
            !bool
            -i

        """
        self.visit_Expression(node)

    def visit_BinaryExpression(self, node: ast.BinaryExpression, context=None):
        """
        A binary expression

        Example::

            q1 || q2

        """
        self.visit_Expression(node)
        self.visit(node.lhs)
        self.visit(node.rhs)

    def visit_IntegerLiteral(self, node: ast.IntegerLiteral, context=None):
        """
        An integer literal

        Example::

            1

        """
        self.visit_Expression(node)

    def visit_FloatLiteral(self, node: ast.FloatLiteral, context=None):
        """
        An real number literal

        Example::

            1.1

        """
        self.visit_Expression(node)

    def visit_ImaginaryLiteral(self, node: ast.ImaginaryLiteral, context=None):
        """
        An real number literal

        Example::

            1.1im

        """
        self.visit_Expression(node)

    def visit_BooleanLiteral(self, node: ast.BooleanLiteral, context=None):
        """
        A boolean expression

        Example::

            true
            false

        """
        self.visit_Expression(node)

    def visit_BitstringLiteral(self, node: ast.BitstringLiteral, context=None):
        """A literal bitstring value.  The ``value`` is the numerical value of the
        bitstring, and the ``width`` is the number of digits given."""
        self.visit_Expression(node)

    def visit_DurationLiteral(self, node: ast.DurationLiteral, context=None):
        """
        A duration literal

        Example::

            1.0ns

        """
        self.visit_Expression(node)

    def visit_ArrayLiteral(self, node: ast.ArrayLiteral, context=None):
        """Array literal, used to initialise declared arrays.

        For example::

            array[uint[8], 2] row{1, 2};
            array[uint[8], 2, 2] my_array{{1, 2}, {3, 4}};
            array[uint[8], 2, 2] my_array{row, row};
        """
        self.visit_Expression(node)
        self._visit_list(node.values, self.visit)

    def visit_FunctionCall(self, node: ast.FunctionCall, context=None):
        """
        A function call expression

        Example::

            foo(1)

            foo // <- name

        """
        self.visit_Expression(node)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit)

    def visit_Cast(self, node: ast.Cast, context=None):
        """
        A cast call expression

        Example::

            counts += int[1](b);

        """
        self.visit_Expression(node)
        self.visit(node.type)
        self.visit(node.argument)

    def visit_DiscreteSet(self, node: ast.DiscreteSet, context=None):
        """
        A set of discrete values.  This can be used for the values in a ``for``
        loop, or to index certain values out of a register::

            for i in {1, 2, 3} {}
            let aliasqubits[{2, 3, 4}];
        """
        self._visit_list(node.values, self.visit)

    def visit_RangeDefinition(self, node: ast.RangeDefinition, context=None):
        """
        Range definition.

        Example::

            1:2
            1:1:10
            :
        """
        if node.start:
            self.visit(node.start)
        if node.end:
            self.visit(node.end)
        if node.step:
            self.visit(node.step)

    IndexElement = ast.DiscreteSet | list[ast.Expression | ast.RangeDefinition]

    def _visit_IndexElement(self, node: IndexElement, context=None):
        if isinstance(node, list):
            return self._visit_list(node, self.visit)
        return self.visit(node)

    def visit_IndexExpression(self, node: ast.IndexExpression, context=None):
        """
        An index expression.

        Example::

            q[1]
        """
        self.visit_Expression(node)
        self.visit(node.collection)
        self._visit_IndexElement(node.index)

    def visit_IndexedIdentifier(self, node: ast.IndexedIdentifier, context=None):
        """An indentifier with index operators, such that it can be used as an
        lvalue.  The list of indices is subsequent index brackets, so in::

            a[{1, 2, 3}][0:1, 0:1]

        the list of indices will have two elements.  The first will be a
        :class:`.DiscreteSet`, and the second will be a list of two
        :class:`.RangeDefinition`\\ s.
        """
        self.visit_Identifier(node.name)
        self._visit_list(node.indices, self._visit_IndexElement)

    def visit_Concatenation(self, node: ast.Concatenation, context=None):
        """
        Concatenation of two registers, for example::

            a ++ b
            a[2:3] ++ a[0:1]
        """
        self.visit_Expression(node)
        self.visit(node.lhs)
        self.visit(node.rhs)

    def visit_QuantumGate(self, node: ast.QuantumGate, context=None):
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
        self.visit_QuantumStatement(node)
        self._visit_list(node.modifiers, self.visit_QuantumGateModifier)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit)
        self._visit_list(node.qubits, self.visit)
        if node.duration:
            self.visit(node.duration)

    def visit_QuantumGateModifier(self, node: ast.QuantumGateModifier, context=None):
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
        if node.argument:
            self.visit(node.argument)

    def visit_QuantumPhase(self, node: ast.QuantumPhase, context=None):
        """
        A quantum phase instruction

        Example::

            ctrl @ gphase(λ) a;

            ctrl @ // <- quantumGateModifier
            λ // <- argument
            a // <- qubit

        """
        self.visit_QuantumStatement(node)
        self._visit_list(node.modifiers, self.visit_QuantumGateModifier)
        self.visit(node.argument)
        self._visit_list(node.qubits, self.visit)

    # Not a full expression because it can only be used in limited contexts.
    def visit_QuantumMeasurement(self, node: ast.QuantumMeasurement, context=None):
        """
        A quantum measurement instruction

        Example::

            measure q;
        """
        self.visit(node.qubit)

    # Note that this is not a QuantumStatement because it involves access to
    # classical bits.
    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement, context=None
    ):
        """Stand-alone statement of a quantum measurement, potentially assigning the
        result to a classical variable.  This is not the only statement that
        `measure` can appear in (it can also be in classical declaration statements
        and returns)."""
        self.visit_Statement(node)
        self.visit_QuantumMeasurement(node.measure)
        if node.target:
            self.visit(node.target)

    def visit_QuantumBarrier(self, node: ast.QuantumBarrier, context=None):
        """
        A quantum barrier instruction

        Example::

            barrier q;
        """
        self.visit_QuantumStatement(node)
        self._visit_list(node.qubits, self.visit)

    def visit_QuantumReset(self, node: ast.QuantumReset, context=None):
        """
        A reset instruction.

        Example::

            reset q;
        """

        self.visit_QuantumStatement(node)
        self.visit(node.qubits)

    def visit_ClassicalArgument(self, node: ast.ClassicalArgument, context=None):
        """
        Classical argument for a gate or subroutine declaration
        """
        self.visit(node.type)
        self.visit_Identifier(node.name)

    def visit_ExternArgument(self, node: ast.ExternArgument, context=None):
        """Classical argument for an extern declaration."""

        self.visit(node.type)

    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration, context=None):
        """
        Classical variable declaration

        Example::

            bit c;
        """

        self.visit_Statement(node)
        self.visit(node.type)
        self.visit_Identifier(node.identifier)
        if node.init_expression:
            self.visit(node.init_expression)

    def visit_IODeclaration(self, node: ast.IODeclaration, context=None):
        """
        Input/output variable declaration

        Exampe::

            input angle[16] theta;
            output bit select;
        """
        self.visit_Statement(node)
        self.visit(node.type)
        self.visit_Identifier(node.identifier)

    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration, context=None):
        """
        Constant declaration

        Example::

            const int[16] n10;
        """
        self.visit_Statement(node)
        self.visit(node.type)
        self.visit_Identifier(node.identifier)
        self.visit(node.init_expression)

    def visit_ClassicalType(self, node: ast.ClassicalType, context=None):
        """
        Base class for classical type
        """

    def visit_IntType(self, node: ast.IntType, context=None):
        """
        Node representing a classical ``int`` (signed integer) type, with an
        optional precision.

        Example:

            int[8]
            int[16]
        """
        self.visit_ClassicalType(node)
        if node.size:
            self.visit(node.size)

    def visit_UintType(self, node: ast.UintType, context=None):
        """
        Node representing a classical ``uint`` (unsigned integer) type, with an
        optional precision.

        Example:

            uint[8]
            uint[16]
        """

        self.visit_ClassicalType(node)
        if node.size:
            self.visit(node.size)

    def visit_FloatType(self, node: ast.FloatType, context=None):
        """
        Node representing the classical ``float`` type, with the particular IEEE-754
        floating-point size optionally specified.

        Example:

            float[16]
            float[64]
        """
        self.visit_ClassicalType(node)
        if node.size:
            self.visit(node.size)

    def visit_ComplexType(self, node: ast.ComplexType, context=None):
        """
        Complex ClassicalType. Its real and imaginary parts are based on other
        classical types.

        Example::

            complex[float]
            complex[float[32]]
        """
        self.visit_ClassicalType(node)
        if node.base_type:
            self.visit(node.base_type)

    def visit_AngleType(self, node: ast.AngleType, context=None):
        """
        Node representing the classical ``angle`` type, with an optional precision.

        Example::

            angle[8]
            angle[16]
        """
        self.visit_ClassicalType(node)
        if node.size:
            self.visit(node.size)

    def visit_BitType(self, node: ast.BitType, context=None):
        """
        Node representing the classical ``bit`` type, with an optional size.

        Example::

            bit[8]
            creg[8]
        """
        self.visit_ClassicalType(node)
        if node.size:
            self.visit(node.size)

    def visit_BoolType(self, node: ast.BoolType, context=None):
        """
        Leaf node representing the Boolean classical type.
        """
        self.visit_ClassicalType(node)

    def visit_ArrayType(self, node: ast.ArrayType, context=None):
        """Type of arrays that include allocation of the storage.

        This is generally any array declared as a standard statement, but not
        arrays declared by being arguments to subroutines.
        """
        self.visit_ClassicalType(node)
        self.visit(node.base_type)
        self._visit_list(node.dimensions, self.visit)

    def visit_ArrayReferenceType(self, node: ast.ArrayReferenceType, context=None):
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

        self.visit_ClassicalType(node)
        self.visit(node.base_type)
        if isinstance(node.dimensions, list):
            self._visit_list(node.dimensions, self.visit)
        else:
            self.visit(node.dimensions)

    def visit_DurationType(self, node: ast.DurationType, context=None):
        """
        Leaf node representing the ``duration`` type.
        """
        self.visit_ClassicalType(node)

    def visit_StretchType(self, node: ast.StretchType, context=None) -> ast.StretchType:
        """
        Leaf node representing the ``stretch`` type.
        """
        self.visit_ClassicalType(node)

    def visit_CalibrationGrammarDeclaration(
        self, node: ast.CalibrationGrammarDeclaration, context=None
    ):
        """
        Calibration grammar declaration

        Example::

            defcalgrammar "openpulse";
        """

    def visit_CalibrationStatement(self, node: ast.CalibrationStatement, context=None):
        """An inline ``cal`` statement for embedded pulse-grammar interactions.

        Example::

            cal {
                shift_phase(drive($0), theta);
            }
        """
        self.visit_Statement(node)
        self._visit_list(node.body, self.visit)

    def visit_CalibrationBlock(self, node: ast.CalibrationBlock, context=None):
        self._visit_list(node.body, self.visit)

    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition, context=None
    ):
        """
        Calibration definition

        Example::

            defcal rz(angle[20] theta) q {
                shift_phase drive(q), -theta;
            }
        """
        self.visit_Statement(node)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit)
        self._visit_list(node.qubits, self.visit_Identifier)
        self._visit_list(node.body, self.visit)
        if node.return_type:
            self.visit(node.return_type)

    def visit_SubroutineDefinition(self, node: ast.SubroutineDefinition, context=None):
        """
        Subroutine definition

        Example::

            def measure(qubit q, context=None) -> bit {
                s q;
                h q;
                return measure q;
            }
        """
        self.visit_Statement(node)
        self.visit_Identifier(node.name)
        self._visit_list(node.arguments, self.visit)
        self._visit_list(node.body, self.visit)
        if node.return_type:
            self.visit(node.return_type)

    def visit_QuantumArgument(self, node: ast.QuantumArgument, context=None):
        """
        Quantum argument for a subroutine declaration
        """
        self.visit_Identifier(node.name)
        if node.size:
            self.visit(node.size)

    def visit_ReturnStatement(self, node: ast.ReturnStatement, context=None):
        """
        Classical or quantum return statement

        Example::

            return measure q;

            return a + b

        """
        self.visit_Statement(node)
        if node.expression:
            self.visit(node.expression)

    def visit_BreakStatement(self, node: ast.BreakStatement, context=None):
        """
        Break statement

        Example::

            break;
        """
        self.visit_Statement(node)

    def visit_ContinueStatement(self, node: ast.ContinueStatement, context=None):
        """
        Continue statement

        Example::

            continue;
        """
        self.visit_Statement(node)

    def visit_EndStatement(self, node: ast.EndStatement, context=None):
        """
        End statement

        Example::

            end;
        """
        self.visit_Statement(node)

    def visit_BranchingStatement(self, node: ast.BranchingStatement, context=None):
        """
        Branch (``if``) statement

        Example::

            if (temp == 1) {
                ry(-pi / 2) scratch[0];
            } else continue;
        """
        self.visit_Statement(node)
        self.visit(node.condition)
        self._visit_list(node.if_block, self.visit)
        self._visit_list(node.else_block, self.visit)

    def visit_WhileLoop(self, node: ast.WhileLoop, context=None):
        """
        While loop

        Example::

            while(~success) {
                reset magic;
                ry(pi / 4) magic;
                successdistill(magic, scratch);
            }
        """
        self.visit_Statement(node)
        self.visit(node.while_condition)
        self._visit_list(node.block, self.visit)

    def visit_ForInLoop(self, node: ast.ForInLoop, context=None):
        """
        For in loop

        Example::

            for i in [0: 2] {
                majority a[i], b[i + 1], a[i + 1];
            }
        """
        self.visit_Statement(node)
        self.visit(node.type)
        self.visit_Identifier(node.identifier)
        self.visit(node.set_declaration)
        self._visit_list(node.block, self.visit)

    def visit_DelayInstruction(self, node: ast.DelayInstruction, context=None):
        """
        Delay instruction

        Example::

            delay[start_stretch] $0;
        """
        self.visit_QuantumStatement(node)
        self.visit(node.duration)
        self._visit_list(node.qubits, self.visit)

    def visit_Box(self, node: ast.Box, context=None):
        """
        Timing box

        Example::

            box [maxdur] {
                delay[start_stretch] $0;
                x $0;
            }
        """
        self.visit_QuantumStatement(node)
        if node.duration:
            self.visit(node.duration)
        self._visit_list(node.body, self.visit)

    def visit_DurationOf(self, node: ast.DurationOf, context=None):
        """
        Duration Of

        Example::

            durationof({x $0;})
        """
        self.visit_Expression(node)
        self._visit_list(node.target, self.visit)

    def visit_SizeOf(self, node: ast.SizeOf, context=None):
        """``sizeof`` an array's dimensions."""
        self.visit_Expression(node)
        self.visit(node.target)
        if node.index:
            self.visit(node.index)

    def visit_AliasStatement(self, node: ast.AliasStatement, context=None):
        """
        Alias statement

        Example::

            let aqubits[0];

        """
        self.visit_Statement(node)
        self.visit_Identifier(node.target)
        self.visit(node.value)

    def visit_ClassicalAssignment(self, node: ast.ClassicalAssignment, context=None):
        """
        Classical assignment

        Example::

            a[0]1;
        """
        self.visit_Statement(node)
        self.visit(node.lvalue)
        self.visit(node.rvalue)

    def visit_Pragma(self, node: ast.Pragma, context=None):
        """
        Pragma
        Example::

            #pragma val1 val2 val3
        """

    def visit_WaveformType(self, node: ast.WaveformType, context=None):
        self.visit_ClassicalType(node)

    def visit_PortType(self, node: ast.PortType, context=None):
        self.visit_ClassicalType(node)

    def visit_FrameType(self, node: ast.FrameType, context=None):
        self.visit_ClassicalType(node)
