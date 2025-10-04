from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from comtypes import COMError
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume


class VolumeError(Enum):
    NOT_FOUND = "Application not found"
    INVALID_INPUT = "Invalid input"
    INVALID_POSITION = "Invalid device position"
    FAILED = "Failed to set volume"


@dataclass
class VolumeResult:
    volume: Optional[float] = None
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


def get_volume_by_name(app_name: str) -> VolumeResult:
    """Return the volume of an app by name."""
    sessions = get_sessions()
    for session in sessions:
        if session.Process and session.Process.name().lower() == app_name.lower():
            try:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume).GetMasterVolume()
                return VolumeResult(volume=volume, name=app_name)
            except COMError:
                return VolumeResult(error=VolumeError.FAILED)
    return VolumeResult(error=VolumeError.NOT_FOUND)

def set_volume_by_name(app_name: str, volume: float | int | str) -> VolumeResult:
    """Set the volume of an app by process name."""
    volume = _normalize_volume(volume)
    if volume is None:
        return VolumeResult(name=app_name, error=VolumeError.INVALID_INPUT)

    return _set_volume_by_name(app_name, volume)



def _set_volume_by_name(app_name: str, volume: float) -> VolumeResult:

    sessions = get_sessions()
    selected = None

    for session in sessions:
        if session.Process:
            if session.Process.name().lower() == app_name.lower():
                selected = session
        else:
            if app_name.lower() == "system sounds":
                selected = session

    if selected:
        name = selected.Process.name() if selected.Process else "System sounds"
        try:
            selected._ctl.QueryInterface(ISimpleAudioVolume).SetMasterVolume(volume, None)
            return VolumeResult(volume=volume, name=name)
        except COMError:
            return VolumeResult(name=name, error=VolumeError.FAILED)  # Failed to set new volume

    return VolumeResult(name=app_name, error=VolumeError.NOT_FOUND)  # Application not found


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


def toggle_volume(app_name: str) -> VolumeResult:
    """Toggle an app between mute (0) and full (1)."""
    volume_data = get_volume_by_name(app_name)

    if volume_data.error:
        return volume_data

    new_vol = 0.0 if volume_data.volume > 0.0 else 1.0
    return set_volume_by_name(app_name, new_vol)



