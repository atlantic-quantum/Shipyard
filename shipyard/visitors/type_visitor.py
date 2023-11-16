# pylint: disable=C0103
# (snake_case naming style)

# todo take another pass at this with better documentation in mind


from openpulse import ast

# pylint: disable=C0103


class TypeVisitor:
    """Class defining methods for visiting openQASM type-nodes"""

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
        return str(node.__class__.__name__).upper().split("TYPE", maxsplit=1)[0]

    def _visit_type_node_wrapper(self, node: ast.ClassicalType):
        return self._visit_type_node(node)

    visit_IntType = _visit_type_node_wrapper
    visit_UintType = _visit_type_node_wrapper
    visit_FloatType = _visit_type_node_wrapper
    visit_ComplexType = _visit_type_node_wrapper  # todo expand to indicate base type
    visit_AngleType = _visit_type_node_wrapper
    visit_BitType = _visit_type_node_wrapper
    visit_BoolType = _visit_type_node_wrapper
    visit_ArrayType = (
        _visit_type_node_wrapper  # todo expand to indicate type+size of array
    )

    def visit_ArrayReferenceType(self, node: ast.ArrayReferenceType) -> None:
        """
        ToDo
        """
        raise NotImplementedError

    visit_DurationType = _visit_type_node_wrapper
    visit_StretchType = _visit_type_node_wrapper

    visit_PortType = _visit_type_node_wrapper
    visit_FrameType = _visit_type_node_wrapper
    visit_WaveformType = _visit_type_node_wrapper
