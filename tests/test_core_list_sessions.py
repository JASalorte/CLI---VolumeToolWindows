from audio_tool import core
from tests.conftest import fake_sessions_standard, fake_sessions_none, fake_sessions_large, fake_sessions_duplicate, \
    fake_sessions_unexpected

class TestListSessions:
    """Covers core.list_sessions_verbose under normal and error conditions."""

    def test_list_sessions_standard(self, mocker):

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

    def test_list_sessions_empty(self, mocker):
        mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_none)
        result = core.list_sessions_verbose(list_pos=True)
        assert result == []
        assert len(result) == 0

    def test_list_sessions_large(self, mocker):
        mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_large)
        result = core.list_sessions_verbose(list_pos=True)

        assert len(result) == 1000
        # Just check that formatting didn’t break
        for formatted, raw in result:
            assert isinstance(formatted, str)
            assert isinstance(raw, core.SessionInfo)

    def test_list_sessions_duplicates(self, mocker):
        mocker.patch("audio_tool.core.list_sessions", return_value=fake_sessions_duplicate)
        result = core.list_sessions_verbose(list_pos=True)

        # Ensure duplicates are preserved (important for debugging real-world apps)
        assert result[1][0] == "1 - Discord: 0.75"
        assert result[3][0] == "3 - Steam: 0.99"
        assert result[4][0] == "4 - Steam: 0.84"

    def test_list_sessions_unexpected(self, mocker):
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