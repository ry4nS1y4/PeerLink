# ruff: noqa: E402

import sys
import types
import pytest
from unittest.mock import Mock, patch

sys.modules.setdefault(
    "keyring",
    types.SimpleNamespace(
        get_password=lambda *args, **kwargs: None,
        set_password=lambda *args, **kwargs: None,
    ),
)

import src.protocol.message_handler_factory as mhf
from src.protocol import models


class DummyHandler(mhf.MessageHandler):
    def handle(self, msg):
        return super().handle(msg)


def make_writer(closing=False):
    writer = Mock()
    writer.is_closing.return_value = closing
    return writer


def test_message_handler_base_handle():
    handler = DummyHandler()
    assert handler.handle({}) is None


def test_pong_handler_updates_last_pong():
    peers = {"peer1": {"last_pong": None}}

    with patch.object(mhf.state, "peers", peers, create=True), patch(
        "src.protocol.message_handler_factory.time.time", return_value=10.5
    ):
        mhf.PongHandler().handle({"peer_id": "peer1"})

    assert peers["peer1"]["last_pong"] == 10.5


def test_pong_handler_missing_peer():
    with patch.object(mhf.state, "peers", {}, create=True):
        mhf.PongHandler().handle({"peer_id": "missing"})


def test_catalog_request_handler():
    with patch.object(mhf.state, "PEER_ID_STUB", "peerA", create=True), patch.object(
        mhf.state, "port", 5001, create=True
    ), patch.object(mhf.state, "local_catalog", [{"file_id": "1"}], create=True):
        result = mhf.CatalogReqHandler().handle({"version": "1.0"})

    assert result == {
        "type": "CATALOG_RESPONSE",
        "version": "1.0",
        "peer_id": "peerA",
        "port": 5001,
        "files": [{"file_id": "1"}],
    }


def test_catalog_response_handler_updates_catalog():
    peers = {"peer1": {"catalog": None}}

    with patch.object(mhf.state, "peers", peers, create=True):
        mhf.CatalogResHandler().handle(
            {"peer_id": "peer1", "files": [{"name": "a.txt"}]}
        )

    assert peers["peer1"]["catalog"] == [{"name": "a.txt"}]


def test_catalog_response_handler_missing_peer():
    with patch.object(mhf.state, "peers", {}, create=True):
        mhf.CatalogResHandler().handle({"peer_id": "missing", "files": []})


def test_file_request_relay_error_when_target_not_reachable():
    with patch.object(mhf.state, "PEER_ID_STUB", "peerA", create=True), patch.object(
        mhf.state, "peers", {"peer2": {"writer": None}}, create=True
    ):
        result = mhf.FileReqHandler().handle(
            {
                "version": "1.0",
                "file_id": "file1",
                "target_peer_id": "peer2",
                "request_id": "req1",
            }
        )

    assert result["type"] == "ERROR"
    assert result["code"] == "PEER_NOT_REACHABLE"


def test_file_request_relay_success():
    writer = make_writer(False)

    with patch.object(mhf.state, "PEER_ID_STUB", "peerA", create=True), patch.object(
        mhf.state, "peers", {"peer2": {"writer": writer}}, create=True
    ):
        result = mhf.FileReqHandler().handle(
            {
                "version": "1.0",
                "file_id": "file1",
                "target_peer_id": "peer2",
                "request_id": "req1",
            }
        )

    assert isinstance(result, models.FileRelayData)
    assert result.target_peer_id == "peer2"
    assert result.request_id == "req1"


def test_file_response_handler_forward():
    writer = make_writer(False)

    with patch.object(mhf.state, "download_routes", {"req1": writer}, create=True):
        result = mhf.FileResHandler().handle(
            {
                "request_id": "req1",
                "size": 100,
                "name": "x.txt",
            }
        )

    assert isinstance(result, models.FileForwardData)
    assert result.size == 100
    assert result.upstream_writer is writer


def test_file_response_handler_receive():
    with patch.object(mhf.state, "download_routes", {}, create=True):
        result = mhf.FileResHandler().handle(
            {
                "request_id": "req1",
                "size": 100,
                "name": "x.txt",
            }
        )

    assert isinstance(result, models.FileReceiveData)
    assert result.size == 100


def test_search_request_handler_returns_none():
    assert mhf.SearchReqHandler().handle({"x": 1}) is None


def test_search_response_handler_returns_none():
    assert mhf.SearchResHandler().handle({"x": 1}) is None


def test_error_handler_sets_exception():
    future = Mock()
    future.done.return_value = False

    with patch.object(
        mhf.state,
        "pending_downloads",
        {("peer1", "file1"): future},
        create=True,
    ), patch("src.protocol.message_handler_factory.logger.error"):
        mhf.ErrorHandler().handle(
            {
                "peer_id": "peer1",
                "file_id": "file1",
                "code": "FILE_NOT_FOUND",
                "message": "missing file",
            }
        )

    future.set_exception.assert_called_once()


def test_announce_handler_returns_for_self():
    with patch.object(mhf.state, "PEER_ID_STUB", "peerA", create=True), patch.object(
        mhf.state, "peers", {}, create=True
    ), patch.object(mhf.state, "connecting_peers", set(), create=True), patch(
        "src.protocol.message_handler_factory.asyncio.create_task"
    ) as create_task:
        mhf.AnnounceHandler().handle(
            {
                "peer_id": "peerA",
                "host": "127.0.0.1",
                "port": 5001,
            }
        )

    create_task.assert_not_called()


def test_announce_handler_adds_new_peer_and_starts_connect():
    peers = {}
    connecting_peers = set()

    with patch.object(
        mhf.state, "PEER_ID_STUB", "self-peer", create=True
    ), patch.object(mhf.state, "peers", peers, create=True), patch.object(
        mhf.state, "connecting_peers", connecting_peers, create=True
    ), patch(
        "src.protocol.message_handler_factory._connect_announced_peer",
        return_value="fake-coro",
    ), patch(
        "src.protocol.message_handler_factory.asyncio.create_task"
    ) as create_task:
        mhf.AnnounceHandler().handle(
            {
                "peer_id": "peer1",
                "host": "10.0.0.1",
                "port": 6001,
            }
        )

    assert "peer1" in peers
    assert "peer1" in connecting_peers
    create_task.assert_called_once()


def test_announce_handler_returns_when_writer_open():
    peers = {
        "peer1": {
            "peer_id": "peer1",
            "host": "old",
            "port": 1111,
            "catalog": None,
            "last_pong": None,
            "reader": None,
            "writer": make_writer(False),
        }
    }

    with patch.object(
        mhf.state, "PEER_ID_STUB", "self-peer", create=True
    ), patch.object(mhf.state, "peers", peers, create=True), patch.object(
        mhf.state, "connecting_peers", set(), create=True
    ), patch(
        "src.protocol.message_handler_factory.asyncio.create_task"
    ) as create_task:
        mhf.AnnounceHandler().handle(
            {
                "peer_id": "peer1",
                "host": "new",
                "port": 2222,
            }
        )

    create_task.assert_not_called()


def test_announce_handler_returns_when_already_connecting():
    peers = {
        "peer1": {
            "peer_id": "peer1",
            "host": "old",
            "port": 1111,
            "catalog": None,
            "last_pong": None,
            "reader": None,
            "writer": None,
        }
    }

    with patch.object(
        mhf.state, "PEER_ID_STUB", "self-peer", create=True
    ), patch.object(mhf.state, "peers", peers, create=True), patch.object(
        mhf.state, "connecting_peers", {"peer1"}, create=True
    ), patch(
        "src.protocol.message_handler_factory.asyncio.create_task"
    ) as create_task:
        mhf.AnnounceHandler().handle(
            {
                "peer_id": "peer1",
                "host": "new",
                "port": 2222,
            }
        )

    create_task.assert_not_called()


@pytest.mark.parametrize(
    "message_type, expected_class",
    [
        ("PONG", mhf.PongHandler),
        ("CATALOG_REQUEST", mhf.CatalogReqHandler),
        ("CATALOG_RESPONSE", mhf.CatalogResHandler),
        ("FILE_REQUEST", mhf.FileReqHandler),
        ("FILE_RESPONSE", mhf.FileResHandler),
        ("SEARCH_REQUEST", mhf.SearchReqHandler),
        ("SEARCH_RESPONSE", mhf.SearchResHandler),
        ("ANNOUNCE", mhf.AnnounceHandler),
        ("ERROR", mhf.ErrorHandler),
        ("UNKNOWN", mhf.ErrorHandler),
    ],
)
def test_message_handler_factory_cases(message_type, expected_class):
    handler = mhf.MessageHandlerFactory.get_handler({"type": message_type})
    assert isinstance(handler, expected_class)
