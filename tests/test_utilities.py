import io
import tempfile
from pathlib import Path

import numpy as np
import pytest
from zhinst.core import compile_seqc

from shipyard.compiler import Compiler
from shipyard.compiler_error import SEQCPrinterError
from shipyard.passes import SemanticAnalyzer
from shipyard.printers.zi.seqcprinter import SEQCPrinter
from shipyard.setup.internal import SetupInternal
from shipyard.utilities import qasm_from_array


def compile_seqc_code(seqc_code: str):
    compile_seqc(seqc_code, "SHFSG4", [""], index=0, sequencer="SG")
    compile_seqc(seqc_code, "HDAWG8", ["PC"], index=0, samplerate=2.4e9)


def fixture_seqc_printer(basic_setup: SetupInternal) -> SEQCPrinter:
    return SEQCPrinter(io.StringIO(), basic_setup)


def test_qasm_from_array():
    """
    Test three arrays (complex, float, and int) and make sure the QASM string is correct
    """
    q1 = "OPENQASM 3.0;\narray[complex[float[64]], 5] waveform_0 = {0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im};\n"
    q2 = "OPENQASM 3.0;\narray[int[64], 5] waveform_0 = {0, 1, 2, 3, 4};\narray[float[64], 6] waveform_1 = {5.0, 6.0, 7.0, 8.0, 9.0, 10.0};\n"
    q1_named = "OPENQASM 3.0;\narray[int[64], 5] myarr1 = {0, 1, 2, 3, 4};\n"
    q2_named = "OPENQASM 3.0;\narray[int[32], 5] myarr1 = {0, 1, 2, 3, 4};\narray[complex[float[64]], 5] myarr2 = {0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im, 0.0 + 0.0im};\n"
    int_arr = np.array([0, 1, 2, 3, 4])
    float_arr = np.array([5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    comp_arr = np.zeros((5,), dtype=np.complex_)
    int_32_arr = np.array([0, 1, 2, 3, 4], dtype=np.int32)

    qasm_str1 = qasm_from_array(comp_arr)
    qasm_str2 = qasm_from_array([int_arr, float_arr])
    assert qasm_str1 == q1
    assert qasm_str2 == q2

    qasm_str1_named = qasm_from_array(int_arr, "myarr1")
    qasm_str2_named = qasm_from_array([int_32_arr, comp_arr], ["myarr1", "myarr2"])
    assert qasm_str1_named == q1_named
    assert qasm_str2_named == q2_named


def test_qasm_from_array_errors():
    """
    Test that errors are raised correctly, when number of arrays and names are not the
    same and when the array type is not supported
    """
    int_arr = np.array([0, 1, 2, 3, 4])
    float_arr = np.array([5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    comp_arr = np.zeros((5,), dtype=np.complex_)
    error_arr = np.array([True, True, True])
    with pytest.raises(AssertionError):
        qasm_from_array([int_arr, float_arr, comp_arr], ["my_arr"])
    with pytest.raises(Exception):
        qasm_from_array(error_arr)


def test_qasm_from_array_compilation():
    """
    Test that the QASM strings generated from arrays can be compiled correctly
    """
    setup_path = Path(__file__).parent / "setups/basic.json"
    seqc_printer = fixture_seqc_printer(setup_path)
    int_arr = np.array([0, 1, 2, 3, 4])
    float_arr = np.array(
        [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    )  # array length does not have to be the same
    comp_arr = np.zeros((5,), dtype=np.complex_)

    qasm_str1 = qasm_from_array([int_arr, float_arr])
    qasm_str2 = qasm_from_array(comp_arr)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".qasm", delete=False
    ) as temp_file:
        temp_file.write(qasm_str1)
        temp_file.flush()
        compiler = Compiler(temp_file.name, setup_path)

        qasm_ast = compiler.load_program(temp_file.name)
        semantic_analyzer = SemanticAnalyzer()
        semantic_analyzer.visit(qasm_ast)

        seqc_printer.visit(qasm_ast)
        compile_seqc_code(seqc_printer.stream.getvalue())
    temp_file.close()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".qasm", delete=False
    ) as temp_file:
        temp_file.write(qasm_str2)
        temp_file.flush()
        compiler = Compiler(temp_file.name, setup_path)

        qasm_ast = compiler.load_program(temp_file.name)
        semantic_analyzer = SemanticAnalyzer()
        semantic_analyzer.visit(qasm_ast)
        with pytest.raises(SEQCPrinterError):
            seqc_printer.visit(qasm_ast)
            compile_seqc_code(seqc_printer.stream.getvalue())
