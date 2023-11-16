"""
QASM Transformer that transforms IODeclarations into ConstanDeclarations.
"""

from openpulse import ast

from ..compiler_error import ErrorCode, SemanticError, SetupError
from ..visitors import GenericTransformer


class ResolveIODeclaration(GenericTransformer):
    def __init__(self, inputs: dict = None):
        self.inputs = inputs or {}  # e.g. inputs = {"basis": 1}

    def visit_IODeclaration(self, node: ast.IODeclaration) -> ast.ConstantDeclaration:
        """
        IODeclaration node Transformer. Transforms IODeclaration nodes to
        ConstantDeclarations. Searches through ResolveIODeclaration.inputs
        for info to populate the ConstantDeclaration.

        Args:
            node (ast.IODeclaration):
                IODeclaration node to transform.

        Returns:
            ast.ConstantDeclaration:
                Tranformed ConstantDeclaration node with relevant data (identifier and
                init_expression)
        """
        if node.io_identifier == ast.IOKeyword.input:
            if node.identifier.name not in self.inputs:
                raise SetupError(
                    ErrorCode.ID_NOT_FOUND,
                    message=f"Input: {node.identifier.name} not found in input"
                    " dictionary",
                )
            match node.type:
                case ast.IntType():
                    return ast.ConstantDeclaration(
                        type=node.type,
                        identifier=node.identifier,
                        init_expression=ast.IntegerLiteral(
                            value=self.inputs[node.identifier.name]
                        ),
                    )
                case ast.DurationType():
                    return ast.ConstantDeclaration(
                        type=node.type,
                        identifier=node.identifier,
                        init_expression=ast.DurationLiteral(
                            value=(self.inputs[node.identifier.name] * 1e9),
                            unit=ast.TimeUnit.ns,
                        ),
                    )
                # todo: AQC-311 add support for complex input type
                # case ast.ComplexType():
                #     return ast.ConstantDeclaration(
                #         type=node.type,
                #         identifier=node.identifier,
                #         init_expression=ast.BinaryExpression(
                #           op= ast.BinaryOperator['+'],
                #           lhs=ast.FloatLiteral(
                #               value= self.inputs[node.identifier.name].real),
                #           rhs=ast.ImaginaryLiteral(
                #               value= self.inputs[node.identifier.name].imag))
                #     )
                case ast.FloatType():
                    return ast.ConstantDeclaration(
                        type=node.type,
                        identifier=node.identifier,
                        init_expression=ast.FloatLiteral(
                            value=self.inputs[node.identifier.name]
                        ),
                    )
                case ast.BoolType():
                    return ast.ConstantDeclaration(
                        type=node.type,
                        identifier=node.identifier,
                        init_expression=ast.BooleanLiteral(
                            value=self.inputs[node.identifier.name]
                        ),
                    )
                case ast.BitType():
                    if isinstance(self.inputs[node.identifier.name], list):
                        return ast.ConstantDeclaration(
                            type=node.type,
                            identifier=node.identifier,
                            init_expression=ast.ArrayLiteral(
                                values=[
                                    ast.IntegerLiteral(value=s)
                                    for s in self.inputs[node.identifier.name]
                                ]
                            ),
                        )
                    elif isinstance(self.inputs[node.identifier.name], int):
                        return ast.ConstantDeclaration(
                            type=node.type,
                            identifier=node.identifier,
                            init_expression=ast.IntegerLiteral(
                                value=self.inputs[node.identifier.name]
                            ),
                        )
                    else:
                        raise SemanticError(
                            ErrorCode.INPUT_TYPE_NOT_SUPPORTED,
                            message=f"Input type not supported: {node.type}",
                        )
                case ast.UintType():
                    return ast.ConstantDeclaration(
                        type=node.type,
                        identifier=node.identifier,
                        init_expression=ast.IntegerLiteral(
                            value=self.inputs[node.identifier.name]
                        ),
                    )
                case _:
                    raise SemanticError(
                        ErrorCode.INPUT_TYPE_NOT_SUPPORTED,
                        message=f"Input type not supported: {node.type}",
                    )
                # case ast.ArrayType():
                #     return ast.ConstantDeclaration(
                #         type=node.type,
                #         identifier=node.identifier,
                #         init_expression=ast.ArrayLiteral(
                #         values = [ast.IntegerLiteral(value=s)
                #         for s in self.inputs[node.identifier.name]]),
                #     )

                # todo: AQC-312 add support for angle input type
                # case ast.AngleType():
                #     # return ast.ConstantDeclaration(
                #     #     type=node.type,
                #     #     identifier=node.identifier,
                #     #     init_expression=ast.FloatLiteral(
                #     #       value = self.inputs[node.identifier.name]),
                #     # )
                # todo: AQC-310 add support for stretch input type
                # case ast.StretchType():
        else:
            raise SemanticError(
                ErrorCode.OUTPUT_NOT_SUPPORTED,
                message=f"Output type not supported: {node}",
            )
