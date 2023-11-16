import functools

import matplotlib.pyplot as plt
import numpy as np
from openpulse import ast

from ...call_stack import ActivationRecord, ARType
from ...compiler_error import Error, ErrorCode
from ...passes import Interpreter
from ...setup.internal import Frame, SetupInternal


def _maybe_annotated(method):  # pragma: no cover
    @functools.wraps(method)
    def annotated(self: "Interpreter", node: ast.Statement) -> None:
        for annotation in node.annotations:
            self.visit(annotation)
        return method(self, node)

    return annotated


class PulseVisualizer(Interpreter):
    def __init__(
        self,
        setup: SetupInternal = None,
        external_functions: dict = None,
    ):
        super().__init__(setup, external_functions)
        self.pulses = {}  # dict of pulses for each frame/ port
        self.phases = {}  # dict of phases for each frame/ port
        self.frequencies = {}  # dict of frequencies for each frame/ port
        self.plot_flag: bool = False

    def visit_Program(self, node: ast.Program) -> None:
        activation_record = ActivationRecord(
            name="main", ar_type=ARType.PROGRAM, nesting_level=1
        )
        with self.ar_context_manager(activation_record):
            for statement in node.statements:
                self.visit(statement)
        for frame in self.pulses.keys():
            self.plotter(
                np.concatenate(self.pulses[frame]),
                np.concatenate(self.phases[frame]),
                np.concatenate(self.frequencies[frame]),
                frame,
            )

    def plotter(self, wfm_array, phase_array, frequency_array, frame_name):
        fig, axs = plt.subplots(3)
        if all(isinstance(i, complex) for i in wfm_array):
            axs[0].plot([value.real for value in wfm_array], label="real")
            axs[0].plot([value.imag for value in wfm_array], label="imag")
            axs[0].legend()
        else:
            axs[0].plot(wfm_array)
        axs[0].set(ylabel=f"{frame_name} amplitude")
        axs[1].plot(phase_array)
        axs[1].set(ylabel=f"{frame_name} phase")
        axs[2].plot(frequency_array)
        axs[2].set(ylabel=f"{frame_name} frequency")
        if self.plot_flag:  # pragma: no cover
            plt.show()

    @_maybe_annotated
    def visit_ClassicalDeclaration(self, node: ast.ClassicalDeclaration) -> None:
        """
        ClassicalDeclaration node visitor:
            Visits and stores classical declarations of variables. If the variable
            declared is a frame, the frame is added to the current activation record,
            as well as the Interpreter's pulse, phase, and frequency dictionaries.

        Args:
            node (ast.ClassicalDeclaration): openQASM ClassicalDeclaration AST node

        """
        activation_record = self.call_stack.peek()
        match node:
            case ast.ClassicalDeclaration(type=ast.PortType()):
                name = node.identifier.name
                activation_record[name] = self.setup.ports[name]
            case ast.ClassicalDeclaration(
                type=ast.FrameType(),
                init_expression=ast.FunctionCall(name=ast.Identifier("newframe")),
            ):
                call = node.init_expression
                assert isinstance(call, ast.FunctionCall)
                assert len(call.arguments) == 3
                port = call.arguments[0].name
                frequency = self.visit(call.arguments[1])
                phase = self.visit(call.arguments[2])
                frame = Frame(
                    name=node.identifier.name,
                    port=activation_record[port],
                    frequency=frequency,
                    phase=phase,
                )
                self.pulses[frame.name] = []
                self.phases[frame.name] = []
                self.frequencies[frame.name] = []
                activation_record[frame.name] = frame
            case ast.ClassicalDeclaration(type=ast.ArrayType()):
                if node.init_expression is None:
                    shapes = [dim.value for dim in node.type.dimensions]
                    activation_record[node.identifier.name] = np.zeros(shape=shapes)
                else:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
            case _:
                if node.init_expression is not None:
                    activation_record[node.identifier.name] = self.visit(
                        node.init_expression
                    )
                else:
                    activation_record[node.identifier.name] = None

    @_maybe_annotated
    def visit_DelayInstruction(self, node: ast.DelayInstruction) -> None:
        """
        DelayInstruction node visitor:
            Appends delay of 0s to relevant frame

        Args:
            node (ast.DelayInstruction): openQASM DelayInstruction AST node
        """
        for q in node.qubits:
            if q.name in self.pulses.keys():
                self.pulses[q.name].append(np.zeros(int(self.visit(node.duration))))
                self.phases[q.name].append(
                    np.full(
                        int(self.visit(node.duration)),
                        self.call_stack.down_stack(q.name)[q.name].phase,
                    )
                )
                self.frequencies[q.name].append(
                    np.full(
                        int(self.visit(node.duration)),
                        self.call_stack.down_stack(q.name)[q.name].frequency,
                    )
                )

    def visit_play(self, node: ast.FunctionCall) -> None:
        """
        FunctionCall node visitor. Handles 'play' and 'capture' function calls.
        For 'play', 'capture_v1', and 'capture_v2' function calls, the function
        call is visited and the resulting waveform is appended to the relevant
        frame's pulse, phase, and frequency arrays. For 'capture_v3' and
        'capture_v1' function calls, the function call is visited and the resulting
        time value is returned and turned into an array of 1s of that length, and
        appeneded to the relevant frame's pulse, phase, and frequency arrays.

        Args:
            node (ast.FunctionCall): 'play' FunctionCall node to visit

        Raises:
            Error:
                ErrorCode.UNHANDLED
                If the node does not match the expected format/structure
        """
        match node:
            case ast.FunctionCall(
                name=ast.Identifier("play"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ) | ast.FunctionCall(
                name=ast.Identifier("capture_v1"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ) | ast.FunctionCall(
                name=ast.Identifier("capture_v2"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ):
                wfm_array = self.visit(wfm_node)
                self.phases[frame_name].append(
                    np.full(
                        len(wfm_array),
                        self.call_stack.down_stack(frame_name)[frame_name].phase,
                    )
                )
                self.pulses[frame_name].append(wfm_array)
                self.frequencies[frame_name].append(
                    np.full(
                        len(wfm_array),
                        self.call_stack.down_stack(frame_name)[frame_name].frequency,
                    )
                )
            case ast.FunctionCall(
                name=ast.Identifier("capture_v3"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ) | ast.FunctionCall(
                name=ast.Identifier("capture_v1_spectrum"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ):
                val = self.visit(wfm_node)
                self.phases[frame_name].append(
                    np.full(
                        len(wfm_array),
                        self.call_stack.down_stack(frame_name)[frame_name].phase,
                    )
                )
                self.pulses[frame_name].append(np.ones(int(val)))
                self.frequencies[frame_name].append(
                    np.full(
                        len(wfm_array),
                        self.call_stack.down_stack(frame_name)[frame_name].frequency,
                    )
                )

            case _:
                raise Error(
                    ErrorCode.UNHANDLED,
                    f"Unhandled waveform generation: {node}",
                )
