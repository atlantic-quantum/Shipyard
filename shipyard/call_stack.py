"""
Call Stack for shipyard
"""
from enum import Enum

from .logger import LOGGER


class ARType(Enum):
    """
    Enumeration of Acivation Record Types
    """

    PROGRAM = "PROGRAM"
    EXTERN = "EXTERN"
    SUBROUTINE = "SUBROUTINE"
    CALIBRATION = "CALIBRATION"
    DEFCAL = "DEFCAL"
    GATE = "GATE"
    LOOP = "LOOP"


class ActivationRecord:
    """Activation Records for shipyard"""

    def __init__(
        self,
        name: str,
        ar_type: ARType,
        nesting_level: int,
    ):
        self.name = name
        self.type = ar_type
        self.nesting_level = nesting_level
        self.members = {}

    def __setitem__(self, key, value):
        self.members[key] = value
        LOGGER.debug("%s: %s", key, value)

    def __getitem__(self, key):
        return self.members[key]

    def get(self, key, default=None):
        """Gets a member of the activation record by key"""
        return self.members.get(key, default)

    def __str__(self):
        lines = [f"{self.nesting_level}: {self.type.value} {self.name}"]
        for name, val in self.members.items():
            lines.append(f"   {name:<20}: {val}")

        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()


class CallStack:
    """
    CallStack for the shipyard
    """

    def __init__(self):
        self._records = []

    def push(self, activation_record: ActivationRecord):
        """
        Pushes records onto the top of the call stack

        Args:
            activation_record (ActivationRecord): record to put on top of the stack
        """
        self._records.append(activation_record)

    def pop(self) -> ActivationRecord:
        """
        Pops the latest record of the call stack and returns it

        Returns:
            ActivationRecord: latest activation record on the stack
        """
        return self._records.pop()

    def peek(self) -> ActivationRecord:
        """
        returns the latest record of the call stack

        Returns:
            ActivationRecord: latest activation record on the stack
        """
        return self._records[-1]

    def down_stack(self, name: str) -> ActivationRecord:
        """
        Searches the stack for an activation record containing the name
        """
        for record in reversed(self._records):
            if name in record.members.keys():
                return record
        raise KeyError(f"Could not find {name} in call stack")

    def get(self, name: str):
        return self.down_stack(name)[name]

    @property
    def nesting_level(self):
        return self.peek().nesting_level

    def __str__(self):
        string = "\n".join(repr(actr) for actr in reversed(self._records))
        string = f"CALL STACK\n{string}\n"
        return string

    def __repr__(self):
        return self.__str__()
