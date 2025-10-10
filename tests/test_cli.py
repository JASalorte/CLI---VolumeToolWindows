import runpy

import pytest
from audio_tool import cli, SessionInfo, VolumeResult
from audio_tool.core import VolumeError

def run_cli(mocker, capsys, args):
    mocker.patch("sys.argv", ["audio_tool"] + args)
    cli.main()
    return capsys.readouterr()

def test_list_command(mocker, capsys):
    """Ensure `list` prints the formatted session list."""
    mocker.patch("audio_tool.core.list_sessions", return_value = [
        (SessionInfo(pos=0,name="Discord.exe",muted=False,volume=1.0)),
        (SessionInfo(pos=1,name="Spotify.exe",muted=False,volume=0.5))
    ])

    out = run_cli(mocker, capsys, ["list"])

    out_text = out.out
    assert "Discord.exe: 1.0" in out_text
    assert "Spotify.exe: 0.5" in out_text

@pytest.mark.parametrize(
        "params, assert1, assert2",
        [
            # Success path:
            (
                ["0", "75"],
                "0 - Discord.exe: 0.99",
                "Volume of Discord.exe set to 75%"
            ),
            (
                ["0", "-598"],
                "0 - Discord.exe: 0.99",
                "Volume of Discord.exe set to 0%"
            ),
            (
                ["1", "-59"],
                "Application not found",
                "",
            ),
            (
                ["-3", "-59"],
                "Invalid device position",
                "",
            ),
            (
                [None, "abc"],
                "Invalid input",
                "",
            ),
            (
                ["0", "abc"],
                "Invalid input",
                "",
            ),
        ],
        ids=[
            "regular success",
            "success_with_wrong_volume",
            "app_not_found",
            "wrong_pos",
            "Invalid_input_pos",
            "Invalid input_volume",
        ]
    )
def test_select_command_params(mocker, monkeypatch, capsys, params, assert1, assert2):
    """Simulate selecting a session and setting volume interactively."""
    # Mock the sessions: [session_info]
    mocker.patch("audio_tool.core.list_sessions", return_value=[
        SessionInfo(pos=0, name="Discord.exe", muted=False, volume=0.99),
        SessionInfo(pos=1, name="Spotify.exe", muted=False, volume=0.5),
        SessionInfo(pos=2, name="Discord.exe", muted=False, volume=0.6),
    ])

    # Mock _interactive_set_volume() result
    inputs = iter(params)
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Discord.exe"
    mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

    out = run_cli(mocker, capsys, ["select"])

    out_text = out.out
    assert assert1 in out_text
    assert assert2 in out_text


def test_set_command_success(mocker, capsys):
    """Ensure `set` calls set_volume_by_name and prints success."""
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Discord.exe"
    mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

    # Spy on the real function so we can assert it was called properly
    spy = mocker.spy(cli, "set_volume_by_name")

    out = run_cli(mocker, capsys, ["set", "Discord.exe", "60"])

    spy.assert_called_once_with("Discord.exe", "60")
    assert "Discord.exe" in out.out
    assert "60%" in out.out


def test_set_command_error(mocker, capsys):
    """Test `set` when it returns an error."""
    fake_session = mocker.MagicMock()
    fake_session.Process.name.return_value = "Spotify.exe"
    mocker.patch("audio_tool.core._get_sessions", return_value=[fake_session])

    # Spy on the real function so we can assert it was called properly
    spy = mocker.spy(cli, "set_volume_by_name")

    out = run_cli(mocker, capsys, ["set", "Discord.exe", "60"])

    spy.assert_called_once_with("Discord.exe", "60")
    assert "Application not found" in out.out


def test_toggle_command_success(mocker, capsys):
    """Ensure `toggle` toggles mute correctly."""
    fake_result = [VolumeResult(name = "Discord.exe", muted = True)]
    mocker.patch("audio_tool.cli.toggle_volume").return_value = fake_result

    out = run_cli(mocker, capsys, ["toggle", "Discord.exe"])

    assert "Discord.exe is now muted" in out.out


def test_toggle_command_error(mocker, capsys):
    """Handle toggle errors cleanly."""
    fake_result = [VolumeResult(error=VolumeError.NOT_FOUND)]
    mocker.patch("audio_tool.cli.toggle_volume").return_value = fake_result

    out = run_cli(mocker, capsys, ["toggle", "We wont find this app"])

    assert "Application not found" in out.out


def test_cdda_command(mocker, capsys):
    """Ensure special 'cdda' command toggles Cataclysm volume."""
    fake_result = [VolumeResult(name = "cataclysm-tiles.exe", muted = True)]
    mocker_iface = mocker.patch("audio_tool.cli.toggle_volume")
    mocker_iface.return_value = fake_result

    out = run_cli(mocker, capsys, ["cdda"])

    mocker_iface.assert_called_once_with("cataclysm-tiles.exe")
    assert "CDDA is now muted" in out.out
    