"""
Python representations of the openQASM openpulse port and frame concepts
"""
import json
from pathlib import Path

import yaml
from pydantic import BaseModel, validator, field_validator

from ..awg_core import CORE_TYPE_TO_CLASS, AWGCore, CoreType
from ..duration import Duration
from .instr_types import InstrumentType

# todo play waveform tutorial to explain playing IQ waveforms


class Instrument(BaseModel):
    """
    Minimal information required to identify an Instrument

    Args:
        name (str):
            name of instrument instance, used to easily identify one intrument from
            another.
        type (InstrumentType):
            Literal representing the type/model of the instrument.
        serial (str):
            Serial number of the instrument in string format.
    """

    name: str
    type: InstrumentType
    serial: str


class Port(BaseModel):
    """
    Representation of the openQASM openpulse port concept as a pydantic model.
    https://openqasm.com/language/openpulse.html#ports

    Args:
        name (str):
            name of the port.
        instrument (Instrument):
            What instrument the port is associated with.
        core (Core):
            Settings for the AWG Core the port is associated with.
    """

    class Core(BaseModel):
        """
        Settings for a AWG core

        Args:
            type (CoreType):
                the Type of AWG Core this 'Core' object is
            index (int):
                the index of the AWG Core on the Instrument this 'Core' object belongs.
            channels (list[int]):
                the channels of the AWG Core this 'Core' object belongs
        """

        type: CoreType
        index: int
        channels: list[int]

        # pylint: disable=R0903
        # too-few-public-methods
        class Config:
            """Pydantic model config for Core"""

            frozen = True

        # pylint: enable=R0903

        def obj(self) -> AWGCore:
            """
            Returns an AWGCore subclass of type matching the type of the pydantic core
            model.

            Returns:
                AWGCore: AWGCore subclass of type matching the model instance.
            """
            return CORE_TYPE_TO_CLASS[self.type]

        @field_validator("channels")
        def not_more_channels_than_core_type_allows(cls, channels: list[int], values):
            """
            Validates that the number of channels for the Core object does
            not exceed the number of channels allowed by the CoreType
            """
            assert channels
            assert "type" in values.data
            assert len(channels) <= CORE_TYPE_TO_CLASS[values.data["type"]].n_channels
            return channels

    name: str
    instrument: Instrument
    core: Core

    # pylint: disable=R0903
    # too-few-public-methods
    class Config:
        """Pydantic model config for Port"""

        frozen = True

    # pylint: enable=R0903


class Frame(BaseModel):
    """
    Representation of the openQASM openpulse frame concept as a pydantic model.
    https://openqasm.com/language/openpulse.html#frames

    Args:
        name (str):
            name of the frame.
        port (Port):
            the Port object the frame is associated with.
        frequency (float):
            the frequency the frame evolves at. Defaults to 0.
        phase (float):
            the phase of the frame.
        time (Duration):
            the time of the frame.
    """

    name: str
    port: Port
    frequency: float = 0.0
    phase: float = 0.0
    time: Duration = Duration(time=0)

    def set_phase(self, phase: float):
        """Sets the phase of the frame

        Args:
            phase (float): the value the phase will be set to
        """
        self.phase = phase

    def shift_phase(self, phase: float):
        """Shifts the phase of the frame

        Args:
            phase (float): the value the phase will be shifted by.
        """
        self.phase += phase

    def get_phase(self) -> float:
        """Gets the phase of the frame

        Returns:
            float: current value of the phase of the frame.
        """
        return self.phase

    def set_frequency(self, frequency: float):
        """Sets the frequency of the frame

        Args:
            frequency (float): the value the frequency will be set to.
        """
        self.frequency = frequency

    def shift_frequency(self, frequency: float):
        """Shifts the frequency of the frame

        Args:
            frequency (float): the value the frequency will be shifted by.
        """
        self.frequency += frequency

    def get_frequency(self) -> float:
        """Gets the frequency of the frame

        Returns:
            float: current value of the frequency of the frame.
        """
        return self.frequency

    def advance(self, duration: Duration):
        """Advances the time of the frame by some duration

        Args:
            duration (Duration): the duration to advance the time of the frame by.
        """
        self.time += duration

    def advance_to(self, duration: Duration):
        """Advances the time of the frame to some other time

        Args:
            duration (Duration): the duratioin to advance the time fo the frame to.

        Raises:
            ValueError:
                If the time the frame should be advanced to is less than the
                current time of the frame.
        """
        duration.set_unit(self.time.unit)
        if self.time > duration:
            raise ValueError(f"Cant advance current time {self.time} to {duration}")
        self.time.time = int(duration.time * duration.unit.value / self.time.unit.value)


def barrier(frames: list[Frame]):
    """Applies the openQASM openpulse barrier method to Frames.

    Args:
        frames (list[Frame]): frames to apply a barrier to.
    """
    max_time = max(frame.time for frame in frames)

    for frame in frames:
        frame.advance_to(max_time)


class SetupInternal(BaseModel):

    """
    A Pydantic model containing the information required to compile an openQASM program
    to instrument level instructions.

    It is recommended to instanciate this object from a configuration file
    (json (future yml?))
    """

    # todo validation

    # todo move to own module
    instruments: dict[str, Instrument]
    ports: dict[str, Port]
    frames: dict[str, Frame]

    @classmethod
    def from_dict(cls, setup: dict[str, dict[str, dict]]) -> "SetupInternal":
        """Creates a Setup object from a dictionary

        Args:
            setup (dict[str, dict[str, dict]]): dictionary to create a Setup object from

        Returns:
            Setup: created from dictionary
        """
        instruments = {
            k: Instrument(name=k, **v) for k, v in setup["Instruments"].items()
        }
        ports = {}
        for k, val in setup["Ports"].items():
            val["instrument"] = instruments[val["instrument"]]
            val["core"] = Port.Core(**val["core"])
            ports[k] = Port(name=k, **val)
        frames = {}
        for k, val in setup["Frames"].items():
            val["port"] = ports[val["port"]]
            frames[k] = Frame(name=k, **val)
        return cls(instruments=instruments, ports=ports, frames=frames)

    def to_dict(self) -> dict[str, dict[str, dict]]:
        """Creates a dictionary from a Setup object

        Args:
            filename (Path | str, optional):
                path to save dictionary to. Defaults to None.

        Returns:
            dict[str, dict[str, dict]]: dictionary created from Setup object
        """
        setup = {
            "Instruments": {
                k: {
                    "type": v.type,
                    "serial": v.serial,
                }
                for k, v in self.instruments.items()
            },
            "Ports": {
                k: {
                    "instrument": v.instrument.name,
                    "core": {
                        "type": v.core.type.value,
                        "index": v.core.index,
                        "channels": v.core.channels,
                    },
                }
                for k, v in self.ports.items()
            },
            "Frames": {
                k: {
                    "port": v.port.name,
                    "frequency": v.frequency,
                    "phase": v.phase,
                }
                for k, v in self.frames.items()
            },
        }
        return setup

    @classmethod
    def from_json(cls, filename: str | Path) -> "SetupInternal":
        """Creates a Setup object from a json file

        Args:
            filename (str | Path): path to json file

        Returns:
            Setup: created from json file
        """
        with open(filename, encoding="utf-8") as file:
            data = json.load(file)
        return cls.from_dict(data)

    def to_json(self, filename: str | Path) -> Path:
        """Writes a Setup object to a json file

        Args:
            filename (str | Path): path to json file to create

        Returns:
            Path: path to json file
        """
        data = self.to_dict()
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        return Path(filename)

    @classmethod
    def from_yml(cls, filename: str | Path) -> "SetupInternal":
        """Creates a Setup object from a yml file

        Args:
            filename (str | Path): path to yml file

        Returns:
            Setup: created from yml file
        """
        with open(filename, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return cls.from_dict(data)

    def to_yml(self, filename: str | Path) -> Path:
        """Writes a Setup object to a yml file

        Args:
            filename (str | Path): path to yml file to create

        Returns:
            Path: path to yml file
        """
        data = self.to_dict()
        with open(filename, "w", encoding="utf-8") as file:
            yaml.dump(data, file)
        return Path(filename)

    def cores(self) -> set[tuple[str, int, str]]:
        """Gets all the AWG Cores used in the setup

        Returns:
            set[tuple[str, int, str]]:
                a Set of tuples, each tuple has a string representing the instruement
                name, a integer representing the index of the awg core of the
                instrument and a string representing the type of the awg core.
        """
        return set(
            (port.instrument.name, port.core.index, port.core.type.value)
            for port in self.ports.values()
        )
