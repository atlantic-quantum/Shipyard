"""
Module that host the SemanticAnalyser QASMVisitor class that can be used to perform
semantic analysis on openQASM Abstract Syntax Trees.
"""
from contextlib import contextmanager

from openpulse import ast

from ...compiler_error import ErrorCode, SemanticError
from ...logger import LOGGER
from ...mangle import Mangler
from ...utilities import ScopeContext
from ...visitors import GenericVisitor, LiteralVisitor, TypeVisitor
from .scoped_symbol_table import CalScopedSymbolTable, ScopedSymbolTable
from .symbols import (
    AliasSymbol,
    ClassicalSymbol,
    ConstantSymbol,
    DefcalSymbol,
    ExternSymbol,
    GateSymbol,
    IOSymbol,
    LiteralSymbol,
    QuantumSymbol,
    SubroutineSymbol,
    Symbol,
)


# pylint: disable=R0904:
# Too many public methods
class SemanticAnalyzer(TypeVisitor, LiteralVisitor, GenericVisitor):
    """
    QASMVisitor class that peforms semantic analysis on a openQASM Abstract Syntax Tree

    usage:
        qasm_ast = openpulse.parse(qasm_program_string)
        sa = SemanticAnalyser()
        sa.visit(qasm_ast)
    """

    def __init__(self) -> None:
        self.current_scope: ScopedSymbolTable = None
        self._calibration_scope: CalScopedSymbolTable = None
        self._scope_context: ScopeContext = None
        super().__init__()

    @property
    def calibration_scope(self) -> CalScopedSymbolTable:
        """Getter for the 'calibration_scope' symbol table of a SemanticAnalyser
        instance. Creates and returns an initialised calibration scope on first call.
        Subsequent calls return the same scope.

        Returns:
            CalScopedSymbolTable: a scoped symbol table used for symbols declared within
            openpulse syntax (cal & defcal)
        """
        if self._calibration_scope is None:
            self.ensure_in_global_scope(ast.Identifier("init cal scope"))
            self._calibration_scope = CalScopedSymbolTable(
                "cal_scope", enclosing_scope=self.current_scope, init_cal=True
            )
        return self._calibration_scope

    @property
    def scope_context(self) -> ScopeContext:
        """Getter for the 'scope_context' property of a SemanticAnalyser instance"""
        return self._scope_context

    @scope_context.setter
    def scope_context(self, value: ScopeContext):
        LOGGER.debug("SET SCOPE CONTEXT: %s", value)
        self._scope_context = value

    # pylint: disable=C0103
    # disable snake_case naming style
    # these functions are of the form "visit_{QASMNode class name}"
    def visit_Program(self, node: ast.Program) -> None:
        """
        Program node visitor,
            creates and enters a global symbol table (global scope),
            visits all other statements in the openQASM program.

        Args:
            node (ast.Program):
                openQASM program ast node to visit
        """
        global_scope = ScopedSymbolTable(
            scope_name="global",
            enclosing_scope=self.current_scope,
        )
        with self.scope_context_manager(global_scope, ScopeContext.GLOBAL):
            for statement in node.statements:
                self.visit(statement)

    def visit_ExternDeclaration(self, node: ast.ExternDeclaration) -> None:
        """
        ExternDeclaration node visitor,
            inserts a symbol representing the external function declaration
            into current_scope (symbol table)

        Args:
            node (ast.ExternDeclaration):
                openQASM external function declaration ast node to visit
        """
        extern_name = node.name.name
        params = [
            ClassicalSymbol(
                name=f"{extern_name}_arg_{i}", kind=self.visit(argument.type)
            )
            for i, argument in enumerate(node.arguments)
        ]
        return_type = self.visit(node.return_type) if node.return_type else None
        extern_symbol = ExternSymbol(
            name=extern_name, params=params, return_type=return_type
        )
        self.declare_symbol(extern_symbol)

    def visit_SubroutineDefinition(self, node: ast.SubroutineDefinition) -> None:
        """
        SubroutineDefinition node visitor, subroutines may only be defined in global
        scope.
            inserts a symbol representing the subroutine definition into current_scope,
            creates and enters a symbol table (local scope) to encapsulate
            the subroutie,
            inserts all the parameters of the subroutine function signature into the
            new symbol table,
            visits all statements within the subroutine.

        Args:
            node (ast.SubroutineDefinition):
                openQASM subroutine definition ast node to visit
        """
        self.ensure_in_global_scope(node.name)
        return_type = self.visit(node.return_type) if node.return_type else None
        subroutine_symbol = SubroutineSymbol(
            name=node.name.name, return_type=return_type
        )

        self.declare_symbol(subroutine_symbol)

        subroutine_scope = ScopedSymbolTable(
            scope_name=node.name.name,
            enclosing_scope=self.current_scope,
        )

        with self.scope_context_manager(subroutine_scope, ScopeContext.SUBROUTINE):
            for argument in node.arguments:
                arg_symbol = self.visit(argument)
                subroutine_symbol.params.append(arg_symbol)

            for statement in node.body:
                self.visit(statement)

    def visit_QuantumGateDefinition(self, node: ast.QuantumGateDefinition) -> None:
        """
        QuantumGateDefinition node visitor, quantum gates may only be defined in global
        scope.
            inserts a symbol representing the gate definition into current_scope,
            creates and enters a symbol table (local scope) to encapsulate
            the gate,
            inserts all the parameters and qubits of the gate function signature
            into the new symbol table,
            visits all statements within the gate definition.

        Args:
            node (ast.QuantumGateDefinition):
                openQASM quantum gate definition ast node to visit
        """
        self.ensure_in_global_scope(node.name)
        gate_symbol = GateSymbol(name=node.name.name)

        self.declare_symbol(gate_symbol)

        gate_scope = ScopedSymbolTable(
            scope_name=gate_symbol.name,
            enclosing_scope=self.current_scope,
        )

        with self.scope_context_manager(gate_scope, ScopeContext.SUBROUTINE):
            for argument in node.arguments:
                arg_symbol = Symbol(name=argument.name)
                self.declare_symbol(arg_symbol)
                gate_symbol.params.append(arg_symbol)

            for qubit in node.qubits:
                qubit_symbol = QuantumSymbol(name=qubit.name, kind="QUBIT")
                self.declare_symbol(qubit_symbol)
                gate_symbol.qubits.append(qubit_symbol)

            for statement in node.body:
                self.visit(statement)

    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration) -> None:
        """
        ClassicalDeclaration node visitor
            inserts a symbol representing the classical variable into current_scope

            Note:
                Arrays cannot be declared inside the body of a function or gate.
                All arrays must be declared within the global scope of the program.
                https://openqasm.com/language/types.html#arrays

        Args:
            node (ast.ClassicalDeclaration):
                openQASM classical declaration ast node to visit
        """
        if isinstance(node.type, ast.ArrayType):
            self.ensure_in_global_scope(node.identifier)
        type_symbol = self.visit(node.type)
        LOGGER.debug(
            "Classical Declaration: name: %s, kind: %s",
            node.identifier.name,
            type_symbol,
        )
        decl_symbol = ClassicalSymbol(name=node.identifier.name, kind=type_symbol)
        self.declare_symbol(decl_symbol)

    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration) -> None:
        """
        ConstantDeclaration node visitor
            inserts a symbol representing the constant into current_scope

        Args:
            node (ast.ConstantDeclaration):
                openQASM constant declaration ast node to visit
        """
        type_symbol = self.visit(node.type)
        decl_symbol = ConstantSymbol(name=node.identifier.name, kind=type_symbol)
        self.declare_symbol(decl_symbol)

    def visit_QubitDeclaration(self, node: ast.QubitDeclaration) -> None:
        """
        QubitDeclaration node visitor
            inserts a symbol representing the qubit into current_scope

            Note:
                All qubits are global variables.
                Qubits cannot be declared within gates or subroutines.
                https://openqasm.com/language/types.html#quantum-types

        Args:
            node (ast.QubitDeclaration):
                openQASM qubit declaration ast node to visit
        """
        # qubits can only be declared in global scope
        self.ensure_in_global_scope(node.qubit)
        decl_symbol = QuantumSymbol(name=node.qubit.name, kind="QUBIT")
        self.declare_symbol(decl_symbol)

    def visit_IODeclaration(self, node: ast.IODeclaration) -> None:
        """
        ToDo: may require more / different handling when we start using this

        IODeclaration node visitor
            inserts a symbol representing the io into current_scope

            input/output modifiers can be used to indicate that variables will be
            supplied to / generated by an openQASM program at runtime

            https://openqasm.com/language/directives.html#input-output

        Args:
            node (ast.IODeclaration):
                openQASM io declaration ast node to visit
        """
        type_symbol = self.visit(node.type)
        decl_symbol = IOSymbol(name=node.identifier.name, kind=type_symbol)
        self.declare_symbol(decl_symbol)

    def visit_Identifier(self, node: ast.Identifier):
        """
        Identifier node visitor:
            Looks up the name of the identifer within current and enclosing scope,
            raises an ID_NOT_FOUND error if the identifier hasn't been declared

        Args:
            node (ast.Identifier):
                openQASM identifier node to visit

        Raises:
            SemanticError with ErrorCode.ID_NOT_FOUND
        """
        node_symbol = self.current_scope.lookup(node.name)
        if node.name[0] == "$":
            pass
        elif node_symbol is None:
            raise self.error(ErrorCode.ID_NOT_FOUND, node.name)

    def visit_AliasStatement(self, node: ast.AliasStatement) -> None:
        """
        AliastStatement node visitor:
            Creates and declares a symbol for an Alias.
            Then visits the value the alias is assigned

        Args:
            node (ast.AliasStatement):
                openQASM alias statment to visit
        """
        alias_symbol = AliasSymbol(name=node.target.name)
        self.declare_symbol(alias_symbol)
        self.visit(node.value)

    def visit_CalibrationStatement(self, node: ast.CalibrationStatement) -> None:
        """
        CalibrationStatement node visitor, (cal {} statements):
            Enters calibration scope and visits all statements in the body of the
            calibration statement.

        Args:
            node (ast.CalibrationStatement):
                openQASM calibration statement node to visit
        """
        self.ensure_in_global_scope(ast.Identifier("Calibration Statement"))
        with self.scope_context_manager(self.calibration_scope, ScopeContext.DEFCAL):
            for statement in node.body:
                self.visit(statement)

    def visit_CalibrationDefinition(self, node: ast.CalibrationDefinition) -> None:
        """
        CalibrationDefinition node visitor, (defcal {} statements):
            Gets a mangles name for the calibration definition and uses it
            to create a symbol representing the defcal statement.
            Inserts a symbol representing the defcal statement into calibration scope.
            Creates a new CalScopedSymbolTable and enters it.
            Inserts symbols for all parameters and qubits into the new scope.
            Visits all statements withing the body of the defcal statement

        Args:
            node (ast.CalibrationDefinition):
                openQASM calibration definition node to visit
        """
        self.ensure_in_global_scope(node.name)
        defcal_name = Mangler(node).signature().mangle()
        return_type = self.visit(node.return_type) if node.return_type else None
        defcal_symbol = DefcalSymbol(name=defcal_name, return_type=return_type)
        with self.scope_context_manager(
            self.calibration_scope, context=ScopeContext.DEFCAL
        ):
            self.declare_symbol(defcal_symbol)

        defcal_scope = CalScopedSymbolTable(
            scope_name=defcal_symbol.name,
            enclosing_scope=self.calibration_scope,
        )

        with self.scope_context_manager(defcal_scope, ScopeContext.DEFCAL):
            for argument in node.arguments:
                arg_symbol = self.visit(argument)
                defcal_symbol.params.append(arg_symbol)

            for qubit in node.qubits:
                qubit_symbol = QuantumSymbol(
                    name=qubit.name, kind=self.current_scope.lookup("QUBIT").name
                )
                self.declare_symbol(qubit_symbol)
                defcal_symbol.qubits.append(qubit_symbol)

            for statement in node.body:
                self.visit(statement)

    def visit_QuantumGate(self, node: ast.QuantumGate) -> None:
        """
        QuantumGate node visitor, (gate call):
            Gets the mangled name best matching the gate call.
            Looks up the mangled name of the gate within the calibration scope.
            Raises an ID_NOT_FOUND error if the gate hasn't been declared.

        Args:
            node (ast.QuantumGate):
                openQASM qauntum gate node to visit

        Raises:
            SemanticError with ErrorCode.ID_NOT_FOUND
        """
        f_signature = Mangler(node).signature()
        symbols = f_signature.match(self.current_scope.keys())
        if not symbols:
            symbols = f_signature.match(self.calibration_scope.keys())
        if symbols:
            # per https://github.com/openqasm/openqasm/issues/245
            return symbols[-1]
        raise self.error(ErrorCode.ID_NOT_FOUND, node.name)

    def visit_ClassicalArgument(self, node: ast.ClassicalArgument) -> ClassicalSymbol:
        """
        ClassicalArgument node visitor:
            Creates and inserts a ClassicalSymbol for function arguments (def, defcal)
            into current scope

        Args:
            node (ast.ClassicalArgument):
                openQASM classical argument node to visit

        Returns:
            ClassicalSymbol: the symbol inserted in to current scope
        """
        arg_symbol = ClassicalSymbol(name=node.name.name, kind=self.visit(node.type))
        self.declare_symbol(arg_symbol)
        return arg_symbol

    def visit_QuantumArgument(self, node: ast.QuantumArgument) -> QuantumSymbol:
        """
        QuantumArgument node visitor:
            Creates and inserts a QuantumSymbol for function arguments (def, defcal)
            into current scope

        Args:
            node (ast.QuantumArgument):
                openQASM quantum argument node to visit

        Returns:
            QuantumSymbol: the symbol inserted in to current scope
        """
        arg_symbol = QuantumSymbol(name=node.name.name, kind="QUBIT")
        self.declare_symbol(arg_symbol)
        return arg_symbol

    def visit_ForInLoop(self, node: ast.ForInLoop) -> None:
        """
        ForInLoop node visitor:
            Visits the set declaration (what will be looped over)
            Enters a new scope.
            Inserts a symbol representing the loop variable into the new scope
            Visits every statement in the block of the ForInLoop

        Args:
            node (ast.ForInLoop):
                openQASM for in loop node to visit
        """
        type_symbol = self.visit(node.type)
        loop_symbol = ClassicalSymbol(name=node.identifier.name, kind=type_symbol)
        self.visit(node.set_declaration)
        with self.local_context_manager("for_loop_scope", node.block):
            self.current_scope.insert(loop_symbol)

    def visit_BranchingStatement(self, node: ast.BranchingStatement) -> None:
        """
        BranchingStatement node visitor (if/else):
            visits the condition node of the if/else statement
            Enters a new scope for the if block and visits every statment within it.
            Leaves the if block scope
            Enters a new scope for the else block and visits every statment within it.

        Args:
            node (ast.BranchingStatement):
                openQASM branching (if/else) node to visit
        """
        self.visit(node.condition)
        with self.local_context_manager("if_scope", node.if_block):
            pass
        with self.local_context_manager("else_scope", node.else_block):
            pass

    def visit_WhileLoop(self, node: ast.WhileLoop) -> None:
        """
        WhileLoop node visitor:
            visits the condition node of the while statement
            Enters a new scope for the while block and visits every statment within it.

        Args:
            node (ast.WhileLoop):
                openQASM while node to visit
        """
        self.visit(node.while_condition)
        with self.local_context_manager("while_scope", node.block):
            pass

    def visit_Box(self, node: ast.Box) -> None:
        """
        Box node visitor:
            visits the duration node of the Box statement
            Enters a new scope for the Box block and visits every statment within it.

        Args:
            node (ast.Box):
                openQASM Box node to visit
        """
        if node.duration:
            self.visit(node.duration)
        with self.local_context_manager("box_scope", node.body):
            pass

    def visit_UnaryExpression(self, node: ast.UnaryExpression):
        """
        UnaryExpression node visitor:
            validates the operator of the unary expression node
            visits the expression of the unary expression node

        Args:
            node (ast.UnaryExpression):
                openQASM unary expression node to visit
        """
        # todo check if unary op is allowed for expression
        assert isinstance(node.op, type(ast.UnaryOperator["!"]))
        self.visit(node.expression)

    def visit_BinaryExpression(self, node: ast.BinaryExpression):
        """
        BinaryExpression node visitor:
            validates the operator of the binary expression node
            visits each side of the binary expression

        Args:
            node (ast.BinaryExpression):
                openQASM binary expression node to visit
        """
        # todo check if binary op is allowed between lhs and rhs
        assert isinstance(node.op, type(ast.BinaryOperator["+"]))
        self.visit(node.lhs)
        self.visit(node.rhs)

    def visit_FunctionCall(self, node: ast.FunctionCall):
        """
        FunctionCall node visitor:
            visits the name (Identifier) node of the function call
            visits all the argument nodes of the function call

        Args:
            node (ast.FunctionCall):
                openQASM function call node to visit
        """
        self.visit(node.name)
        for argument in node.arguments:
            self.visit(argument)

    def visit_Cast(self, node: ast.Cast):
        """
        Cast node visitor:
            validates that the type being cast to is a classical type
            # todo should be more narrow, e.g. durration can't be cast to
            visits the argument node of the cast node

        Args:
            node (ast.Cast):
                openQASM cast node to visit
        """
        assert isinstance(node.type, ast.ClassicalType)
        self.visit(node.argument)

    def visit_IndexExpression(self, node: ast.IndexExpression):
        """
        IndexExpression node visitor:
            visits collection node of an index expression node
            visits index node of an index expression node

        Args:
            node (ast.IndexExpression):
                openQASM index expression node to visit
        """
        self.visit(node.collection)
        if isinstance(node.index, list):
            for i_node in node.index:
                self.visit(i_node)
        else:
            self.visit(node.index)

    def visit_DiscreteSet(self, node: ast.DiscreteSet):
        """
        DiscreteSet node visitor:
            visits each node of a DiscreteSet

        Args:
            node (ast.DiscreteSet):
                openQASM discreate set node to visit
        """
        for expression in node.values:
            self.visit(expression)

    def visit_RangeDefinition(self, node: ast.RangeDefinition):
        """
        RangeDefinition node visitor:
            visits start, end and step nodes of a RangeDefinition

        Args:
            node (ast.RangeDefinition):
                openQASM range definition node to visit
        """
        if node.start:
            self.visit(node.start)
        if node.end:
            self.visit(node.end)
        if node.step:
            self.visit(node.step)

    def visit_Concatenation(self, node: ast.Concatenation):
        """
        Concatenation node visitor:
            visits each side of the concatenation expression

        Args:
            node (ast.Concatenation):
                openQASM concatenation node to visit
        """
        self.visit(node.lhs)
        self.visit(node.rhs)

    def visit_BitstringLiteral(self, node: ast.BitstringLiteral) -> LiteralSymbol:
        """
        BitstringLiteral node visitor:

        Args:
            node (ast.BitstringLiteral):
                openQASM bitstring literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_BitstringLiteral(node)
        return LiteralSymbol(name=value, kind="BITSTRING")

    def visit_IntegerLiteral(self, node: ast.IntegerLiteral) -> LiteralSymbol:
        """
        IntegerLiteral node visitor:

        Args:
            node (ast.IntegerLiteral):
                openQASM integer literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_IntegerLiteral(node)
        return LiteralSymbol(name=value, kind="INT")

    def visit_FloatLiteral(self, node: ast.FloatLiteral) -> LiteralSymbol:
        """
        FloatLiteral node visitor:

        Args:
            node (ast.FloatLiteral):
                openQASM float literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_FloatLiteral(node)
        return LiteralSymbol(name=value, kind="FLOAT")

    def visit_ImaginaryLiteral(self, node: ast.ImaginaryLiteral) -> LiteralSymbol:
        """
        ImaginaryLiteral node visitor:

        Args:
            node (ast.ImaginaryLiteral):
                openQASM imaginary literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_ImaginaryLiteral(node)
        return LiteralSymbol(name=value, kind="IMAGINARY")

    def visit_BooleanLiteral(self, node: ast.BooleanLiteral) -> LiteralSymbol:
        """
        BooleanLiteral node visitor:

        Args:
            node (ast.BooleanLiteral):
                openQASM boolean literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_BooleanLiteral(node)
        return LiteralSymbol(name=value, kind="BOOL")

    def visit_DurationLiteral(self, node: ast.DurationLiteral) -> LiteralSymbol:
        """
        DurationLiteral node visitor:

        Args:
            node (ast.DurationLiteral):
                openQASM duration literal node to visit

        Returns:
            LiteralSymbol: symbol representation of the node value
        """
        value = super().visit_DurationLiteral(node)
        return LiteralSymbol(name=value, kind="DURATION")

    # pylint: disable=C0103
    # (snake_case naming style)

    def _visit_type_node(self, node: ast.ClassicalType) -> str:
        """
        type node visitor:
            Returns the name of a Type node
            Example:
                node:ast.FloatType -> 'FLOAT'

        Args:
            node (ast.ClassicalType): node that is a subclass of ClassicalType

        Returns:
            str: name of the node type
        """
        name = super()._visit_type_node(node)
        name_in_table = self.current_scope.lookup(name).name
        return name_in_table

    def error(self, error_code: ErrorCode, name: str) -> SemanticError:
        """
        Method for standardizing error handling of the SemanticAnalyser class.
        Logs current scope and returns a SemanticError object that should be raised
        immediately after this method retuns

        Usage:
            raise self.error(...)

        Args:
            error_code (ErrorCode):
                Code to identify what issue caused an error to be raised
            name (str):
                An identifer string to identify what caused the error

        Returns:
            SemanticError: should be raised immediatly on method return
        """
        LOGGER.debug("CURRENT SCOPE: %s", self.current_scope)
        LOGGER.debug("CALIBRATION SCOPE: %s", self._calibration_scope)
        return SemanticError(error_code, message=f"{error_code.value} -> {name}")

    def declare_symbol(self, symbol: Symbol):
        """Method for standardizing symbol declaration.
        Symbols are first looked up (in current scope only)
        before being inserted into current scope (if not already in scope)

        Args:
            symbol (Symbol): to insert into current scope

        Raises:
            SemanticError: ErrorCode.DUBLICATE_ID
        """
        if self.current_scope.lookup(symbol.name, current_scope_only=True):
            raise self.error(ErrorCode.DUPLICATE_ID, symbol.name)
        self.current_scope.insert(symbol)

    def ensure_in_global_scope(self, node: ast.Identifier):
        """
        Ensures that the current scope_context is global scope
        Used to make sure that declarations such as Subroutines and defcals
        Are only used in the allowed scope (GLOBAL)

        Args:
            node (ast.Identifier): Node that is currently being visited

        Raises:
            SemanticError: ErrorCode.NOT_IN_GLOBAL_SCOPE
        """
        if not self.scope_context == ScopeContext.GLOBAL:
            raise self.error(ErrorCode.NOT_IN_GLOBAL_SCOPE, node.name)

    @contextmanager
    def scope_context_manager(
        self,
        symbol_table: ScopedSymbolTable,
        context: ScopeContext,
    ):
        """
        Context manager for entering/leaving scopes in specific ScopeContext

        Args:
            symbol_table (ScopedSymbolTable): Symbol Table / Scope to enter
            context (ScopeContext): what context the scope is entered in
        """
        enclosing_scope = self.current_scope
        enclosing_context = self.scope_context
        self.current_scope = symbol_table
        self.scope_context = context
        try:
            yield
        finally:
            if enclosing_context:
                self.scope_context = enclosing_context
            if enclosing_scope:
                self.current_scope = enclosing_scope
            LOGGER.debug(symbol_table)
            LOGGER.debug("LEAVE scope: %s", symbol_table.scope_name)

    @contextmanager
    def local_context_manager(self, name: str, block: list[ast.Statement]):
        """
        Context manager for entering/leaving local scopes (if/else, for, while, box)
        What ScopeContext is entered depends on the current ScopeContext.
            If in GLOBAL then enter LOCAL
            Else (LOCAL, SUBROUTINE, DEFCAL) then keep context unchanged.
        Once in the new scope nodes in the block of the scope will be visited in order

        Args:
            name (str):
                Name of the ScopedSymbolTable to enter
            block (list[ast.Statement]):
                list of openQASM statments nodes, visited in order
        """
        scope = ScopedSymbolTable(name, enclosing_scope=self.current_scope)
        context = (
            ScopeContext.LOCAL
            if self.scope_context == ScopeContext.GLOBAL
            else self.scope_context
        )

        with self.scope_context_manager(scope, context):
            yield
            for statement in block:
                self.visit(statement)


# pylint: enable=R0904
