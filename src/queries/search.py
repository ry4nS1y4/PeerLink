import asyncio
import uuid
import logging

import src.state as state
import src.protocol.codec as codec
from config import DEFAULT_TTL, SEARCH_TIMEOUT, SUPPORTED_VERSIONS
from src.protocol.Local_Address import get_lan_ip

logger = logging.getLogger(__name__)


def _send_line(writer: asyncio.StreamWriter, msg: dict) -> None:
    writer.write(codec.encode(msg).encode("utf-8"))


def search_peer_with_file(filename: str) -> list[dict]:
    """
    Direct (single-hop) search through catalogs of directly connected peers.
    Kept for backwards compatibility.
    """
    found_peers: list = []
    for peer_id, peer in state.peers.items():
        if not peer["catalog"]:
            continue
        for entry in peer["catalog"]:
            if entry["name"] == filename:
                found_peers.append({**entry, "peer_id": peer_id})
    return found_peers


async def handle_search_request(
    msg: dict,
    incoming_writer: asyncio.StreamWriter,
) -> None:
    """
    Called by manager.py when a SEARCH_REQUEST arrives on an active connection.

    incoming_writer: the writer back toward whoever sent us this request.
      - Used to send SEARCH_RESPONSE back if we have the file.
      - Recorded in request_routes so intermediate nodes can forward responses.
      - Skipped when flooding onward (don't re-flood back the way it came).
    """
    request_id: str = msg["request_id"]

    # 1. Deduplication
    if request_id in state.seen_requests:
        return
    state.seen_requests.add(request_id)

    # 2. Record route back toward whoever sent this to us
    state.request_routes[request_id] = incoming_writer

    filename: str = msg["filename"]
    ttl: int = msg["ttl"]

    # 3. Check our own local catalog
    for entry in state.local_catalog:
        if entry["name"] == filename:
            response: dict = {
                "type": "SEARCH_RESPONSE",
                "version": msg["version"],
                "peer_id": state.PEER_ID_STUB,
                "request_id": request_id,
                "filename": filename,
                "file_id": entry["file_id"],
                "size": entry["size"],
                "host": get_lan_ip(),
                "port": state.port,
            }
            _send_line(incoming_writer, response)
            await incoming_writer.drain()
            logger.debug(f"[SEARCH] Hit for '{filename}' — sent SEARCH_RESPONSE back")
            # Don't return: keep flooding so origin collects all results

    # 4. Flood onward if TTL allows
    if ttl <= 1:
        logger.debug(f"[SEARCH] TTL exhausted for request_id={request_id}")
        return

    forwarded_msg: dict = {**msg, "ttl": ttl - 1}

    for peer_id, peer in list(state.peers.items()):
        peer_writer: asyncio.StreamWriter | None = peer.get("writer")
        if peer_writer is None or peer_writer is incoming_writer:
            continue  # never flood back the way it came
        try:
            _send_line(peer_writer, forwarded_msg)
            await peer_writer.drain()
            logger.debug(
                f"[SEARCH] Forwarded request_id={request_id} to peer {peer_id}"
            )
        except Exception as e:
            logger.warning(f"[SEARCH] Failed to forward to {peer_id}: {e}")


async def handle_search_response(msg: dict) -> None:
    """
    Called by manager.py when a SEARCH_RESPONSE arrives.

    If we originated this search -> collect into pending_searches.
    Otherwise -> route back toward origin via request_routes.
    """
    request_id: str = msg["request_id"]

    # Are we the origin?
    if request_id in state.pending_searches:
        state.pending_searches[request_id].append(msg)
        logger.debug(
            f"[SEARCH] Collected result for '{msg['filename']}' "
            f"from {msg['host']}:{msg['port']}"
        )
        return

    # Intermediate node — route back upstream
    upstream_writer: asyncio.StreamWriter | None = state.request_routes.get(request_id)
    if upstream_writer is None:
        logger.warning(
            f"[SEARCH] No route for request_id={request_id}, dropping SEARCH_RESPONSE"
        )
        return

    try:
        _send_line(upstream_writer, msg)
        await upstream_writer.drain()
        logger.debug(f"[SEARCH] Routed SEARCH_RESPONSE for {request_id} upstream")
    except Exception as e:
        logger.warning(f"[SEARCH] Failed to route SEARCH_RESPONSE upstream: {e}")


async def flood_search(filename: str) -> list[dict]:
    """
    Originate a multihop search from this node.

    Returns a list of SEARCH_RESPONSE dicts after SEARCH_TIMEOUT seconds.
    Each result has: host, port, file_id, size, filename, peer_id.
    Caller picks result[0] (or best) and opens a direct TCP connection to
    host:port to download — no proxy involved.
    """
    request_id: str = str(uuid.uuid4())
    state.seen_requests.add(request_id)
    state.pending_searches[request_id] = []

    search_msg: dict = {
        "type": "SEARCH_REQUEST",
        "version": SUPPORTED_VERSIONS[0],
        "peer_id": state.PEER_ID_STUB,
        "request_id": request_id,
        "filename": filename,
        "ttl": DEFAULT_TTL,
        "origin_host": get_lan_ip(),
        "origin_port": state.port,
    }

    for peer_id, peer in list(state.peers.items()):
        peer_writer: asyncio.StreamWriter | None = peer.get("writer")
        if peer_writer is None:
            continue
        try:
            _send_line(peer_writer, search_msg)
            await peer_writer.drain()
            logger.debug(f"[SEARCH] Flooded SEARCH_REQUEST to peer {peer_id}")
        except Exception as e:
            logger.warning(f"[SEARCH] Failed to flood to {peer_id}: {e}")

    await asyncio.sleep(SEARCH_TIMEOUT)

    results: list[dict] = state.pending_searches.pop(request_id, [])
    state.request_routes.pop(request_id, None)

    logger.info(f"[SEARCH] '{filename}' — {len(results)} result(s) found")
    return results
