import asyncio
import time
import logging

import src.state as state
import src.protocol.codec as codec
from config import (
    HEARTBEAT_INTERVAL_SECONDS,
    MAX_MISSED_HEARTBEATS,
    SUPPORTED_VERSIONS,
)

logger = logging.getLogger(__name__)


def _send_ping(writer: asyncio.StreamWriter, peer_id: str) -> None:
    """Write a PING message to the wire (non-blocking)."""
    msg = {
        "type": "PING",
        "version": SUPPORTED_VERSIONS[0],
        "peer_id": state.PEER_ID_STUB,
    }
    writer.write(codec.encode(msg).encode("utf-8"))


async def heartbeat_loop(peer_id: str) -> None:
    """
    Continuously PING a single peer.

    - Sends a PING every HEARTBEAT_INTERVAL_SECONDS.
    - A PONG updates peer["last_pong"] via PongHandler (already wired in
      message_handler_factory.py).
    - If last_pong is older than MAX_MISSED_HEARTBEATS * interval the peer
      is considered offline: it is removed from state.peers and the loop exits.
    """
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

        peer = state.peers.get(peer_id)
        if peer is None:
            logger.info(
                f"[HEARTBEAT] peer {peer_id!r} gone from state — stopping loop."
            )
            return

        writer: asyncio.StreamWriter | None = peer.get("writer")
        if writer is None or writer.is_closing():
            logger.warning(
                f"[HEARTBEAT] writer for {peer_id!r} is closed — stopping loop."
            )
            state.peers.pop(peer_id, None)
            return

        # ── send PING ──────────────────────────────────────────────────────
        try:
            _send_ping(writer, peer_id)
            await writer.drain()
        except Exception as e:
            logger.warning(f"[HEARTBEAT] Could not send PING to {peer_id!r}: {e}")

        # ── check last_pong ────────────────────────────────────────────────
        # Count how many heartbeat intervals have passed since the last PONG.
        # If last_pong is None the peer has never responded at all.
        last_pong: float | None = peer.get("last_pong")
        deadline = HEARTBEAT_INTERVAL_SECONDS * MAX_MISSED_HEARTBEATS

        if last_pong is not None and (time.time() - last_pong) <= deadline:
            # Peer is alive — heard from them recently enough
            logger.debug(
                f"[HEARTBEAT] peer={peer_id!r} alive (last pong {time.time() - last_pong:.1f}s ago)"
            )
            continue

        # Either never ponged, or pong is too old — count missed intervals
        if last_pong is None:
            elapsed_intervals = 1  # first interval, give benefit of the doubt
        else:
            elapsed_intervals = int(
                (time.time() - last_pong) / HEARTBEAT_INTERVAL_SECONDS
            )

        logger.debug(
            f"[HEARTBEAT] peer={peer_id!r} missed ~{elapsed_intervals}/{MAX_MISSED_HEARTBEATS} intervals"
        )

        if elapsed_intervals >= MAX_MISSED_HEARTBEATS:
            logger.warning(
                f"[HEARTBEAT] peer {peer_id!r} is OFFLINE "
                f"(no PONG after {elapsed_intervals} intervals). Removing from peers."
            )
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            state.peers.pop(peer_id, None)
            return


def start_heartbeat(peer_id: str) -> asyncio.Task:
    """
    Spawn a heartbeat_loop task for peer_id and return it.
    Call this right after a peer is fully connected.
    """
    task = asyncio.create_task(heartbeat_loop(peer_id), name=f"heartbeat-{peer_id}")
    logger.info(f"[HEARTBEAT] started for peer {peer_id!r}")
    return task
