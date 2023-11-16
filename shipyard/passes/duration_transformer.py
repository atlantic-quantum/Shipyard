"""
QASM Transformer that transforms DurationLiterals to have units of samples (dt).
"""
from enum import Enum

from openpulse import ast

from ..visitors import GenericTransformer


# pylint: disable=C0103
# UPPER_CASE naming style
class TimeUnitToValue(Enum):
    """
    Enumeration of time units to transform them to values.
    Used by DurationTransformer in conjunction with openpulse.ast.TimeUnit enumeration.
    """

    ns = 1e-9
    us = 1e-6
    ms = 1e-3
    s = 1


# pylint: enable=C0103


class DurationTransformer(GenericTransformer):
    """
    QASM Transformer that transforms DurationLiterals to have units of samples (dt).

    Args:
        sample_rate (int):
            the sample rate that DurationLiterals will be transformed to.
            Default value = 2e9
    """

    def __init__(self, sample_rate: int = 2e9) -> None:
        self.sample_rate = sample_rate
        super().__init__()

    # pylint: disable=C0103
    # snake_case naming style

    def visit_DurationLiteral(self, node: ast.DurationLiteral) -> ast.DurationLiteral:
        """
        DurationLiteral node Transformer. Transforms DurationLiteral nodes from any
        unit to a node with sample units (dt).

        Example:
            in: node = ast.DurationLiteral(value=20, unit=ast.TimeUnit.ns)

            usage: DurationTransformer().visit(node)

            out: ast.DurationLiteral(value=40, unit=ast.TimeUnit.dt)


        Args:
            node (ast.DurationLiteral):
                DurationLiteral node to transform.

        Returns:
            ast.DurationLiteral:
                Tranformed DurationLiteral node with unit set to samples (dt)
        """
        if node.unit.name != "dt":
            new_node = ast.DurationLiteral(
                value=int(
                    round(
                        node.value
                        * TimeUnitToValue[node.unit.name].value
                        * self.sample_rate
                    )
                ),
                unit=ast.TimeUnit.dt,
            )
            return new_node
        return node

    # pylint: enable=C0103
