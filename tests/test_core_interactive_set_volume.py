import builtins
import pytest
from audio_tool import core
from audio_tool.core import VolumeResult, VolumeError, SessionInfo


@pytest.mark.parametrize(
    "inputs, sessions, expected",
    [
        # Invalid position input (non-integer)
        (["abc", "50"], [("0 - Discord.exe: 1.00", SessionInfo(pos=0, name="Discord.exe", volume=1.0,muted=False))], [VolumeResult(error=VolumeError.INVALID_INPUT)]),

        # Position out of range
        (["10", "50"], [("0 - Discord.exe: 1.00", SessionInfo(pos=0, name="Discord.exe", volume=1.0,muted=False))], [VolumeResult(error=VolumeError.INVALID_POSITION)]),

        # None volume (unlikely, but good edge test)
        (["0", None], [("0 - Discord.exe: 1.00", SessionInfo(pos=0, name="Discord.exe", volume=1.0,muted=False))], [VolumeResult(error=VolumeError.INVALID_INPUT)]),

        # Valid selection, set_volume_by_name success
        (["0", "50"], [("0 - Discord.exe: 1.00", VolumeResult(name="Discord.exe"))], [VolumeResult(name="Discord.exe", volume=0.5)]),
    ],
)
def test_interactive_set_volume(monkeypatch, mocker, inputs, sessions, expected):
    # Mock list_sessions_verbose to return your fake sessions
    mocker.patch("audio_tool.core.list_sessions_verbose", return_value=sessions)

    # Mock set_volume_by_name to just return a VolumeResult with volume=0.5
    mocker.patch("audio_tool.core.set_volume_by_name",return_value=[VolumeResult(name="Discord.exe", volume=0.5)])

    # Replace input() with our predefined sequence
    monkeypatch.setattr(builtins, "input", lambda _: inputs.pop(0))

    result = core._interactive_set_volume()
    assert result == expected
