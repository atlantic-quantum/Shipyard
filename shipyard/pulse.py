"""
Old pulse module.  This is a wrapper around the internal setup module.
To be removed in the future.

Users should use the external setup module instead. which is exposed as
shipyard.Setup
"""
from deprecated import deprecated

from .setup.internal import CoreType, Frame, Instrument
from .setup.internal import Port as PortInternal
from .setup.internal import SetupInternal

__all__ = ["CoreType", "Frame", "Instrument", "Port", "Setup"]


@deprecated(
    version="0.1.0",
    reason="shipyard.pulse.Port is deprecated use shipyard.setup.internal.Port"
    "instead.",
)
class Port(PortInternal):
    ...


@deprecated(
    version="0.1.0",
    reason="shipyard.pulse.Setup is deprecated use shipyard.Setup instead.\n"
    "use setup.get_serial(port) instead of setup.ports[port].instrument.serial\n"
    "use setup.get_core_index(port) instead of setup.ports[port].core.index - 1",
)
class Setup(SetupInternal):
    ...
