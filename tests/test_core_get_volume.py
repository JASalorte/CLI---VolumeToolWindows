import pytest
from _ctypes import COMError

from audio_tool import core, get_volume_by_name, VolumeResult
from audio_tool.core import VolumeError

class TestGetVolumeByName:
    """Covers core.set_volume_by_name under normal and error conditions."""

    def test_get_volume_by_name_input_validation(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = "Discord.exe"

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.GetMasterVolume.return_value = 0.5
        mock_interface.GetMute.return_value = 0

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        assert get_volume_by_name("discord.exe") == [VolumeResult(volume=0.5,muted=False,name='Discord.exe')]
        assert get_volume_by_name(None) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="None")]
        assert get_volume_by_name(0.5) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="0.5")]
        assert get_volume_by_name(-59) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="-59")]
        assert get_volume_by_name([]) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="[]")]
        assert get_volume_by_name({}) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="{}")]
        assert get_volume_by_name(False) == [VolumeResult(error=VolumeError.INVALID_INPUT, name="False")]

    def test_get_volume_by_name_system_sounds_success(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process = None  # System Sounds case

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.GetMasterVolume.return_value = 0.5
        mock_interface.GetMute.return_value = 0

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        result = core.get_volume_by_name("system sounds")

        # Verify SetMasterVolume was always called
        mock_interface.GetMasterVolume.assert_called_once_with()

        # Compare result with expected
        assert result == [core.VolumeResult(volume=0.5,muted=False, name="System sounds")]

    def test_get_volume_by_name_system_sounds_com_error(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process = None  # System Sounds case

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.GetMasterVolume.side_effect = COMError(42, "Unspecified error", None)

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        result = core.get_volume_by_name("System sounds")

        # Verify SetMasterVolume was always called
        mock_interface.GetMasterVolume.assert_called_once_with()

        # Compare result with expected
        assert result == [core.VolumeResult(volume=None, name="System sounds", error=core.VolumeError.FAILED)]

    def test_get_volume_by_name_multiple_matches(self, mocker):
        fake_session1 = mocker.MagicMock()
        fake_session1.Process.name.return_value = "Discord.exe"
        fake_session1.SimpleAudioVolume.GetMasterVolume.return_value = 0.3
        fake_session1.SimpleAudioVolume.GetMute.return_value = 0

        fake_session2 = mocker.MagicMock()
        fake_session2.Process.name.return_value = "Discord.exe"
        fake_session2.SimpleAudioVolume.GetMasterVolume.return_value = 0.8
        fake_session2.SimpleAudioVolume.GetMute.return_value = 0

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session1, fake_session2])

        result = core.get_volume_by_name("Discord.exe")

        # Both matches are returned in order
        assert result[0] == core.VolumeResult(volume=0.3, muted=False, name="Discord.exe")
        assert result[1] == core.VolumeResult(volume=0.8, muted=False, name="Discord.exe")


    @pytest.mark.parametrize(
        "session_name, query, expected_result",
        [
            # Success path: matches case-insensitive, volume returned
            (
                "Discord.exe",
                "Discord.exe",
                [core.VolumeResult(volume=0.65, muted=False, name="Discord.exe")]
            ),
            (
                "Discord.exe",
                "discord.exe",
                [core.VolumeResult(volume=0.65, muted=False, name="Discord.exe")]
            ),
            (
                "Discord.exe",
                "DISCORD.EXE",
                [core.VolumeResult(volume=0.65, muted=False, name="Discord.exe")]
            ),
            (
                "Discord.exe",
                "DiScOrD.EXE",
                [core.VolumeResult(volume=0.65, muted=False, name="Discord.exe")]
            ),
            # Not found path: no session matches query
            (
                "Spotify.exe",
                "Discord.exe",
                [core.VolumeResult(name="Discord.exe", error=core.VolumeError.NOT_FOUND)]
            ),
        ],
        ids=[
            "regular success",
            "lowercase match",
            "uppercase match",
            "random case match",
            "not-found",
        ]
    )
    def test_get_volume_by_name_app_cases(self, mocker, session_name, query, expected_result):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = session_name

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.GetMasterVolume.return_value = 0.65
        mock_interface.GetMute.return_value = 0

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        result = core.get_volume_by_name(query)

        assert result == expected_result

    def test_get_volume_by_name_app_comerror(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = "Discord.exe"

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.GetMasterVolume.side_effect = COMError(42, "Unspecified error", None)

        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        result = core.get_volume_by_name("Discord.exe")

        assert result == [core.VolumeResult(volume=None, name="Discord.exe", error=core.VolumeError.FAILED)]

    def test_get_volume_by_name_process_name_none(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = None
        mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

        result = core.get_volume_by_name("Discord.exe")

        assert len(result) == 1
        assert result[0].error == core.VolumeError.NOT_FOUND
#endregion