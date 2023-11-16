"""
Specific core level functionality for SG cores (e.g. SHFSG)
"""
from ..utilities import BinOps, UnOps
from .awg_core import AWGCore, Printer, PrinterState, WFMDatatype, ast


class SGCore(AWGCore):
    """
    SG Core (i.g. SHFSG) pydantic data model. SG cores have a single channel and
    real waveforms.

    This classes should not be instanciated directly by the user.

    Args:
        n_channels (int):
            number of channels supported by the AWG Core. Default value 1
        datatype (WFMDatatype):
            Waveform datatype supported by the AWG Core. Default value REAL
    """

    n_channels: int = 1
    datatype: WFMDatatype = WFMDatatype.REAL

    @staticmethod
    def play(wfm_node: ast.Expression, printer: Printer, context: PrinterState):
        """
        Visit waveform node of openQASM FunctionCall AST Nodes that call the 'play'
        function, i.e.:
            play(frame, wfm_node)
                        ^^^^^^^^

        The SG Core specifically translates to SEQC code.

        Example 1 (SSB IQ waveform):
            qasm:
                play(frame, wave_real + ii * wave_imag)
                play(frame, wave_real + wave_imag * ii)

            seqc:
                playWave(1, 2, wave_real, 1, 2, wave_imag)
                playWave(1, 2, wave_real, 1, 2, wave_imag)

        Example 2 (SSB Q waveform (just quadrature component)):
            qasm:
                play(frame, ii * wave_imag)
                play(frame, wave_imag * ii)

            seqc:
                playWave(1, 2, 0 * wave_imag, 1, 2, wave_imag)
                playWave(1, 2, 0 * wave_imag, 1, 2, wave_imag)

        Example 3: (SSB I waveform (just in-phase component))
            qasm:
                play(frame, wave_real)

            seqc:
                playWave(1, 2, wave_real)
                playWave(1, 2, wave_real)

        Args:
            wfm_node (ast.Expression):
                the waveform node of the play function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
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
                printer._start_line(context)
                printer.stream.write("playWave(1, 2, ")
                printer.visit(wfm_node)
                printer.stream.write(")")
                printer._end_statement(context)

    @staticmethod
    def capture_v3(
        capture_node: ast.Expression, printer: Printer, context: PrinterState
    ):
        raise ValueError("SG cores do not support capture")

    @staticmethod
    def shift_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit shift_phase openQASM FunctionCall AST Node, i.e.:
            shift_phase(frame, phase_value)

        The SG Core specifically translates to SEQC code.

        Example:
            qasm:
                shift_phase(frame, 1.1);

            seqc:
                incrementSinePhase(1.1);

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
                printer.stream.write("incrementSinePhase(")
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

        The SG Core specifically translates to SEQC code.

        Example:
            qasm:
                set_phase(frame, 1.1);

            seqc:
                setSinePhase(1.1);

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
                printer.stream.write("setSinePhase(")
                printer.visit(phase_value)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                raise NotImplementedError

    @staticmethod
    def set_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit set_frequency openQASM FunctionCall AST Node, i.e.:
            set_frequency(frame, frequency_value)

        The SG Core specifically translates to SEQC code.

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
                printer.stream.write("setOscFreq(0, ")  # todo which oscillator?
                """
                SG Cores have 8 digital oscillators.
                Could in theory run up to 8 qubits on a single channel,
                i.e. 8 different frames
                need to keep track of the number of frames used for the channel
                each gets assigned its own oscillator and then use the correct one?

                It  seems that using more than 1 oscillator at the same time requires
                using the command table formalisim.

                Pause on this until we support compiling to command table instead of
                waveforms.
                """
                printer.visit(frequency_value)
                printer.stream.write(")")
                printer._end_statement(context)
            case _:
                raise NotImplementedError

    @staticmethod
    def shift_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        raise ValueError("SG cores do not support shifting frequency of oscillators")
