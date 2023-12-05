from openpulse import ast
from openpulse.printer import dumps as qasm_dumps
from zhinst.toolkit import CommandTable

from ..logger import LOGGER
from ..utilities import LazyRepr
from ..visitors import GenericTransformer as QASMTransformer


class InsertCTWaveforms(QASMTransformer):
    """
    QASMTransformer to add in assignWaveIndex(placeholder(length), index) statements
    for each waveform in the command table

    Args:
            CommandTable:
                ZI CommandTable object

    Returns:
        list[ast.Statement]:
            A list of QASM statements

    """

    def __init__(self, commandtable: CommandTable | None) -> None:
        self.ct = commandtable or {}

    @staticmethod
    def add_assignWaveIndex(
        waveform_set: set[tuple[int, int]]
    ) -> ast.CalibrationStatement:
        """
        Create list of openQASM statements to of
        assignWaveIndex(placeholder(length), index) for each waveform in the
        waveform_set

        Args:
            waveform_set (set(tuple[int, int])):
                A set of tuples of waveform index and length
        Returns:
            list[ast.Statement]:
                A list of QASM statements
        """
        awi_statments = [
            ast.FunctionCall(
                name=ast.Identifier("assignWaveIndex"),
                arguments=[
                    ast.FunctionCall(
                        name=ast.Identifier("placeholder"),
                        arguments=[ast.IntegerLiteral(length)],
                    ),
                    ast.IntegerLiteral(index),
                ],
            )
            for (index, length) in waveform_set
        ]
        return ast.CalibrationStatement(
            body=[ast.ExpressionStatement(awi) for awi in awi_statments]
        )

    # pylint: disable=C0103
    # snake_case naming

    def visit_Program(self, node: ast.Program):
        """
        Program node transformer:
            inserts assignWaveformIndex and placeholder statememnets at the beginning
            of the program

        Args:
            node (ast.Program): openQASM program to process

        Returns:
            ast.Program: same node with waveform declarations inserted
        """
        if self.ct:
            i = 0
            waveform_set = set()
            while (
                self.ct.table[i].waveform.index is not None
                and self.ct.table[i].waveform.length is not None
            ):
                # iterating over the command table items ran indices that were out of
                # the bounds of the json schema, could not use for loop/ list
                # comprehension
                waveform_set.add(
                    (self.ct.table[i].waveform.index, self.ct.table[i].waveform.length)
                )
                i += 1
            node.statements.insert(1, self.add_assignWaveIndex(waveform_set))
        LOGGER.debug("\n%s", LazyRepr(qasm_dumps, [node]))
        return node
