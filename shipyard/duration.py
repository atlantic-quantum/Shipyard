"""
Duration is a class for managing durations in openQASM Programs.
"""
from enum import Enum

from pydantic import BaseModel


# pylint: disable=C0103
# UPPER_CASE naming stype
# pylint: disable=C2401
# non ascii name
class TimeUnits(Enum):
    """
    Enumerations of common time units
        ns, µs, us, ms, s

        and

        dt = 0.5e-9 <- timestep @ 2GS/s
    """

    dt = 0.5e-9
    ns = 1e-9
    µs = 1e-6
    us = 1e-6
    ms = 1e-3
    s = 1


# pylint: enable=C0103
# pylint: enable=C2401


class Duration(BaseModel):
    """
    pydantic model for managing times/durations in openQASM programs

    Durations have both time and unit (ns, us, ms, s) (and dt which represents sample
    time at 2GS/s)

    Durations can be added to other Durations or numbers (int, float), they can also
    be compared to one another or to numbers (int, float)

    the native max/min python operations work with lists of Durations.

    The unit of a Duration can be changed using the 'set_unit' method.
    """

    # todo consider rounding to nearest ps/fs to avoid floating point errors.
    time: float
    unit: TimeUnits = TimeUnits.dt

    def set_unit(self, unit: TimeUnits):
        """
        Changes the unit of the Duration and updates the time to be represented in the
        new unit.

            Example:
                dur = Duration(time=100, unit=TimeUnits.ns)
                dur.set_unit(TimeUnits.us)

            # dur -> Duration(time=0.1, unit=TimeUnits.us)
        """
        self.time = self.time * self.unit.value / unit.value
        self.unit = unit

    def _real_time(self) -> float:
        """Calculates the time in seconds

        Returns:
            float: time in seconds
        """
        return self.time * self.unit.value

    def __add__(self, other):  # (self, other: Self) -> Self
        """
        Adds Durations together or a number to a Duration

            Example (two Durations):
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = Duration(time=0.1, unit=TimeUnits.us)
                dur3 = dur1 + dur2  # dur3 -> Duration(time=101, unit=TimeUnits.ns)
                dur4 = dur2 + dur1  # dur3 -> Duration(time=0.101, unit=TimeUnits.us)

            Example (Duration and int or float):
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = dur1 + 10e-9  # dur2 -> Duration(time=11, unit.TimeUnits.ns)

        Args:
            other (Duration | int | float): the Duration or number to add to this
            duration

        Raises:
            ValueError: if 'other' is not a Durration, int or float

        Returns:
            Duration: sum of this Duration and other
        """
        if isinstance(other, Duration):
            return Duration(
                time=self.time + other.time * other.unit.value / self.unit.value,
                unit=self.unit,
            )
        if isinstance(other, (int, float)):
            return Duration(time=self.time + other / self.unit.value, unit=self.unit)
        raise ValueError(f"'+' not supported between {type(self)} and {type(other)}")

    def __radd__(self, other):
        """
        right addition, allows Durations to be added to numbers
        addition of Durations is complimentary

        Args:
            other (int | float): number Duration is being added to

        Returns:
            Duration: sum of this Duration and other
        """
        return self.__add__(other)

    def __str__(self) -> str:
        """
        Formats how Durations are printed
            Example:
                dur = Duration(time=16, unit=TimeUnits.ns)
                print(dur) -> '16 ns'

        Returns:
            str: formated string representation of Duration
        """
        return f"{self.time} {self.unit.name}"

    def __lt__(self, other) -> bool:  # (self, other: Self) -> bool:
        """
        Compares if this Duration is lower than another Duration, int or Float

            Example:
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = Duration(time=0.1, unit=TimeUnits.us)

                dur1 < dur2 -> True
                dur < 2 -> False
                dur < 0.1 -> False

        Args:
            other (Duration | int | float): to compare to

        Raises:
            ValueError: if other is not a Duration, int or float

        Returns:
            bool:
                True if _real_time() value of this duration is lower than other,
                else False.
        """
        if isinstance(other, Duration):
            return self._real_time() < other._real_time()
        if isinstance(other, (int, float)):
            return self._real_time() < other
        raise ValueError(f"'<' not supported between {type(self)} and {type(other)}")

    def __gt__(self, other) -> bool:  # (self, other: Self) -> bool:
        """
        Compares if this Duration is greater than another Duration, int or Float

            Example:
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = Duration(time=0.1, unit=TimeUnits.us)

                dur1 > dur2 -> False
                dur > 2 -> False
                dur > 0.1e-9 -> True

        Args:
            other (Duration | int | float): to compare to

        Raises:
            ValueError: if other is not a Duration, int or float

        Returns:
            bool:
                True if _real_time() value of this duration is greater than other,
                else False.
        """
        if isinstance(other, Duration):
            return self._real_time() > other._real_time()
        if isinstance(other, (int, float)):
            return self._real_time() > other
        raise ValueError(f"'>' not supported between {type(self)} and {type(other)}")

    def __eq__(self, other) -> bool:  # (self, other: Self) -> bool:
        """
        Compares if this Duration is equal to another Duration, int or Float

            Example:
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = Duration(time=0.1, unit=TimeUnits.us)

                dur1 == dur2 -> False
                dur1 == dur1 -> True
                dur == 1e-9 -> True

        Args:
            other (Duration | int | float): to compare to

        Raises:
            ValueError: if other is not a Duration, int or float

        Returns:
            bool:
                True if _real_time() value of this duration is equal to other,
                else False.
        """
        if isinstance(other, Duration):
            return self._real_time() == other._real_time()
        if isinstance(other, (int, float)):
            return self._real_time() == other
        raise ValueError(f"'==' not supported between {type(self)} and {type(other)}")

    def __ne__(self, other) -> bool:  # (self, other: Self) -> bool:
        """
        Compares if this Duration is not equal to another Duration, int or Float

            Example:
                dur1 = Duration(time=1, unit=TimeUnits.ns)
                dur2 = Duration(time=0.1, unit=TimeUnits.us)

                dur1 != dur2 -> True
                dur1 != dur1 -> False
                dur != 1e-9 -> False

        Args:
            other (Duration | int | float): to compare to

        Raises:
            ValueError: if other is not a Duration, int or float

        Returns:
            bool:
                True if _real_time() value of this duration is equal to other,
                else False.
        """
        if isinstance(other, Duration):
            return self._real_time() != other._real_time()
        if isinstance(other, (int, float)):
            return self._real_time() != other
        raise ValueError(f"'!=' not supported between {type(self)} and {type(other)}")
