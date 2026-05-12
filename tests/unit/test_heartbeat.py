import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import src.state as state
import src.connection.heartbeat as hb


def _make_writer(closing=False):
    writer = MagicMock()
    writer.is_closing.return_value = closing
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


def _add_peer(peer_id, writer=None, last_pong=None):
    state.peers[peer_id] = {
        "peer_id": peer_id,
        "host": "127.0.0.1",
        "port": 9000,
        "catalog": None,
        "last_pong": last_pong,
        "reader": None,
        "writer": writer or _make_writer(),
    }


def _reset():
    state.peers.clear()
    state.PEER_ID_STUB = "local-peer"


def test_loop_exits_if_peer_not_in_state():
    _reset()

    async def runner():
        with patch(
            "src.connection.heartbeat.asyncio.sleep", new=AsyncMock(return_value=None)
        ):
            await hb.heartbeat_loop("ghost-peer")

    asyncio.run(runner())


def test_loop_exits_on_closed_writer():
    _reset()
    _add_peer("peer1", writer=_make_writer(closing=True))

    async def runner():
        with patch(
            "src.connection.heartbeat.asyncio.sleep", new=AsyncMock(return_value=None)
        ):
            await hb.heartbeat_loop("peer1")

    asyncio.run(runner())
    assert "peer1" not in state.peers


def test_loop_ping_error_logs_warning_and_peer_is_removed():
    _reset()
    writer = _make_writer(closing=False)
    writer.drain = AsyncMock(side_effect=Exception("drain failed"))
    _add_peer("peer2", writer=writer, last_pong=None)

    async def runner():
        with patch.object(hb, "HEARTBEAT_INTERVAL_SECONDS", 1), patch.object(
            hb, "MAX_MISSED_HEARTBEATS", 1
        ), patch(
            "src.connection.heartbeat.asyncio.sleep", new=AsyncMock(return_value=None)
        ), patch(
            "src.connection.heartbeat.logger.warning"
        ) as mock_warning:
            await hb.heartbeat_loop("peer2")
            assert mock_warning.call_count >= 1

    asyncio.run(runner())

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert "peer2" not in state.peers


def test_loop_alive_peer_hits_recent_pong_branch():
    _reset()
    writer = _make_writer(closing=False)
    _add_peer("peer3", writer=writer, last_pong=100.0)

    async def runner():
        sleep_mock = AsyncMock(side_effect=[None, RuntimeError("stop")])

        with patch.object(hb, "HEARTBEAT_INTERVAL_SECONDS", 1), patch.object(
            hb, "MAX_MISSED_HEARTBEATS", 3
        ), patch("src.connection.heartbeat.asyncio.sleep", new=sleep_mock), patch(
            "src.connection.heartbeat.time.time", return_value=100.5
        ), patch(
            "src.connection.heartbeat.logger.debug"
        ) as mock_debug:
            try:
                await hb.heartbeat_loop("peer3")
            except RuntimeError as exc:
                assert str(exc) == "stop"

            writer.drain.assert_awaited_once()
            mock_debug.assert_called()

    asyncio.run(runner())
    assert "peer3" in state.peers


def test_loop_stale_peer_wait_closed_exception_is_ignored():
    _reset()
    writer = _make_writer(closing=False)
    writer.wait_closed = AsyncMock(side_effect=Exception("close failed"))
    _add_peer("peer4", writer=writer, last_pong=time.time() - 100)

    async def runner():
        with patch.object(hb, "HEARTBEAT_INTERVAL_SECONDS", 1), patch.object(
            hb, "MAX_MISSED_HEARTBEATS", 1
        ), patch(
            "src.connection.heartbeat.asyncio.sleep", new=AsyncMock(return_value=None)
        ):
            await hb.heartbeat_loop("peer4")

    asyncio.run(runner())

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()
    assert "peer4" not in state.peers


def test_start_heartbeat_returns_task():
    _reset()
    _add_peer("peer5", writer=_make_writer(), last_pong=time.time())

    async def runner():
        task = hb.start_heartbeat("peer5")
        assert isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(runner())
