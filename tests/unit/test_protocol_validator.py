# Validators
from unittest.mock import patch

import src.protocol.validator as validator


def test_validate_announce_valid():
    msg = {
        "type": "ANNOUNCE",
        "version": "1.0",
        "peer_id": "peerB",
        "host": "192.168.2.12",
        "port": 5009,
    }

    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "peerA"
    ):
        assert validator.validate(msg) is True


def test_validate_fails_when_peer_id_is_self():
    msg = {
        "type": "PING",
        "version": "1.0",
        "peer_id": "peerA",
    }

    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "peerA"
    ):
        assert validator.validate(msg) is False


def test_validate_fails_when_version_unsupported():
    msg = {
        "type": "PING",
        "version": "9.9",
        "peer_id": "peerB",
    }

    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "peerA"
    ):
        assert validator.validate(msg) is False


def test_validate_catalog_response_requires_files_shape():
    good = {
        "type": "CATALOG_RESPONSE",
        "version": "1.0",
        "peer_id": "peerB",
        "files": [{"file_id": "x", "name": "a.txt", "size": 5}],
    }
    bad = {
        "type": "CATALOG_RESPONSE",
        "version": "1.0",
        "peer_id": "peerB",
        "files": [{"file_id": "x", "name": "a.txt"}],  # missing size
    }

    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "peerA"
    ):
        assert validator.validate(good) is True
        assert validator.validate(bad) is False


def test_validate_unknown_type_returns_false():
    msg = {
        "type": "WHATEVER",
        "version": "1.0",
        "peer_id": "peerB",
    }

    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "peerA"
    ):
        assert validator.validate(msg) is False


def test_validate_ping_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate({"type": "PING", "version": "1.0", "peer_id": "other"})
            is True
        )


def test_validate_pong_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate({"type": "PONG", "version": "1.0", "peer_id": "other"})
            is True
        )


def test_validate_catalog_request_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate(
                {"type": "CATALOG_REQUEST", "version": "1.0", "peer_id": "other"}
            )
            is True
        )


def test_validate_file_request_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate(
                {
                    "type": "FILE_REQUEST",
                    "version": "1.0",
                    "peer_id": "other",
                    "file_id": "x",
                }
            )
            is True
        )


def test_validate_file_response_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate(
                {
                    "type": "FILE_RESPONSE",
                    "version": "1.0",
                    "peer_id": "other",
                    "file_id": "x",
                    "name": "a",
                    "size": 1,
                }
            )
            is True
        )


def test_validate_error_true():
    with patch("src.protocol.validator.SUPPORTED_VERSIONS", {"1.0"}), patch(
        "src.protocol.validator.state.PEER_ID_STUB", "self"
    ):
        assert (
            validator.validate(
                {
                    "type": "ERROR",
                    "version": "1.0",
                    "peer_id": "other",
                    "code": "E",
                    "message": "msg",
                }
            )
            is True
        )
