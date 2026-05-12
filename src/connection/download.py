from config import SUPPORTED_VERSIONS
import src.state as state
import asyncio
import uuid
import src.protocol.codec as codec


async def download_file_from_fileId(file_id: str, peer_id: str) -> str:
    """
    Download a file by file_id from peer_id.

    Direct path: if a live writer to peer_id exists, send FILE_REQUEST straight to them.
    Relay path: if no direct connection, pick any connected peer as an intermediary and
                send FILE_REQUEST with target_peer_id so they forward it on our behalf.
    """
    peer = state.peers.get(peer_id)
    writer: asyncio.StreamWriter | None = None if peer is None else peer.get("writer")

    if writer is not None and not writer.is_closing():
        # Direct download
        json_body: dict = {
            "type": "FILE_REQUEST",
            "version": SUPPORTED_VERSIONS[0],
            "peer_id": state.PEER_ID_STUB,
            "file_id": file_id,
        }
        return await _execute_download(file_id, peer_id, writer, json_body)

    # Relay download: route through any directly connected peer
    relay_writer: asyncio.StreamWriter | None = None
    for p in state.peers.values():
        w = p.get("writer")
        if w is not None and not w.is_closing():
            relay_writer = w
            break

    if relay_writer is None:
        raise ConnectionError(
            f"Peer {peer_id} is not directly reachable and no relay peers are available."
        )

    request_id = str(uuid.uuid4())
    relay_body: dict = {
        "type": "FILE_REQUEST",
        "version": SUPPORTED_VERSIONS[0],
        "peer_id": state.PEER_ID_STUB,
        "file_id": file_id,
        "target_peer_id": peer_id,
        "request_id": request_id,
    }
    return await _execute_download(file_id, peer_id, relay_writer, relay_body)


async def _execute_download(
    file_id: str,
    peer_id: str,
    writer: asyncio.StreamWriter,
    json_body: dict,
) -> str:
    key = (peer_id, file_id)
    if key in state.pending_downloads:
        raise RuntimeError(
            f"Download already in progress for {file_id} from {peer_id}."
        )

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    state.pending_downloads[key] = future

    try:
        writer.write(codec.encode(json_body).encode("utf-8"))
        await writer.drain()

        saved_path = await asyncio.wait_for(future, timeout=30)
        return saved_path
    finally:
        state.pending_downloads.pop(key, None)
