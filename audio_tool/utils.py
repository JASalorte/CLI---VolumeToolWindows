from typing import Optional, Union


def _normalize_volume(volume: Union[str, float, int]) -> Optional[float]:
    """
    Normalize a volume value to [0.0, 1.0].

    Args:
        volume: Can be:
            - int (0–100): will be scaled down to 0.0 - 1.0
            - float (0.0–1.0): clamped
            - str: either "0–100" (int) or "0.0–1.0" (float)

    Returns:
        Normalized volume in [0.0, 1.0], or None if invalid.
    """
    if isinstance(volume, bool):
        return None  # Explicitly reject booleans, True would end as 0.01 volume

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
        return None

    return None


def _string_parse(value: str) -> Union[str, None]:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped if stripped else None
