"""
Specific core level functionality for HD cores (e.g. HDAWG)
"""
from ..utilities import BinOps, UnOps
from .awg_core import AWGCore, Printer, PrinterState, WFMDatatype, ast


class HDCore(AWGCore):
    """
    HD Core (i.g. HDAWG) pydantic data model. HD cores have a two channels and
    real waveforms.

    This class should not be instanciated directly by the user.

    Args:
        n_channels (int):
            number of channels supported by the AWG Core. Default value 2
        datatype (WFMDatatype):
            Waveform datatype supported by the AWG Core. Default value REAL
    """

    n_channels: int = 2
    datatype: WFMDatatype = WFMDatatype.REAL

    @staticmethod
    def play(
        wfm_node: ast.Expression,
        printer: Printer,
        context: PrinterState,
        channel: int = 1,
    ):
        """
        Visit waveform node of openQASM FunctionCall AST Nodes that call the 'play'
        function, i.e.:
            play(frame, wfm_node)
                        ^^^^^^^^

        The HD Core specifically translates to SEQC code.

        Example 1: (Baseband waveform)
            qasm:
                play(frame, wave_real)

            seqc:
                playWave(1, wave_real) # if channel == 1
                playWave(2, wave_real) # if channel == 2 etc.

                # todo baseband waveforms on the 2nd channel.

        Example 2 (SSB IQ waveform) w/ ext. mixer:
            qasm:
                play(frame, wave_real + ii * wave_imag)
                play(frame, wave_real + wave_imag * ii)

            seqc:
                playWave(1, 2, wave_real, 1, 2, wave_imag)
                playWave(1, 2, wave_real, 1, 2, wave_imag)

        Example 3 (SSB Q waveform (just quadrature component)) w/ ext. mixer:
            qasm:
                play(frame, ii * wave_imag)
                play(frame, wave_imag * ii)

            seqc:
                playWave(1, 2, 0 * wave_imag, 1, 2, wave_imag)
                playWave(1, 2, 0 * wave_imag, 1, 2, wave_imag)

        Args:
            wfm_node (ast.Expression):
                the waveform node of the play function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
            channel (int):
                the hd core channel to play the waveform on. Default value 1
                Can be 1 or 2
        """
        match wfm_node:
            case ast.BinaryExpression(
                op=BinOps.PLUS,
                lhs=lhs,
                rhs=ast.BinaryExpression(op=BinOps.ASTERIX, lhs=UnOps.IMAG, rhs=rhs)
                | ast.BinaryExpression(op=BinOps.ASTERIX, lhs=rhs, rhs=UnOps.IMAG),
            ):
                printer._start_line(context)
                printer.stream.write("playWave(1, 2, ")
                printer.visit(lhs)
                printer.stream.write(", 1, 2, ")
                printer.visit(rhs)
                printer.stream.write(")")
                printer._end_statement(context)
            case ast.BinaryExpression(
                op=BinOps.ASTERIX, lhs=UnOps.IMAG, rhs=waveform
            ) | ast.BinaryExpression(op=BinOps.ASTERIX, rhs=UnOps.IMAG, lhs=waveform):
                printer._start_line(context)
                printer.stream.write("playWave(1, 2, 0 * ")
                printer.visit(waveform)
                printer.stream.write(", 1, 2, ")
                printer.visit(waveform)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                if channel == 1:
                    printer._start_line(context)
                    printer.stream.write("playWave(1, ")
                    printer.visit(wfm_node)
                    printer.stream.write(")")
                    printer._end_statement(context)
                elif channel == 2:
                    printer._start_line(context)
                    printer.stream.write('playWave(1, "", 2, ')
                    printer.visit(wfm_node)
                    printer.stream.write(")")
                    printer._end_statement(context)

    @staticmethod
    def play_channels(
        wfm_nodes: list[ast.Expression],
        printer: Printer,
        context: PrinterState,
    ):
        """
        print playWave statement that plays waveforms on multiple channels
        simultaneously

        Args:
            wfm_nodes (list[ast.Expression]):
                list of waveform nodes to play on each channel
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        printer._visit_sequence(
            wfm_nodes, context, start="playWave(", end=")", separator=", "
        )

    # pylint: disable=W0212
    # access private functions

    @staticmethod
    def capture_v3(
        capture_node: ast.Expression, printer: Printer, context: PrinterState
    ):
        raise ValueError("HD cores do not support capture")

    @staticmethod
    def shift_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit shift_phase openQASM FunctionCall AST Node, i.e.:
            shift_phase(frame, phase_value)

        The HD Core specifically translates to SEQC code.

        Example:
            qasm:
                shift_phase(frame, 1.1);

            seqc:
                incrementSinePhase(0, 1.1);
                incrementSinePhase(1, 1.1);

        Args:
            phase_node (ast.FunctionCall):
                the shift_phase function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)

        Raises:
            NotImplementedError: if structure of phase_node is not as expected
        """
        match phase_node:
            case ast.FunctionCall(
                name=ast.Identifier("shift_phase"), arguments=[_, phase_value]
            ):
                printer._start_line(context)
                printer.stream.write("incrementSinePhase(0, ")
                printer.visit(phase_value)
                printer.stream.write(")")
                printer._end_statement(context)
                printer._start_line(context)
                printer.stream.write("incrementSinePhase(1, ")
                printer.visit(phase_value)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                raise NotImplementedError

    @staticmethod
    def set_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit set_phase openQASM FunctionCall AST Node, i.e.:
            set_phase(frame, phase_value)

        The HD Core specifically translates to SEQC code.

        Example:
            qasm:
                set_phase(frame, 1.1);

            seqc:
                setSinePhase(0, 1.1);
                setSinePhase(1, 1.1);

        Args:
            phase_node (ast.FunctionCall):
                the set_phase function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)

        Raises:
            NotImplementedError: if structure of phase_node is not as expected
        """
        match phase_node:
            case ast.FunctionCall(
                name=ast.Identifier("set_phase"), arguments=[_, phase_value]
            ):
                printer._start_line(context)
                printer.stream.write("setSinePhase(0, ")
                printer.visit(phase_value)
                printer.stream.write(")")
                printer._end_statement(context)
                printer._start_line(context)
                printer.stream.write("setSinePhase(1, ")
                printer.visit(phase_value)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                raise NotImplementedError

    # pylint: enable=W0212

    @staticmethod
    def set_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("HD cores do not support setting frequency of oscillators")

    @staticmethod
    def shift_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("HD cores do not support shifting frequency of oscillators")
