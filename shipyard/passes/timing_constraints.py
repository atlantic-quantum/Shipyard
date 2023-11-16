"""Check that waveforms meet ZI timing constraints"""
from contextlib import contextmanager

import numpy as np
from openpulse import ast
from openpulse.printer import dumps

from ..call_stack import ActivationRecord, ARType
from ..compiler_error import Error, ErrorCode
from ..setup.internal import SetupInternal
from .interpreter import Interpreter


class TimingConstraints(Interpreter):
    """
    Analyzes the waveforms played or captured in the program to make sure they meet
    the timing constraints of the ZI hardware.

    Args:
        minimum_length (int | None):
            minimum length of the waveform in samples (default: 32)
        granularity (int | None):
            granularity of the waveform in samples (default: 16)
    """

    def __init__(
        self,
        setup: SetupInternal = None,
        external_funcs: dict = None,
        minimum_length: int = 32,
        granularity: int = 16,
    ) -> None:
        self.minimum_length = minimum_length
        self.granularity = granularity
        self.flagged_wfs = []
        super().__init__(setup=setup, external_funcs=external_funcs)

    def check_timing_constraints(self, node, delay_flag=False) -> tuple[bool, int]:
        """
        Checks the timing constraints of a waveform

        Args:
            node
                can be various types

        Returns:
            bool: True if the waveform meets the timing constraints
            int: length of the waveform
        """
        dur_val = self.visit(node)
        if isinstance(dur_val, np.ndarray):
            dur_val = len(dur_val)
        elif dur_val is None:  # should occur during ExecuteTableEntry
            return True, -1
        return (
            dur_val >= self.minimum_length and dur_val % self.granularity == 0
        ), dur_val

    def visit_Program(self, node: ast.Program) -> None:
        activation_record = ActivationRecord(
            name="main", ar_type=ARType.PROGRAM, nesting_level=1
        )
        for extern in self.external_funcs:
            activation_record[extern] = "external"
        with self.ar_context_manager(activation_record):
            for statement in node.statements:
                self.visit(statement)
        if self.flagged_wfs:
            total_message = self.construct_warning_message()
            raise Error(
                ErrorCode.INVALID_WAVEFORM,
                message=total_message,
            )

    def construct_warning_message(self):
        """
        Constructs the warning message for the user based on information
        in self.flagged_wfs
        """
        message = "waveform(s) do not meet timing constraints:\n\n"
        for wf in self.flagged_wfs:
            message += (
                f"Waveform: {dumps(wf['wfm'])}\n\t"
                f"Waveform Length: {wf['length']},\n\t"
                f"Sufficient Length: {wf['length'] >= self.minimum_length},\n\t"
                f"Correct Granularity: {(wf['length'] % self.granularity) == 0}\n\n"
            )
        return message

    def visit_DelayInstruction(self, node: ast.DelayInstruction) -> None:
        """
        DelayInstruction node visitor
            Visits the expression of the delay instruction

        Args:
            node (ast.DelayInstruction):
                openQASM delay instruction ast node to visit
        """
        valid, duration = self.check_timing_constraints(node.duration, True)
        if not valid:
            warning_info = {
                "wfm": node.duration,
                "length": duration,
            }
            self.flagged_wfs.append(warning_info)

    def visit_ForInLoop(self, node: ast.ForInLoop) -> None:
        """
        ForInLoop node visitor
            Note we only want to check the first iteration of the for loop
        """
        name = node.identifier.name
        activation_record = ActivationRecord(
            name=f"for_loop_{self.call_stack.nesting_level+1}",
            ar_type=ARType.LOOP,
            nesting_level=self.call_stack.nesting_level + 1,
        )
        with self.ar_context_manager(activation_record):
            match node.set_declaration:
                case ast.RangeDefinition():
                    start, end, step = self.visit(node.set_declaration)
                    activation_record = self.call_stack.peek()
                    for value in [start, start + step, end]:
                        activation_record[name] = value
                        for statement in node.block:
                            self.visit(statement)
                case _:
                    raise Error(
                        ErrorCode.UNHANDLED,
                        (
                            f"unsupported set declaration in for loop:"
                            f"{node.set_declaration}"
                        ),
                    )

    def visit_FunctionCall(self, node: ast.FunctionCall) -> None:
        """
        FunctionCall node visitor:
            Checks for waveform plays/ captures to check the waveform
            characteristics

        Args:
            node (ast.FunctionCall): openQASM FunctionCall AST node
        """
        activation_record = ActivationRecord(
            name=f"{node.name.name}",
            ar_type=ARType.SUBROUTINE,
            nesting_level=self.call_stack.nesting_level + 1,
        )
        with self.ar_context_manager(activation_record):
            match node:
                case ast.FunctionCall(
                    name=ast.Identifier("play"), arguments=[_, arg]
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v1"), arguments=[_, arg]
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v2"), arguments=[_, arg]
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v3"), arguments=[_, arg]
                ) | ast.FunctionCall(
                    name=ast.Identifier("capture_v1_spectrum"), arguments=[_, arg]
                ):
                    match arg:
                        case ast.FunctionCall(name=ast.Identifier("executeTableEntry")):
                            pass
                        case _:
                            if not self.check_timing_constraints(arg)[0]:
                                warning_info = {
                                    "wfm": arg,
                                    "length": self.check_timing_constraints(arg)[1],
                                }
                                self.flagged_wfs.append(warning_info)
                case _:
                    return super().visit_FunctionCall(node)

    @contextmanager
    def ar_context_manager(
        self,
        activation_record: ActivationRecord,
    ):
        """
        Context manager for activation records / call stack,
        the activation record tracks ports and frames declared in the program
        to make sure frames can be replaced with approprate channels

        Args:
            activation_record (ActivationRecord): activation record to activate
        """
        self.call_stack.push(activation_record)
        try:
            yield
        finally:
            self.call_stack.pop()
