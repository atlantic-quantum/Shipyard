import pytest
from numpy import allclose
from numpy.random import rand

from shipyard.duration import Duration, TimeUnits

TIME_UNITS = [
    TimeUnits.dt,
    TimeUnits.ns,
    TimeUnits.µs,
    TimeUnits.us,
    TimeUnits.ms,
    TimeUnits.s,
]


def test_duration_max_min():
    durations = [Duration(time=1, unit=unit) for unit in TIME_UNITS]
    assert max(durations) == durations[-1]
    assert min(durations) == durations[0]


@pytest.mark.parametrize("set_unit", TIME_UNITS)
@pytest.mark.parametrize("time_unit", TIME_UNITS)
def test_duration_basic(time_unit: TimeUnits, set_unit: TimeUnits):
    for i in range(-100, 100):
        duration = Duration(time=i, unit=time_unit)
        assert duration.time == i
        assert duration.unit == time_unit

        assert allclose(duration._real_time(), i * time_unit.value)

        duration.set_unit(set_unit)

        assert duration.time == i * time_unit.value / set_unit.value
        assert duration.unit == set_unit

        assert allclose(duration._real_time(), i * time_unit.value)


@pytest.mark.parametrize("rhs_unit", TIME_UNITS)
@pytest.mark.parametrize("lhs_unit", TIME_UNITS)
def test_duration_arithmetic(lhs_unit: TimeUnits, rhs_unit: TimeUnits):
    for _ in range(100):
        t1 = rand()
        t2 = rand()
        assert allclose(
            (
                Duration(time=t1, unit=lhs_unit) + Duration(time=t2, unit=lhs_unit)
            )._real_time(),
            Duration(time=t1 + t2, unit=lhs_unit)._real_time(),
        )

        assert allclose(
            (
                Duration(time=t1, unit=lhs_unit) + Duration(time=t2, unit=rhs_unit)
            )._real_time(),
            t1 * lhs_unit.value + t2 * rhs_unit.value,
        )

        assert allclose(
            (Duration(time=t1, unit=lhs_unit) + t2 * rhs_unit.value)._real_time(),
            (t1 * lhs_unit.value + Duration(time=t2, unit=rhs_unit))._real_time(),
        )


@pytest.mark.parametrize("unit", TIME_UNITS)
def test_duration_arihmetic_unsupported(unit):
    with pytest.raises(ValueError):
        Duration(time=1, unit=unit) + "string"

    with pytest.raises(ValueError):
        "string" + Duration(time=1, unit=unit)


@pytest.mark.parametrize("rhs_unit", TIME_UNITS)
@pytest.mark.parametrize("lhs_unit", TIME_UNITS)
def test_duration_comparison(lhs_unit: TimeUnits, rhs_unit: TimeUnits):
    assert (Duration(time=1, unit=lhs_unit) < Duration(time=1, unit=rhs_unit)) == (
        lhs_unit.value < rhs_unit.value
    )
    assert (Duration(time=1, unit=lhs_unit) > Duration(time=1, unit=rhs_unit)) == (
        lhs_unit.value > rhs_unit.value
    )
    assert (Duration(time=1, unit=lhs_unit) == Duration(time=1, unit=rhs_unit)) == (
        lhs_unit.value == rhs_unit.value
    )
    assert (Duration(time=1, unit=lhs_unit) != Duration(time=1, unit=rhs_unit)) == (
        lhs_unit.value != rhs_unit.value
    )

    assert (Duration(time=1, unit=lhs_unit) < rhs_unit.value) == (
        lhs_unit.value < Duration(time=1, unit=rhs_unit)
    )
    assert (Duration(time=1, unit=lhs_unit) > rhs_unit.value) == (
        lhs_unit.value > Duration(time=1, unit=rhs_unit)
    )
    assert (Duration(time=1, unit=lhs_unit) == rhs_unit.value) == (
        lhs_unit.value == Duration(time=1, unit=rhs_unit)
    )
    assert (Duration(time=1, unit=lhs_unit) != rhs_unit.value) == (
        lhs_unit.value != Duration(time=1, unit=rhs_unit)
    )


@pytest.mark.parametrize("lhs_unit", TIME_UNITS)
def test_duration_comparison_not_implemented(lhs_unit):
    with pytest.raises(ValueError):
        Duration(time=1, unit=lhs_unit) < "string"

    with pytest.raises(ValueError):
        Duration(time=1, unit=lhs_unit) > "string"

    with pytest.raises(ValueError):
        Duration(time=1, unit=lhs_unit) == "string"

    with pytest.raises(ValueError):
        Duration(time=1, unit=lhs_unit) != "string"

    with pytest.raises(ValueError):
        "string" < Duration(time=1, unit=lhs_unit)

    with pytest.raises(ValueError):
        "string" > Duration(time=1, unit=lhs_unit)

    with pytest.raises(ValueError):
        "string" == Duration(time=1, unit=lhs_unit)

    with pytest.raises(ValueError):
        "string" != Duration(time=1, unit=lhs_unit)


@pytest.mark.parametrize("unit", TIME_UNITS)
def test_duration_print(unit):
    for _ in range(100):
        n = rand()
        assert str(Duration(time=n, unit=unit)) == f"{n} {unit.name}"
