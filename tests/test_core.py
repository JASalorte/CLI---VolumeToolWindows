import random
import string

import pytest
from _ctypes import COMError

from audio_tool import core, VolumeResult, set_volume_by_name
from audio_tool.core import VolumeError

# region Setup mocks
# Standard mock sessions result
fake_sessions_standard = [
    core.SessionInfo(pos=0, name="Spotify", volume=0.5),
    core.SessionInfo(pos=1, name="Discord", volume=0.75),
    core.SessionInfo(pos=2, name="Steam", volume=0.99),
]

# Sessions returning an empty list
fake_sessions_none = []

# Excessively large sessions result
fake_sessions_large = []
for idx in range(1000):
    fake_sessions_large.append(core.SessionInfo(pos=idx, name=''.join(random.choices(string.ascii_letters + string.digits, k=10)), volume=round(random.uniform(0.0, 1.0),2)))

# Sessions resulting duplicates
fake_sessions_duplicate = [
    core.SessionInfo(pos=0, name="Discord", volume=0.75),
    core.SessionInfo(pos=1, name="Discord", volume=0.75),
    core.SessionInfo(pos=2, name="Firefox", volume=0.2),
    core.SessionInfo(pos=3, name="Steam", volume=0.99),
    core.SessionInfo(pos=4, name="Steam", volume=0.84),
]

# Sessions returning unexpected data
fake_sessions_unexpected = [
    core.SessionInfo(pos=0, name="Spotify", volume=-15),
    core.SessionInfo(pos=1, name="Firefox", volume=-23.4),
    core.SessionInfo(pos=2, name="Discord", volume=256.7),
    core.SessionInfo(pos=3, name="Chrome", volume=56),
    core.SessionInfo(pos=4, name="Steam", volume=None),
    core.SessionInfo(pos=5, name='', volume=None),
]
#endregion


#region Tests _set_volume_by_name
@pytest.mark.parametrize(
    "side_effect, expected_result",
    [
        # Success path: no error, should return VolumeResult with volume=0.5
        (
            None,
            core.VolumeResult(volume=0.5, name="System sounds", error=None)
        ),

        # Failure path: COMError raised, should return FAILED
        (
            COMError(42, "Unspecified error", None),
            core.VolumeResult(volume=None, name="System sounds", error=core.VolumeError.FAILED),
        ),

    ],
    ids=[
        "success",
        "COM error",
    ]
)
def test__set_volume_by_name_system_sounds_cases(mocker, side_effect, expected_result):
    fake_session = mocker.MagicMock()
    fake_session.Process = None  # System Sounds case

    mock_interface = fake_session._ctl.QueryInterface.return_value
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
                core.VolumeResult(volume=0.8, name="Discord.exe", error=None),
        ),
        # Case-insensitive random match → success
        (
                "dIsCoRd.ExE",
                "Discord.exe",
                None,
                core.VolumeResult(volume=0.8, name="Discord.exe", error=None),
        ),
        # Case-insensitive lowercase match → success
        (
                "discord.exe",
                "Discord.exe",
                None,
                core.VolumeResult(volume=0.8, name="Discord.exe", error=None),
        ),
        # Case-insensitive uppercase match → success
        (
                "DISCORD.EXE",
                "Discord.exe",
                None,
                core.VolumeResult(volume=0.8, name="Discord.exe", error=None),
        ),
        # No match at all → NOT_FOUND
        (
                "Spotify.exe",
                "Discord.exe",
                None,
                core.VolumeResult(volume=None, name="Spotify.exe", error=core.VolumeError.NOT_FOUND),
        ),
        # Match, but COMError → FAILED
        (
                "Discord.exe",
                "Discord.exe",
                COMError(42, "Unspecified error", None),
                core.VolumeResult(volume=None, name="Discord.exe", error=core.VolumeError.FAILED),
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
def test__set_volume_by_name_app_cases(mocker, search_name, session_name, side_effect, expected_result):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = session_name

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.SetMasterVolume.side_effect = side_effect

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.set_volume_by_name(search_name, 0.8)

    if side_effect is None and expected_result.error is None:
        # Only assert call if success was expected
        mock_interface.SetMasterVolume.assert_called_once_with(0.8, None)

    assert result == expected_result
#endregion

#region Tests _normalize_volume
def test__normalize_volume_valid_inputs():
    assert core._normalize_volume(0) == 0.0
    assert core._normalize_volume(1) == 0.01
    assert core._normalize_volume(100) == 1.0
    assert core._normalize_volume(50) == 0.5
    assert core._normalize_volume("25") == 0.25
    assert core._normalize_volume("2.7") == 1.0
    assert core._normalize_volume("0.3") == 0.3
    assert core._normalize_volume(0.75) == 0.75
    assert core._normalize_volume(150) == 1.0
    assert core._normalize_volume(2.3) == 1.0
    assert core._normalize_volume(-5) == 0.0
    assert core._normalize_volume(-18.6) == 0.0

def test__normalize_volume_invalid_inputs():
    assert core._normalize_volume("abc") is None
    assert core._normalize_volume('') is None
    assert core._normalize_volume('asd') is None
    assert core._normalize_volume('AS!"&/(!··^*ASD^*\nasd') is None
    assert core._normalize_volume(None) is None
    assert core._normalize_volume(True) is None
    assert core._normalize_volume(False) is None
    assert core._normalize_volume([]) is None
    assert core._normalize_volume({}) is None
#endregion

#region Test set_volume_by_name
#Simple “helper orchestration” test, no really that useful
def test_set_volume_by_name_calls_helpers(mocker):
    mock_norm = mocker.patch("audio_tool.core._normalize_volume", return_value=0.5)

    fake_result = VolumeResult(name="Discord.exe",volume=0.5)
    mock_set = mocker.patch("audio_tool.core._set_volume_by_name", return_value=fake_result)

    result = set_volume_by_name("discord.exe", 50)

    mock_norm.assert_called_once_with(50)
    mock_set.assert_called_once_with("discord.exe", 0.5)
    assert result == fake_result

@pytest.mark.parametrize(
    "input_app, input_volume, expected",
    [
        ("Discord.exe", 0.5, VolumeResult(name="Discord.exe", volume=0.5)),
        ("Discord.exe", 50, VolumeResult(name="Discord.exe", volume=0.5)),
        ("Discord.exe", 150, VolumeResult(name="Discord.exe", volume=1.0)),
        ("Discord.exe", -23.7, VolumeResult(name="Discord.exe", volume=0.0)),
        ("Discord.exe", None, VolumeResult(name="Discord.exe", error=VolumeError.INVALID_INPUT)),
        ("Discord.exe", True, VolumeResult(name="Discord.exe", error=VolumeError.INVALID_INPUT)),
        ("Spotify.exe", 0.5, VolumeResult(name="Spotify.exe", error=VolumeError.NOT_FOUND)),
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
def test_set_volume_by_name_inputs_param(mocker, input_app, input_volume, expected):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Discord.exe"

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])


    result = set_volume_by_name(input_app, input_volume)

    assert result.name == expected.name
    assert result.volume == pytest.approx(expected.volume)
    assert result.error == expected.error
#endregion

#region Tests list_sessions
def test_list_sessions_standard(mocker):

    # Patch list_sessions to return standard case fake data
    mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_standard)
    result = core.list_sessions_verbose(list_pos=True)

    # Check that the formatting logic works
    assert result[0][0] == "0 - Spotify: 0.50"
    assert result[1][0] == "1 - Discord: 0.75"
    assert result[2][0] == "2 - Steam: 0.99"

    # Check that the raw SessionInfo is preserved
    assert isinstance(result[1][1], core.SessionInfo)
    assert result[1][1].name == "Discord"
    assert abs(result[1][1].volume - 0.75) == 0.0

def test_list_sessions_empty(mocker):
    mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_none)
    result = core.list_sessions_verbose(list_pos=True)
    assert result == []
    assert len(result) == 0

def test_list_sessions_large(mocker):
    mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_large)
    result = core.list_sessions_verbose(list_pos=True)

    assert len(result) == 1000
    # Just check that formatting didn’t break
    for formatted, raw in result:
        assert isinstance(formatted, str)
        assert isinstance(raw, core.SessionInfo)

def test_list_sessions_duplicates(mocker):
    mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_duplicate)
    result = core.list_sessions_verbose(list_pos=True)

    # Ensure duplicates are preserved (important for debugging real-world apps)
    assert result[1][0] == "1 - Discord: 0.75"
    assert result[3][0] == "3 - Steam: 0.99"
    assert result[4][0] == "4 - Steam: 0.84"

def test_list_sessions_unexpected(mocker):
    mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_unexpected)
    result = core.list_sessions_verbose(list_pos=True)

    assert result[0][0] == "0 - Spotify: -15.00"
    assert result[1][0] == "1 - Firefox: -23.40"
    assert result[2][0] == "2 - Discord: 256.70"
    assert result[3][0] == "3 - Chrome: 56.00"
    assert result[4][0] == "4 - Steam: N/A" # empty volume preserved
    assert result[5][0] == "5 - N/A: N/A"   # empty name preserved
#endregion