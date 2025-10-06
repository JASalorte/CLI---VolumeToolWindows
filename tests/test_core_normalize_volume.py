from audio_tool import core

class TestNormalizeVolume:
    """Covers core._normalize_volume under normal and error conditions."""

    def test__normalize_volume_valid_inputs(self):
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

    def test__normalize_volume_invalid_inputs(self):
        assert core._normalize_volume("abc") is None
        assert core._normalize_volume('') is None
        assert core._normalize_volume('asd') is None
        assert core._normalize_volume('AS!"&/(!··^*ASD^*\nasd') is None
        assert core._normalize_volume(None) is None
        assert core._normalize_volume(True) is None
        assert core._normalize_volume(False) is None
        assert core._normalize_volume([]) is None
        assert core._normalize_volume({}) is None