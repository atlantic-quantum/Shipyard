from pathlib import Path

import pytest
from openpulse import ast, parse

from shipyard.compiler import Compiler
from shipyard.compiler_error import Error


def load_ast(file: str) -> ast.Program:
    path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    with open(path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()
    return parse(qasm_code)


def test_no_warnings(file="no_warnings"):
    """
    Test for no warnings in a simple program
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/basic.json"

    compiler = Compiler(qasm_path, setup_path)

    compiler.compile()


def test_simple_warnings(file="simple_warnings"):
    """
    Test for warnings in a simple program
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/basic.json"

    compiler = Compiler(qasm_path, setup_path)

    target = (
        "Error: (ErrorCode.INVALID_WAVEFORM) waveform(s)"
        " do not meet timing constraints:\n\n"
        "Waveform: w_gauss\n\t"
        "Waveform Length: 8001,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
        "Waveform: ones(52)\n\t"
        "Waveform Length: 52,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
    )
    with pytest.raises(Error) as e_info:
        compiler.compile()
    assert e_info.value.message == target


def test_complex_warnings(file="complex_warnings"):
    """
    Test for warnings for a complex play commands
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"

    compiler = Compiler(qasm_path, setup_path)
    target = (
        "Error: (ErrorCode.INVALID_WAVEFORM) waveform(s)"
        " do not meet timing constraints:\n\n"
        "Waveform: w_gauss\n\t"
        "Waveform Length: 8001,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
        "Waveform: ones(dummy_func())\n\t"
        "Waveform Length: 2401,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
    )
    with pytest.raises(Error) as e_info:
        compiler.compile()
    assert e_info.value.message == target


def test_execute_table(file="execute_table"):
    """
    Should ignore play commands of executeTableEntry commands
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"

    compiler = Compiler(qasm_path, setup_path)

    compiler.compile()


def test_for_loop(file="for_loop"):
    """
    Should ignore play commands of executeTableEntry commands
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"

    compiler = Compiler(qasm_path, setup_path)

    compiler.compile()


def test_delay(file="delay_warnings"):
    """
    Should ignore play commands of executeTableEntry commands
    """
    qasm_path = Path(__file__).parent.parent / f"qasm/timing_constraints/{file}.qasm"
    setup_path = Path(__file__).parent.parent / "setups/complex.json"

    compiler = Compiler(qasm_path, setup_path)

    target = (
        "Error: (ErrorCode.INVALID_WAVEFORM) waveform(s)"
        " do not meet timing constraints:\n\n"
        "Waveform: 0dt\n\t"
        "Waveform Length: 0,\n\t"
        "Sufficient Length: False,\n\t"
        "Correct Granularity: True\n\n"
        "Waveform: 2dt\n\t"
        "Waveform Length: 2,\n\t"
        "Sufficient Length: False,\n\t"
        "Correct Granularity: False\n\n"
        "Waveform: 34dt\n\t"
        "Waveform Length: 34,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
        "Waveform: some_dur\n\t"
        "Waveform Length: 62,\n\t"
        "Sufficient Length: True,\n\t"
        "Correct Granularity: False\n\n"
    )

    with pytest.raises(Error) as e_info:
        compiler.compile()
    assert e_info.value.message == target
