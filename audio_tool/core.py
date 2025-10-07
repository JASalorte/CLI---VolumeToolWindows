from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from comtypes import COMError
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

from audio_tool.utils import _string_parse, _normalize_volume


class VolumeError(Enum):
    NOT_FOUND = "Application not found"
    INVALID_INPUT = "Invalid input"
    INVALID_POSITION = "Invalid device position"
    FAILED = "Failed to set volume"


@dataclass
class VolumeResult:
    volume: Optional[float] = None
    muted: Optional[bool] = None
    name: Optional[str] = None
    error: Optional[VolumeError] = None


@dataclass
class SessionInfo:
    pos: int
    name: str
    muted: bool
    volume: Optional[float]


def get_sessions():
    """Retrieve all current audio sessions."""
    return AudioUtilities.GetAllSessions()

def list_sessions() -> List[SessionInfo]:
    """
    Returns:
        List[SessionInfo]: List of audio sessions with position, name, and volume.
    """
    sessions = get_sessions()
    results = []

    for idx, session in enumerate(sessions):
        # Determine the name of the session
        if session.Process:
            name = session.Process.name()  # e.g. "firefox.exe", "steam.exe"
        else:
            name = "System Sounds"

        try:
            volume = session.SimpleAudioVolume.GetMasterVolume()
            muted = session.SimpleAudioVolume.GetMute()
        except COMError:
            volume = None
            muted = None

        results.append(SessionInfo(pos=idx, name=name, volume=volume, muted=muted))
    return results

def list_sessions_verbose(list_pos: bool = False) -> List[Tuple[str, SessionInfo]]:
    """
    List all active sessions and their volumes.

    Args:
        list_pos: Include positional index.

    Returns:
        List[Tuple[str, SessionInfo]]: Each entry contains a formatted string and its raw SessionInfo.
    """
    results = list_sessions()
    results_formatted = []

    for s in results:
        vol_str = f"{s.volume:.2f}" if s.volume is not None else "N/A"
        prefix = f"{s.pos} - " if list_pos else ""
        name = s.name if s.name != '' else "N/A"
        results_formatted.append([f"{prefix}{name}: {vol_str}", s])

    return results_formatted


def get_volume_by_name(app_name: str) -> List[VolumeResult]:
    """
    Return the volume(s) of an app by name.

    Always returns a list:
    - If multiple matches exist, returns one VolumeResult per session.
    - If none found, returns a single VolumeResult with NOT_FOUND error.
    """
    parsed = _string_parse(app_name)
    if parsed is None:
        return [VolumeResult(name=str(app_name), error=VolumeError.INVALID_INPUT)]

    app_name = parsed

    sessions = get_sessions()
    selected = []
    for session in sessions:
        proc_name = session.Process.name() if session.Process else None
        if proc_name and proc_name.lower() == app_name.lower():
            selected.append((session,proc_name))
        elif not session.Process and "system sounds" == app_name.lower():
            selected.append((session, "System sounds"))

    if not selected:
        return [VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)]

    results = []
    for selected_session, resolved_name in selected:
        try:
            interface = selected_session.SimpleAudioVolume
            volume = interface.GetMasterVolume()
            muted = interface.GetMute()
            results.append(VolumeResult(volume=volume, name=resolved_name, muted=bool(muted)))
        except COMError:
            results.append(VolumeResult(name=resolved_name, error=VolumeError.FAILED))

    return results

def set_volume_by_name(app_name: str, volume: float | int | str, all_matches: bool = True) -> List[VolumeResult]:
    """
    Set the volume of an app by process name.

    Args:
        app_name: Name of the app to change its name
        volume: The desired volume
        all_matches: Change the volume for all matches found, if False, only the first found (which is kinda useless?)
    Returns:
        List of VolumeResult with the results of the operation
    """
    volume = _normalize_volume(volume)
    if volume is None:
        return [VolumeResult(name=app_name, error=VolumeError.INVALID_INPUT)]

    return _set_volume_by_name(app_name, volume, all_matches)

def _set_volume_by_name(app_name: str, volume: float, all_matches: bool) -> List[VolumeResult]:
    """Set volume(s) by name. Returns a list of VolumeResult, one per matching session."""
    parsed = _string_parse(app_name)
    if parsed is None:
        return [VolumeResult(name=str(app_name), error=VolumeError.INVALID_INPUT)]

    app_name = parsed

    sessions = get_sessions()
    selected = []

    for session in sessions:
        proc_name = session.Process.name() if session.Process else None
        if proc_name and proc_name.lower() == app_name.lower():
                selected.append((session, proc_name))
        elif not session.Process and app_name.lower() == "system sounds":
                selected.append((session, "System sounds"))

        if selected and not all_matches:
            break

    if selected:
        results = []
        for selected_session, resolved_name in selected:
            try:
                selected_session.SimpleAudioVolume.SetMasterVolume(volume, None)
                results.append(VolumeResult(volume=volume, name=resolved_name))
            except COMError:
                results.append(VolumeResult(name=resolved_name, error=VolumeError.FAILED))
        return results

    return [VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)]  # Application not found

def toggle_volume(app_name: str) -> List[VolumeResult]:
    """
    If there are multiple sessions and just one of them is unmuted, all will be muted.
    If all are muted, all will be unmuted.
    """
    parsed = _string_parse(app_name)
    if parsed is None:
        return [VolumeResult(name=str(app_name), error=VolumeError.INVALID_INPUT)]

    app_name = parsed

    sessions = get_sessions()

    selected = []
    for session in sessions:
        proc_name = session.Process.name() if session.Process else None
        if proc_name and proc_name.lower() == app_name.lower():
            selected.append((session, proc_name))
        elif not session.Process and app_name.lower() == "system sounds":
            selected.append((session, "System sounds"))

    if not selected:
        return [VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)]

    # Determine the new global mute state
    interfaces = [s.SimpleAudioVolume for s, _ in selected]
    any_unmuted = any(not i.GetMute() for i in interfaces)
    new_mute = 1 if any_unmuted else 0  # if any is unmuted, mute all

    results = []
    for (session, resolved_name), interface in zip(selected, interfaces):
        try:
            interface.SetMute(new_mute, None)
            results.append(VolumeResult(name=resolved_name, muted=bool(new_mute)))
        except COMError:
            results.append(VolumeResult(name=resolved_name, error=VolumeError.FAILED))

    return results

def interactive_set_volume() -> List[VolumeResult]:
    """Prompt user to pick a session and set its volume."""
    sessions = list_sessions_verbose(list_pos=True)
    for session_formatted, session_info in sessions:
        print(session_formatted)
    try:
        pos = int(input("Select device by position: "))
        volume = float(input("Select desired volume 0-100: "))
    except ValueError:
        return [VolumeResult(error=VolumeError.INVALID_INPUT)]  # Invalid input

    if pos < 0 or pos >= len(sessions):
        return [VolumeResult(error=VolumeError.INVALID_POSITION)]  # Invalid device position

    if volume is None:
        return [VolumeResult(error=VolumeError.INVALID_INPUT)]  # Invalid volume

    return set_volume_by_name(sessions[pos][1].name, volume)

if __name__ == "__main__":
    interactive_set_volume()