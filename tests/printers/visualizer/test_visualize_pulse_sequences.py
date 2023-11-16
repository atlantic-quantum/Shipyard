import codecs
import json
from pathlib import Path

import numpy as np
import pytest

from shipyard.awg_core.awg_core import CoreType
from shipyard.call_stack import ActivationRecord, ARType
from shipyard.compiler import Compiler
from shipyard.duration import Duration, TimeUnits
from shipyard.passes.duration_transformer import DurationTransformer
from shipyard.passes.resolve_io_declaration import ResolveIODeclaration
from shipyard.passes.semantic_analysis.semantic_analyzer import SemanticAnalyzer
from shipyard.printers.visualizer.visualize_pulse_sequence import PulseVisualizer
from shipyard.printers.zi import waveform_functions
from shipyard.setup.internal import Frame, Instrument, Port, SetupInternal

final_call_stack = {
    "nested_subroutines": {"dummy": 16},
    "complex_arrays": {
        "dummy": 4,
        "two_d": [[1, 2], [3, 4], [5, 6]],
        "my_arr": [complex(1, 0), complex(0, 1), complex(0.8, 0.6)],
        "second": [1, 2, 3, 4],
    },
}


def files() -> list[str]:
    base_path = Path(__file__).parent.parent.parent / "qasm/visualize_pulse"

    plen = len(base_path.parts)
    FILES = list(base_path.glob("**/*.qasm"))
    return [str(Path(*path.parts[plen:])) for path in FILES]


QASM_FILES = files()


def common_files() -> list[str]:
    files = []
    cut = -5
    for q_file in QASM_FILES:
        files.append(q_file[:cut])
    return files


COMMON_FILES = common_files()


@pytest.fixture(name="basic_setup")
def fixture_basic_setup() -> SetupInternal:
    json_path = Path(__file__).parent.parent.parent / "setups/interpreter.json"
    return SetupInternal.from_json(json_path)


def test_visit_ClassicalDeclaration():
    setup_path = Path(__file__).parent.parent.parent / "setups/complex.json"
    qasm_path = Path(__file__).parent.parent.parent / "qasm/interpreter/phase_freq.qasm"
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    ResolveIODeclaration().visit(qasm_ast)
    SemanticAnalyzer().visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = PulseVisualizer(
        SetupInternal.from_json(setup_path), waveform_functions.__dict__
    )
    activation_record = ActivationRecord(
        name="main", ar_type=ARType.PROGRAM, nesting_level=1
    )
    pv.call_stack.push(activation_record)
    for stmnt in qasm_ast.statements:
        pv.visit(stmnt)
    assert pv.call_stack.peek().members == {"f1": 3000.0, "f2": 4000.0, "p1": 1.0}
    assert pv.calibration_scope == {
        "dac1": Port(
            name="dac1",
            instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
            core=Port.Core(type=CoreType.HD, index=2, channels=[1]),
        ),
        "dac0": Port(
            name="dac0",
            instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
            core=Port.Core(type=CoreType.HD, index=1, channels=[1]),
        ),
        "spec_frame": Frame(
            name="spec_frame",
            port=Port(
                name="dac1",
                instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
                core=Port.Core(type=CoreType.HD, index=2, channels=[1]),
            ),
            frequency=5000.0,
            phase=2.0,
            time=Duration(time=0.0, unit=TimeUnits.dt),
        ),
        "tx_frame_0": Frame(
            name="tx_frame_0",
            port=Port(
                name="dac0",
                instrument=Instrument(name="hdawg1", type="HDAWG8", serial="DEVXXXX"),
                core=Port.Core(type=CoreType.HD, index=1, channels=[1]),
            ),
            frequency=3000.0,
            phase=1.5,
            time=Duration(time=0.0, unit=TimeUnits.dt),
        ),
    }
    assert pv.pulses == {"spec_frame": [], "tx_frame_0": []}
    assert pv.phases == {"spec_frame": [], "tx_frame_0": []}
    assert pv.frequencies == {"spec_frame": [], "tx_frame_0": []}
    pv.call_stack.pop()


@pytest.mark.parametrize("file_name", COMMON_FILES)
def test_uses_basic_setup(file_name: str, basic_setup: SetupInternal):
    setup_path = Path(__file__).parent.parent.parent / "setups/basic.json"
    qasm_path = (
        Path(__file__).parent.parent.parent / f"qasm/visualize_pulse/{file_name}.qasm"
    )
    arr_path = (
        Path(__file__).parent.parent.parent / f"qasm/visualize_pulse/{file_name}.json"
    )
    compiler = Compiler(qasm_path, setup_path)
    qasm_ast = compiler.load_program(qasm_path)
    semantic_analyzer = SemanticAnalyzer()
    semantic_analyzer.visit(qasm_ast)
    DurationTransformer().visit(qasm_ast)
    pv = PulseVisualizer(basic_setup, waveform_functions.__dict__)
    pv.visit(qasm_ast)
    for frame in pv.pulses.keys():
        pv.pulses[frame] = np.concatenate(pv.pulses[frame]).tolist()
        pv.phases[frame] = np.concatenate(pv.phases[frame]).tolist()
        pv.frequencies[frame] = np.concatenate(pv.frequencies[frame]).tolist()
    # json_list = [pv.pulses, pv.phases, pv.frequencies]
    # with open(arr_path, 'w') as f:
    #     json.dump(json_list, f)
    if file_name == "complex_values":
        assert "drive_frame" in pv.pulses.keys()
        assert "drive_frame" in pv.phases.keys()
        assert "drive_frame" in pv.frequencies.keys()
        assert isinstance(pv.pulses["drive_frame"][0], complex)
        return
    obj_text = codecs.open(arr_path, "r", encoding="utf-8").read()
    b_new = json.loads(obj_text)
    assert pv.pulses.keys() == b_new[0].keys()
    assert pv.phases.keys() == b_new[1].keys()
    assert pv.frequencies.keys() == b_new[2].keys()
    for key in pv.pulses.keys():
        assert np.allclose(b_new[0][key], pv.pulses[key])
        assert np.allclose(b_new[1][key], pv.phases[key])
        assert np.allclose(b_new[2][key], pv.frequencies[key])
