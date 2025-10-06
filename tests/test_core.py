import random
import string

import pytest
from _ctypes import COMError

from audio_tool import core, VolumeResult, set_volume_by_name, get_volume_by_name
from audio_tool.core import VolumeError

@pytest.fixture
def mock_session(mocker):
    def _make(app_name="Discord.exe"):
        s = mocker.MagicMock()
        if app_name is not None:
            s.Process = mocker.MagicMock()
            s.Process.name.return_value = app_name
        else:
            s.Process = None    # for System sounds case
        return s
    return _make


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

#region Test get_volume_by_name()
def test_get_volume_by_name_input_validation(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Discord.exe"

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.GetMasterVolume.return_value = 0.5

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    assert get_volume_by_name("discord.exe") == [VolumeResult(volume=0.5,name='Discord.exe',error=None)]
    assert get_volume_by_name(None) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]
    assert get_volume_by_name(0.5) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]
    assert get_volume_by_name(-59) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]
    assert get_volume_by_name([]) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]
    assert get_volume_by_name({}) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]
    assert get_volume_by_name(False) == [VolumeResult(volume=None, name=None, error=VolumeError.INVALID_INPUT)]

def test_get_volume_by_name_system_sounds_success(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process = None  # System Sounds case

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.GetMasterVolume.return_value = 0.5

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.get_volume_by_name("system sounds")

    # Verify SetMasterVolume was always called
    mock_interface.GetMasterVolume.assert_called_once_with()

    # Compare result with expected
    assert result == [core.VolumeResult(volume=0.5, name="System sounds", error=None)]

def test_get_volume_by_name_system_sounds_com_error(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process = None  # System Sounds case

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.GetMasterVolume.side_effect = COMError(42, "Unspecified error", None)

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.get_volume_by_name("System sounds")

    # Verify SetMasterVolume was always called
    mock_interface.GetMasterVolume.assert_called_once_with()

    # Compare result with expected
    assert result == [core.VolumeResult(volume=None, name="System sounds", error=core.VolumeError.FAILED)]

def test_get_volume_by_name_multiple_matches(mocker):
    fake_session1 = mocker.MagicMock()
    fake_session1.Process.name.return_value = "Discord.exe"
    fake_session1._ctl.QueryInterface.return_value.GetMasterVolume.return_value = 0.3

    fake_session2 = mocker.MagicMock()
    fake_session2.Process.name.return_value = "Discord.exe"
    fake_session2._ctl.QueryInterface.return_value.GetMasterVolume.return_value = 0.8

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session1, fake_session2])

    result = core.get_volume_by_name("Discord.exe")

    # Both matches are returned in order
    assert result[0] == core.VolumeResult(volume=0.3, name="Discord.exe", error=None)
    assert result[1] == core.VolumeResult(volume=0.8, name="Discord.exe", error=None)


@pytest.mark.parametrize(
    "session_name, query, expected_result",
    [
        # Success path: matches case-insensitive, volume returned
        (
            "Discord.exe",
            "Discord.exe",
            [core.VolumeResult(volume=0.65, name="Discord.exe", error=None)]
        ),
        (
            "Discord.exe",
            "discord.exe",
            [core.VolumeResult(volume=0.65, name="Discord.exe", error=None)]
        ),
        (
            "Discord.exe",
            "DISCORD.EXE",
            [core.VolumeResult(volume=0.65, name="Discord.exe", error=None)]
        ),
        (
            "Discord.exe",
            "DiScOrD.EXE",
            [core.VolumeResult(volume=0.65, name="Discord.exe", error=None)]
        ),
        # Not found path: no session matches query
        (
            "Spotify.exe",
            "Discord.exe",
            [core.VolumeResult(volume=None, name="Discord.exe", error=core.VolumeError.NOT_FOUND)]
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
def test_get_volume_by_name_app_cases(mocker, session_name, query, expected_result):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = session_name

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.GetMasterVolume.return_value = 0.65

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.get_volume_by_name(query)

    assert result == expected_result

def test_get_volume_by_name_app_comerror(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Discord.exe"

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.GetMasterVolume.side_effect = COMError(42, "Unspecified error", None)

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.get_volume_by_name("Discord.exe")

    assert result == [core.VolumeResult(volume=None, name="Discord.exe", error=core.VolumeError.FAILED)]

def test_get_volume_by_name_process_name_none(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = None
    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.get_volume_by_name("Discord.exe")

    assert len(result) == 1
    assert result[0].error == core.VolumeError.NOT_FOUND
#endregion

#region Tests _set_volume_by_name
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
def test__set_volume_by_name_app_cases(mocker, search_name, session_name, side_effect, expected_result):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = session_name

    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.SetMasterVolume.side_effect = side_effect

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.set_volume_by_name(search_name, 0.8)

    if side_effect is None and expected_result[0].error is None:
        # Only assert call if success was expected
        mock_interface.SetMasterVolume.assert_called_once_with(0.8, None)

    assert result == expected_result

def test_set_volume_by_name_process_name_none(mocker):
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = None
    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = core.set_volume_by_name("Discord.exe",0.5)

    assert len(result) == 1
    assert result[0].error == core.VolumeError.NOT_FOUND

def test_set_volume_by_name_multiple_matches(mocker):
    # Create two independent fake sessions
    fake_session1 = mocker.MagicMock()
    fake_session1.Process.name.return_value = "Discord.exe"
    mock_interface1 = fake_session1._ctl.QueryInterface.return_value

    fake_session2 = mocker.MagicMock()
    fake_session2.Process.name.return_value = "Discord.exe"
    mock_interface2 = fake_session2._ctl.QueryInterface.return_value

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
def test_set_volume_by_name_calls_helpers(mocker, mock_session):
    mock_norm = mocker.patch("audio_tool.core._normalize_volume", return_value=0.3)

    # Use fixture twice
    fake_session1 = mock_session()
    fake_session2 = mock_session()

    mock_interface1 = fake_session1._ctl.QueryInterface.return_value
    mock_interface1.SetMasterVolume.return_value = None

    mock_interface2 = fake_session2._ctl.QueryInterface.return_value
    mock_interface2.SetMasterVolume.return_value = None

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session1, fake_session2])

    # --- all_matches=True (both sessions updated) ---
    result_multiple = set_volume_by_name("discord.exe", 30, True)

    mock_norm.assert_called_with(30)
    fake_session1._ctl.QueryInterface.return_value.SetMasterVolume.assert_called_once_with(0.3, None)
    fake_session2._ctl.QueryInterface.return_value.SetMasterVolume.assert_called_once_with(0.3, None)
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
def test_set_volume_by_name_inputs_param(mocker, input_app, input_volume, expected, mock_session):
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
def test_set_volume_by_name_parametrized(mocker, mock_session, app_name, query_name, expected_name):
    fake_session = mock_session(app_name)
    mock_interface = fake_session._ctl.QueryInterface.return_value
    mock_interface.SetMasterVolume.return_value = None

    mocker.patch("audio_tool.core.get_sessions", return_value=[fake_session])

    result = set_volume_by_name(query_name, 53, False)

    assert len(result) == 1
    assert result[0].name == expected_name
    if app_name is not None:
        fake_session.Process.name.assert_called()                       # verify name was actually accessed
    mock_interface.SetMasterVolume.assert_called_once_with(0.53, None)   # normalized value

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
    assert result[5][1].name == ""
    assert result[5][1].volume is None
#endregion