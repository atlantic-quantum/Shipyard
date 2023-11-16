"""
Abstract base class for AWG Core level functionality
"""
from abc import ABC, abstractmethod
from enum import Enum

from openpulse import ast
from openpulse.printer import Printer, PrinterState
from pydantic import BaseModel


class WFMDatatype(Enum):
    """Enumeration of waveform datatype"""

    COMPLEX = "complex"
    REAL = "real"


class CoreType(Enum):
    """Enumeration of AWG Core types"""

    HD = "HD"
    QA = "QA"
    SG = "SG"


class AWGCore(BaseModel, ABC):
    """Pydantic model for AWG core types.

    These class should not be instanciated directly by the user.

    Args:
        n_channels (int): number of channels supported by the AWG Core
        datatype (WFMDatatype): Waveform datatype supported by the AWG Core
    """

    n_channels: int
    datatype: WFMDatatype

    @staticmethod
    @abstractmethod
    def play(wfm_node: ast.Expression, printer: Printer, context: PrinterState):
        """
        Visit waveform node of openQASM FunctionCall AST Nodes that call the 'play'
        function, i.e.:
            play(frame, wfm_node)
                        ^^^^^^^^

        Each CoreType has different handling of how play statements are handled
        by the Printer.

        Args:
            wfm_node (ast.Expression):
                the waveform node of the play function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def capture_v3(
        capture_node: ast.Expression, printer: Printer, context: PrinterState
    ):
        """
        Visit capture_v3 openQASM FunctionCall AST Nodes i.e.:
            caputre_v3(frame, duration)

        Each CoreType has different handling of how capture_v3 statements are handled
        by the Printer.

        Args:
            capture_node (ast.Expression):
                the capture node of the play function call
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def set_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit set_phase openQASM FunctionCall AST Node, i.e.:
            set_phase(frame, phase_value)

        Each CoreType has different handling of how set_phase statements are handled
        by the Printer.

        Args:
            phase_node (ast.FunctionCall):
                set_phase function call to handle
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def shift_phase(
        phase_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit shift_phase openQASM FunctionCall AST Node, i.e.:
            shift_phase(frame, phase_value)

        Each CoreType has different handling of how set_phase statements are handled
        by the Printer.

        Args:
            phase_node (ast.FunctionCall):
                shift_phase function call to handle
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def set_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit set_frequency openQASM FunctionCall AST Node, i.e.:
            set_frequency(frame, frequency_value)

        Each CoreType has different handling of how set_frequency statements are handled
        by the Printer.

        Args:
            frequency_node (ast.FunctionCall):
                set_frequency function call to handle
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def shift_frequency(
        frequency_node: ast.FunctionCall, printer: Printer, context: PrinterState
    ):
        """
        Visit shift_frequency openQASM FunctionCall AST Node, i.e.:
            shift_frequency(frame, frequency_value)

        Each CoreType has different handling of how set_frequency statements are handled
        by the Printer.

        Args:
            frequency_node (ast.FunctionCall):
                frequency_phase function call to handle
            printer (Printer):
                a qasm AST Printer
            context (PrinterState):
                the printer state (i.e. indentation)
        """
        raise NotImplementedError
