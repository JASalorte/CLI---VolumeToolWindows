from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from comtypes import COMError
from pycaw import pycaw
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume


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
            volume = session._ctl.QueryInterface(ISimpleAudioVolume).GetMasterVolume()
        except COMError:
            volume = None

        results.append(SessionInfo(pos=idx, name=name, volume=volume))
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

    if not isinstance(app_name, str):
        return [VolumeResult(error=VolumeError.INVALID_INPUT)]

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
            ctl = selected_session._ctl.QueryInterface(ISimpleAudioVolume)
            volume = ctl.GetMasterVolume()
            muted = ctl.GetMute()
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
    if not isinstance(app_name, str):
        try:
            failed_app_name = str(app_name)
        except Exception:
            failed_app_name = "Undefined"
        return [VolumeResult(name=failed_app_name, error=VolumeError.INVALID_INPUT)]

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
                selected_session._ctl.QueryInterface(ISimpleAudioVolume).SetMasterVolume(volume, None)
                results.append(VolumeResult(volume=volume, name=resolved_name))
            except COMError:
                results.append(VolumeResult(name=resolved_name, error=VolumeError.FAILED))
        return results

    return [VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)]  # Application not found


def interactive_set_volume() -> VolumeResult:
    """Prompt user to pick a session and set its volume."""
    sessions = list_sessions_verbose(list_pos=True)
    for session_formated, session_info in sessions:
        print(session_formated)
    try:
        pos = int(input("Select device by position: "))
        volume = input("Select desired volume 0-100: ")
    except ValueError:
        return VolumeResult(error=VolumeError.INVALID_INPUT)  # Invalid input

    if pos < 0 or pos >= len(sessions):
        return VolumeResult(error=VolumeError.INVALID_POSITION)  # Invalid device position

    if volume is None:
        return VolumeResult(error=VolumeError.INVALID_INPUT)  # Invalid volume

    result = set_volume_by_name(sessions[pos][1].name, volume)
    if result.error:
        return result

    return VolumeResult(volume=result.volume, name=result.name)


def _normalize_volume(volume: str | float | int) -> Optional[float]:
    """
    Normalize a volume value to [0.0, 1.0].

    Args:
        volume: Can be:
            - int (0–100): will be scaled down
            - float (0.0–1.0): clamped
            - str: either "0–100" (int) or "0.0–1.0" (float)

    Returns:
        Normalized volume in [0.0, 1.0], or None if invalid.
    """
    if isinstance(volume,bool):
        return None # explicitly reject booleans, True would end as 0.01 volume

    def clamp(v: float) -> float:
        return max(0.0, min(v, 1.0))

    if isinstance(volume, float):
        return clamp(volume)

    if isinstance(volume, int):
        return clamp(volume / 100.0)

    def _try_parse_int_or_float(value: str) -> Optional[float]:
        try:
            return int(value) / 100.0
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None

    if isinstance(volume, str):
        parsed = _try_parse_int_or_float(volume)
        if parsed is not None:
            return clamp(parsed)
        else:
            return None

    return None


def toggle_volume(app_name: str) -> List[VolumeResult]:
    sessions = get_sessions()

    if not isinstance(app_name, str):
        try:
            failed_app_name = str(app_name)
        except Exception:
            failed_app_name = "Undefined"
        return [VolumeResult(name=failed_app_name, error=VolumeError.INVALID_INPUT)]

    selected = []
    for session in sessions:
        proc_name = session.Process.name() if session.Process else None
        if proc_name and proc_name.lower() == app_name.lower():
            selected.append((session, proc_name))
        elif not session.Process and app_name.lower() == "system sounds":
            selected.append((session, "System sounds"))

    if not selected:
        return [VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)]

    results = []
    for session, resolved_name in selected:
        try:
            ctl = session._ctl.QueryInterface(ISimpleAudioVolume)
            mute = ctl.GetMute()
            new_mute = 1 if mute == 0 else 0
            ctl.SetMute(new_mute, None)
            results.append(VolumeResult(name=resolved_name, muted=bool(new_mute)))
        except COMError:
            results.append(VolumeResult(name=resolved_name, error=VolumeError.FAILED))

    return results


result = toggle_volume("steam.exe")
print(result)
