
import pytest
from _ctypes import COMError

from audio_tool import set_volume_by_name, VolumeResult, core
from audio_tool.core import VolumeError

#region Test public API set_volume_by_name
class TestSetVolumeByName:
    """Covers core.set_volume_by_name under normal and error conditions."""

    def test_set_volume_by_name_calls_helpers(self, mocker, mock_session):
        mock_norm = mocker.patch("audio_tool.core._normalize_volume", return_value=0.3)

        # Use fixture twice
        fake_session1 = mock_session()
        fake_session2 = mock_session()

        mock_interface1 = fake_session1.SimpleAudioVolume
        mock_interface1.SetMasterVolume.return_value = None

        mock_interface2 = fake_session2.SimpleAudioVolume
        mock_interface2.SetMasterVolume.return_value = None

        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session1, fake_session2])

        # --- all_matches=True (both sessions updated) ---
        result_multiple = set_volume_by_name("discord.exe", 30, True)

        mock_norm.assert_called_with(30)
        fake_session1.SimpleAudioVolume.SetMasterVolume.assert_called_once_with(0.3, None)
        fake_session2.SimpleAudioVolume.SetMasterVolume.assert_called_once_with(0.3, None)
        assert result_multiple[0] == VolumeResult(volume=0.3, name="Discord.exe")
        assert result_multiple[1] == VolumeResult(volume=0.3, name="Discord.exe")

        # --- all_matches=False (only one updated) ---
        result_single = set_volume_by_name("discord.exe", 30, False)
        assert len(result_single) == 1
        assert result_single[0].name == "Discord.exe"

    @pytest.mark.parametrize(
        "input_app, input_volume, expected",
        [
            ("Discord.exe", 0.5, [VolumeResult(name="Discord.exe", volume=0.5)]),
            ("Discord.exe", 50, [VolumeResult(name="Discord.exe", volume=0.5)]),
            ("Discord.exe", 150, [VolumeResult(name="Discord.exe", volume=1.0)]),
            ("Discord.exe", -23.7, [VolumeResult(name="Discord.exe", volume=0.0)]),
            ("Discord.exe", None, [VolumeResult(name="Discord.exe", error=VolumeError.INVALID_INPUT)]),
            ("Discord.exe", True, [VolumeResult(name="Discord.exe", error=VolumeError.INVALID_INPUT)]),
            ("Spotify.exe", 0.5, [VolumeResult(name="Spotify.exe", error=VolumeError.NOT_FOUND)]),
        ],
        ids=[
            "exact_success",
            "int_volume_success",
            "int_volume_overrange_success",
            "float_volume_success",
            "None_volume_failure",
            "True_volume_failure",
            "App_not_found",
        ]
    )
    def test_set_volume_by_name_inputs_param(self, mocker, input_app, input_volume, expected, mock_session):
        fake_session = mock_session()


        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

        result = set_volume_by_name(input_app, input_volume)

        assert result[0].name == expected[0].name
        assert result[0].volume == pytest.approx(expected[0].volume)
        assert result[0].error == expected[0].error

    @pytest.mark.parametrize(
        "app_name, query_name, expected_name",
        [
            ("Discord.exe", "discord.exe", "Discord.exe"),      # normal case-insensitive
            ("Spotify.exe", "spotify.exe", "Spotify.exe"),      # another app
            (None, "system sounds", "System sounds"),           # system sounds
        ],
        ids=["discord", "spotify", "system_sounds"]
    )
    def test_set_volume_by_name_parametrized(self, mocker, mock_session, app_name, query_name, expected_name):
        fake_session = mock_session(app_name)
        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.SetMasterVolume.return_value = None

        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

        result = set_volume_by_name(query_name, 53, False)

        assert len(result) == 1
        assert result[0].name == expected_name
        if app_name is not None:
            fake_session.Process.name.assert_called()                       # verify name was actually accessed
        mock_interface.SetMasterVolume.assert_called_once_with(0.53, None)   # normalized value
    #endregion

    #region Tests private _set_volume_by_name
    @pytest.mark.parametrize(
        "side_effect, expected_result",
        [
            # Success path: no error, should return VolumeResult with volume=0.5
            (
                None,
                [core.VolumeResult(volume=0.5, name="System sounds", error=None)]
            ),

            # Failure path: COMError raised, should return FAILED
            (
                COMError(42, "Unspecified error", None),
                [core.VolumeResult(volume=None, name="System sounds", error=core.VolumeError.FAILED)],
            ),

        ],
        ids=[
            "success",
            "COM error",
        ]
    )
    def test__set_volume_by_name_system_sounds_cases(self, mocker, side_effect, expected_result):
        fake_session = mocker.MagicMock()
        fake_session.Process = None  # System Sounds case

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.SetMasterVolume.side_effect = side_effect

        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

        result = core.set_volume_by_name("System sounds", 0.5)

        # Verify SetMasterVolume was always called
        mock_interface.SetMasterVolume.assert_called_once_with(0.5, None)

        # Compare result with expected
        assert result == expected_result

    @pytest.mark.parametrize(
        "search_name, session_name, side_effect, expected_result",
        [
            # Exact match → success
            (
                    "Discord.exe",
                    "Discord.exe",
                    None,
                    [core.VolumeResult(volume=0.8, name="Discord.exe", error=None)],
            ),
            # Case-insensitive random match → success
            (
                    "dIsCoRd.ExE",
                    "Discord.exe",
                    None,
                    [core.VolumeResult(volume=0.8, name="Discord.exe", error=None)],
            ),
            # Case-insensitive lowercase match → success
            (
                    "discord.exe",
                    "Discord.exe",
                    None,
                    [core.VolumeResult(volume=0.8, name="Discord.exe", error=None)],
            ),
            # Case-insensitive uppercase match → success
            (
                    "DISCORD.EXE",
                    "Discord.exe",
                    None,
                    [core.VolumeResult(volume=0.8, name="Discord.exe", error=None)],
            ),
            # No match at all → NOT_FOUND
            (
                    "Spotify.exe",
                    "Discord.exe",
                    None,
                    [core.VolumeResult(volume=None, name="Spotify.exe", error=core.VolumeError.NOT_FOUND)],
            ),
            # Match, but COMError → FAILED
            (
                    "Discord.exe",
                    "Discord.exe",
                    COMError(42, "Unspecified error", None),
                    [core.VolumeResult(volume=None, name="Discord.exe", error=core.VolumeError.FAILED)],
            ),
        ],
        ids=[
            "exact_match_success",
            "case_insensitive_random_success",
            "case_insensitive_lowercase_success",
            "case_insensitive_uppercase_success",
            "not_found",
            "com_failure",
        ],
    )
    def test__set_volume_by_name_app_cases(self, mocker, search_name, session_name, side_effect, expected_result):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = session_name

        mock_interface = fake_session.SimpleAudioVolume
        mock_interface.SetMasterVolume.side_effect = side_effect

        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

        result = core.set_volume_by_name(search_name, 0.8)

        if side_effect is None and expected_result[0].error is None:
            # Only assert call if success was expected
            mock_interface.SetMasterVolume.assert_called_once_with(0.8, None)

        assert result == expected_result

    def test_set_volume_by_name_process_name_none(self, mocker):
        fake_session = mocker.MagicMock()
        fake_session.Process.name.return_value = None
        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

        result = core.set_volume_by_name("Discord.exe",0.5)

        assert len(result) == 1
        assert result[0].error == core.VolumeError.NOT_FOUND

    def test_set_volume_by_name_multiple_matches(self, mocker):
        # Create two independent fake sessions
        fake_session1 = mocker.MagicMock()
        fake_session1.Process.name.return_value = "Discord.exe"
        mock_interface1 = fake_session1.SimpleAudioVolume

        fake_session2 = mocker.MagicMock()
        fake_session2.Process.name.return_value = "Discord.exe"
        mock_interface2 = fake_session2.SimpleAudioVolume

        # Patch get_sessions to return both
        mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session1, fake_session2])

        result = core.set_volume_by_name("Discord.exe", 0.5, True)

        # Verify both sessions were updated
        mock_interface1.SetMasterVolume.assert_called_once_with(0.5, None)
        mock_interface2.SetMasterVolume.assert_called_once_with(0.5, None)

        # By current implementation: first one wins
        assert len(result) == 2
        assert result[0] == core.VolumeResult(volume=0.5, name="Discord.exe", error=None)
        assert result[1] == core.VolumeResult(volume=0.5, name="Discord.exe", error=None)
    #endregion