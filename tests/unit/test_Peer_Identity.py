from unittest.mock import Mock, mock_open, patch
import hashlib

# change this import to your real module
import src.identification.Peer_Identity as pk


def test___CheckKey_returns_false_when_missing():
    # open() raises FileNotFoundError
    with patch("src.identification.Peer_Identity.open", side_effect=FileNotFoundError):
        assert pk.__CheckKey() is False


def test___CheckKey_returns_false_when_empty_file():
    m = mock_open(read_data=b"")
    with patch("src.identification.Peer_Identity.open", m):
        assert pk.__CheckKey() is False


def test___CheckKey_returns_true_when_file_has_bytes():
    m = mock_open(read_data=b"not-empty")
    with patch("src.identification.Peer_Identity.open", m):
        assert pk.__CheckKey() is True


def test_CreateKeys_creates_new_key_when_missing():
    # Force branch: __CheckKey() == False
    with patch(
        "src.identification.Peer_Identity.__CheckKey", return_value=False
    ), patch(
        "src.identification.Peer_Identity.get_or_create_passphrase",
        return_value=b"x" * 32,
    ), patch(
        "src.identification.Peer_Identity.rsa.generate_private_key"
    ) as gen_key, patch(
        "src.identification.Peer_Identity.open", mock_open()
    ) as mopen:

        # Fake private key object + its behaviors
        fake_priv_obj = Mock()
        fake_priv_obj.private_bytes.return_value = b"PRIVATE_PEM_BYTES"

        fake_pub_obj = Mock()
        fake_pub_obj.public_bytes.return_value = b"PUBLIC_PEM_BYTES"

        fake_priv_obj.public_key.return_value = fake_pub_obj
        gen_key.return_value = fake_priv_obj

        out = pk.CreateKeys()

        # wrote private key to file
        handle = mopen()
        handle.write.assert_called_once_with(b"PRIVATE_PEM_BYTES")

        # returns hex of public bytes
        assert out == b"PUBLIC_PEM_BYTES".hex()


def test_CreateKeys_loads_existing_key_when_present():
    # Force branch: __CheckKey() == True
    with patch("src.identification.Peer_Identity.__CheckKey", return_value=True), patch(
        "src.identification.Peer_Identity.get_or_create_passphrase",
        return_value=b"x" * 32,
    ), patch(
        "src.identification.Peer_Identity.serialization.load_pem_private_key"
    ) as load_key, patch(
        "src.identification.Peer_Identity.open",
        mock_open(read_data=b"PRIVATE_PEM_ON_DISK"),
    ):

        fake_loaded_priv = Mock()
        fake_loaded_pub = Mock()
        fake_loaded_pub.public_bytes.return_value = b"PUBLIC_PEM_FROM_LOADED"

        fake_loaded_priv.public_key.return_value = fake_loaded_pub
        load_key.return_value = fake_loaded_priv

        out = pk.CreateKeys()

        load_key.assert_called_once()
        assert out == b"PUBLIC_PEM_FROM_LOADED".hex()


def test_CreatePeerID_matches_sha256():
    data = b"hello"
    assert pk.CreatePeerID(data) == hashlib.sha256(data).hexdigest()
