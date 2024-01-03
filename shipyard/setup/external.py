"""
External representation of the setup, meant to be used by the user. and free
the user from having to know the internal representation of the setup. This
representation is purely a data model.

"""

from pathlib import Path

import yaml
from openpulse import ast
from openpulse.printer import dumps
from pydantic import BaseModel

from .instr_types import CoreType, InstrumentType, instrument_type_info
from .internal import SetupInternal

__all__ = ["SetupExternal"]


class SetupExternal(BaseModel):
    """
    External representation of the setup, meant to be used by the user. and free
    the user from having to know the internal representation of the setup. This
    representation is purely a data model.

    Args:
        Frames (dict[str, Frame]):
            A dictionary of Frames, where the key is the name of the frame
        Instruments (dict[str, Instrument]):
            A dictionary of Instruments, where the key is the name of the
            instrument
        Ports (dict[str, Port]):
            A dictionary of Ports, where the key is the name of the port
    """

    class Frame(BaseModel):
        """
        Data model for a Frame

        Args:
            port (str):
                The name of the port the frame is connected to
            frequency (float):
                The frequency of the frame
            phase (float):
                The phase of the frame
        """

        port: str
        frequency: float = 0.0
        phase: float = 0.0

        def __hash__(self) -> int:
            return hash(self.__class__) + hash(tuple(self.__dict__.values()))

    class Instrument(BaseModel):
        """
        Data model for an Instrument

        Args:
            serial (str):
                The serial number of the instrument
            type (InstrumentType - Literal String):
                The type of the instrument, see shipyard.instr_types for details.
        """

        serial: str
        type: InstrumentType

        class Config:
            frozen = True

    class Port(BaseModel):
        """
        Data model for a Port

        Args:
            instrument (str):
                The name of the instrument the port is connected to
            core (Core):
                The core of the port
        """

        class Core(BaseModel):
            """
            Data model for a Core

            Args:
                index (int):
                    The index of the core on the instrument
                channels (list[int]):
                    The channels of the core on the instrument used by the port
                type (CoreType - Literal String):
                    The type of the core, currently only "HD", "QA" and "SG" are
                    supported
            """

            index: int
            channels: list[int]
            type: CoreType

            def __hash__(self) -> int:
                return hash(self.__class__) + hash(
                    (self.index, self.type) + tuple(self.channels)
                )

        instrument: str
        core: Core

        class Config:
            frozen = True

    Frames: dict[str, Frame] = {}
    Instruments: dict[str, Instrument] = {}
    Ports: dict[str, Port] = {}

    def __hash__(self) -> int:
        return hash(self.__class__) + hash(
            tuple(self.Frames.keys())
            + tuple(self.Frames.values())
            + tuple(self.Instruments.keys())
            + tuple(self.Instruments.values())
            + tuple(self.Ports.keys())
            + tuple(self.Ports.values())
        )

    @classmethod
    def from_file(
        cls, path: str | Path, generate_ports: bool = False
    ) -> "SetupExternal":
        """
        Creates a SetupExternal from a file, the file format is determined by the
        file extension. Currently supported extensions are ".json" and ".yml".

        Args:
            path (str | Path): path to the file
            generate_ports (bool, optional):
                whether to generate ports automatically based on the instruments defined
                in the setup file. Defaults to False.

        Raises:
            ValueError: if the file extension is not supported

        Returns:
            SetupExternal: created from the file with possibly generated ports
        """
        path = Path(path)
        match path.suffix:
            case ".json":
                setup = cls.model_validate_json(path.read_text(encoding="utf-8"))
            case ".yml":
                setup = cls(**yaml.safe_load(path.read_text(encoding="utf-8")))
            case _:
                raise ValueError(f"Unknown file extension: {path.suffix}")
        if generate_ports:
            assert setup.Ports == {}
            setup.generate_ports()
        return setup

    # methods that mirror the internal setup methods
    from_json = from_file
    from_yml = from_file

    def to_file(self, path: str | Path) -> Path:
        """
        Converts the setup to a file,
        the file format is determined by the file extension.
        Currently supported extensions are ".json" and ".yml".

        Args:
            path (str | Path): path to the file

        Raises:
            ValueError: if the file extension is not supported

        Returns:
            Path: the path to the file
        """
        path = Path(path)
        match path.suffix:
            case ".json":
                path.write_text(self.model_dump_json(), encoding="utf-8")
            case ".yml":
                path.write_text(yaml.dump(self.model_dump()), encoding="utf-8")
            case _:
                raise ValueError(f"Unknown file extension: {path.suffix}")
        return path

    def generate_ports(self) -> None:
        """
        Automatically generates ports based on the instruments defined in the setup
        """

        def _core_ports(
            instr_name: str, core_index: int, kind: CoreType
        ) -> dict[str, SetupExternal.Port]:
            match kind:
                case "HD":
                    return self._hd_ports(instr_name, core_index, kind)
                case "QA":
                    return self._qa_ports(instr_name, core_index, kind)
                case "SG":
                    return self._sg_ports(instr_name, core_index, kind)
                case _:  # pragma: no cover
                    raise ValueError(f"Unknown CoreType {kind}")

        for instr_name, instr in self.Instruments.items():
            for n_cores, core_type in instrument_type_info[instr.type]:
                for core_index in range(n_cores):
                    self.Ports.update(
                        _core_ports(instr_name, core_index + 1, core_type)
                    )

    def get_serial(self, name: str) -> str:
        """
        Returns the serial string of an instrument, either by the name of the
        instrument, the name of a port associated with the instrument, or the name of a
        frame connected to a port.

        Args:
            name (str): name of the instrument, port or frame

        Raises:
            KeyError: if the name is not an instrument, port or frame name in the setup

        Returns:
            str: serial string of the instrument
        """
        if name in self.Instruments:
            return self.Instruments[name].serial
        if name in self.Ports:
            return self.get_serial(self.Ports[name].instrument)
        if name in self.Frames:
            return self.get_serial(self.Frames[name].port)
        raise KeyError(f"Unknown Instrument, Port or Frame name {name}")

    def get_core_index(self, name: str) -> int:
        """
        Returns the core index of a port, either by the name of the port or the name
        of a frame connected to the port.

        Args:
            name (str): name of the port or frame

        Raises:
            KeyError: if the name is not a port or frame name in the setup

        Returns:
            int: core index of the port as enumerated by the instrument node api (ZI)
        """
        if name in self.Ports:
            return self.Ports[name].core.index - 1
        if name in self.Frames:
            return self.get_core_index(self.Frames[name].port)
        raise KeyError(f"Unknown Port or Frame name {name}")

    def get_core(self, name: str) -> tuple[str, int, str]:
        """
        Returns a tuple of core information, either by the name of a port or frame.

        Args:
            name (str): name of the port or frame

        Raises:
            KeyError: if the name is not a port or frame name in the setup

        Returns:
            tuple[str, int, str]: instrument name, core index and core type
        """
        if name in self.Ports:
            port = self.Ports[name]
            return port.instrument, port.core.index, port.core.type
        if name in self.Frames:
            return self.get_core(self.Frames[name].port)
        raise KeyError(f"Unknown Port or Frame name {name}")

    def set_port(self, frame_name: str, port_name: str) -> None:
        """
        Sets the port of a frame

        Args:
            frame_name (str): name of the frame to set the port of
            port_name (str): name of the port to set as the port of the frame
        """
        assert frame_name in self.Frames
        assert port_name in self.Ports
        self.Frames[frame_name].port = port_name

    def cores(self) -> set[tuple[str, int, str]]:
        """Gets all the AWG Cores used in the setup

        Returns:
            set[tuple[str, int, str]]:
                a Set of tuples, each tuple has a string representing the instruement
                name, a integer representing the index of the awg core of the
                instrument and a string representing the type of the awg core.
        """
        return set(
            (port.instrument, port.core.index, port.core.type)
            for port in self.Ports.values()
        )

    def add_frame(
        self,
        frame_name: str,
        port_name: str,
        frequency: float = 0.0,
        phase: float = 0.0,
    ) -> None:
        """
        Adds a frame to the setup

        Args:
            frame_name (str): name of the frame
            port_name (str): name of the port the frame is connected to
            frequency (float): frequency of the frame, defaults to 0.0
            phase (float): phase of the frame, defaults to 0.0
        """
        self.Frames[frame_name] = self.Frame(
            port=port_name, frequency=frequency, phase=phase
        )

    def get_qasm(self) -> ast.CalibrationStatement:
        used_ports = list(set(frame.port for frame in self.Frames.values()))
        used_ports.sort()
        statements = [
            ast.ClassicalDeclaration(
                type=ast.PortType(), identifier=ast.Identifier(port)
            )
            for port in used_ports
        ]
        statements.extend(
            [
                ast.ClassicalDeclaration(
                    type=ast.FrameType(),
                    identifier=ast.Identifier(name),
                    init_expression=ast.FunctionCall(
                        ast.Identifier("newframe"),
                        [
                            ast.Identifier(frame.port),
                            ast.FloatLiteral(frame.frequency),
                            ast.FloatLiteral(frame.phase),
                        ],
                    ),
                )
                for name, frame in self.Frames.items()
            ]
        )
        return ast.CalibrationStatement(body=statements)

    def get_qasm_str(self) -> str:
        qasm = self.get_qasm()
        return dumps(qasm)

    ######################################
    # methods for conversion to internal #
    ######################################

    def to_internal(self) -> SetupInternal:
        """
        Converts the external setup representation to the internal setup representation

        Returns:
            SetupInternal: internal setup representation
        """
        return SetupInternal.from_dict(self.model_dump())

    @classmethod
    def from_internal(cls, internal: SetupInternal) -> "SetupExternal":
        """
        Creates a external setup representation from an internal setup representation

        Args:
            internal (SetupInternal): internal setup representation

        Returns:
            SetupExternal: external setup representation
        """
        return cls(**internal.to_dict())

    ######################################
    # core type specific port generation #
    ######################################

    def _name_prefix(self, instr_name: str, core_type: CoreType) -> str:
        """
        gets the name prefix for a port based on the instrument name and the core,
        used in the automatic port generation.
        """
        if "shfqc" in self.Instruments[instr_name].type.lower():
            return f"{instr_name}_{core_type.lower()}"
        return instr_name

    def _hd_ports(
        self, instr_name: str, core_index: int, kind: CoreType
    ) -> dict[str, "Port"]:
        """Generates the ports for a HDAWG core"""
        ports = {}
        for ch in [1, 2]:
            name = f"{instr_name}_ch{2*(core_index-1)+ch}"
            core = self.Port.Core(type=kind, index=core_index, channels=[ch])
            ports[name] = self.Port(instrument=instr_name, core=core)
        return ports

    def _sg_ports(
        self, instr_name: str, core_index: int, kind: CoreType
    ) -> dict[str, "Port"]:
        """Generates the ports for a SG core"""
        name_prefix = f"{self._name_prefix(instr_name, kind)}"
        name = f"{name_prefix}_ch{core_index}"
        core = self.Port.Core(type=kind, index=core_index, channels=[1])
        port = self.Port(instrument=instr_name, core=core)
        return {name: port}

    def _qa_ports(
        self, instr_name: str, core_index: int, kind: CoreType
    ) -> dict[str, "Port"]:
        """Generates the ports for a QC core"""
        ports = {}
        name_prefix = f"{self._name_prefix(instr_name, kind)}"
        for ch, direction in zip([1, 2], ["out", "in"]):
            name = f"{name_prefix}_ch{core_index}_{direction}"
            core = self.Port.Core(type=kind, index=core_index, channels=[ch])
            ports[name] = self.Port(instrument=instr_name, core=core)
        return ports
