from numpy import ndarray
from openpulse import ast
from openpulse.printer import dumps as qasm_dumps

from ..logger import LOGGER
from ..utilities import LazyRepr
from ..visitors import GenericTransformer as QASMTransformer


class IncludeWaveforms(QASMTransformer):
    """
    QASMTransformer loads in files that are included in the qasm program

    """

    def __init__(self, waveforms: dict[str, ndarray] | None) -> None:
        self.waveforms = waveforms or {}

    @staticmethod
    def qasm_for_placeholders(
        waveforms: dict[str, ndarray]
    ) -> ast.CalibrationStatement:
        """
        Convert a dictionary of waveforms into a list of QASM statements

        Args:
            dict[str, np.ndarray]:
                A dictionary of waveforms

        Returns:
            list[ast.Statement]:
                A list of QASM statements
        """
        waveform_statements = [
            ast.ClassicalDeclaration(
                type=ast.WaveformType(),
                identifier=ast.Identifier(name),
                init_expression=ast.FunctionCall(
                    name=ast.Identifier("placeholder"),
                    arguments=[
                        ast.DurationLiteral(
                            value=waveform.size, unit=ast.TimeUnit["dt"]
                        )
                    ],
                ),
            )
            for name, waveform in waveforms.items()
        ]
        return ast.CalibrationStatement(body=waveform_statements)

    # pylint: disable=C0103
    # snake_case naming

    def visit_Program(self, node: ast.Program):
        """
        Program node transformer:
            inserts waveform declarations placeholders at the beginning of the program
            The waveforms are populated during upload of compiled program to AWGs

        Args:
            node (ast.Program): openQASM program to process

        Returns:
            ast.Program: same node with waveform declarations inserted
        """
        if self.waveforms:
            node.statements.insert(1, self.qasm_for_placeholders(self.waveforms))
        LOGGER.debug(
            "Program after inserting waveforms:\n%s", LazyRepr(qasm_dumps, [node])
        )
        return node
