import pytest

from audio_tool import core, VolumeResult
from audio_tool.core import VolumeError


class TestToggleVolumeValidation:

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "", None, 123, "   ", [], {}, object()
        ]
    )
    def test_toggle_volume_invalid_input_returns_error(self, invalid_input):
        result = core.toggle_volume(invalid_input)
        assert result == [VolumeResult(name=str(invalid_input), error=VolumeError.INVALID_INPUT)]

    def test_toggle_volume_ignores_whitespace(self, mocker, mock_session):
        fake = mock_session("Discord.exe")
        mocker.patch("audio_tool.core.get_sessions", return_value=[fake])
        fake.SimpleAudioVolume.GetMute.return_value = 0

        result = core.toggle_volume("   discord.exe   ")
        assert result == [VolumeResult(name="Discord.exe", muted=True)]


class TestToggleVolumeLogic:
    """Covers core.toggle_volume under normal and error conditions."""
    @pytest.mark.parametrize(
        "sessions, result_expected",
        [
            ([], [VolumeResult(name="discord.exe", error=VolumeError.NOT_FOUND)]),
            ([("Discord.exe", 0)], [VolumeResult(name="Discord.exe", muted=True)]),
            ([("Discord.exe", 0), ("Discord.exe", 1)], [VolumeResult(name="Discord.exe", muted=True), VolumeResult(name="Discord.exe", muted=True)]),
            ([("Discord.exe", 1), ("Discord.exe", 1)], [VolumeResult(name="Discord.exe", muted=False), VolumeResult(name="Discord.exe", muted=False)]),
            ([("Discord.exe", 0), ("Discord.exe", 0)], [VolumeResult(name="Discord.exe", muted=True), VolumeResult(name="Discord.exe", muted=True)]),
            ([("Spotify.exe", 0), ("Discord.exe", 1)], [VolumeResult(name="Discord.exe", muted=False)]),
            ([("Discord.exe", 0), ("Spotify.exe", 1)], [VolumeResult(name="Discord.exe", muted=True)]),
        ],
        ids=[
            "not_found",
            "exact_success",
            "one_match_mute_all",
            "no_match_unmute",
            "all_match_mute_all",
            "exact_match_in_list_unmute",
            "exact_match_in_list_mute"
        ]
    )
    def test_toggle_volume(self, mocker, mock_session, sessions ,result_expected):
        fake_sessions = []
        for name, mute in sessions:
            s = mock_session(name)
            s.SimpleAudioVolume.GetMute.return_value = mute
            fake_sessions.append(s)

        mocker.patch("audio_tool.core.get_sessions", return_value=fake_sessions)

        result = core.toggle_volume("discord.exe")

        for s in fake_sessions:
            if s.Process and s.Process.name() == "Discord.exe":
                s.SimpleAudioVolume.SetMute.assert_called_once()

        assert result == result_expected
