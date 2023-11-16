"""Module for consitent error handling/raising across the shipyard"""

from enum import Enum


class ErrorCode(Enum):
    """Class to enumerate error codes of the shipyard"""

    ID_NOT_FOUND = "Identifier not found"
    DUPLICATE_ID = "Duplicate id found"
    NOT_IN_GLOBAL_SCOPE = "Not in global scope"
    INVALID_DEFCAL_ARGUMENT = "Invalid defcal argument"
    EXPRESSION_IN_DEFCAL = "Expression in defcal signature, unhandled"
    INVALID_GATECALL_ARGUMENT = "Invalid gatecall argument"
    UNHANDLED = "Unhandled case"
    UNDETERMINED_CALL = "Unable to determine a unique function for function call"
    NO_SEQC_STATEMENT = "No equivalent SEQC statement"
    COMPILE_OUT = "Statement should be compiled out before printing SEQC code"
    PORT_NOT_FOUND = "Port was not found within setup"
    INSTRUMENT_NOT_FOUND = "Instrument was not found within setup"
    INPUT_NOT_FOUND = "Input value was not found"
    OUTPUT_NOT_SUPPORTED = "Output type not supported"
    INPUT_TYPE_NOT_SUPPORTED = "Input type not supported"
    INVALID_ARGUMENT = "Invalid argument"
    INVALID_WAVEFORM = "Waveform does not meet timing constraints"
    INCLUDE_ERROR = "Error in include statement"


class Error(Exception):
    """Base Error Class for shipyard"""

    def __init__(self, error_code=None, message=None):
        self.error_code = error_code
        # self.token = token
        # add exception class name before the message
        class_name = self.__class__.__name__.rsplit(".", maxsplit=1)[-1]
        self.message = f"{class_name}: ({self.error_code}) {message}"
        super().__init__(self.message)


class SemanticError(Error):
    """Error class for semantic errors, raised by SemanticAnalyser"""


class SEQCPrinterError(Error):
    """Error class for SEQC Printer errors, raised by SEQCPrinter"""


class TransformError(Error):
    """Error class for Transformation Errors, raised by QASMTransformer subclasses"""


class SetupError(Error):
    """Error class for errors relating to setup"""
