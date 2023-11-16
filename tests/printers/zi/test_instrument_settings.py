import pytest

from shipyard.printers.zi.instrument_settings import HDCORE


def test_output():
    output = HDCORE.Output(output=2)

    assert len(output.settings(2)) == 4
    assert output.settings(1)[0] == ("/SIGOUTS/1/ON", 1)
    assert output.settings(1)[1] == ("/SIGOUTS/1/RANGE", 5.0)
    assert output.settings(1)[2] == ("/SIGOUTS/1/DIRECT", 0)
    assert output.settings(1)[3] == ("/AWGS/0/OUTPUTS/1/HOLD", 1)


@pytest.mark.parametrize(
    "channel, output, expected",
    [
        (1, 1, 0),
        (1, 2, 1),
        (2, 1, 2),
        (2, 2, 3),
        (3, 1, 4),
        (3, 2, 5),
        (4, 1, 6),
        (4, 2, 7),
    ],
)
def test_output_to_physical_channel(channel: int, output: int, expected: int):
    settings = HDCORE.Output(output=output).settings(channel)
    assert settings[0] == (f"/SIGOUTS/{expected}/ON", 1)
    assert settings[3] == (f"/AWGS/{channel-1}/OUTPUTS/{output-1}/HOLD", 1)


def test_hdcore_settings():
    hdcore = HDCORE(channel=1, outputs={1: HDCORE.Output(channel=1)})

    assert len(hdcore.settings()) == 4 + 3

    hdcore = HDCORE(
        channel=3, outputs={1: HDCORE.Output(channel=1), 2: HDCORE.Output(channel=2)}
    )
    assert len(hdcore.settings()) == 2 * 4 + 3
