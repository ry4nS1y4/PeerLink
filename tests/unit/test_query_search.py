# ruff: noqa: E402

import asyncio
import sys
import types
from unittest.mock import Mock, AsyncMock, patch

sys.modules.setdefault(
    "keyring",
    types.SimpleNamespace(
        get_password=lambda *args, **kwargs: None,
        set_password=lambda *args, **kwargs: None,
    ),
)

import src.state as state
import src.queries.search as search


def make_writer(drain_side_effect=None):
    writer = Mock()
    writer.write = Mock()
    writer.drain = AsyncMock(side_effect=drain_side_effect)
    return writer


def reset_state():
    state.peers = {}
    state.local_catalog = []
    state.seen_requests = set()
    state.request_routes = {}
    state.pending_searches = {}
    state.PEER_ID_STUB = "self-peer"
    state.port = 5001


def test_send_line_writes_encoded_bytes():
    writer = make_writer()

    with patch("src.queries.search.codec.encode", return_value='{"x":1}'):
        search._send_line(writer, {"x": 1})

    writer.write.assert_called_once_with(b'{"x":1}')


def test_search_peer_with_file_returns_matches_only():
    reset_state()
    state.peers = {
        "peer1": {
            "catalog": [
                {"name": "a.txt", "file_id": "f1", "size": 10},
                {"name": "b.txt", "file_id": "f2", "size": 20},
            ]
        },
        "peer2": {"catalog": None},
        "peer3": {
            "catalog": [
                {"name": "a.txt", "file_id": "f3", "size": 30},
            ]
        },
    }

    result = search.search_peer_with_file("a.txt")

    assert result == [
        {"name": "a.txt", "file_id": "f1", "size": 10, "peer_id": "peer1"},
        {"name": "a.txt", "file_id": "f3", "size": 30, "peer_id": "peer3"},
    ]


def test_handle_search_request_returns_if_seen_request():
    reset_state()
    state.seen_requests.add("req1")
    incoming_writer = make_writer()

    async def runner():
        await search.handle_search_request(
            {
                "request_id": "req1",
                "filename": "a.txt",
                "ttl": 2,
                "version": "1.0",
            },
            incoming_writer,
        )

    asyncio.run(runner())

    incoming_writer.drain.assert_not_awaited()
    assert state.request_routes == {}


def test_handle_search_request_local_hit_and_ttl_exhausted():
    reset_state()
    incoming_writer = make_writer()
    state.local_catalog = [{"name": "a.txt", "file_id": "f1", "size": 100}]

    async def runner():
        with patch("src.queries.search.get_lan_ip", return_value="192.168.1.10"), patch(
            "src.queries.search._send_line"
        ) as mock_send, patch("src.queries.search.logger.debug") as mock_debug:
            await search.handle_search_request(
                {
                    "request_id": "req2",
                    "filename": "a.txt",
                    "ttl": 1,
                    "version": "1.0",
                },
                incoming_writer,
            )

            assert "req2" in state.seen_requests
            assert state.request_routes["req2"] is incoming_writer
            mock_send.assert_called_once_with(
                incoming_writer,
                {
                    "type": "SEARCH_RESPONSE",
                    "version": "1.0",
                    "peer_id": "self-peer",
                    "request_id": "req2",
                    "filename": "a.txt",
                    "file_id": "f1",
                    "size": 100,
                    "host": "192.168.1.10",
                    "port": 5001,
                },
            )
            assert incoming_writer.drain.await_count == 1
            assert mock_debug.call_count >= 2

    asyncio.run(runner())


def test_handle_search_request_floods_and_logs_warning_on_failure():
    reset_state()
    incoming_writer = make_writer()
    good_writer = make_writer()
    bad_writer = make_writer(drain_side_effect=Exception("boom"))

    state.peers = {
        "peer-good": {"writer": good_writer},
        "peer-same": {"writer": incoming_writer},
        "peer-none": {"writer": None},
        "peer-bad": {"writer": bad_writer},
    }

    async def runner():
        with patch("src.queries.search._send_line") as mock_send, patch(
            "src.queries.search.logger.warning"
        ) as mock_warning:
            await search.handle_search_request(
                {
                    "request_id": "req3",
                    "filename": "missing.txt",
                    "ttl": 3,
                    "version": "1.0",
                },
                incoming_writer,
            )

            assert state.request_routes["req3"] is incoming_writer
            mock_send.assert_any_call(
                good_writer,
                {
                    "request_id": "req3",
                    "filename": "missing.txt",
                    "ttl": 2,
                    "version": "1.0",
                },
            )
            mock_send.assert_any_call(
                bad_writer,
                {
                    "request_id": "req3",
                    "filename": "missing.txt",
                    "ttl": 2,
                    "version": "1.0",
                },
            )
            good_writer.drain.assert_awaited_once()
            bad_writer.drain.assert_awaited_once()
            mock_warning.assert_called_once()

    asyncio.run(runner())


def test_handle_search_response_collects_at_origin():
    reset_state()
    state.pending_searches = {"req4": []}

    async def runner():
        with patch("src.queries.search.logger.debug") as mock_debug:
            await search.handle_search_response(
                {
                    "request_id": "req4",
                    "filename": "a.txt",
                    "host": "1.2.3.4",
                    "port": 5001,
                }
            )

            assert state.pending_searches["req4"] == [
                {
                    "request_id": "req4",
                    "filename": "a.txt",
                    "host": "1.2.3.4",
                    "port": 5001,
                }
            ]
            mock_debug.assert_called_once()

    asyncio.run(runner())


def test_handle_search_response_warns_when_no_route():
    reset_state()

    async def runner():
        with patch("src.queries.search.logger.warning") as mock_warning:
            await search.handle_search_response({"request_id": "req5"})
            mock_warning.assert_called_once()

    asyncio.run(runner())


def test_handle_search_response_routes_upstream():
    reset_state()
    upstream_writer = make_writer()
    state.request_routes = {"req6": upstream_writer}

    async def runner():
        message = {
            "request_id": "req6",
            "filename": "a.txt",
            "host": "1.1.1.1",
            "port": 5001,
        }

        with patch("src.queries.search._send_line") as mock_send, patch(
            "src.queries.search.logger.debug"
        ) as mock_debug:
            await search.handle_search_response(message)

            mock_send.assert_called_once_with(upstream_writer, message)
            upstream_writer.drain.assert_awaited_once()
            mock_debug.assert_called_once()

    asyncio.run(runner())


def test_handle_search_response_logs_warning_when_route_forward_fails():
    reset_state()
    upstream_writer = make_writer(drain_side_effect=Exception("fail"))
    state.request_routes = {"req7": upstream_writer}

    async def runner():
        with patch("src.queries.search._send_line") as mock_send, patch(
            "src.queries.search.logger.warning"
        ) as mock_warning:
            await search.handle_search_response({"request_id": "req7"})
            mock_send.assert_called_once()
            mock_warning.assert_called_once()

    asyncio.run(runner())


def test_flood_search_sends_to_peers_collects_results_and_cleans_up():
    reset_state()
    good_writer = make_writer()
    bad_writer = make_writer(drain_side_effect=Exception("boom"))
    state.peers = {
        "peer1": {"writer": good_writer},
        "peer2": {"writer": None},
        "peer3": {"writer": bad_writer},
    }

    async def runner():
        with patch("src.queries.search.uuid.uuid4", return_value="req8"), patch(
            "src.queries.search.get_lan_ip", return_value="192.168.0.10"
        ), patch("src.queries.search.DEFAULT_TTL", 4), patch(
            "src.queries.search.SEARCH_TIMEOUT", 0
        ), patch(
            "src.queries.search._send_line"
        ) as mock_send, patch(
            "src.queries.search.logger.warning"
        ) as mock_warning, patch(
            "src.queries.search.logger.info"
        ) as mock_info, patch(
            "src.queries.search.asyncio.sleep", new=AsyncMock()
        ):

            async def fake_sleep(_):
                state.pending_searches["req8"].append(
                    {
                        "request_id": "req8",
                        "filename": "a.txt",
                        "file_id": "f1",
                        "size": 10,
                        "peer_id": "peer1",
                        "host": "10.0.0.5",
                        "port": 6000,
                    }
                )

            with patch(
                "src.queries.search.asyncio.sleep",
                new=AsyncMock(side_effect=fake_sleep),
            ):
                results = await search.flood_search("a.txt")

            expected_msg = {
                "type": "SEARCH_REQUEST",
                "version": search.SUPPORTED_VERSIONS[0],
                "peer_id": "self-peer",
                "request_id": "req8",
                "filename": "a.txt",
                "ttl": 4,
                "origin_host": "192.168.0.10",
                "origin_port": 5001,
            }

            mock_send.assert_any_call(good_writer, expected_msg)
            mock_send.assert_any_call(bad_writer, expected_msg)
            good_writer.drain.assert_awaited_once()
            bad_writer.drain.assert_awaited_once()
            mock_warning.assert_called_once()
            mock_info.assert_called_once()
            assert results == [
                {
                    "request_id": "req8",
                    "filename": "a.txt",
                    "file_id": "f1",
                    "size": 10,
                    "peer_id": "peer1",
                    "host": "10.0.0.5",
                    "port": 6000,
                }
            ]
            assert "req8" not in state.pending_searches
            assert "req8" not in state.request_routes

    asyncio.run(runner())
