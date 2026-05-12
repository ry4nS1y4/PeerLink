from src.Security.Private_Key_Pass import get_or_create_passphrase
import base64
from unittest.mock import patch

from src.Security.Private_Key_Pass import SERVICE, ACCOUNT


def test_creates_and_stores_when_missing():
    fake_bytes = b"\xaa" * 32

    with patch(
        "src.Security.Private_Key_Pass.keyring.get_password", return_value=None
    ), patch(
        "src.Security.Private_Key_Pass.secrets.token_bytes", return_value=fake_bytes
    ), patch(
        "src.Security.Private_Key_Pass.keyring.set_password"
    ) as set_pw:

        out = get_or_create_passphrase()

        assert out == fake_bytes
        set_pw.assert_called_once_with(
            SERVICE,
            ACCOUNT,
            base64.urlsafe_b64encode(fake_bytes).decode("utf-8"),
        )


def test_reuses_when_present():
    expected = b"\x01" * 32
    saved = base64.urlsafe_b64encode(expected).decode("utf-8")

    with patch(
        "src.Security.Private_Key_Pass.keyring.get_password", return_value=saved
    ), patch("src.Security.Private_Key_Pass.keyring.set_password") as set_pw:

        out = get_or_create_passphrase()

        assert out == expected
        set_pw.assert_not_called()
