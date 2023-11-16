import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from numpy import ndarray
from openpulse.printer import dumps as qasm_dumps
from zhinst.core import compile_seqc

from shipyard import Compiler, Setup
from shipyard.setup.internal import SetupInternal
from shipyard.utilities import waveforms_to_zi


def compile_seqc_code(seqc_code: str):
    compile_seqc(seqc_code, "SHFSG4", [""], index=0, sequencer="SG")
    compile_seqc(seqc_code, "HDAWG8", ["PC"], index=0, samplerate=2.4e9)


def compile_seqc_code_qa(seqc_code: str):
    compile_seqc(seqc_code, "SHFQC", [""], index=0, sequencer="QA")
    compile_seqc(seqc_code, "SHFQA4", [""], index=0)


core_compiler_args = {
    "HD": (("HDAWG8", ["PC"]), {"index": 0, "samplerate": 2.4e9}),
    "QA": (("SHFQA4", [""]), {"index": 0}),
    "SG": (("SHFSG4", [""]), {"index": 0, "sequencer": "SG"}),
}


def test_compiler_basic():
    qasm_path = Path(__file__).parent / "qasm/basic.qasm"
    setup_path = Path(__file__).parent / "setups/basic.json"
    seqc_path = Path(__file__).parent / "seqc/basic.seqc"

    compiler = Compiler(qasm_path, setup_path)

    compiler.compile()

    assert ("hdawg1", 1, "HD") in compiler.split_compiled
    assert ("hdawg1", 1, "HD") in compiler.split_programs

    assert ("shfsg1", 1, "SG") in compiler.split_compiled
    assert ("shfsg1", 1, "SG") in compiler.split_programs

    with open(seqc_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for genrated, target in zip(
        compiler.split_compiled[("hdawg1", 1, "HD")].split("\n"), seqc_code.split("\n")
    ):
        assert genrated == target

    assert not compiler.split_compiled[("shfsg1", 1, "SG")]


TESTS = [
    "basic",
    "capture_v1",
    "capture_v2",
    "command_table",
    "complex",
    "complex_setup",
    "hd_channel_2",
    "multi_qubit_readout",
    "placeholder",
    "play_measure",
    "qubit_spectroscopy",
    "rabi_length",
    "ramsey",
    "ramsey_core_2",
    "resonator_spectroscopy",
    "resonator_spectroscopy_raw",
    "two_tone_spectroscopy",
]

warning_tests = [
    ("complex", ("hdawg1", 1, "HD")),
    ("multi_qubit_readout", ("hdawg1", 1, "HD")),
    ("ramsey", ("hdawg1", 1, "HD")),
    ("ramsey_core_2", ("hdawg1", 1, "HD")),
]


def get_cores_for_test(test):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    setup_path = folder / "setup.json"
    setup = SetupInternal.from_json(setup_path)
    cores = list(setup.cores())
    cores.sort()
    return cores


TEST_CORES = [
    (test, core, i + 1)
    for test in TESTS
    for i, core in enumerate(get_cores_for_test(test))
]


@lru_cache
def compile_files(folder: Path, average_shots: bool = True, test: str = None):
    qasm_path = folder / "source.qasm"
    setup_path = folder / "setup.json"
    frames_from_setup = True if folder.stem == "complex_setup" else False
    compiler = Compiler(qasm_path, setup_path, frames_from_setup)
    compiler.compile(printer_kwargs={"average_shots": average_shots})
    return compiler


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_files_split_program(test: str, core: tuple[str, int, str], i: int):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)

    assert core in compiler.split_programs

    print(qasm_dumps(compiler.split_programs[core]))

    qasm_split_path = folder / f"cores/core{i}.qasm"
    with open(qasm_split_path, encoding="utf_8") as qasm_file:
        qasm_code = qasm_file.read()

    for genrated, target in zip(
        qasm_dumps(compiler.split_programs[core]).split("\n"), qasm_code.split("\n")
    ):
        assert genrated == target


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_files_split_seqc(test: str, core: tuple[str, int, str], i: int):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)

    assert core in compiler.split_compiled

    print(compiler.split_compiled[core])

    seqc_split_path = folder / f"cores/core{i}.seqc"
    with open(seqc_split_path, encoding="utf_8") as seqc_file:
        seqc_code = seqc_file.read()

    for genrated, target in zip(
        compiler.split_compiled[core].split("\n"), seqc_code.split("\n")
    ):
        assert genrated == target


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_files_compile_split_seqc(test: str, core: tuple[str, int, str], i: int):
    if test in ["complex", "complex_setup"] and i in [1, 2, 3]:
        pytest.xfail()
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)

    compiler_args, compiler_kwargs = core_compiler_args[core[2]]
    compile_seqc(compiler.split_compiled[core], *compiler_args, **compiler_kwargs)


@pytest.fixture(name="qa_nodes")
def fixture_qa_nodes() -> dict[str, dict]:
    filename = Path(__file__).parent / "device_json/nodedoc_dev1234_shfqa.json"
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    # the nodes in the json file start with '/dev1234/....' remove '/dev1234'
    return {"/" + node.split("/", 2)[2]: value for node, value in data.items()}


@pytest.fixture(name="hd_nodes")
def fixture_hd_nodes() -> dict[str, dict]:
    filename = Path(__file__).parent / "device_json/nodedoc_dev1234_hdawg.json"
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    # the nodes in the json file start with '/dev1234/....' remove '/dev1234'
    return {"/" + node.split("/", 2)[2]: value for node, value in data.items()}


@pytest.fixture(name="sg_nodes")
def fixture_sg_nodes() -> dict[str, dict]:
    filename = Path(__file__).parent / "device_json/nodedoc_dev1234_shfsg.json"
    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    # the nodes in the json file start with '/dev1234/....' remove '/dev1234'
    return {"/" + node.split("/", 2)[2]: value for node, value in data.items()}


zi_types = {
    "Double": float,
    "Integer (64 bit)": int,
    "Integer (enumerated)": int,
    "ZIVectorData": ndarray,
}


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_files_compile_split_settings(
    test: str,
    core: tuple[str, int, str],
    i: int,
    qa_nodes: dict[str, dict],
    hd_nodes: dict[str, dict],
    sg_nodes: dict[str, dict],
):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)

    nodes_d = {"QA": qa_nodes, "HD": hd_nodes, "SG": sg_nodes}

    # verify that all the nodes that are generated for the core are
    #  a) valid nodes
    #  b) it is allowed to write a value of this node
    #  c) the type of the value we want to write to the node is correct
    nodes = nodes_d[core[2]]
    if compiler.core_settings[core]:
        for node, value in compiler.core_settings[core]:
            assert node.lower() in nodes.keys()
            assert "Write" in nodes[node.lower()]["Properties"]
            assert isinstance(value, zi_types[nodes[node.lower()]["Type"]])


@pytest.mark.parametrize(
    "test, instrument, core_index, core_type, core_file",
    [
        ("basic", "hdawg1", 1, "HD", 1),
        ("basic", "hdawg2", 1, "HD", 2),
        ("capture_v1", "shfqa1", 1, "QA", 1),
        ("capture_v2", "shfqa1", 1, "QA", 1),
        ("hd_channel_2", "hdawg1", 1, "HD", 1),
        ("hd_channel_2", "hdawg2", 2, "HD", 1),
        ("multi_qubit_readout", "shfqa1", 1, "QA", 1),
        ("qubit_spectroscopy", "shfsg1", 1, "SG", 3),
        ("ramsey", "shfqa1", 1, "QA", 2),
        ("ramsey_core_2", "shfqa1", 3, "QA", 2),
        ("resonator_spectroscopy_raw", "shfqa1", 1, "QA", 1),
        ("two_tone_spectroscopy", "shfsg1", 1, "SG", 2),
    ],
)
def test_ramsey_qa_settings(
    test: str, instrument: str, core_index: int, core_type: str, core_file: int
):
    core = instrument, core_index, core_type
    folder = Path(__file__).parent / f"compiler_test_files/{test}"
    compiler = compile_files(folder)
    files = {core: i + 1 for i, core in enumerate(get_cores_for_test(test))}

    settings = compiler.core_settings[core]

    settings_path = folder / f"cores/core{files[core]}.json"
    with open(settings_path, encoding="utf_8") as settings_file:
        settings_json = json.load(settings_file)
    expected_settings = [(node, value) for node, value in settings_json["settings"]]
    assert len(settings) == len(expected_settings)
    for setting, expected_setting in zip(settings, expected_settings):
        assert len(setting) == len(expected_setting) == 2
        assert setting[0] == expected_setting[0]
        if isinstance(expected_setting[1], list):
            assert len(setting[1] == len(setting[1]))
            assert np.all(setting[1] == expected_setting[1])
        else:
            assert setting[1] == expected_setting[1]


def test_resonator_spectroscopy_raw_qa_settings():
    core = "shfqa1", 1, "QA"
    folder = Path(__file__).parent / "compiler_test_files/resonator_spectroscopy_raw"
    compiler = compile_files(folder)

    settings = compiler.core_settings[core]

    settings_path = folder / "cores/core1.json"
    with open(settings_path, encoding="utf_8") as settings_file:
        settings_json = json.load(settings_file)
    expected_settings = [(node, value) for node, value in settings_json["settings"]]
    assert len(settings) == len(expected_settings)
    for setting, expected_setting in zip(settings, expected_settings):
        assert len(setting) == len(expected_setting) == 2
        assert setting[0] == expected_setting[0]
        if isinstance(expected_setting[1], list):
            assert np.all(setting[1] == expected_setting[1])
        else:
            assert setting[1] == expected_setting[1]


@pytest.mark.parametrize(
    "test, core, expected_length",
    [("ramsey", 1, 10), ("capture_v1", 1, 1), ("resonator_spectroscopy_raw", 1, 100)],
)
def test_qa_average_shots(test: str, core: int, expected_length: int):
    compiler_core = "shfqa1", core, "QA"
    folder = Path(__file__).parent / f"compiler_test_files/{test}"

    compiler = compile_files(folder, average_shots=False)

    settings = compiler.core_settings[compiler_core]

    for setting in settings:
        if "/RESULT/LENGTH" in setting[0]:
            assert setting[1] == expected_length
        if "/RESULT/AVERAGES" in setting[0]:
            assert setting[1] == 1


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_cached_compile(test: str, core: tuple[str, int, str], i: int):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)
    frames_from_setup = True if folder.stem == "complex_setup" else False
    cached_compiler = Compiler.cached_compile(
        folder / "source.qasm",
        folder / "setup.json",
        frames_from_setup=frames_from_setup,
    )

    for compiled, cached in zip(
        qasm_dumps(compiler.split_programs[core]).split("\n"),
        qasm_dumps(cached_compiler.split_programs[core]).split("\n"),
    ):
        assert compiled == cached


@pytest.mark.parametrize("test, core, i", TEST_CORES)
def test_cached_compile_setup(test: str, core: tuple[str, int, str], i: int):
    folder = Path(__file__).parent / "compiler_test_files/" / test
    compiler = compile_files(folder)
    frames_from_setup = True if folder.stem == "complex_setup" else False
    setup = Setup.from_file(folder / "setup.json")
    cached_compiler = Compiler.cached_compile(
        folder / "source.qasm",
        setup,
        frames_from_setup=frames_from_setup,
    )

    for compiled, cached in zip(
        qasm_dumps(compiler.split_programs[core]).split("\n"),
        qasm_dumps(cached_compiler.split_programs[core]).split("\n"),
    ):
        assert compiled == cached


def test_supply_waveforms():
    folder = Path(__file__).parent / "compiler_test_files/supply_waveforms"
    qasm_path = folder / "source.qasm"
    setup_path = folder / "setup.json"
    compiler = Compiler(qasm_path, setup_path)
    waveforms = {
        "supplied_waveform1": np.ones(112),
        "supplied_waveform2": np.zeros(112),
    }
    compiler.compile(waveforms=waveforms)

    for i, core in enumerate(get_cores_for_test("supply_waveforms")):
        qasm_split_path = folder / f"cores/core{i+1}.qasm"
        with open(qasm_split_path, encoding="utf_8") as qasm_file:
            qasm_code = qasm_file.read()

        for genrated, target in zip(
            qasm_dumps(compiler.split_programs[core]).split("\n"), qasm_code.split("\n")
        ):
            assert genrated == target

        seqc_split_path = folder / f"cores/core{i+1}.seqc"
        with open(seqc_split_path, encoding="utf_8") as seqc_file:
            seqc_code = seqc_file.read()

        for genrated, target in zip(
            compiler.split_compiled[core].split("\n"), seqc_code.split("\n")
        ):
            assert genrated == target

        assert compiler.wfm_mapping[core] == {0: f"supplied_waveform{i+1}"}

        elf, _ = compile_seqc(seqc_code, "HDAWG8", ["PC"], index=0, samplerate=2.0e9)

        waveforms_zi = waveforms_to_zi(waveforms, compiler.wfm_mapping[core])

        waveforms_zi.validate(elf)


def test_frames_from_setup_err():
    setup_path = Path(__file__).parent / "setups/basic.json"
    no_grammar = Path(__file__).parent / "qasm/no_defcalgrammar.qasm"
    with pytest.raises(ValueError):
        Compiler(no_grammar, setup_path, frames_from_setup=True)

    wrong_grammar = Path(__file__).parent / "qasm/wrong_defcalgrammar.qasm"
    with pytest.raises(ValueError):
        Compiler(wrong_grammar, setup_path, frames_from_setup=True)


def profile(folder: Path, average_shots: bool, input_dict: dict[str, str] = None):
    qasm_path = folder / "source.qasm"
    setup_path = folder / "setup.json"

    compiler = Compiler(qasm_path, setup_path)
    compiler.compile(printer_kwargs={"average_shots": average_shots}, inputs=input_dict)


MEASUREMNT_QASM_FILES = [
    f
    for f in (Path(__file__).parent / "qasm/used_in_measurements/").iterdir()
    if f.is_file()
]


def profile_measurements(qasm_path: Path, average_shots: bool):
    setup_path = Path(__file__).parent / "setups/setup_atlantis1.json"

    input_dict = {
        "start_time": 16e-9,
        "time_step": 8e-9,
        "n_steps": 1000,
        "n_shots": 2000,
        "capture_time": 2e-6,
        "resonator_frequency": 100e6,
        "qubit_frequency": 5e7,
        "xhalf_drive_amp": 0.5,
        "xhalf_drive_time": 32e-9,
        "x_drive_amp": 1.0,
        "x_drive_time": 32e-9,
        "wait_time": 5e-6,
        "frequency_start": -5e6,
        "frequency_step": 0.1e6,
        "drive_time": 512e-9,
        "drive_amplitude": 1.0,
        "waveform_duration": 512e-9,
        "readout_delay": 128e-9,
        "waveform_idle_value": 0.0,
    }

    compiler = Compiler(qasm_path, setup_path)
    compiler.compile(printer_kwargs={"average_shots": average_shots}, inputs=input_dict)


if __name__ == "__main__":
    # for i in range(10):
    #     for test in TESTS:
    #         folder = Path(__file__).parent / "compiler_test_files/" / test
    #         profile(folder, True)
    #         profile(folder, False)
    for i in range(100):
        for qasm_file in MEASUREMNT_QASM_FILES:
            if qasm_file.name == "full_waveform.qasm":
                pass
            else:
                profile_measurements(qasm_file, True)
                profile_measurements(qasm_file, False)
