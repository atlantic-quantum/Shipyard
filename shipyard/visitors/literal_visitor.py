"""
Module for shared visitor methods
"""

from openpulse import ast

# pylint: disable=C0103


class LiteralVisitor:
    """Class defining methods for visiting openQASM literal-nodes"""

    def visit_BitstringLiteral(self, node: ast.BitstringLiteral) -> str:
        """
        BitstringLiteral node visitor:

        Args:
            node (ast.BitstringLiteral):
                openQASM bitstring literal node to visit

        Returns:
            str: string representation of the node value
        """
        value = bin(node.value)[2:]
        if len(value) < node.width:
            value = "0" * (node.width - len(value)) + value
        return f'"{value}"'

    def visit_IntegerLiteral(self, node: ast.IntegerLiteral) -> str:
        """
        IntegerLiteral node visitor:

        Args:
            node (ast.IntegerLiteral):
                openQASM integer literal node to visit

        Returns:
            str: string representation of the node value
        """
        return str(node.value)

    def visit_FloatLiteral(self, node: ast.IntegerLiteral) -> str:
        """
        FloatLiteral node visitor:

        Args:
            node (ast.FloatLiteral):
                openQASM float literal node to visit

        Returns:
            str: string representation of the node value
        """
        return str(node.value)

    def visit_ImaginaryLiteral(self, node: ast.ImaginaryLiteral) -> str:
        """
        ImaginaryLiteral node visitor:

        Args:
            node (ast.ImaginaryLiteral):
                openQASM imaginary literal node to visit

        Returns:
            str: string representation of the node value
        """
        return str(node.value) + "im"

    def visit_BooleanLiteral(self, node: ast.BooleanLiteral) -> str:
        """
        BooleanLiteral node visitor:

        Args:
            node (ast.BooleanLiteral):
                openQASM boolean literal node to visit

        Returns:
            str: string representation of the node value
        """
        return "true" if node.value else "false"

    def visit_DurationLiteral(self, node: ast.DurationLiteral) -> str:
        """
        DurationLiteral node visitor:

        Args:
            node (ast.DurationLiteral):
                openQASM duration literal node to visit

        Returns:
            str: string representation of the node value
        """
        return f"{node.value}{node.unit.name}"

    # def visit_ArrayLiteral(self, node: ast.ArrayLiteral) -> None:
    #     self._visit_sequence(node.values, context, start="{", end="}", separator=", ")


# pylint: enable=C0103
