"""
The main compiler class for the shipyard.

This class serves as the entry point for most users of the compiler.

Usage:
    program_path = Path("path/to/qasm/program.qasm")
    setup_path = Path("path/to/setup/configuration/file.json")
    compiler = Compiler(program_path, setup_path)
    compiler.compile()

    # print out compiled programs:
    for core in compiler.setup.cores():
        print(compiler.split_compiled[core])
"""
import io
from functools import lru_cache
from pathlib import Path
from typing import Any

from numpy import ndarray
from openpulse import ast, parse
from openpulse.printer import dumps as qasm_dumps
from zhinst.toolkit import CommandTable

from .logger import LOGGER
from .passes import (
    CoreSplitter,
    DetermineMaxDelay,
    DurationTransformer,
    IncludeAnalyzer,
    IncludeWaveforms,
    InsertCTWaveforms,
    RemoveUnused,
    ResolveIODeclaration,
    SemanticAnalyzer,
    ShotsExtractor,
    TimingConstraints,
    ports_for_core,
)
from .printers import PulseVisualizer, SEQCPrinter, external_zi_function_dict
from .setup import Setup
from .utilities import LazyRepr
from .visitors import CopyTransformer


class Compiler:
    version = "0.1.1"
    """
    Compiler to compile openQASM programs to target programs for different AWG Cores.
    Currently supports compilation to ZI SEQC cores.

    Args:
        program_path (Path):
            Path object pointing to a qasm program file.
        setup (Setup | Path):
            Path object pointing to a experiment setup json file.
        frames_from_setup (bool, optional):
            If True, frame definitions and port declarations are generated from setup.
            If False, frame definitions and port declarations should be written
            explicitly in the qasm program.
            Defaults to False to preserve original behavior.
    """

    def __init__(
        self,
        program_path: Path,
        setup: Setup | Path,
        frames_from_setup: bool = False,
    ) -> None:
        self.program_path = program_path
        self.program = CopyTransformer().visit_Program(self.load_program(program_path))
        setup = setup if isinstance(setup, Setup) else Setup.from_file(setup)
        if frames_from_setup:
            self._frames_from_setup(setup)
        self.setup = setup.to_internal()
        self.split_programs: dict[tuple[str, int, str], ast.Program] = {}
        self.split_compiled: dict[tuple[str, int, str], str] = {}
        self.core_settings: dict[tuple[str, int, str], list[tuple[str], Any]] = {}
        self.wfm_mapping: dict[tuple[str, int, str], dict[int, str]] = {}

    @staticmethod
    @lru_cache()
    def load_program(path: Path) -> ast.Program:
        """
        Loads a qasm program as an AST from a file

        Args:
            path (Path): path to the qasm program file

        Returns:
            ast.Program: qasm program as an AST
        """
        with open(path, encoding="utf_8") as qasm_file:
            qasm_code = qasm_file.read()
        return parse(qasm_code)

    def compile(
        self,
        inputs: dict = None,
        printer_kwargs: dict = None,
        waveforms: dict[str, ndarray] | None = None,
        command_tables: dict[tuple[str, int, str], CommandTable] | None = None,
    ):
        """
        Compile a single openQASM program into multiple programs for each
        AWG core in the setup

        Args:
            inputs (dict, optional):
                Dictionary of input values for the program. Defaults to None.
                Used to resolve input declarations in the program.
            printer_kwargs (dict, optional):
                Dictionary of keyword arguments to pass to the printer.
                See the printer documentation for more details.
        """
        ResolveIODeclaration(inputs).visit(self.program)
        IncludeAnalyzer(self.program_path).visit(self.program)
        IncludeWaveforms(waveforms).visit(self.program)
        SemanticAnalyzer().visit(self.program)
        DurationTransformer().visit(self.program)
        TimingConstraints(self.setup, external_zi_function_dict()).visit(self.program)
        max_delay_obj = DetermineMaxDelay(
            self.program, self.setup, external_zi_function_dict()
        )
        extractor_obj = ShotsExtractor()
        extractor_obj.visit(self.program)
        signature = extractor_obj.create_signature()
        printer_kwargs = printer_kwargs or {}
        for instr, core_index, core_type in self.setup.cores():
            if command_tables:
                command_table = command_tables.get((instr, core_index, core_type))
            else:
                command_table = None
            ports = ports_for_core(self.setup, instr, core_index)
            split_program = CoreSplitter(ports).visit_Program(self.program)
            LOGGER.debug(
                "Split Program before removing unused, core: (%s, %i, %s):",
                instr,
                core_index,
                core_type,
            )
            LOGGER.debug("\n%s", LazyRepr(qasm_dumps, [split_program]))
            for repetition in ["1st pass", "2nd pass"]:
                RemoveUnused(split_program)
                LOGGER.debug(
                    "Split Program after removing unused (%s), core: (%s, %i, %s):",
                    repetition,
                    instr,
                    core_index,
                    core_type,
                )
                LOGGER.debug("\n%s", LazyRepr(qasm_dumps, [split_program]))
            self.split_programs[(instr, core_index, core_type)] = split_program
            # todo dynamically choose printer based on instrument type
            InsertCTWaveforms(command_table).visit(split_program)
            printer = SEQCPrinter(
                io.StringIO(),
                self.setup,
                signature,
                max_delay_obj.result(),
                **printer_kwargs
            )
            printer.visit(split_program)
            compiled = printer.stream.getvalue()
            LOGGER.debug(
                "Compiled Program, core: core: (%s, %i, %s):",
                instr,
                core_index,
                core_type,
            )
            LOGGER.debug("\n%s", compiled)
            self.split_compiled[(instr, core_index, core_type)] = compiled
            self.core_settings[(instr, core_index, core_type)] = printer.settings()
            self.wfm_mapping[(instr, core_index, core_type)] = printer.wfm_mapping()

    @lru_cache()
    @staticmethod
    def cached_compile(
        program_path: Path,
        setup: Setup | Path,
        inputs: dict | None = None,
        printer_kwargs: dict | None = None,
        frames_from_setup: bool = False,
    ) -> "Compiler":
        """Method to compile a program and cache the result.

        Args:
            program_path (Path):
                path to the qasm program file
            setup (Setup | Path):
                path to the laboratory setup file
            inputs (dict | None, optional):
                dictionary of input values for the program,
                used to resolve input declarations. Defaults to None.
            printer_kwargs (dict | None, optional):
                Dictionary of kwarg arguments to pass to the printer,
                see printer documentation for details. Defaults to None.
            frames_from_setup (bool, optional):
                If True, frame definitions and port declarations are generated from
                setup.
                If False, frame definitions and port declarations should be written
                explicitly in the qasm program.
                Defaults to False to preserve original behavior.

        Returns:
            Compiler: cached compiler object
        """
        compiler = Compiler(program_path, setup, frames_from_setup)
        compiler.compile(inputs, printer_kwargs)
        return compiler

    def _frames_from_setup(self, setup: Setup) -> None:
        """
        inserts a calibrationStatement after the defcalgrammar statement, the
        calibrationStatement created from the setup file

        Args:
            setup_path (Path): path to the setup file

        Raises:
            ValueError: if no calibration grammar is defined in the program
            ValueError: if the calibration grammar is not openpulse
        """
        # make sure defcalgrammar has been define before inserting setup
        for i, statement in enumerate(self.program.statements):
            if isinstance(statement, ast.CalibrationGrammarDeclaration):
                break
        else:
            raise ValueError(
                "No calibration grammar defined in program, cannot insert setup."
            )
        # make sure defcalgrammar is openpulse
        if statement.name != "openpulse":
            raise ValueError("calibration grammar be 'openpulse', ")
        # insert cal from setup after defcalgrammar statement
        self.program.statements.insert(i + 1, setup.get_qasm())


def visualize_pulses(qasm_path, setup_path, input_dict=None):  # pragma: no cover
    qasm_ast = Compiler(qasm_path, setup_path).load_program(qasm_path)
    ResolveIODeclaration(input_dict).visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    setup = Setup.from_json(setup_path).to_internal()
    pv = PulseVisualizer(setup, external_zi_function_dict())
    pv.plot_flag = True
    pv.visit(qasm_ast)
