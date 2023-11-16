"""Traversing AST and creating a stack to modify nodes as needed"""


from openpulse import ast

from ..visitors import GenericTransformer


class StackAnalyzer(GenericTransformer):
    """
    Analyzes the stack of for loop statements to determine if a the for loop should be
    written to seqc using a constant variable or a regular variable.

    This is done by observing if the loop variable is used in a function call, if it is
    then the loop variable must be a constant variable.

    Some functions are handled specially by the seqcprinter such as the 'ones' function
    call to those functions are skipped.

    Args:
        skip_calls (list[str] | None):
            list of function names to skip, defaults to None these are handled specially
            by the seqcprinter.

    """

    def __init__(self, skip_calls: list[str] | None = None) -> None:
        self.name = None
        self.firstcallflag = True
        self.constant_for_loops = False
        self.skip_calls = skip_calls or []

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
        return node

    def visit_ConstantDeclaration(self, node: ast.ConstantDeclaration) -> None:
        """
        ConstantDeclaration node visitor
            inserts a symbol representing the constant into current_scope

        Args:
            node (ast.ConstantDeclaration):
                openQASM constant declaration ast node to visit
        """
        return node

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
        if node.name == self.name:
            self.constant_for_loops = True
        return node

    def visit_FunctionCall(self, node: ast.FunctionCall):
        """
        FunctionCall node visitor:
            visits the name (Identifier) node of the function call
            visits all the argument nodes of the function call

        Args:
            node (ast.FunctionCall):
                openQASM function call node to visit
        """
        if node.name.name not in self.skip_calls:
            for argument in node.arguments:
                self.visit(argument)
        return node

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
        if self.firstcallflag is True:
            self.name = node.identifier.name
        self.firstcallflag = False
        for statement in node.block:
            self.visit(statement)
