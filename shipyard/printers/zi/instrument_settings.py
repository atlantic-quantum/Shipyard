"""
ZI Instrument and Sequencing core specific settings that cant be expressed in SEQC
"""
from enum import Enum
from typing import Any

from numpy import ndarray
from pydantic import BaseModel


class ReadoutSource(Enum):
    """Enumeration of readout mode

    1: INTEGRATION
        Complex-valued integration results of the Weighted Integration in
        Qubit Readout mode.
    3: DISCRIMINATION
        The results after state discrimination.
    """

    INTEGRATION = 1
    DISCRIMINATION = 3


class Mode(Enum):
    """Enumeration of QA core operation modes

    0: SPECTROSCOPY
        In Spectroscopy mode, the Signal Output is connected to the Oscillator,
        with which also the measured signals are correlated.
    1: READOUT
        In Qubit Readout mode, the Signal Output is connected to the Readout Pulse
        Generator, and the measured signals are correlated with the Integration Weights
        before state discrimination.
    """

    SPECTROSCOPY = 0
    READOUT = 1


class SpectroscopyMode(Enum):
    """Enumeration of spectroscopy modes"""

    CONTINUOUS = 0
    PULSED = 1


class AveragingMode(Enum):
    """Enumeration of averaging mode

    0: CYCLIC
        Cyclic averaging: a sequence of multiple results is recorded first,
        then averaged with the next repetition of the same sequence.
    1: SEQUENTIAL
        Sequential averaging: each result is recorded and averaged first,
        before the next result is recorded and averaged.
    """

    CYCLIC = 0
    SEQUENTIAL = 1


class ClockSource(Enum):
    """Enumeration of clock source

    0: INTERNAL
    1: EXTERNAL
    2: ZSYNC

    """

    INTERNAL = 0
    EXTERNAL = 1
    ZSYNC = 2


class AWGCore(BaseModel):
    """
    Base class for ZI AWG Core model to generated settings that can't be
    expressed in seqc code
    """

    channel: int


class SHFQACore(AWGCore):
    """
    Model to generate settings for SHFQA cores that can't be expressed in seqc code

    Args:
        channel (int):
            the qachannel number (1-4)
        readouts (dict[int, READOUT]):
            dictionary of discriminator indicies and READOUT objects, initially empty
            and populated as the seqc code is printed.
        spectra (dict[int, SPECTRA]):
            dictionary of indicies and SPECTRA objects.
        generator_delay (float):
            delay between trigger and waveform generation, default value = 0.0
        integrator_delay (float):
            delay between trigger and start of integration, default value = 0.0
        mode (Mode):
            Operation mode of the QA core: Mode.READOUT (defaul) / Mode.SPECTROSCOPY
        num_averages (int):
            how many times each point will be averaged in the result, default value = 1
        points_to_record (int):
            how many points should be recored in the result, default value = 1
        averaging_mode (AveragingMode)
            Averaging mode either:
                AveragingMode.CYCLIC (default) or AveragingMode.SEQUENCTIAL
        readout_source (ReadoutSource)
            What is used as the source of readout result, either:
                ReadoutSource.DISCRIMINATION (default) or ReadoutSource.INTEGRATION
        average_shots (bool):
            Whether to average the shots or not, default value = True
            if false, the length of the acquisition is multiplied by the number of
            averages and averages in the acquisition are set to 1.

    Usage:
        core = SHFQACore(...)
        settings = core.settings() <- upload to instrument
    """

    class READOUT(BaseModel):
        """
        Model of readout settings that can't be expressed in seqc code

        Args:
            index (int):
                disciriminator index (0-15)
            generator_wfm (ndarray):
                sampled waveform to generate readout signal
            integrator_wmf (ndarray):
                sampled waveform, used to integrated aqcuired signal
            threshold: (float):
                threshold used to discriminate integrated readout result. note
                per ZI convention, while a complex number is acquired from integration
                only the real component of the number is thresholded (thresheld?)

        """

        index: int
        generator_wfm: ndarray
        integrator_wfm: ndarray
        threshold: float

        # pylint: disable=R0903
        # too-few-public-methods
        class Config:
            """Pydantic model config for READOUT"""

            arbitrary_types_allowed = True

        # pylint: enable=R0903

        def settings(self) -> list[tuple[str, Any]]:
            """
            Returns:
                list[tuple[str, Any]]:
                    node names of QA readout settings and their values
            """
            return [
                (f"/GENERATOR/WAVEFORMS/{self.index}/WAVE", self.generator_wfm),
                (
                    f"/READOUT/INTEGRATION/WEIGHTS/{self.index}/WAVE",
                    self.integrator_wfm,
                ),
                (f"/READOUT/DISCRIMINATORS/{self.index}/THRESHOLD", self.threshold),
            ]

    class SPECTRA(BaseModel):
        """
        Model of spectroscopy and scope settings that can't be expressed in seqc code,
        for use with openQASM/openpulse capture_v3, i.e. waveform capture.

        Args:
            envelope_wfm (ndarray):
                For pulsed spectroscopy mode. in general this may be 'ones'
            integration_time (int):
                Numbers of samples to acquire at 2GS/s follows ZI node convention
            mode (SpectroscopyMode):
                Mode the spectroscopy module operates, either:
                    SpectroscopyMode.CONTINUOUS or
                    SpectroscopyMode.PULSED (default)
            scope_segments (int):
                How many different waveforms (i.e. segments) should acquired
                default value = 0

        """

        envelope_wfm: ndarray
        integration_time: int  # samples
        mode: SpectroscopyMode = SpectroscopyMode.PULSED

        # pylint: disable=R0903
        # too-few-public-methods
        class Config:
            """Pydantic model config for SPECTRA"""

            arbitrary_types_allowed = True

        # pylint: enable=R0903

        def settings(self) -> list[tuple[str, Any]]:
            """
            Returns:
                list[tuple[str, Any]]:
                    node names of QA spectroscopy settings and their values
            """
            return [
                ("/SPECTROSCOPY/ENVELOPE/ENABLE", self.mode.value),
                ("/SPECTROSCOPY/ENVELOPE/WAVE", self.envelope_wfm),
                ("/SPECTROSCOPY/LENGTH", self.integration_time),
            ]

    channel: int
    readouts: dict[int, READOUT] = {}
    spectra: dict[int, SPECTRA] = {}
    generator_delay: float = 0.0
    integrator_delay: float = 0.0  # 220e-9
    mode: Mode = Mode.READOUT
    num_averages: int = 1
    points_to_record: int = 1
    averaging_mode: AveragingMode = AveragingMode.SEQUENTIAL
    readout_source: ReadoutSource = ReadoutSource.DISCRIMINATION
    enable_scope: bool = False
    average_shots: bool = True
    clock_source: ClockSource = ClockSource.ZSYNC

    def settings(self) -> list[tuple[str, Any]]:
        """
        Generate settings for a QA Core

        Returns:
            list[tuple[str, Any]]:
                node names of QA Core settings and their values
        """
        prefix = f"/QACHANNELS/{self.channel-1}"
        mode_str = "READOUT" if self.mode == Mode.READOUT else "SPECTROSCOPY"
        settings = [
            (prefix + "/MODE", self.mode.value),
            (prefix + "/INPUT/ON", 1),
            (prefix + "/OUTPUT/ON", 1),
            (
                prefix + f"/{mode_str}/RESULT/LENGTH",
                self.points_to_record
                if self.average_shots
                else self.points_to_record * self.num_averages,
            ),
            (prefix + f"/{mode_str}/RESULT/MODE", self.averaging_mode.value),
            (
                prefix + f"/{mode_str}/RESULT/AVERAGES",
                self.num_averages if self.average_shots else 1,
            ),
            ("/SYSTEM/CLOCKS/REFERENCECLOCK/IN/SOURCE", self.clock_source.value),
        ]
        if self.mode == Mode.READOUT:
            integration_time = max(
                [len(read.generator_wfm) for read in self.readouts.values()] or [1]
            )
            settings.extend(
                [
                    (
                        prefix + "/GENERATOR/AUXTRIGGERS/0/CHANNEL",
                        32 + self.channel - 1,
                    ),
                    (prefix + "/GENERATOR/CLEARWAVE", 1),
                    (prefix + "/GENERATOR/DELAY", self.generator_delay),
                    (prefix + "/READOUT/INTEGRATION/CLEARWEIGHT", 1),
                    (prefix + "/READOUT/INTEGRATION/DELAY", self.integrator_delay),
                    (prefix + "/READOUT/INTEGRATION/LENGTH", integration_time),
                    (prefix + "/READOUT/RESULT/SOURCE", self.readout_source.value),
                    (prefix + "/READOUT/RESULT/ENABLE", 1),
                ]
            )
        else:
            settings.extend(
                [
                    (prefix + "/SPECTROSCOPY/TRIGGER/CHANNEL", 32 + self.channel - 1),
                    (prefix + "/SPECTROSCOPY/ENVELOPE/DELAY", self.generator_delay),
                    (prefix + "/SPECTROSCOPY/DELAY", self.integrator_delay),
                    (prefix + "/SPECTROSCOPY/RESULT/ENABLE", 1),
                ]
            )
            integration_time = max(
                [spectra.integration_time for spectra in self.spectra.values()] or [1]
            )
        if self.enable_scope:
            settings.extend(
                [
                    ("/SCOPES/0/SINGLE", 1),
                    ("/SCOPES/0/LENGTH", integration_time),
                    ("/SCOPES/0/SEGMENTS/ENABLE", self.points_to_record),
                    ("/SCOPES/0/SEGMENTS/COUNT", self.points_to_record),
                    (
                        f"/SCOPES/0/CHANNELS/{self.channel - 1}/INPUTSELECT",
                        self.channel - 1,
                    ),
                    (
                        "/SCOPES/0/TRIGGER/CHANNEL",
                        (64 if self.mode == Mode.READOUT else 32) + self.channel - 1,
                    ),
                    ("/SCOPES/0/TRIGGER/DELAY", self.integrator_delay),
                ]
            )

        to_add = self.readouts if self.mode == Mode.READOUT else self.spectra
        for adding in to_add.values():
            settings.extend(
                [(prefix + path, value) for (path, value) in adding.settings()]
            )
        return settings


class SHFSGCore(AWGCore):
    """
    Model to generate settings for SHFSG cores that can't be expressed in seqc code

    Args:
        channel (int):
            the sgchannel number (1-4)
        on (bool):
            whether the output is on or off, default value = True / ON
        clock_source (ClockSource):
            clock source of the Instrument, default value = ClockSource.ZSYNC
            ? this is the clock source of the instrument, not the core,
            ? should it be here?
    """

    channel: int
    on: bool = True
    clock_source: ClockSource = ClockSource.ZSYNC

    def settings(self) -> list[tuple[str, Any]]:
        """
        Generate settings for an SG Core

        Returns:
            list[tuple[str, Any]]:
                node names of SG Core settings and their values
        """
        settings = [
            (f"/SGCHANNELS/{self.channel-1}/OUTPUT/ON", 1 if self.on else 0),
            (f"/SGCHANNELS/{self.channel-1}/AWG/DIOZSYNCSWITCH", 1),
            (f"/SGCHANNELS/{self.channel-1}/AWG/MODULATION/ENABLE", 1),
            (f"/SGCHANNELS/{self.channel-1}/SINES/0/HARMONIC", 1),  # IS THIS NEEDED?
            ("/SYSTEM/CLOCKS/REFERENCECLOCK/IN/SOURCE", self.clock_source.value),
        ]

        return settings


class OutputPath(Enum):
    """
    Enumeration of output path of HDAWG

    0: AMPLIFIED
        The output goes through the amplifier after the DAC.
    1: DIRECT
        The output goes directly to the output connector after the DAC.

    """

    AMPLIFIED = 0
    DIRECT = 1


class OutputRange(Enum):
    """
    Enumeration of output range of HDAWG

    Technically the range is automatically set by the HDAWG to the nearest
    range above any value set. So if you set the range to 0.1 V, the range
    is automatically set to 0.2 V, etc. But these values are the real settable
    ranges.
    """

    V_0_200 = 0.2
    V_0_400 = 0.4
    V_0_600 = 0.6
    V_0_800 = 0.8
    V_1_000 = 1.0
    V_2_000 = 2.0
    V_3_000 = 3.0
    V_4_000 = 4.0
    V_5_000 = 5.0


class HDCORE(AWGCore):
    """
    Model to generate settings for HDAWG cores that can't be expressed in seqc code

    Args:
        channel (int):
            the awg core number (1-4)
        channels (list[Output]):
            list of Output objects, initially empty and populated as the seqc code is
            printed.

    """

    class Output(BaseModel):
        """
        Model of output settings that can't be expressed in seqc code

        Args:
            output (int):
                which of the two AWG ouputs associated with the core this model
                describes, either 1 or 2, default value = 1
            on (bool):
                whether the output is on or off, default value = True / ON
            path (OutputPath):
                whether the output is amplified or direct,
                default value = OutputPath.AMPLIFIED
            range (OutputRange):
                the range of the output, default value = OutputRange.V_5_000 / 5 V
            hold (bool):
                whether the output is held at the last value played by the AWG, or
                if the output is set to 0 V when the AWG is not playing,
                default value = True
        """

        output: int = 1
        on: bool = True
        path: OutputPath = OutputPath.AMPLIFIED
        range: OutputRange = OutputRange.V_5_000
        hold: bool = True

        def settings(self, core: int) -> list[tuple[str, Any]]:
            """
            Generate settings for the output of the HDAWG

            Args:
                channel (int): the awg core number (1-4)

            Returns:
                list[tuple[str, Any]]:
                    node names of HDAWG output settings and their values
            """
            physical_channel = 2 * (core - 1) + self.output - 1
            sigout_base = f"/SIGOUTS/{physical_channel}"
            return [
                (sigout_base + "/ON", 1 if self.on else 0),
                (sigout_base + "/RANGE", self.range.value),
                (sigout_base + "/DIRECT", self.path.value),
                (
                    f"/AWGS/{core-1}/OUTPUTS/{self.output-1}/HOLD",
                    1 if self.hold else 0,
                ),
            ]

    channel: int
    outputs: dict[int, Output] = {}
    clock_source: ClockSource = ClockSource.ZSYNC
    sample_frequency: float = 2.0e9

    def settings(self) -> list[tuple[str, Any]]:
        """
        Generate settings for an HDAWG Core

        Returns:
            list[tuple[str, Any]]:
                node names of HDAWG output settings and their values
        """
        settings = [
            setting
            for output in self.outputs.values()
            for setting in output.settings(self.channel)
        ]
        settings.extend(
            [
                ("/SYSTEM/CLOCKS/REFERENCECLOCK/SOURCE", self.clock_source.value),
                ("/SYSTEM/CLOCKS/SAMPLECLOCK/FREQ", self.sample_frequency),
                ("/DIOS/0/MODE", 3),
            ]
        )
        return settings
