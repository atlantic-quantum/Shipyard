# pylint: disable=C0302
# Too many lines in module
"""
SEQCPrinter:
Class for printing out openQASM ASTs as SEQC code.

the openQASM AST may have to go through other compilation steps in
order for the SEQCPrinter to be able to print the tree as SEQC code
"""

import functools
import io
from contextlib import contextmanager
from typing import Any, Optional

import numpy as np
from numpy import prod
from openpulse import ast
from openpulse.printer import Printer

# from openqasm3 import ast, properties
from openqasm3.printer import PrinterState

from ...awg_core import CoreType
from ...call_stack import ActivationRecord, ARType, CallStack
from ...compiler_error import ErrorCode, SemanticError, SEQCPrinterError
from ...logger import LOGGER
from ...mangle import Mangler
from ...passes import Interpreter, ShotsSignature, StackAnalyzer
from ...setup.internal import Frame, SetupInternal
from ...utilities import LazyRepr
from ...visitors import CopyTransformer
from . import waveform_functions
from .instrument_settings import HDCORE, Mode, ReadoutSource, SHFQACore, SHFSGCore
from .sample_waveform import sample_waveform


def dump(node: ast.QASMNode, file: io.TextIOBase, **kwargs) -> None:
    """Write textual SEQC code representing ``node`` to the open stream ``file``.

    It is generally expected that ``node`` will be an instance of :class:`.ast.Program`,
    but this does not need to be the case.

    For more details on the available keyword arguments, see :ref:`printer-kwargs`.
    """
    SEQCPrinter(file, **kwargs).visit(node)


def dumps(node: ast.QASMNode, **kwargs) -> str:
    """Get a string representation of the SEQC code representing ``node``.

    It is generally expected that ``node`` will be an instance of :class:`.ast.Program`,
    but this does not need to be the case.

    For more details on the available keyword arguments, see :ref:`printer-kwargs`.
    """
    out = io.StringIO()
    dump(node, out, **kwargs)
    return out.getvalue()


def _maybe_annotated(method):  # pragma: no cover
    @functools.wraps(method)
    def annotated(
        self: "SEQCPrinter", node: ast.Statement, context: PrinterState
    ) -> None:
        for annotation in node.annotations:
            self.visit(annotation)
        return method(self, node, context)

    return annotated


def _visit_interpreter(method):
    @functools.wraps(method)
    def interpreter_visit(
        self: "SEQCPrinter", node: ast.Statement, context: PrinterState
    ) -> None:
        if self.interpret:
            self.interpreter.visit(node)
        return method(self, node, context)

    return interpreter_visit


__math_functions__ = {  # todo write tests
    # from SHFQA manual readout pulse generator - Expressions
    "abs": np.abs,
    "acos": np.arccos,
    "acosh": np.arccosh,
    "asin": np.arcsin,
    "asinh": np.arcsinh,
    "atan": np.arctan,
    "atanh": np.arctanh,
    "cos": np.cos,
    "cosh": np.cosh,
    "exp": np.exp,
    "ln": np.log,
    "log": np.log10,
    "log2": np.log2,
    "log10": np.log10,
    "sign": np.sign,
    "sin": np.sin,
    "sinh": np.sinh,
    "sqrt": np.sqrt,
    "tan": np.tan,
    "tanh": np.tanh,
    "ceil": np.ceil,
    "round": np.round,
    "floor": np.floor,
    "avg": np.mean,
    "max": np.max,
    "min": np.min,
    "pow": np.power,
    "sum": np.sum,
}


def external_function_dict():
    exteranl_funcs = {
        k: v
        for k, v in waveform_functions.__dict__.items()
        if k in waveform_functions.__all__
    }
    exteranl_funcs.update(__math_functions__)
    return exteranl_funcs


# pylint: disable=R0904
# to many public methods
class SEQCPrinter(Printer):
    """Internal AST-visitor for writing AST nodes out to a stream as valid ZI SEQC code.

    This class can be used directly to write multiple nodes to the same stream,
    potentially with some manual control fo the state between them.

    If subclassing, generally only the specialised ``visit_*`` methods need to be
    overridden.  These are derived from the base class, and use the name of the
    relevant :mod:`AST node <.ast>` verbatim after ``visit_``.

    Based on the openQASM3 Printer"""

    def __init__(
        self,
        stream: io.TextIOBase,
        setup: SetupInternal = None,
        sig: ShotsSignature = ShotsSignature(),
        measurement_delay: float = None,
        constant_for_loops: bool = True,
        average_shots: bool = True,
    ):
        # todo docstring
        self.call_stack = CallStack()
        self.setup = setup
        self.sig = sig
        self.meas_delay = measurement_delay
        self.defcal_names = []
        self.multi_measure_bit = None
        super().__init__(
            stream, indent="  ", chain_else_if=False, old_measurement=False
        )
        self.interpreter = Interpreter(
            setup=setup, external_funcs=external_function_dict()
        )
        self.interpreter.call_stack = self.call_stack
        self.core = None
        self.constant_for_loops = constant_for_loops
        self.interpret = True
        self.average_shots = average_shots
        self.placeholder_index = 0
        self.wfm_indices = {}

    def visit(self, node: ast.QASMNode, context: Optional[PrinterState] = None) -> None:
        try:
            return super().visit(node, context)
        except NotImplementedError as exception:
            LOGGER.debug(LazyRepr(self.stream.getvalue, []))
            raise exception

    def visit_Program(self, node: ast.Program, context: PrinterState) -> None:
        # todo compiler verions etc.
        # if node.version:
        #     self._write_statement(f"OPENQASM {node.version}", context)
        activation_record = ActivationRecord(
            name="main", ar_type=ARType.PROGRAM, nesting_level=1
        )
        for extern in self.interpreter.external_funcs:
            activation_record[extern] = "external"
        with self.ar_context_manager(activation_record):
            for statement in node.statements:
                self.visit(statement, context)

    @_maybe_annotated
    def visit_Include(self, node: ast.Include, context: PrinterState) -> None:
        raise self.compile_out(node)

    def visit_ExpressionStatement(
        self, node: ast.ExpressionStatement, context: PrinterState
    ) -> None:
        self.visit(node.expression, context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_QubitDeclaration(
        self, node: ast.QubitDeclaration, context: PrinterState
    ) -> None:
        """the concept of Qubit does not exist in SEQC code, pass for now but maybe
        replace with some combination of port / frame? or as with include statements,
        should this be resolved before writing SEQC code"""
        pass

    @_maybe_annotated
    def visit_QuantumGateDefinition(
        self, node: ast.QuantumGateDefinition, context: PrinterState
    ) -> None:
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_ExternDeclaration(
        self, node: ast.ExternDeclaration, context: PrinterState
    ) -> None:
        # todo: HERE: make sure declared externals are allowed
        pass

    def visit_ImaginaryLiteral(
        self, node: ast.ImaginaryLiteral, context: PrinterState
    ) -> None:
        if node.value == 1.0:
            return self.interpreter.visit_ImaginaryLiteral(node)
        raise self.compile_out(node)
        # Imaginary numbers are not supported by SEQC

    @_visit_interpreter
    def visit_DurationLiteral(
        self, node: ast.DurationLiteral, context: PrinterState
    ) -> None:
        # todo time w/ units translate to actual time in SI or Samples?
        self.stream.write(f"{int(node.value)}")

    @_visit_interpreter
    def visit_ArrayLiteral(self, node: ast.ArrayLiteral, context: PrinterState) -> None:
        # todo compile array literals into multiple literals
        # todo what about waveforms defined from a vector?
        self._visit_sequence(
            node.values, context, start="vect(", end=")", separator=", "
        )

    def visit_DiscreteSet(self, node: ast.DiscreteSet, context: PrinterState) -> None:
        raise self.compile_out(node)
        # seems to be intended for use in for loops e.g. for i in {1, 3, 56}: ...
        # it should be possible to compile such a statement into a traditional for loop
        # or multiple executions

    def visit_RangeDefinition(
        self, node: ast.RangeDefinition, context: PrinterState
    ) -> None:
        raise self.compile_out(node)

    @_visit_interpreter
    def visit_IndexExpression(
        self, node: ast.IndexExpression, context: PrinterState
    ) -> None:
        self.stream.write(f"{node.collection.name}[{int(node.index[0].value)}]")

    @_visit_interpreter
    def visit_IndexedIdentifier(
        self, node: ast.IndexedIdentifier, context: PrinterState
    ) -> None:
        """
        IndexedIdentifier node visitor:
            prints openqasm indexed identifier

            array[float, 10] a;

            a[3] = 1.1;
            ^^^^
            indexed identifer

            openqasm supports using discreate sets as indecies
            seqc does not support this and an error gets raised upon visiting
            DiscreateSet nodes

        Args:
            node (ast.IndexedIdentifier): openQASM IndexedIdentifier node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        self.visit(node.name, context)
        for index in node.indices:
            self.stream.write("[")
            match index:
                # todo more specific for non DiscreateSet (limit to 1D)
                # todo raise errors directly here
                case ast.DiscreteSet():
                    self.visit(index, context)
                case _:
                    self._visit_sequence(index, context, separator=", ")
            self.stream.write("]")

    @_visit_interpreter
    def visit_Concatenation(
        self, node: ast.Concatenation, context: PrinterState
    ) -> None:
        """
        Concatenation node visitor:
            Prints openqasm concatenation statement as a SEQC join statement

            example:
                qasm: 'a ++ b ++ c;'
                ->
                seqc: 'join(a, b, c);'

        Args:
            node (ast.Concatenation): openQASM concatenation AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """

        def process_side(c_node: ast.Expression):
            match c_node:
                case ast.Concatenation():
                    process_side(c_node.lhs)
                    self.stream.write(", ")
                    process_side(c_node.rhs)
                case _:
                    self.visit(c_node, context)

        self.stream.write("join(")
        process_side(node)
        self.stream.write(")")

    @_visit_interpreter
    @_maybe_annotated
    def visit_QuantumGate(self, node: ast.QuantumGate, context: PrinterState) -> None:
        """
        QuantumGate node visitor:
            Prints quantum gate call as a mangled function name, at this point the
            gate operation should have a calibration definition (defcal)

            Example:
                qasm:
                    defcal x90 $0 {...}
                  >>x90 $0;
                ->  ^^^^^^^
                seqc
                    void _ZN3x90_PN0_QN1__0_R() {...}
                  >>_ZNx90_PN0_QN1__0_R();
                    ^^^^^^^^^^^^^^^^^^^^^^
        Args:
            node (ast.QuantumGate): openQASM QuantumGate AST node
            context (PrinterState): state of the printer (e.g. indentation)

        Raises:
            SEQCPrinterError: ErrorCode.COMPILE_OUT:
                if modifiers are applied to the gate, modifiers should be handled prior
                to printing to SEQC code
        """
        # gate has to have a defcal implementation at this point
        if node.modifiers:
            raise self.compile_out(node.modifiers)
        signature = Mangler(node).signature()
        mangled_name = signature.match(self.defcal_names)[0]
        self._start_line(context)
        self.visit(ast.Identifier(self.make_string_legal(mangled_name)), context)
        self._visit_sequence(
            node.arguments, context, start="(", end=")", separator=", "
        )
        self._end_statement(context)

    def visit_QuantumGateModifier(
        self, node: ast.QuantumGateModifier, context: PrinterState
    ) -> None:
        """
        the concept of QuantumGateModifier does not exist in SEQC code,
        This node needs to be resolved in earlier stages of the compilation process
        """
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_QuantumPhase(self, node: ast.QuantumPhase, context: PrinterState) -> None:
        raise self.compile_out(node)

    @_visit_interpreter
    def visit_QuantumMeasurement(
        self, node: ast.QuantumMeasurement, context: PrinterState
    ) -> None:
        """
        QuantumMeasurement node visitor:
            Prints quantum measurement call as a mangled function name,
            at this point the quantum measurement should have a calibration definition
            (defcal)

            Example:
                qasm:
                    defcal measure $0 -> bit {...}
                  >>b1 = measure $0;
                ->       ^^^^^^^^^^^
                seqc
                    var _ZN7measure_PN0_QN1__0_RBIT() {...}
                  >>b1 = _ZN7measure_PN0_QN1__0_RBIT();
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Args:
            node (ast.QuantumMeasurement): openQASM QuantumMeasurement AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        signature = Mangler(node).signature()
        mangled_name = signature.match(self.defcal_names)[0]
        self._start_line(context)
        self.visit(ast.Identifier(self.make_string_legal(mangled_name)), context)
        self.stream.write("()")

    @_visit_interpreter
    @_maybe_annotated
    def visit_QuantumReset(self, node: ast.QuantumReset, context: PrinterState) -> None:
        """
        QuantumReset node visitor:
            Prints quantum reset call as a mangled function name,
            at this point the quantum reset should have a calibration definition
            (defcal)

            Example:
                qasm:
                    defcal reset $0 {...}
                  >>reset $0;
                ->  ^^^^^^^^^
                seqc
                    void _ZN5reset_PN0_QN1__0_R() {...}
                  >>_ZN5reset_PN0_QN1__0_R();
                    ^^^^^^^^^^^^^^^^^^^^^^^^^
        Args:
            node (ast.QuantumReset): openQASM QuantumReset AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        signature = Mangler(node).signature()
        mangled_name = signature.match(self.defcal_names)[0]
        self._start_line(context)
        self.visit(ast.Identifier(self.make_string_legal(mangled_name)), context)
        self.stream.write("()")
        self._end_statement(context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_QuantumBarrier(
        self, node: ast.QuantumBarrier, context: PrinterState
    ) -> None:
        """
        QuantumBarrier node visitor:
            Replaces barrier statement with a waitZSyncTrigger() call for
            synchronization of channels for ZI instruments. Update documentation of
            visit_QuantumBarrier. According to OpenQASM specification, barrier invoked
            without arguments assumes all qubits are arguments. Applying the
            waitZSyncTrigger command places a barrier on all the qubits assocaited with
            a particular core.
            Note: barrier is only supported globally by the SEQCPrinter, behavior when
            placing such a barrier in a middle of a program/loop is not fully known.

            Example:
                qasm:
                    barrier;
                seqc:
                    waitZSyncTrigger();
        Args:
            node (ast.QuantumBarrier): openQASM QuantumBarrier AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        # todo write appropriate playZero/Wait instructions
        if node.qubits == []:
            self.stream.write("waitZSyncTrigger()")
            self._end_statement(context)
        else:
            raise self.compile_out(node)

    @_visit_interpreter
    @_maybe_annotated
    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement, context: PrinterState
    ) -> None:
        """
        QuantumMeasurementStatement node visitor:
            QuantumMeasurementStatement contains a QuantumMeasurement and 'target'
            the the result of the QuantumMeasurement is asigned to

            i.e.
                      |----------------| <- QuantumMeasurmentStatement
                      t_bit = measure $1
            target -> |---|   |--------| <- QuantumMeasurement

            Example:
                qasm:
                    defcal measure $0 -> bit {...}
                  >>b1 = measure $0;
                ->  ^^^^^^^^^^^^^^^^
                seqc
                    var _ZN7measure_PN0_QN1__0_RBIT() {...}
                  >>b1 = _ZN7measure_PN0_QN1__0_RBIT();
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Args:
            node (ast.QuantumMeasurementStatement):
                openQASM QuantumMeasurementStatement AST node
            context (PrinterState):
                state of the printer (e.g. indentation)
        """
        self._start_line(context)
        if node.target:
            self.visit(node.target)
            self.stream.write(" = ")
        self.visit(node.measure)
        self._end_statement(context)

    def visit_ClassicalArgument(
        self, node: ast.ClassicalArgument, context: PrinterState
    ) -> None:
        """
        ClassicalArgument node visitor:
            Prints arguments in procedure/defcal/gate definitions:

            Example:
                qasm:
                    def my_function(int i) {...}
                ->                  ^^^^^
                seqc:
                    void my_function(var i) {...}
                                     ^^^^^
        Args:
            node (ast.ClassicalArgument): openQASM ClassicalArgument AST node
            context (PrinterState): state of the printer (e.g. indentation)

        Raises:
            NotImplementedError:
                if the argument has access control (not supported by SEQC)
        """
        if node.access is not None:
            raise NotImplementedError
        self.stream.write("var ")
        self.visit(node.name, context)

    @_visit_interpreter
    def visit_ExternArgument(
        self, node: ast.ExternArgument, context: PrinterState
    ) -> None:
        # todo extern arguments should only be in ExternDeclarations
        # todo we may want to compile ExternDeclarations out and remove this visitor
        if node.access is not None:
            raise NotImplementedError
        self.visit(node.type, context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration, context: PrinterState
    ) -> None:
        match node.type:
            case ast.PortType():
                name = node.identifier.name
                activation_record = self.call_stack.peek()
                port = self.setup.ports[name]
                activation_record[name] = port
                if not self.core:
                    if port.core.type == CoreType.HD:
                        self.core = HDCORE(channel=port.core.index)
                    elif port.core.type == CoreType.SG:
                        self.core = SHFSGCore(channel=port.core.index)
                if port.core.type == CoreType.HD:
                    self.core.outputs[port.core.channels[0]] = HDCORE.Output(
                        output=port.core.channels[0]
                    )
            case ast.FrameType():
                match node.init_expression:
                    case ast.FunctionCall(name=ast.Identifier("newframe")):
                        call = node.init_expression
                        assert isinstance(call, ast.FunctionCall)
                        assert len(call.arguments) == 3
                        port = call.arguments[0].name  # Identifier
                        frequency = call.arguments[1].value  # Literal
                        phase = call.arguments[2].value  # Literal
                        activation_record = self.call_stack.peek()
                        frame = Frame(
                            name=node.identifier.name,
                            port=activation_record[port],
                            frequency=frequency,
                            phase=phase,
                        )
                        self.setup.frames[frame.name] = frame
                        activation_record[frame.name] = frame
                    case _:
                        raise SEQCPrinterError(
                            ErrorCode.INVALID_ARGUMENT,
                            "Only newframe() is supported for frame initialization",
                        )
            case ast.ArrayType():
                self._start_line(context)
                self.stream.write("wave ")
                self.visit(node.identifier)
                if node.init_expression is None:
                    self.stream.write(" = zeros")
                    self._visit_sequence(
                        node.type.dimensions,
                        context,
                        start="(",
                        end=")",
                        separator=", ",
                    )
                else:
                    self.stream.write(" = ")
                    self.visit(node.init_expression)
                self._end_statement(context)
            case ast.WaveformType():
                self._start_line(context)
                self.visit(node.type)
                self.stream.write(" ")
                self.visit(node.identifier, context)
                if node.init_expression is not None:
                    self.stream.write(" = ")
                    self.visit(node.init_expression)
                self._end_statement(context)
                match node.init_expression:
                    case ast.FunctionCall(name=ast.Identifier("placeholder")):
                        self._start_line(context)
                        self.stream.write("assignWaveIndex(")
                        self.visit(node.identifier, context)
                        self.stream.write(f", {self.placeholder_index})")
                        self.wfm_indices[self.placeholder_index] = node.identifier.name
                        self.placeholder_index += 1
                        self._end_statement(context)
                    case _:
                        pass
            case _:
                self._start_line(context)
                self.stream.write("var")
                self.stream.write(" ")
                self.visit(node.identifier, context)
                if node.init_expression is not None:
                    self.stream.write(" = ")
                    self.visit(node.init_expression)
                self._end_statement(context)

    @_maybe_annotated
    def visit_IODeclaration(
        self, node: ast.IODeclaration, context: PrinterState
    ) -> None:
        raise self.compile_out(node)

    @_visit_interpreter
    @_maybe_annotated
    def visit_ConstantDeclaration(
        self, node: ast.ConstantDeclaration, context: PrinterState
    ) -> None:
        """
        ConstantDeclaration node visitor:
            Prints constant declarations in correct seqc format, in seqc the datatype
            is automatically infered from the value assigned to the constant.

            Example:
                qasm:
                    const float f = 1.1;
                ->
                seqc:
                    const f = 1.1;

        Args:
            node (ast.ConstantDeclaration): openQASM ConstantDeclaration AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        match node:
            case ast.ConstantDeclaration(
                ast.ComplexType(), ast.Identifier("ii"), ast.ImaginaryLiteral(1.0)
            ):
                return
            case _:
                self._start_line(context)
                self.stream.write("const ")
                self.visit(node.identifier, context)
                self.stream.write(" = ")
                self.visit(node.init_expression, context)
                self._end_statement(context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_CalibrationGrammarDeclaration(
        self, node: ast.CalibrationGrammarDeclaration, context: PrinterState
    ) -> None:
        """
        CalibrationGrammarDeclaration node visitor:
            calibration grammar is not a concept in SEQC so this is omitted from the
            printed stream.

            ToDo: print the grammar as a comment instead

        Args:
            node (ast.CalibrationGrammarDeclaration):
                openQASM CalibrationGrammarDeclaration AST node
            context (PrinterState):
                state of the printer (e.g. indentation)
        """

    @_visit_interpreter
    @_maybe_annotated
    def visit_CalibrationDefinition(
        self, node: ast.CalibrationDefinition, context: PrinterState
    ) -> None:
        """
        CalibrationDefinition (defcal) node visitor:
            Converts to openQASM calibration definitions into SEQC functions with a
            mangled name:

            Example 1:
                qasm: defcal x90 $1 {...}
                seqc: void _ZN3x90_PN0_QN1__1_R() {...}

            Some definitions (e.g. qubit state measurements) require special handling as
            multiple statements in openQASM (e.g. play followed by caputure) are
            performed by a single statment in SEQC (startQA)

            Example 2:
                qasm:
                    defcal measure $0 {
                        play(tx_frame, wfm_measure);
                        return capture_v2(rx_frame, wfm_integration);
                    }
                ->
                seqc:
                    var _ZN7measure_PN0_QN1__0_RBIT() {
                        startQA(QA_GEN_0, QA_INT_0, false, 0x0, 0b0);
                        return getDIO(0x0)
                    }

                The measure and integration waveforms are stored and uploaded to the
                appropriate waveform memories on the QA instrument during instrument
                setup <- ToDo This needs to be fully implemented

        Args:
            node (ast.CalibrationDefinition): defcal node to visit
            context (PrinterState): printer state (e.g. indentation)
        """
        with self.interpret_context_manager(False):
            # here we turn off the interpreter as we don't want to interpret the
            # the contents of the defcal statement when it is defined (only when it is
            # called)
            self._start_line(context)
            self.stream.write("void " if node.return_type is None else "var ")
            mangled_name = Mangler(node).signature().mangle()
            self.defcal_names.append(mangled_name)
            self.visit(ast.Identifier(self.make_string_legal(mangled_name)), context)
            arguments = [
                ast.ClassicalArgument(ast.IntType(), ast.Identifier(f"lit_{i}"))
                if isinstance(argument, ast.Expression)
                else argument
                for i, argument in enumerate(node.arguments)
            ]
            self._visit_sequence(arguments, context, start="(", end=")", separator=", ")
            self.stream.write(" {")
            self._end_line(context)
            with context.increase_scope():
                LOGGER.debug(node.body)
                match node.body:
                    case [
                        ast.ExpressionStatement(
                            ast.FunctionCall(
                                name=ast.Identifier("play"), arguments=play_args
                            )
                        ),
                        # todo should ExpressionStatement be supported for v2?
                        ast.ReturnStatement(
                            ast.FunctionCall(
                                name=ast.Identifier("capture_v2"),
                                arguments=capture_args,
                            )
                        )
                        | ast.ExpressionStatement(
                            ast.FunctionCall(
                                name=ast.Identifier("capture_v1"),
                                arguments=capture_args,
                            )
                        ),
                    ]:
                        # ensure that play and caputure commands are using ports on the
                        # same instrument
                        is_v2 = node.body[1].expression.name.name == "capture_v2"
                        # todo make generic for QA/QC
                        # todo make a separate validation step for these assertions.
                        play_frame = self.setup.frames[play_args[0].name]
                        capture_frame = self.setup.frames[capture_args[0].name]
                        assert (
                            play_frame.port.instrument == capture_frame.port.instrument
                        )
                        assert play_frame.port.core.channels == [1]
                        assert capture_frame.port.core.channels == [2]
                        assert (
                            play_frame.port.core.type
                            == capture_frame.port.core.type
                            == CoreType.QA
                        )
                        readout = SHFQACore.READOUT(
                            index=-1,
                            generator_wfm=self.interpreter.visit(play_args[1]).astype(
                                complex
                            ),
                            integrator_wfm=self.interpreter.visit(
                                capture_args[1]
                            ).astype(complex),
                            threshold=0,  # todo
                        )
                        if self.core is None:
                            readout.index = 0
                            core = SHFQACore(
                                channel=play_frame.port.core.index,
                                readouts={readout.index: readout},
                                points_to_record=prod(self.sig.steps),
                                num_averages=self.sig.shots,
                                readout_source=ReadoutSource.DISCRIMINATION
                                if is_v2
                                else ReadoutSource.INTEGRATION,
                                average_shots=self.average_shots,
                            )
                            self.core = core
                        else:
                            readout.index = len(self.core.readouts.keys())
                            self.core.readouts[readout.index] = readout
                        # todo write correct registers
                        self._start_line(context)
                        self.stream.write(f"playZero({len(readout.generator_wfm)})")
                        self._end_statement(context)
                        self._start_line(context)
                        self.stream.write(f"startQA(QA_GEN_{readout.index}, ")
                        self.stream.write(f"QA_INT_{readout.index}, true, ")
                        self.stream.write(f"0x{readout.index}, 0b0)")
                        self._end_statement(context)
                        if is_v2:
                            self._start_line(context)
                            # self.stream.write(f"return getDIO() & 0x{readout.index}")
                            # self.stream.write(
                            # f"return getZSyncData(ZSYNC_DATA_PQSC_REGISTER)"
                            # )
                            self.stream.write("return getZSyncData(ZSYNC_DATA_RAW)")
                            self._end_statement(context)
                    case _:
                        for statement in node.body:
                            self.visit(statement, context)
            self._start_line(context)
            self.stream.write("}")
            self._end_line(context)

    @_maybe_annotated
    def visit_CalibrationStatement(
        self, node: ast.CalibrationStatement, context: PrinterState
    ) -> None:
        """
        CalibrationStatement node visitor:
            Visits all statements in the CalibrationStatement, unlike when printing
            to openQASM format this visitor omits 'cal {...}' as 'cal' is not a concept
            in the SEQC language.

            Example:
                qasm:
                    cal {
                        cal_stmt_1;
                        cal_stmt_2;
                    }
                ->
                seqc:
                    cal_stmt_1;
                    cal_stmt_2;

        Args:
            node (ast.CalibrationStatement): openQASM CalibrationStatement AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        for statement in node.body:
            self.visit(statement, context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_SubroutineDefinition(
        self, node: ast.SubroutineDefinition, context: PrinterState
    ) -> None:
        """
        SubroutineDefinition node visitor:
            Prints out subroutine definitions in SEQC format

            Example 1:
                qasm: def subroutine(int i) -> float {...}
                seqc: var subroutine(var i) {...}

            Example 2:
                qasm: def subroutine(float f) {...}
                seqc: void subroutine(var f) {...}

        Args:
            node (ast.SubroutineDefinition): openQASM SubroutineDefinition AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        if node.name.name == "measure_func":
            # The measure_func is a special case as it is defined and is not written
            # to the output stream. Later, the call of the function will mark where
            # to replace the function call with multi-qubit seqc code.
            return
        with self.interpret_context_manager(False):
            # here we turn off the interpreter as we don't want to interpret the
            # the contents of the subroutine when it is defined (only when it is
            # called)
            self._start_line(context)
            self.stream.write("void " if node.return_type is None else "var ")
            self.visit(node.name, context)
            self._visit_sequence(
                node.arguments, context, start="(", end=")", separator=", "
            )
            self.stream.write(" {")
            self._end_line(context)
            with context.increase_scope():
                for statement in node.body:
                    self.visit(statement, context)
            self._start_line(context)
            self.stream.write("}")
            self._end_line(context)

    def visit_QuantumArgument(
        self, node: ast.QuantumArgument, context: PrinterState
    ) -> None:
        raise self.compile_out(node)

    @_maybe_annotated
    def visit_BreakStatement(
        self, node: ast.BreakStatement, context: PrinterState
    ) -> None:
        raise SEQCPrinterError(ErrorCode.NO_SEQC_STATEMENT, "no 'break' statement")

    @_maybe_annotated
    def visit_ContinueStatement(
        self, node: ast.ContinueStatement, context: PrinterState
    ) -> None:
        raise SEQCPrinterError(ErrorCode.NO_SEQC_STATEMENT, "no 'continue' statement")

    @_maybe_annotated
    def visit_EndStatement(self, node: ast.EndStatement, context: PrinterState) -> None:
        raise SEQCPrinterError(ErrorCode.NO_SEQC_STATEMENT, "no 'end' statement")

    @_maybe_annotated
    def visit_WhileLoop(self, node: ast.WhileLoop, context: PrinterState) -> None:
        """
        WhileLoop node visitor:
            Prints out a while loop in SEQC format (which happens to be identical to
            openQASM format) All the statements in the block of the while loop are
            visited

            Example:
                qasm:
                    while (int i < 10) {...; i=i+1;}
                ->
                seqc:
                    while (cvar i < 10) {...; i=i+1;}

        Args:
            node (ast.WhileLoop): openQASM WhileLoop AST node
            context (PrinterState): state of the printer (e.g. indentation)
        """
        self._end_line(context)
        self._start_line(context)
        self.stream.write("while (")
        self.visit(node.while_condition, context)
        self.stream.write(") {")
        self._end_line(context)
        with context.increase_scope():
            for statement in node.block:
                self.visit(statement, context)
        self._start_line(context)
        self.stream.write("}")
        self._end_line(context)
        self._end_line(context)

    @_maybe_annotated
    def visit_ForInLoop(self, node: ast.ForInLoop, context: PrinterState) -> None:
        """
        ForInLoop node visitor:
            openQASM used a type of for loop called ForInLoop (think python like),
            SEQC uses a 'traditional' for loop. This node translates between the two
            in limited cases. Specifically if the SET the ForInLoop iterates over is
            defined using a RANGE. Defining the SET using a DiscreteSet is not supported

            Example 1 (supported):
                qasm: for int i in [0:2:10] {...}
                ->
                seqc: cvar i;
                      for( i = 0; i < 10; i = i + 2 ) {...}

            Example 2 (not supported):
                qasm: for int j in {1, 2, 3} {...}
                ->
                SEQCPrinterError

            Further reading:

        Args:
            node (ast.ForInLoop): openQASM ForInLoop AST node
            context (PrinterState): state of the printer (e.g. indentation)

        Raises:
            SEQCPrinterError: ErrorCode.UNHANDLED
                If the SET iterated over by the ForInLoop is incorrectly defined or not
                created using a RangeDefinition
        """

        self._end_line(context)
        self._start_line(context)
        stack_obj = StackAnalyzer(skip_calls=["ones"])
        stack_obj.visit(node)
        self.constant_for_loops = stack_obj.constant_for_loops
        loop_var_type = "cvar " if self.constant_for_loops else "var "
        self.stream.write(loop_var_type)
        # todo need to distinquse between compile and runtime execution of for loop
        self.visit(node.identifier, context)
        self._end_statement(context)
        self._start_line(context)
        self.stream.write("for ( ")
        # self.visit(node.type)
        name = node.identifier.name

        curr_nesting = self.call_stack.peek().nesting_level
        activation_record = ActivationRecord(
            name="for loop", ar_type=ARType.LOOP, nesting_level=curr_nesting + 1
        )
        with self.ar_context_manager(activation_record):
            match node.set_declaration:
                case ast.RangeDefinition():
                    self.stream.write(f"{name} = ")
                    match node.set_declaration.start:
                        case (
                            ast.IntegerLiteral()
                            | ast.Identifier()
                            | ast.IndexExpression()
                        ):
                            self.visit(node.set_declaration.start)
                            activation_record[name] = self.interpreter.visit(
                                node.set_declaration.start
                            )
                        case None:
                            self.stream.write("0")
                            activation_record[name] = 0
                        case _:
                            raise SEQCPrinterError(
                                ErrorCode.UNHANDLED,
                                f"unsupported set declaration in for loop: \
                                    {node.set_declaration}",
                            )
                    self.stream.write(f"; {name} < ")
                    match node.set_declaration.end:
                        case (
                            ast.IntegerLiteral()
                            | ast.Identifier()
                            | ast.IndexExpression()
                        ):
                            self.visit(node.set_declaration.end)
                        case _:
                            raise SEQCPrinterError(
                                ErrorCode.UNHANDLED,
                                f"unsupported set declaration in for loop: \
                                    {node.set_declaration}",
                            )
                    self.stream.write(f"; {name} = {name} + ")
                    match node.set_declaration.step:
                        case (
                            ast.IntegerLiteral()
                            | ast.Identifier()
                            | ast.IndexExpression()
                        ):
                            self.visit(node.set_declaration.step)
                        case None:
                            self.stream.write("1")
                        case _:
                            raise SEQCPrinterError(
                                ErrorCode.UNHANDLED,
                                f"unsupported set declaration in for loop: \
                                    {node.set_declaration}",
                            )
                case _:
                    raise SEQCPrinterError(
                        ErrorCode.UNHANDLED,
                        f"unsupported set declaration in for loop: \
                        {node.set_declaration}",
                    )

            self.stream.write(" ) {")
            self._end_line(context)
            with context.increase_scope():
                with self.interpret_context_manager(False):
                    # here we turn off the interpreter as interpreting the contents of
                    # of the for loop can be very time consuming, while a program can
                    # be written that would require this, it is not a common use case
                    # and should be avoided / considered carefully.
                    for statement in node.block:
                        self.visit(statement, context)
            self._start_line(context)
            self.stream.write("}")
            self._end_line(context)
            self._end_line(context)

    @_visit_interpreter
    @_maybe_annotated
    def visit_DelayInstruction(
        self, node: ast.DelayInstruction, context: PrinterState
    ) -> None:
        """
        DelayInstruction node visitor:
            Prints delay instruction as a playZero statement

            Example:
                qasm: delay[10] $1;
                ->
                seqc: playZero(10);

        Args:
            node (ast.DelayInstruction): openQASM DelayInstruction AST node
            context (PrinterState): state of printer (e.g. indentation)
        """
        self._start_line(context)
        self.stream.write("playZero(")
        self.visit(node.duration, context)
        self.stream.write(")")
        self._end_statement(context)

    def _play_hold(self, node: ast.Expression, context: PrinterState) -> None:
        """
        Writes a playHold statement to the stream, the node is an expression for the
        duration of the hold. the playHold statement holds the output of the
        AWG/Generator at the last value it was set to.

        Args:
            node (ast.Expression):
                An expression that evaluates to the duration of the hold
            context (PrinterState):
                state of the printer (e.g. indentation)
        """
        self._start_line(context)
        self.stream.write("playHold(")
        self.visit(node, context)
        self.stream.write(")")
        self._end_statement(context)

    @_maybe_annotated
    def visit_Box(self, node: ast.Box, context: PrinterState) -> None:
        """
        Box node visitor:
            visits all the statements in the Box, (The box has special meaning in terms
            of qasm to qasm compilation but we assume that this optimisation is done
            by the time we convert the qasm code to seqc code.

            Example 1 (supported):
                qasm:
                    box {
                        cal_stmt_1;
                        cal_stmt_2;
                    }
                ->
                seqc:
                    cal_stmt_1;
                    cal_stmt_2;

            Currently having boxes with duration is not supported

            Example 2 (unsupported):
                qasm: box[100ns] {}
                ->
                SEQCPrinterError

        Args:
            node (ast.Box): openQASM Box AST node
            context (PrinterState): state of printer (e.g. indentation)

        Raises:
            SEQCPrinterError: ErrorCode.COMPILE_OUT
                Specific duration of boxes should be handled during prior compilation
                steps.
        """
        self._start_line(context)
        if node.duration is not None:
            raise self.compile_out(node)
        for statement in node.body:
            self.visit(statement, context)
        self._end_line(context)

    def visit_DurationOf(self, node: ast.DurationOf, context: PrinterState) -> None:
        raise self.compile_out(node)

    def visit_SizeOf(self, node: ast.SizeOf, context: PrinterState) -> None:
        raise self.compile_out(node)

    @_visit_interpreter
    @_maybe_annotated
    def visit_AliasStatement(
        self, node: ast.AliasStatement, context: PrinterState
    ) -> None:
        # todo doctring
        match node:
            case ast.AliasStatement(
                ast.Identifier(alias),
                ast.IndexExpression(
                    ast.Identifier(name),
                    [
                        ast.RangeDefinition(
                            ast.IntegerLiteral(start), ast.IntegerLiteral(end), None
                        )
                    ],
                ),
            ):
                self._start_line(context)
                self.stream.write(f"wave {alias} = cut({name}, {start}, {end})")
                self._end_statement(context)
            case ast.AliasStatement(target=ast.Identifier(), value=ast.Concatenation()):
                self._start_line(context)
                self.stream.write("wave ")
                self.visit(node.target)
                self.stream.write(" = ")
                self.visit(node.value)
                self._end_statement(context)
            case _:
                raise self.compile_out(node)

    @_visit_interpreter
    @_maybe_annotated
    def visit_ClassicalAssignment(
        self, node: ast.ClassicalAssignment, context: PrinterState
    ) -> None:
        """
        ClassicalAssignment node visitor:
            prints a classical assignment

            Example:
                qasm: a = 1;
                seqc: a = 1;

                qasm: b = 2 + 3;
                seqc: b = 2 + 3;

                qasm: c = a - b:
                seqc: c = a - b;

        Args:
            node (ast.ClassicalAssignment): openQASM ClassicalAssignment AST node
            context (PrinterState): state of printer (e.g. indentation)
        """
        match node.rvalue:
            case ast.FunctionCall(name=ast.Identifier("measure_func")):
                self.multi_measure_bit = node.lvalue
                self.visit(node.rvalue, context)
            case _:
                self._start_line(context)
                self.visit(node.lvalue, context)
                self.stream.write(f" {node.op.name} ")
                self.visit(node.rvalue, context)
                self._end_statement(context)

    def visit_Annotation(self, node: ast.Annotation, context: PrinterState) -> None:
        raise Warning("Annotations are not supported, this will not do anything")

    def visit_Pragma(self, node: ast.Pragma, context: PrinterState) -> None:
        raise Warning("Pragmas are not supported, this will not do anything")

    @_visit_interpreter
    def visit_WaveformType(self, node: ast.WaveformType, context: PrinterState) -> None:
        self.stream.write("wave")

    @_visit_interpreter
    def visit_FunctionCall(self, node: ast.FunctionCall, context: PrinterState) -> None:
        """
        FunctionCall node visitor:
            prints function calls to seqc code, 'play' function calls are translated
            to 'playWave' function calls

        Args:
            node (ast.FunctionCall): openQASM FunctionCall AST node
            context (PrinterState): state of printer (e.g. indentation)
        """
        match node:
            case ast.FunctionCall(name=ast.Identifier("play")):
                self.visit_play(node, context)
            case ast.FunctionCall(
                name=ast.Identifier("set_phase"),
                arguments=[ast.Identifier(frame_name), _],
            ):
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().set_phase(node, self, context)
            case ast.FunctionCall(
                name=ast.Identifier("shift_phase"),
                arguments=[ast.Identifier(frame_name), _],
            ):
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().shift_phase(node, self, context)
            case ast.FunctionCall(
                name=ast.Identifier("set_frequency"),
                arguments=[ast.Identifier(frame_name), _],
            ):
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().set_frequency(node, self, context)
            case ast.FunctionCall(
                name=ast.Identifier("shift_frequency"),
                arguments=[ast.Identifier(frame_name), _],
            ):
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().shift_frequency(node, self, context)
            case ast.FunctionCall(
                name=ast.Identifier("capture_v3"),
                arguments=[ast.Identifier(frame_name), ast.Identifier(capture_time)],
            ):
                capture_time = self.call_stack.get(capture_time)
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().capture_v3(node, self, context)
                # todo refactor this monster
                self.core = SHFQACore(
                    channel=frame.port.core.index,
                    spectra={
                        1: SHFQACore.SPECTRA(
                            envelope_wfm=sample_waveform(
                                ast.FunctionCall(
                                    ast.Identifier("ones"),
                                    arguments=[ast.IntegerLiteral(capture_time)],
                                )
                            ),
                            integration_time=capture_time,
                        )
                    },
                    mode=Mode.SPECTROSCOPY,
                    points_to_record=prod(self.sig.steps),
                    num_averages=self.sig.shots,
                    enable_scope=True,
                    average_shots=self.average_shots,
                )
            case ast.FunctionCall(
                name=ast.Identifier("capture_v1_spectrum"),
                arguments=[ast.Identifier(frame_name), ast.Identifier(capture_time)],
            ):
                capture_time = self.call_stack.get(capture_time)
                frame: Frame = self.call_stack.get(frame_name)
                frame.port.core.obj().capture_v3(node, self, context)
                # todo refactor this monster
                self.core = SHFQACore(
                    channel=frame.port.core.index,
                    spectra={
                        1: SHFQACore.SPECTRA(
                            envelope_wfm=sample_waveform(
                                ast.FunctionCall(
                                    ast.Identifier("ones"),
                                    arguments=[ast.IntegerLiteral(capture_time)],
                                )
                            ),
                            integration_time=capture_time,
                        )
                    },
                    mode=Mode.SPECTROSCOPY,
                    points_to_record=prod(self.sig.steps),
                    num_averages=self.sig.shots,
                    average_shots=self.average_shots,
                )
            case ast.FunctionCall(name=ast.Identifier("measure_func")):
                # TODO: AQC-216 PQSC Registers
                args = [self.interpreter.visit(arg) for arg in node.arguments]
                qubits = args[0]
                num_qubits = len(qubits)
                assert num_qubits == args[1]
                if num_qubits > 16:
                    raise SEQCPrinterError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"Cannot simultaneously measure more than 16 qubits: {node}",
                    )
                if self.meas_delay is not None:
                    self._start_line(context)
                    self.stream.write(
                        f"play{'Zero' if isinstance(self.core, SHFQACore) else 'Hold'}"
                        f"({self.meas_delay})"
                    )
                    self._end_statement(context)
                if isinstance(self.core, SHFQACore):
                    self._start_line(context)
                    self.stream.write("startQA(")
                    gen_str = " | ".join([f"QA_GEN_{q[1]}" for q in qubits])
                    int_str = " | ".join([f"QA_INT_{q[1]}" for q in qubits])
                    self.stream.write(f"{gen_str}, {int_str}, true, 0x0, 0b0)")
                    self._end_statement(context)
                    if self.multi_measure_bit is not None:
                        self._start_line(context)
                        mbit_name = self.multi_measure_bit.name
                        self.stream.write(f"{mbit_name} = getZSyncData(ZSYNC_DATA_RAW)")
                        self._end_statement(context)
            case ast.FunctionCall(name=ast.Identifier("assignWaveIndex")):
                match node.arguments[0]:
                    case ast.FunctionCall(name=ast.Identifier("placeholder")):
                        wave_length = self.interpreter.visit(
                            node.arguments[0].arguments[0]
                        )
                        wave_ind = self.interpreter.visit(node.arguments[1])
                        self._start_line(context)
                        self.stream.write(
                            f"assignWaveIndex(placeholder({wave_length}), {wave_ind})"
                        )
                        self._end_statement(context)
            case _:
                super().visit_FunctionCall(node, context)

    def visit_play(self, node: ast.FunctionCall, context: PrinterState) -> None:
        """
        FunctionCall node visitor. Handles 'play' calls by converting the frame
        the play function is applied to to the approprated channel(s) on an ZI AWG
        Core.

        If the waveform is a 'ones' waveform and its duration is greater than
        128 samples, the play command is split into two parts
        i)
            the first part plays the 'ones' waveform for the shortest possible time
            (16 samples)
        ii)
            the second part executes a 'playHold' command for the remainder of the time
            (hold time = total time - 16 samples)

        # ToDo how long does it take to execute a playHold command on the ZI AWG Cores?
        # what if the total time is shorter than execution of playWave + playHold?

        Args:
            node (ast.FunctionCall): 'play' FunctionCall node to visit
            context (PrinterState): state of the printer stream (e.g. indentation)

        Raises:
            SEQCPrinterError:
                ErrorCode.UNHANDLED
                If the node does not match the expected format/structure
        """

        def _play_frame(frame: Frame, wfm_node: ast.Expression) -> None:
            if frame.port.core.type == CoreType.HD:
                channel = frame.port.core.channels[0]
                frame.port.core.obj().play(wfm_node, self, context, channel)
            else:
                frame.port.core.obj().play(wfm_node, self, context)

        def _loop_parameters(
            duration_arg: ast.Expression,
        ) -> Optional[tuple[ActivationRecord, str, float]]:
            # get all activation records for 'for loops' in the call stack
            records = [
                record
                for record in self.call_stack._records
                if record.name == "for loop"
            ]
            duration = self.interpreter.visit(duration_arg)
            for record in records:
                loop_var = next(iter(record.members))
                loop_value = record[loop_var]
                # vary each loop variable by 1 and check if the duration changes
                record[loop_var] = loop_value + 1
                new_duration = self.interpreter.visit(duration_arg)
                record[loop_var] = loop_value
                if new_duration != duration:
                    return record, loop_var, loop_value

        new_node = CopyTransformer().visit(node)
        match new_node:
            case ast.FunctionCall(
                name=ast.Identifier("play"),
                arguments=[ast.Identifier(frame_name), wfm_node],
            ):
                frame: Frame = self.call_stack.get(frame_name)
                match wfm_node:
                    case ast.FunctionCall(
                        ast.Identifier("ones"), arguments=args
                    ) | ast.BinaryExpression(
                        lhs=ast.FunctionCall(ast.Identifier("ones"), arguments=args)
                    ) | ast.BinaryExpression(
                        rhs=ast.FunctionCall(ast.Identifier("ones"), arguments=args)
                    ):
                        try:
                            duration = self.interpreter.visit(args[0])
                        except SemanticError:
                            # if the duration is not a constant assume 64 samples
                            # or longer to force the use of playHold
                            duration = 64
                        if duration < 64:  # this parameter may need adjustment
                            l_params = _loop_parameters(args[0])
                            if l_params is None:
                                _play_frame(frame, wfm_node)
                                return
                            record, loop_var, loop_value = l_params
                            args[0] = ast.DurationLiteral(duration, "dt")
                            new_statement = ast.BranchingStatement(
                                condition=ast.BinaryExpression(
                                    op=ast.BinaryOperator[">"],
                                    lhs=ast.Identifier(loop_var),
                                    rhs=ast.IntegerLiteral(loop_value),
                                ),
                                if_block=[node],
                                else_block=[new_node] if duration > 0 else [],
                            )
                            record[loop_var] = loop_value + 1
                            self.visit(new_statement, context)
                            record[loop_var] = loop_value
                        else:
                            hold_time = ast.BinaryExpression(
                                ast.BinaryOperator["-"], args[0], ast.IntegerLiteral(32)
                            )
                            args[0] = ast.DurationLiteral(32, "dt")
                            _play_frame(frame, wfm_node)
                            self._play_hold(hold_time, context)
                    case ast.FunctionCall(
                        name=ast.Identifier(name="executeTableEntry"),
                        arguments=[ct_index_node],
                    ):
                        self._start_line(context)
                        self.stream.write("executeTableEntry(")
                        self.visit(ct_index_node)
                        self.stream.write(")")
                        self._end_statement(context)
                    case _:
                        _play_frame(frame, wfm_node)
            case _:
                raise SEQCPrinterError(
                    ErrorCode.UNHANDLED, f"format of play node: {node}"
                )

    @_visit_interpreter
    def visit_BooleanLiteral(self, node: ast.BooleanLiteral, context: PrinterState):
        super().visit_BooleanLiteral(node, context)

    @_visit_interpreter
    def visit_FloatLiteral(self, node: ast.FloatLiteral, context: PrinterState):
        super().visit_FloatLiteral(node, context)

    @_visit_interpreter
    def visit_IntegerLiteral(self, node: ast.IntegerLiteral, context: PrinterState):
        super().visit_IntegerLiteral(node, context)

    @_visit_interpreter
    def visit_BinaryExpression(self, node: ast.BinaryExpression, context: PrinterState):
        super().visit_BinaryExpression(node, context)

    @_visit_interpreter
    def visit_UnaryExpression(self, node: ast.UnaryExpression, context: PrinterState):
        super().visit_UnaryExpression(node, context)

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
        LOGGER.debug("ENTER: ACTIVATION RECORD %s", activation_record.name)
        LOGGER.debug(self.call_stack)
        try:
            yield
        finally:
            LOGGER.debug("LEAVE: ACTIVATION RECORD %s", activation_record.name)
            LOGGER.debug(self.call_stack)
            self.call_stack.pop()

    @contextmanager
    def interpret_context_manager(self, interpret: bool):
        """
        Context manager for interpreter, used to turn on/off interpreter
        """
        prev_interpret = self.interpret
        self.interpret = interpret
        try:
            yield
        finally:
            self.interpret = prev_interpret

    def compile_out(self, node: ast.QASMNode) -> SEQCPrinterError:
        """
        Method for standartizing raising errors when SEQCPrinter is asked to visit
        nodes that should be compiled out of the AST before the SEQCPrinter is used.

        Args:
            node (ast.QASMNode):
                Should have been removed from the AST by prior compilation steps

        Returns:
            SEQCPrinterError: should be raised immediately after this method returns
        """
        return SEQCPrinterError(ErrorCode.COMPILE_OUT, f"{node}")

    @classmethod
    def make_string_legal(cls, input_str: str) -> str:
        """
        method for making strings 'legal' in seqc code.

        currenlty replaces '$' with '_'

        '$' are not allowed in seqc code but used in qasm code to represent physical
        qubits.

        Args:
            input_str (str): string to make seqc 'legal'

        Returns:
            str: 'legal' seqc string
        """
        return input_str.replace("$", "_")

    def settings(self) -> list[tuple[str, Any]]:
        """
        Returns instrument settings generated by the printer while
        visiting the AST

        Returns:
            list[tuple[str, Any]]:
                list of instrument settings, each setting is a tuple of string and value
                where the string represents the ZI node tree path to the setting and the
                value is the value of the setting
        """
        return self.core.settings() if self.core else None

    def wfm_mapping(self) -> dict:
        """
        Returns waveform mapping generated by the printer while
        visiting the AST

        Returns:
            dict:
                dictionary of waveform mapping, each key maps a instrument specific
                way to assign waveforms to a waveform name
        """
        return self.wfm_indices
