import random
import string

import pytest

from audio_tool import core


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


# Standard mock sessions result
fake_sessions_standard = [
    core.SessionInfo(pos=0, name="Spotify", volume=0.5, muted=False),
    core.SessionInfo(pos=1, name="Discord", volume=0.75, muted=False),
    core.SessionInfo(pos=2, name="Steam", volume=0.99, muted=False),
]

# Sessions returning an empty list
fake_sessions_none = []

# Excessively large sessions result
fake_sessions_large = []
for idx in range(1000):
    fake_sessions_large.append(core.SessionInfo(pos=idx, name=''.join(random.choices(string.ascii_letters + string.digits, k=10)), volume=round(random.uniform(0.0, 1.0),2), muted=False))

# Sessions resulting duplicates
fake_sessions_duplicate = [
    core.SessionInfo(pos=0, name="Discord", volume=0.75, muted=False),
    core.SessionInfo(pos=1, name="Discord", volume=0.75, muted=False),
    core.SessionInfo(pos=2, name="Firefox", volume=0.2, muted=False),
    core.SessionInfo(pos=3, name="Steam", volume=0.99, muted=False),
    core.SessionInfo(pos=4, name="Steam", volume=0.84, muted=False),
]

# Sessions returning unexpected data
fake_sessions_unexpected = [
    core.SessionInfo(pos=0, name="Spotify", volume=-15, muted=False),
    core.SessionInfo(pos=1, name="Firefox", volume=-23.4, muted=False),
    core.SessionInfo(pos=2, name="Discord", volume=256.7, muted=False),
    core.SessionInfo(pos=3, name="Chrome", volume=56, muted=False),
    core.SessionInfo(pos=4, name="Steam", volume=None, muted=False),
    core.SessionInfo(pos=5, name='', volume=None, muted=False),
]