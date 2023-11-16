from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from shipyard.setup.external import SetupExternal as Setup
from shipyard.setup.internal import SetupInternal


def test_setup_from_to_json():
    json_path = Path(__file__).parent.parent / "setups/basic.json"
    setup = Setup.from_file(json_path)
    with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as f:
        json_path_saved = setup.to_file(f.name)
        setup_saved = Setup.from_file(json_path_saved)
    assert setup == setup_saved
    Setup.from_json(json_path)


def test_setup_from_to_yml():
    yml_path = Path(__file__).parent.parent / "setups/basic.yml"
    setup = Setup.from_file(yml_path)
    with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yml") as f:
        yml_path_saved = setup.to_file(f.name)
        setup_saved = Setup.from_file(yml_path_saved)
    assert setup == setup_saved
    Setup.from_yml(yml_path)


def test_setup_from_unknown_file_extension():
    with pytest.raises(ValueError):
        Setup.from_file("foo.bar")


def test_setup_to_unknown_file_extension():
    setup = Setup.from_file(Path(__file__).parent.parent / "setups/basic.yml")
    with pytest.raises(ValueError):
        setup.to_file("foo.bar")


def test_setup_generate_ports():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    assert len(setup.Instruments.values()) == 11
    assert len(setup.Ports.values()) == 58
    assert len(setup.Frames.values()) == 0


def test_add_frame():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    setup.add_frame("frame1", "hdawg1_ch1")
    assert len(setup.Frames.values()) == 1
    assert setup.Frames["frame1"].port == "hdawg1_ch1"
    setup.add_frame("frame2", "hdawg1_ch2")
    assert len(setup.Frames.values()) == 2
    assert setup.Frames["frame2"].port == "hdawg1_ch2"
    setup.add_frame("frame3", "hdawg1_ch3")
    assert len(setup.Frames.values()) == 3
    assert setup.Frames["frame3"].port == "hdawg1_ch3"


def test_set_port():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    setup.add_frame("frame1", "hdawg1_ch1")
    assert len(setup.Frames.values()) == 1
    assert setup.Frames["frame1"].port == "hdawg1_ch1"
    setup.set_port("frame1", "hdawg1_ch2")
    assert setup.Frames["frame1"].port == "hdawg1_ch2"


expected_basic_qasm_str = """cal {
  port ch1;
  frame frame1 = newframe(ch1, 0.0, 0.0);
}
"""


def test_get_qasm_basic_str():
    basic_yml_path = Path(__file__).parent.parent / "setups/basic.yml"
    basic_setup = Setup.from_file(basic_yml_path)
    qasm_str = basic_setup.get_qasm_str()
    assert qasm_str == expected_basic_qasm_str


def test_get_qasm_str_empty():
    instr_yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    basic_setup = Setup.from_file(instr_yml_path, generate_ports=True)
    qasm_str = basic_setup.get_qasm_str()
    assert qasm_str == """cal {\n}\n"""


expected_instr_qasm_str = """cal {
  port hdawg1_ch1;
  port hdawg1_ch2;
  frame frame1 = newframe(hdawg1_ch1, 0.0, 0.0);
  frame frame2 = newframe(hdawg1_ch2, 0.0, 0.0);
}
"""


def test_get_qasm_instr_str():
    instr_yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    basic_setup = Setup.from_file(instr_yml_path, generate_ports=True)
    basic_setup.add_frame("frame1", "hdawg1_ch1")
    basic_setup.add_frame("frame2", "hdawg1_ch2")
    qasm_str = basic_setup.get_qasm_str()
    assert qasm_str == expected_instr_qasm_str


def test_cores():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)

    assert len(setup.cores()) == 42


def test_to_from_internal():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    setup_internal = setup.to_internal()
    setup2 = Setup.from_internal(setup_internal)
    assert setup == setup2
    assert setup.cores() == setup2.cores()


def test_compare_internal_external():
    yml_path = Path(__file__).parent.parent / "setups/basic.yml"
    setup_external = Setup.from_file(
        yml_path,
    )
    setup_internal_from_external = setup_external.to_internal()
    setup_internal = SetupInternal.from_yml(yml_path)

    assert setup_internal == setup_internal_from_external

    setup_external_from_internal = Setup.from_internal(setup_internal)
    assert setup_external == setup_external_from_internal

    assert setup_internal.cores() == setup_external.cores()
    assert setup_internal.cores() == setup_internal_from_external.cores()
    assert setup_internal.cores() == setup_external_from_internal.cores()


def test_get_serial():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    setup.add_frame("frame1", "hdawg1_ch1")
    assert setup.get_serial("hdawg1") == "DEVXXXX"
    assert setup.get_serial("hdawg1_ch1") == "DEVXXXX"
    assert setup.get_serial("frame1") == "DEVXXXX"
    with pytest.raises(KeyError):
        setup.get_serial("foo")


def test_get_core_index():
    yml_path = Path(__file__).parent.parent / "setups/instr.yml"
    setup = Setup.from_file(yml_path, generate_ports=True)
    setup.add_frame("frame1", "hdawg1_ch1")
    assert setup.get_core_index("hdawg1_ch1") == 0
    assert setup.get_core_index("frame1") == 0
    with pytest.raises(KeyError):
        setup.get_core_index("foo")


@pytest.mark.parametrize("channels", [4, 8], ids=["HDAWG4", "HDAWG8"])
def test_add_ports_hdawg(channels):
    setup = Setup(instruments={}, ports={}, frames={})
    setup.Instruments["hdawg1"] = Setup.Instrument(
        name="hdawg1", type=f"HDAWG{channels}", serial="xxx"
    )
    setup.generate_ports()

    assert len(setup.Ports.values()) == channels
    for i in range(channels):
        assert f"hdawg1_ch{i+1}" in setup.Ports
        port = setup.Ports[f"hdawg1_ch{i+1}"]
        assert port.instrument == "hdawg1"
        assert port.core.type == "HD"
        assert port.core.channels == [i % 2 + 1]
        assert port.core.index == i // 2 + 1


@pytest.mark.parametrize("channels", [4, 8], ids=["SHFSG4", "SHFSG8"])
def test_add_ports_shfsg(channels):
    setup = Setup(instruments={}, ports={}, frames={})
    setup.Instruments["shfsg1"] = Setup.Instrument(
        name="shfsg1", type=f"SHFSG{channels}", serial="xxx"
    )
    setup.generate_ports()

    assert len(setup.Ports.values()) == channels
    for i in range(channels):
        assert f"shfsg1_ch{i+1}" in setup.Ports
        port = setup.Ports[f"shfsg1_ch{i+1}"]
        assert port.instrument == "shfsg1"
        assert port.core.type == "SG"
        assert port.core.channels == [1]
        assert port.core.index == i + 1


@pytest.mark.parametrize("channels", [2, 4, 6], ids=["SHFQC2", "SHFQC4", "SHFQC6"])
def test_add_ports_shfqc(channels):
    setup = Setup(instruments={}, ports={}, frames={})
    setup.Instruments["shfqc1"] = Setup.Instrument(
        name="shfqc1", type=f"SHFQC{channels}", serial="xxx"
    )
    setup.generate_ports()

    assert len(setup.Ports.values()) == channels + 2
    for i in range(channels):
        assert f"shfqc1_sg_ch{i+1}" in setup.Ports
        port = setup.Ports[f"shfqc1_sg_ch{i+1}"]
        assert port.instrument == "shfqc1"
        assert port.core.type == "SG"
        assert port.core.channels == [1]
        assert port.core.index == i + 1

    for ch, dir in zip([1, 2], ["out", "in"]):
        assert f"shfqc1_qa_ch1_{dir}" in setup.Ports
        port = setup.Ports[f"shfqc1_qa_ch1_{dir}"]
        assert port.instrument == "shfqc1"
        assert port.core.type == "QA"
        assert port.core.channels == [ch]
        assert port.core.index == 1


@pytest.mark.parametrize("channels", [2, 4], ids=["SHFQA2", "SHFQA4"])
def test_add_ports_shfqa(channels):
    setup = Setup(instruments={}, ports={}, frames={})
    setup.Instruments["shfqa1"] = Setup.Instrument(
        name="shfqa1", type=f"SHFQA{channels}", serial="xxx"
    )
    setup.generate_ports()

    assert len(setup.Ports.values()) == channels * 2
    for index in range(channels):
        for ch, dir in zip([1, 2], ["out", "in"]):
            assert f"shfqa1_ch{index+1}_{dir}" in setup.Ports
            port = setup.Ports[f"shfqa1_ch{index+1}_{dir}"]
            assert port.instrument == "shfqa1"
            assert port.core.type == "QA"
            assert port.core.channels == [ch]
            assert port.core.index == index + 1


def test_hash_setup():
    instr_path = Path(__file__).parent.parent / "setups/instr.yml"
    instr_setup = Setup.from_file(instr_path, generate_ports=True)
    hash1 = instr_setup.__hash__()
    assert hash1 == instr_setup.__hash__()
    hash1_f = hash(instr_setup)
    assert hash1_f == hash(instr_setup)
    assert hash1 == hash1_f
    assert hash(instr_setup) == instr_setup.__hash__()

    instr_setup.add_frame("frame1", "hdawg1_ch1")
    hash2 = hash(instr_setup)
    assert hash1 != hash2
    assert hash2 == hash(instr_setup)

    instr_setup.set_port("frame1", "hdawg1_ch2")
    hash3 = hash(instr_setup)
    assert hash2 != hash3
    assert hash3 == hash(instr_setup)


def test_get_core():
    instr_path = Path(__file__).parent.parent / "setups/instr.yml"
    instr_setup = Setup.from_file(instr_path, generate_ports=True)
    instr_setup.add_frame("frame1", "hdawg1_ch1")
    core_from_port = instr_setup.get_core("hdawg1_ch1")
    core = instr_setup.get_core("frame1")
    assert core_from_port == core
    assert core == (
        instr_setup.Ports["hdawg1_ch1"].instrument,
        instr_setup.Ports["hdawg1_ch1"].core.index,
        instr_setup.Ports["hdawg1_ch1"].core.type,
    )
    with pytest.raises(KeyError):
        instr_setup.get_core("foo")
