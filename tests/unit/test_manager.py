# ruff: noqa: E402

import asyncio
import sys
import types
import pytest
from unittest.mock import Mock, AsyncMock, patch

sys.modules.setdefault(
    "keyring",
    types.SimpleNamespace(
        get_password=lambda *args, **kwargs: None,
        set_password=lambda *args, **kwargs: None,
    ),
)

import src.connection.manager as mng
from src.protocol import models


class AsyncFile:
    def __init__(self, read_data=b""):
        self._read_data = read_data
        self.written = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self):
        return self._read_data

    async def write(self, data):
        self.written = data


def make_writer(closing=False):
    writer = Mock()
    writer.write = Mock()
    writer.drain = AsyncMock()
    writer.close = Mock()
    writer.wait_closed = AsyncMock()
    writer.is_closing.return_value = closing
    writer.get_extra_info.return_value = ("127.0.0.1", 9999)
    return writer


def make_reader(lines=None, data=b""):
    reader = Mock()
    reader.readline = AsyncMock(side_effect=lines if lines is not None else [b""])
    reader.readexactly = AsyncMock(return_value=data)
    return reader


def test_send_line_writes_encoded_bytes():
    writer = make_writer()

    with patch("src.connection.manager.codec.encode", return_value='{"x":1}'):
        mng._send_line(writer, {"x": 1})

    writer.write.assert_called_once_with(b'{"x":1}')


def test_peer_registry_methods():
    peers = {}
    registry = mng.PeerRegistry(peers)
    reader = Mock()
    writer = make_writer()

    registry.upsert("p1", "h1", 1000, reader, writer)
    assert peers["p1"]["host"] == "h1"
    assert peers["p1"]["heartbeat_started"] is False

    peers["p1"]["catalog"] = ["keep"]
    peers["p1"]["last_pong"] = 5
    registry.upsert("p1", "h2", 2000, "r2", "w2")
    assert peers["p1"]["host"] == "h2"
    assert peers["p1"]["port"] == 2000
    assert peers["p1"]["catalog"] == ["keep"]
    assert peers["p1"]["last_pong"] == 5

    registry.remove_by_address("h2", 2000)
    assert "p1" not in peers

    registry.upsert("p2", "h3", 3000, reader, writer)
    registry.remove_by_peer_id("p2")
    assert "p2" not in peers


def test_dispatch_routes_each_result_type():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        writer = make_writer()
        reader = make_reader()

        with patch.object(
            dispatcher, "_handle_dict", new=AsyncMock()
        ) as h_dict, patch.object(
            dispatcher, "_handle_file_response", new=AsyncMock()
        ) as h_resp, patch.object(
            dispatcher, "_handle_file_receive", new=AsyncMock()
        ) as h_recv, patch.object(
            dispatcher, "_handle_file_relay", new=AsyncMock()
        ) as h_relay, patch.object(
            dispatcher, "_handle_file_forward", new=AsyncMock()
        ) as h_forward:
            await dispatcher.dispatch({"type": "X"}, {}, writer, reader, False)
            await dispatcher.dispatch(
                models.FileResponseData({}, "a"), {}, writer, reader, False
            )
            await dispatcher.dispatch(
                models.FileReceiveData(1, "b"), {}, writer, reader, False
            )
            await dispatcher.dispatch(
                models.FileRelayData("peer2", "req1"), {}, writer, reader, False
            )
            await dispatcher.dispatch(
                models.FileForwardData(1, writer), {}, writer, reader, False
            )

            h_dict.assert_awaited_once()
            h_resp.assert_awaited_once()
            h_recv.assert_awaited_once()
            h_relay.assert_awaited_once()
            h_forward.assert_awaited_once()

    asyncio.run(runner())


def test_handle_dict_sends_followup_catalog_request():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        writer = make_writer()

        with patch.object(
            mng.state, "peers", {"peer2": {"catalog": None}}, create=True
        ), patch.object(mng.state, "PEER_ID_STUB", "self-peer", create=True), patch(
            "src.connection.manager._send_line"
        ) as mock_send:
            await dispatcher._handle_dict(
                {"type": "CATALOG_RESPONSE", "version": "1.0"},
                {"type": "CATALOG_REQUEST", "peer_id": "peer2"},
                writer,
                False,
            )

            assert mock_send.call_count == 2
            writer.drain.assert_awaited()

    asyncio.run(runner())


def test_handle_file_response_sends_header_and_file_bytes():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        writer = make_writer()
        fake_file = AsyncFile(read_data=b"abc")

        with patch("src.connection.manager._send_line") as mock_send, patch(
            "src.connection.manager.aiofiles.open", return_value=fake_file
        ):
            await dispatcher._handle_file_response(
                models.FileResponseData({"type": "FILE_RESPONSE"}, "path.txt"),
                writer,
            )

            mock_send.assert_called_once_with(writer, {"type": "FILE_RESPONSE"})
            writer.write.assert_called_once_with(b"abc")

    asyncio.run(runner())


def test_handle_file_receive_success_hash_ok_sets_result():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        reader = make_reader(data=b"data")
        future = Mock()
        future.done.return_value = False
        fake_file = AsyncFile()

        with patch.object(
            mng.state, "pending_downloads", {("peer1", "fid"): future}, create=True
        ), patch("src.connection.manager.aiofiles.open", return_value=fake_file), patch(
            "src.connection.hash_check.verify_file_hash", return_value=True
        ):
            await dispatcher._handle_file_receive(
                models.FileReceiveData(4, "save.bin"),
                {"peer_id": "peer1", "file_id": "fid"},
                reader,
            )

            future.set_result.assert_called_once_with("save.bin")

    asyncio.run(runner())


def test_handle_file_receive_hash_fail_sets_exception():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        reader = make_reader(data=b"data")
        future = Mock()
        future.done.return_value = False
        fake_file = AsyncFile()

        with patch.object(
            mng.state, "pending_downloads", {("peer1", "fid"): future}, create=True
        ), patch("src.connection.manager.aiofiles.open", return_value=fake_file), patch(
            "src.connection.hash_check.verify_file_hash", return_value=False
        ):
            await dispatcher._handle_file_receive(
                models.FileReceiveData(4, "save.bin"),
                {"peer_id": "peer1", "file_id": "fid"},
                reader,
            )

            future.set_exception.assert_called_once()

    asyncio.run(runner())


def test_handle_file_receive_reader_exception_sets_exception_and_raises():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        reader = make_reader()
        reader.readexactly = AsyncMock(side_effect=RuntimeError("boom"))
        future = Mock()
        future.done.return_value = False

        with patch.object(
            mng.state, "pending_downloads", {("peer1", "fid"): future}, create=True
        ):
            with pytest.raises(RuntimeError):
                await dispatcher._handle_file_receive(
                    models.FileReceiveData(4, "save.bin"),
                    {"peer_id": "peer1", "file_id": "fid"},
                    reader,
                )

            future.set_exception.assert_called_once()

    asyncio.run(runner())


def test_handle_file_relay_error_and_success():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        upstream_writer = make_writer()
        target_writer = make_writer()

        with patch.object(
            mng.state, "PEER_ID_STUB", "self-peer", create=True
        ), patch.object(
            mng.state, "peers", {"peer2": {"writer": None}}, create=True
        ), patch(
            "src.connection.manager._send_line"
        ) as mock_send:
            await dispatcher._handle_file_relay(
                models.FileRelayData("peer2", "req1"),
                {"version": "1.0", "file_id": "fid"},
                upstream_writer,
            )
            mock_send.assert_called_once()

        with patch.object(mng.state, "download_routes", {}, create=True), patch.object(
            mng.state, "peers", {"peer2": {"writer": target_writer}}, create=True
        ), patch("src.connection.manager._send_line") as mock_send:
            await dispatcher._handle_file_relay(
                models.FileRelayData("peer2", "req1"),
                {"type": "FILE_REQUEST", "file_id": "fid", "target_peer_id": "peer2"},
                upstream_writer,
            )

            assert mng.state.download_routes["req1"] is upstream_writer
            mock_send.assert_called_once_with(
                target_writer,
                {"type": "FILE_REQUEST", "file_id": "fid"},
            )

    asyncio.run(runner())


def test_handle_file_forward_pipes_bytes_and_clears_route():
    async def runner():
        dispatcher = mng.MessageDispatcher()
        reader = make_reader(data=b"xyz")
        upstream_writer = make_writer()

        with patch.object(
            mng.state, "download_routes", {"req1": upstream_writer}, create=True
        ), patch("src.connection.manager._send_line") as mock_send:
            await dispatcher._handle_file_forward(
                models.FileForwardData(3, upstream_writer),
                {"request_id": "req1", "type": "FILE_RESPONSE"},
                reader,
            )

            mock_send.assert_called_once_with(
                upstream_writer,
                {"request_id": "req1", "type": "FILE_RESPONSE"},
            )
            upstream_writer.write.assert_called_once_with(b"xyz")
            assert "req1" not in mng.state.download_routes

    asyncio.run(runner())


def test_connection_handler_run_invalid_decode_and_invalid_validate():
    async def runner():
        registry = Mock()
        registry.remove_by_peer_id = Mock()
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock()
        handler = mng.ConnectionHandler(registry, dispatcher)
        reader = make_reader(lines=[b"bad\n", b"good\n", b""])
        writer = make_writer()

        with patch(
            "src.connection.manager.codec.decode",
            side_effect=[Exception("bad"), {"peer_id": "p1"}],
        ), patch(
            "src.connection.manager.validator.validate", return_value=False
        ), patch(
            "src.connection.manager._send_line"
        ) as mock_send:
            await handler.run(reader, writer)

            mock_send.assert_called_once()
            dispatcher.dispatch.assert_not_awaited()
            writer.close.assert_called_once()
            writer.wait_closed.assert_awaited_once()

    asyncio.run(runner())


def test_connection_handler_run_registers_peer_and_dispatches_using_existing_port():
    async def runner():
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock()
        reader = make_reader(lines=[b"msg\n", b""])
        writer = make_writer()

        fake_handler = Mock()
        fake_handler.handle.return_value = {"ok": True}
        peers = {"peer1": {"port": 7777}}
        registry = mng.PeerRegistry(peers)

        with patch.object(mng.state, "peers", peers, create=True), patch(
            "src.connection.manager.codec.decode",
            return_value={"peer_id": "peer1", "type": "PING"},
        ), patch("src.connection.manager.validator.validate", return_value=True), patch(
            "src.connection.manager.start_heartbeat"
        ) as mock_hb, patch(
            "src.protocol.message_handler_factory.MessageHandlerFactory.get_handler",
            return_value=fake_handler,
        ), patch.object(
            registry, "upsert", wraps=registry.upsert
        ) as upsert_spy:
            await mng.ConnectionHandler(registry, dispatcher).run(reader, writer)

            upsert_spy.assert_called_once_with(
                "peer1", "127.0.0.1", 7777, reader, writer
            )
            mock_hb.assert_called_once_with("peer1")
            dispatcher.dispatch.assert_awaited_once()
            assert writer.close.called

    asyncio.run(runner())


def test_connection_handler_run_search_request_and_response_and_wait_close_error():
    async def runner():
        reader = make_reader(lines=[b"one\n", b"two\n", b""])
        writer = make_writer()
        writer.wait_closed = AsyncMock(side_effect=Exception("close fail"))
        dispatcher = Mock()
        dispatcher.dispatch = AsyncMock()
        peers = {}
        registry = mng.PeerRegistry(peers)

        fake_handler = Mock()
        fake_handler.handle.return_value = None
        search_module = type(
            "SearchMod",
            (),
            {
                "handle_search_request": staticmethod(lambda msg, writer: "req-task"),
                "handle_search_response": staticmethod(lambda msg: "res-task"),
            },
        )

        with patch.object(mng.state, "peers", peers, create=True), patch(
            "src.connection.manager.codec.decode",
            side_effect=[
                {"peer_id": "peer1", "type": "SEARCH_REQUEST", "port": 6000},
                {"peer_id": "peer1", "type": "SEARCH_RESPONSE"},
            ],
        ), patch("src.connection.manager.validator.validate", return_value=True), patch(
            "src.connection.manager.start_heartbeat"
        ), patch(
            "src.protocol.message_handler_factory.MessageHandlerFactory.get_handler",
            return_value=fake_handler,
        ), patch(
            "src.connection.manager.asyncio.create_task"
        ) as create_task, patch.dict(
            "sys.modules", {"src.queries.search": search_module}
        ):
            await mng.ConnectionHandler(registry, dispatcher).run(reader, writer)

            assert create_task.call_count == 2
            dispatcher.dispatch.assert_not_awaited()
            writer.close.assert_called_once()

    asyncio.run(runner())


def test_handle_connection_builds_objects_and_runs_handler():
    async def runner():
        reader = make_reader()
        writer = make_writer()

        with patch("src.connection.manager.PeerRegistry") as MockRegistry, patch(
            "src.connection.manager.MessageDispatcher"
        ) as MockDispatcher, patch(
            "src.connection.manager.ConnectionHandler"
        ) as MockHandler, patch.object(
            mng.state, "peers", {}, create=True
        ):
            MockHandler.return_value.run = AsyncMock()
            await mng.handle_connection(reader, writer, True)

            MockRegistry.assert_called_once_with(mng.state.peers)
            MockDispatcher.assert_called_once()
            MockHandler.assert_called_once()
            MockHandler.return_value.run.assert_awaited_once_with(reader, writer)

    asyncio.run(runner())


def test_start_server_calls_asyncio_start_server():
    async def runner():
        with patch.object(mng.state, "port", 5001, create=True), patch(
            "src.connection.manager.asyncio.start_server",
            new=AsyncMock(return_value="server"),
        ) as mock_start:
            result = await mng.start_server()

            mock_start.assert_awaited_once_with(mng.handle_connection, "0.0.0.0", 5001)
            assert result == "server"

    asyncio.run(runner())


def test_connect_to_peer_returns_if_already_connected():
    async def runner():
        peers = {"p1": {"host": "h1", "port": 5001, "writer": make_writer(False)}}

        with patch.object(mng.state, "peers", peers, create=True), patch(
            "src.connection.manager.asyncio.open_connection", new=AsyncMock()
        ) as open_conn:
            await mng.connect_to_peer("h1", 5001)
            open_conn.assert_not_awaited()

    asyncio.run(runner())


def test_connect_to_peer_raises_if_peer_closes_during_handshake():
    async def runner():
        reader = make_reader(lines=[b""])
        writer = make_writer()

        with patch.object(mng.state, "peers", {}, create=True), patch.object(
            mng.state, "PEER_ID_STUB", "self-peer", create=True
        ), patch.object(mng.state, "port", 5001, create=True), patch(
            "src.connection.manager.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ), patch(
            "src.connection.manager._send_line"
        ):
            with pytest.raises(ConnectionError):
                await mng.connect_to_peer("h1", 5001)

    asyncio.run(runner())


def test_connect_to_peer_handshake_updates_catalog_and_starts_background_handler():
    async def runner():
        reader = make_reader(lines=[b"bad\n", b"good\n"])
        writer = make_writer()
        peers = {}

        with patch.object(mng.state, "peers", peers, create=True), patch.object(
            mng.state, "PEER_ID_STUB", "self-peer", create=True
        ), patch.object(mng.state, "port", 5001, create=True), patch(
            "src.connection.manager.asyncio.open_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ), patch(
            "src.connection.manager.codec.decode",
            side_effect=[
                {"peer_id": "peer2", "type": "NOPE"},
                {"peer_id": "peer2", "type": "CATALOG_RESPONSE", "files": ["a.txt"]},
            ],
        ), patch(
            "src.connection.manager.validator.validate", side_effect=[False, True]
        ), patch(
            "src.connection.manager._send_line"
        ) as mock_send, patch(
            "src.connection.heartbeat.start_heartbeat"
        ) as mock_hb, patch(
            "src.connection.manager.handle_connection"
        ) as mock_handle, patch(
            "src.connection.manager.asyncio.create_task"
        ) as mock_task:
            await mng.connect_to_peer("h1", 5001)

            mock_send.assert_called_once()
            assert peers["peer2"]["catalog"] == ["a.txt"]
            assert peers["peer2"]["heartbeat_started"] is True
            mock_hb.assert_called_once_with("peer2")
            mock_handle.assert_called_once_with(reader, writer, is_connector=True)
            mock_task.assert_called_once()

    asyncio.run(runner())
