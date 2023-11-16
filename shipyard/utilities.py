"""
Utility functions for shipyard
"""
from enum import Enum

import numpy as np
from openpulse import ast
from zhinst.toolkit import Waveforms


def is_number(string: str) -> bool:
    """
    Args:
        string (str): any string

    Returns:
        bool: True if this input string represents a number, else False
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


def qasm_from_array(
    arrays: np.ndarray | list[np.ndarray], names: str | list[str] = None
) -> str:
    """Convert a numpy array into a QASM string

    Args:
        arrays: A numpy array or list of numpy arrays
        names: A string or list of strings to use as the name of the waveform

    Returns:
        A QASM string representing the waveform
    """
    if isinstance(arrays, np.ndarray):
        arrays = [arrays]
    if names is None:
        names = [f"waveform_{i}" for i in range(len(arrays))]
    elif isinstance(names, str):
        names = [names]
    assert len(arrays) == len(names), "Must have the same number of arrays and names"
    assert all(np.squeeze(array).ndim == 1 for array in arrays), "Arrays must be 1D"
    qasm = "OPENQASM 3.0;\n"
    array_strs = []
    for array, name in zip(arrays, names):
        array_str = ""
        if np.issubdtype(array.dtype, complex):
            # having item size in complex type is invalid openqasm syntax
            array_header = (
                f"array[complex[float[{array.itemsize*4}]], "
                f"{(array.shape[0])}] {name} = {{"
            )
            array_elements = [f"{elem.real} + {elem.imag}im" for elem in array]
            array_str = array_header + ", ".join(array_elements) + "};\n"
        elif np.issubdtype(array.dtype, np.floating):
            array_type = "float"
        elif np.issubdtype(array.dtype, np.integer):
            array_type = "int"

        else:
            raise Exception(
                f"Array type not supported to turn into qasm waveform: {array.dtype}"
            )
        if not array_str:
            array_header = (
                f"array[{array_type}[{array.itemsize*8}], "
                f"{(array.shape[0])}] {name} = {{"
            )
            array_elements = [f"{elem}" for elem in array]
            array_str = array_header + ", ".join(array_elements) + "};\n"
        array_strs.append(array_str)
    qasm += "".join(array_strs)
    return qasm


def waveforms_to_zi(wfms: dict[str, np.ndarray], mapping: dict[int, str]) -> Waveforms:
    """
    Converts a dictionary of waveform name:value pairs to a
    zhinst.toolkit.Waveforms object using a mapping generating from a compiler.

    Args:
        waveforms (dict[str, np.ndarray]):
            dictionary of waveform name:value pairs
        mapping (dict[int, str]):
            mapping from waveform index to name

    Returns:
        zhinst.toolkit.Waveforms: waveform object to be uploaded to AWGs
    """
    for name in mapping.values():
        assert name in wfms, f"Waveform {name} not found in waveforms"
    waveforms_zi = Waveforms()
    # TODO: investigate why below block was failing in measurement
    # but passing compiler tests
    # if mapping:
    #     for index, wfm_name in mapping.items():
    #         waveforms_zi[index] = wfms[wfm_name]
    #     return waveforms_zi
    # for index, wfm_name in enumerate(wfms.keys()):
    #     waveforms_zi[index] = wfms[wfm_name]
    # return waveforms_zi
    for index, wfm_name in mapping.items():
        waveforms_zi[index] = wfms[wfm_name]
    return waveforms_zi


# pylint: disable=R0903:
# Too few public methods (0/2) (too-few-public-methods)
class BinOps:
    """
    Class that warps openQASM BinaryOperators
    for use in structural patern matching
    """

    PLUS = ast.BinaryOperator["+"]
    ASTERIX = ast.BinaryOperator["*"]


class UnOps:
    """
    Clas what wraps unary operations for use in structural pattern mattching
    """

    IMAG = ast.Identifier("ii")


# pylint: enable=R0903:
# Too few public methods (0/2) (too-few-public-methods)


class ScopeContext(Enum):
    """
    Class for keeping track of the current scope of a openQASM program

    detailed discussion can be found at:
    https://openqasm.com/language/scope.html

    With additional discussion regarding the scope of calibration definitions at:
    https://openqasm.com/language/pulses.html#inline-calibration-blocks
    """

    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"
    SUBROUTINE = "SUBROUTINE"
    DEFCAL = "DEFCAL"


class LazyRepr:
    """
    wrap representation for lazy evaluation in logging.
    based of https://stackoverflow.com/a/60072502
    """

    def __init__(self, callback: callable, args: list):
        self.callback = callback
        self.args = args

    def __repr__(self):
        return repr(self.callback(*self.args))
