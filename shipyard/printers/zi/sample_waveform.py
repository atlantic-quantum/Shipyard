"""
Transform openpulse nodes that would create waveforms on supported seqc cores
into sampled waveforms for later upload to instrument waveform memory.
"""
import operator

from numpy import ndarray
from openpulse import ast

from ...compiler_error import ErrorCode, SEQCPrinterError
from . import waveform_functions


def sample_waveform(node: ast.Expression) -> ndarray:
    """Transform supported function call to sampled waveform

    currently support sampling the following waveform:
        - blackman,
        - chirp,
        - cosine,
        - drag,
        - gauss,
        - hamming,
        - hann,
        - ones,
        - ramp,
        - rect,
        - rrc,
        - sawtooth,
        - sinc,
        - sine,
        - triangle,
        - zeros,
    see printers/zi/waveform_functions.py for further details


    Args:
        node (ast.Expression):
            FunctionCall (or binary expression) openqasm node expressing a waveform.

    Raises:
        SEQCPrinterError: if node does not match supported structural pattern

    Returns:
        ndarray: sampled waveform
    """
    match node:
        case ast.FunctionCall(name=ast.Identifier(name), arguments=args):
            try:
                func = waveform_functions.__dict__[name]
                wfm = func(*literal_args_to_values(args))
                return wfm.astype(complex)
            except KeyError as exc:
                raise SEQCPrinterError(
                    ErrorCode.UNDETERMINED_CALL,
                    f"Atempted sampling a unsupported function: {name}",
                ) from exc
        case ast.BinaryExpression(op=operation, lhs=lhs, rhs=rhs):
            return ops[operation.value](sample_waveform(lhs), sample_waveform(rhs))
        case ast.FloatLiteral() | ast.IntegerLiteral():
            return node.value
        case _:
            raise SEQCPrinterError(
                ErrorCode.UNHANDLED, "Atempted sampling a unknown waveform"
            )


def literal_args_to_values(nodes: list[ast.Expression]) -> list:
    """
    visits a list of literal nodes and returns a list of their values

    Args:
        nodes (list[ast.Expression]): list of literal nodes

    Returns:
        list: list of values of literal nodes
    """
    return [node.value for node in nodes]


# todo use for NodeEvaluator visitor
# orders mirrors ast.BinaryOperator enumeration order
# this is important for correct function
# https://stackoverflow.com/questions/1740726/turn-string-into-operator
ops = {
    1: operator.gt,
    2: operator.lt,
    3: operator.ge,
    4: operator.le,
    5: operator.eq,
    6: operator.ne,
    7: lambda x, y: x and y,
    8: lambda x, y: x or y,
    9: operator.or_,
    10: operator.xor,
    11: operator.and_,
    12: operator.lshift,
    13: operator.rshift,
    14: operator.add,
    15: operator.sub,
    16: operator.mul,
    17: operator.truediv,
    18: operator.mod,
    19: operator.pow,
}
