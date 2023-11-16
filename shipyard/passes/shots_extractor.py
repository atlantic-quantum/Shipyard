"""
Module for extracting number of shots and steps from qasm program
"""
from openpulse import ast
from pydantic import BaseModel, Field

from ..visitors import GenericVisitor as QASMVisitor


class ShotsSignature(BaseModel):
    """
    Pydantic Model for signature of number of shots and steps in a qasm program
    """

    steps: list[int] = Field(default_factory=list)
    shots: int = 0


class ShotsExtractor(QASMVisitor):
    """
    QASMVisitor that visits ConstantDeclaration or ClassicalDeclaration nodes to gather
    the information required to create signatures for number of shots and steps in a
    qasm program
    """

    def __init__(self) -> None:
        self.steps = [1]
        self.shots = 1

    def visit_Program(self, node: ast.Program):
        """
        Program (defcal) node transformer:
            Enters GLOBAL context and visits the program node
            Exits GLOBAL context before returning the node

        Args:
            node (ast.Program): openQASM program to process

        Returns:
            ast.Program: same node
        """
        self.generic_visit(node)
        return node

    def visit_ConstantDeclaration(
        self, node: ast.ConstantDeclaration
    ) -> ast.ConstantDeclaration:
        """
        ConstantDeclaration node visitor
        Extracts number of shots and potentially steps (when written as a const int in
        qasm) from node

        Example:
            qasm:
                const int n_shots = 100;
                const int n_steps = 5;

            ->

            ShotsExtractor:
                self.shots = 100
                self.steps = [5]

        Args:
            node (ast.ConstantDeclaration):
                openQASM defcal statement to visit
        """
        if node.identifier.name == "n_shots":
            self.shots = node.init_expression.value

        if node.identifier.name == "n_steps":
            self.steps = [node.init_expression.value]
        return node

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration
    ) -> ast.ClassicalDeclaration:
        """
        Classical node visitor
        Extracts number of steps (when written as array in qasm) from node
        Raises TypeError if n_steps is not of ArrayType

        Example:
            qasm:
                rray[int, 4] n_steps = {5, 6, 7, 8};

            ->

            ShotsExtractor:
                self.steps = [5, 6, 7, 8]

        Args:
            node (ast.ClassicalDeclaration):
                openQASM defcal statement to visit
        """

        if node.identifier.name == "n_steps":
            if not isinstance(node.type, ast.ArrayType):
                raise TypeError("n_steps must be of ArrayType")
            self.steps = [val.value for val in node.init_expression.values]
        return node

    def create_signature(self):
        """Creates signature for number of steps and shots in qasm program

        Returns:
            ShotsSignature:
                with steps and shots
        """
        return ShotsSignature(steps=self.steps, shots=self.shots)
