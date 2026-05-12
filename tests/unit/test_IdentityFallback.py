from unittest.mock import mock_open, patch

import src.identification.Identity_fallback as identity


def test___checkPeerIdentity_file_missing():
    with patch(
        "src.identification.Identity_fallback.open", side_effect=FileNotFoundError
    ):
        assert identity.__checkPeerIdentity() is False


def test___checkPeerIdentity_empty_file_returns_false():
    m = mock_open(read_data="   \n")
    with patch("src.identification.Identity_fallback.open", m):
        assert identity.__checkPeerIdentity() is False


def test___checkPeerIdentity_nonempty_file_returns_true():
    m = mock_open(read_data="abc-123\n")
    with patch("src.identification.Identity_fallback.open", m):
        assert identity.__checkPeerIdentity() is True
