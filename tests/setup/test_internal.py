import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from numpy import allclose
from pydantic import ValidationError

from shipyard.duration import Duration, TimeUnits
from shipyard.setup.internal import (
    CORE_TYPE_TO_CLASS,
    AWGCore,
    CoreType,
    Frame,
    Instrument,
    Port,
    SetupInternal,
    barrier,
)


def test_load_setup_from_file():
    json_path = Path(__file__).parent.parent / "setups/basic.json"
    setup = SetupInternal.from_json(json_path)

    assert "hdawg1" in setup.instruments
    assert "hdawg1" == setup.instruments["hdawg1"].name
    assert "HDAWG8" == setup.instruments["hdawg1"].type
    assert "DEVXXXX" == setup.instruments["hdawg1"].serial

    assert "ch1" in setup.ports
    assert "ch1" == setup.ports["ch1"].name
    assert CoreType.HD == setup.ports["ch1"].core.type
    assert setup.instruments["hdawg1"] == setup.ports["ch1"].instrument
    assert [1] == setup.ports["ch1"].core.channels

    assert "frame1" in setup.frames
    assert "frame1" == setup.frames["frame1"].name
    assert setup.ports["ch1"] == setup.frames["frame1"].port
    assert 0 == setup.frames["frame1"].frequency
    assert 0 == setup.frames["frame1"].phase


def test_load_setup_from_yml_file():
    yml_path = Path(__file__).parent.parent / "setups/basic.yml"
    setup = SetupInternal.from_yml(yml_path)

    assert "hdawg1" in setup.instruments
    assert "hdawg1" == setup.instruments["hdawg1"].name
    assert "HDAWG8" == setup.instruments["hdawg1"].type
    assert "DEVXXXX" == setup.instruments["hdawg1"].serial

    assert "ch1" in setup.ports
    assert "ch1" == setup.ports["ch1"].name
    assert CoreType.HD == setup.ports["ch1"].core.type
    assert setup.instruments["hdawg1"] == setup.ports["ch1"].instrument
    assert [1] == setup.ports["ch1"].core.channels

    assert "frame1" in setup.frames
    assert "frame1" == setup.frames["frame1"].name
    assert setup.ports["ch1"] == setup.frames["frame1"].port
    assert 0 == setup.frames["frame1"].frequency
    assert 0 == setup.frames["frame1"].phase


def test_setup_to_dict():
    json_path = Path(__file__).parent.parent / "setups/basic.json"
    with open(json_path, encoding="utf-8") as file:
        data = json.load(file)
    setup = SetupInternal.from_dict(data)
    setup_to_dict = setup.to_dict()

    with open(json_path, encoding="utf-8") as file:
        data2 = json.load(file)

    assert data2 == setup_to_dict


def test_setup_to_json():
    json_path = Path(__file__).parent.parent / "setups/basic.json"
    setup = SetupInternal.from_json(json_path)
    with NamedTemporaryFile(mode="w", encoding="utf-8") as f:
        json_path_saved = setup.to_json(f.name)
        assert json_path.read_text() == json_path_saved.read_text()


def test_setup_to_yml():
    yml_path = Path(__file__).parent.parent / "setups/basic.yml"
    setup = SetupInternal.from_yml(yml_path)
    with NamedTemporaryFile(mode="w", encoding="utf-8") as f:
        yml_path_saved = setup.to_yml(f.name)
        assert yml_path.read_text() == yml_path_saved.read_text()


INSTR_TYPES = ["HDAWG8", "HDAWG4", "SHFSG4", "SHFQA4", "SHFQC", "PQSC"]


@pytest.mark.parametrize("instr_type", INSTR_TYPES)
def test_instrument(instr_type):
    instr = Instrument(name=f"test_{instr_type}", type=instr_type, serial="DEVXXXX")

    assert instr.name == f"test_{instr_type}"
    assert instr.type == instr_type
    assert instr.serial == "DEVXXXX"


def test_instrument_unsupported_type():
    with pytest.raises(ValidationError):
        Instrument(name="error", type="not_supported", serial="xxxx")


@pytest.mark.parametrize("core_type", [CoreType.HD, CoreType.QA, CoreType.SG])
def test_port_core(core_type):
    n_channels = CORE_TYPE_TO_CLASS[core_type].n_channels
    for i in range(n_channels):
        channels = [j + 1 for j in range(n_channels)]
        port_core = Port.Core(type=core_type, index=i, channels=channels)
        assert port_core.type == core_type
        assert port_core.index == i
        assert port_core.channels == channels

        assert isinstance(port_core.obj(), AWGCore)

    with pytest.raises(ValidationError):
        channels = [i + 1 for i in range(n_channels + 1)]
        port_core = Port.Core(type=core_type, index=1, channels=channels)

    with pytest.raises(ValidationError):
        port_core = Port.Core(type=core_type, index=1, channels=[])


@pytest.mark.parametrize("core_type", ["HD", "QA", "SG"])
def test_port_core_str(core_type):
    Port.Core(type=core_type, index=1, channels=[1])


def test_port_core_incorrect_core_type():
    with pytest.raises(ValidationError):
        Port.Core(type="not_core_type", index=1, channels=[1])


@pytest.fixture(name="port")
def fixture_port() -> Port:
    return Port(
        name="ch1",
        instrument=Instrument(name="instr", type="HDAWG8", serial="xxx"),
        core=Port.Core(type="HD", index=1, channels=[1]),
    )


def test_port(port: Port):
    assert port.name == "ch1"


@pytest.fixture(name="frame")
def fixture_frame(port) -> Frame:
    return Frame(name="frame", port=port)


def test_frame_basic(frame: Frame):
    assert frame.name == "frame"
    assert frame.frequency == 0
    assert frame.phase == 0
    assert frame.time == Duration(time=0)


def test_frame_phase(frame: Frame):
    assert frame.get_phase() == 0
    frame.shift_phase(1.0)
    assert allclose(frame.get_phase(), 1.0)
    frame.set_phase(2.2)
    assert allclose(frame.get_phase(), 2.2)
    frame.shift_phase(-1.0)
    assert allclose(frame.get_phase(), 1.2)


def test_frame_frequency(frame: Frame):
    assert frame.get_frequency() == 0
    frame.shift_frequency(1.0e9)
    assert allclose(frame.get_frequency(), 1.0e9)
    frame.set_frequency(2.2e9)
    assert allclose(frame.get_frequency(), 2.2e9)
    frame.shift_frequency(-1.0e8)
    assert allclose(frame.get_frequency(), 2.1e9)


def test_frame_time(frame: Frame):
    assert frame.time.time == 0
    frame.advance(Duration(time=100, unit=TimeUnits.ns))
    assert allclose(frame.time._real_time(), 100e-9)
    frame.advance_to(Duration(time=10, unit=TimeUnits.us))
    assert allclose(frame.time._real_time(), 10e-6)
    frame.advance(Duration(time=100, unit=TimeUnits.ns))
    assert allclose(frame.time._real_time(), 10.1e-6)

    with pytest.raises(ValueError):
        frame.advance_to(Duration(time=100, unit=TimeUnits.ns))


def test_barrier(port: Port):
    frame1 = Frame(name="frame1", port=port)
    frame2 = Frame(name="frame2", port=port, time=Duration(time=20))
    assert frame1.time == 0
    assert frame2.time == 10e-9

    barrier([frame1, frame2])

    assert frame1.time == frame2.time


def test_get_cores_from_setup():
    json_path = Path(__file__).parent.parent / "setups/complex.json"
    setup = SetupInternal.from_json(json_path)

    cores = setup.cores()

    assert len(cores) == 4
    assert cores == {
        ("hdawg1", 1, "HD"),
        ("hdawg1", 2, "HD"),
        ("hdawg1", 3, "HD"),
        ("shfqa1", 1, "QA"),
    }
