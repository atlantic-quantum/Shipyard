"""
Module for storing the experimental setup.

Contains both a model for external use and a model for internal use.
"""
from .external import SetupExternal as Setup
from .internal import Port, SetupInternal

__all__ = ["Port", "Setup", "SetupInternal"]
