"""
Specific core level functionality for QA cores (e.g. SHFQA)
"""
from .awg_core import AWGCore, Printer, PrinterState, WFMDatatype, ast


class QACore(AWGCore):
    """
    QA Core (e.g. SHFQA) pydantic data model. QA cores have a two channels (in/out) and
    complex waveforms.

    This class should not be instanciated directly by the user.

    Args:
        n_channels (int):
            number of channels supported by the AWG Core. Default value 2
        datatype (WFMDatatype):
            Waveform datatype supported by the AWG Core. Default value COMPLEX
    """

    n_channels: int = 2
    datatype: WFMDatatype = WFMDatatype.COMPLEX

    @staticmethod
    def play(wfm_node: ast.FunctionCall, printer: Printer, context: PrinterState):
        raise ValueError("QA cores do not support play statments directly")

    @staticmethod
    def capture_v3(
        capture_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        match capture_node:
            case ast.FunctionCall(
                name=ast.Identifier("capture_v3" | "capture_v1_spectrum"),
                arguments=[_, duration_node],
            ):
                printer._start_line(context)
                printer.stream.write("playZero(")
                printer.visit(duration_node)
                printer.stream.write(")")
                printer._end_statement(context)
                printer._start_line(context)
                printer.stream.write("setTrigger(1)")
                printer._end_statement(context)
                printer._start_line(context)
                printer.stream.write("setTrigger(0)")
                printer._end_statement(context)

    @staticmethod
    def shift_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("QA cores do not support shifting phase of oscillators")

    @staticmethod
    def set_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("QA cores do not support setting phase of oscillators")

    @staticmethod
    def set_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit set_frequency openQASM FunctionCall AST Node, i.e.:
            set_frequency(frame, frequency_value)

        The QA Core specifically translates to SEQC code.

        Example:
            qasm:
                set_frequency(frame, 1.1);

            seqc:
                setOscFreq(0, 1.1);

        Args:
            phase_node (ast.FunctionCall):
                the set_frequency function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)

        Raises:
            NotImplementedError: if structure of set_frequency is not as expected
        """
        match frequency_node:
            case ast.FunctionCall(
                name=ast.Identifier("set_frequency"), arguments=[_, frequency_value]
            ):
                printer._start_line(context)
                printer.stream.write("setOscFreq(0, ")
                # todo make sure 0 is correct core on all channels
                printer.visit(frequency_value)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                raise NotImplementedError

    @staticmethod
    def shift_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("QA cores do not support shifting frequency of oscillators")
