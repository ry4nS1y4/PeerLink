import asyncio
import aiofiles
import src.state as state
import src.protocol.codec as codec
import src.protocol.validator as validator
from src.protocol import models
from config import SUPPORTED_VERSIONS
from src.connection.heartbeat import start_heartbeat


def _send_line(writer: asyncio.StreamWriter, msg: dict) -> None:
    """
    Send one protocol message as a single newline-delimited JSON line.
    """
    writer.write((codec.encode(msg)).encode("utf-8"))


class PeerRegistry:
    """
    Manages upsert and cleanup of peer entries in state.
    """

    def __init__(self, peers: dict):
        self.peers = peers

    def upsert(
        self,
        peer_id: str,
        host: str,
        port: int,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """
        Create/update the peer entry. Do NOT overwrite catalog/last_pong if they already exist.
        """
        existing: dict | None = self.peers.get(peer_id)

        if existing is None:
            self.peers[peer_id] = {
                "peer_id": peer_id,
                "host": host,
                "port": port,
                "catalog": None,
                "last_pong": None,
                "reader": reader,
                "writer": writer,
                "heartbeat_started": False,
            }
        else:
            existing["host"] = host
            existing["port"] = port
            existing["reader"] = reader
            existing["writer"] = writer

    def remove_by_peer_id(self, peer_id: str) -> None:
        """
        Remove a peer entry by peer_id.
        """
        self.peers.pop(peer_id, None)

    def remove_by_address(self, host: str, port: int) -> None:
        """
        Remove a peer entry matched by host/port on disconnect.
        """
        close_id: str = ""
        for peer_id, peer in list(self.peers.items()):
            if peer.get("host") == host and peer.get("port") == port:
                close_id = peer_id
                break

        if close_id:
            del self.peers[close_id]


class MessageDispatcher:
    """
    Dispatches handler results to the appropriate send/receive logic.
    """

    async def dispatch(
        self,
        result,
        msg: dict,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
        is_connector: bool,
    ) -> None:
        if isinstance(result, dict):
            await self._handle_dict(result, msg, writer, is_connector)
        elif isinstance(result, models.FileResponseData):
            await self._handle_file_response(result, writer)
        elif isinstance(result, models.FileReceiveData):
            await self._handle_file_receive(result, msg, reader)
        elif isinstance(result, models.FileRelayData):
            await self._handle_file_relay(result, msg, writer)
        elif isinstance(result, models.FileForwardData):
            await self._handle_file_forward(result, msg, reader)

    async def _handle_dict(
        self,
        result: dict,
        msg: dict,
        writer: asyncio.StreamWriter,
        is_connector: bool,
    ) -> None:
        _send_line(writer, result)
        await writer.drain()

        if (
            not is_connector
            and msg.get("type") == "CATALOG_REQUEST"
            and result.get("type") == "CATALOG_RESPONSE"
        ):
            other_id = msg["peer_id"]
            if state.peers.get(other_id) and not state.peers[other_id].get("catalog"):
                followup_req: dict = {
                    "type": "CATALOG_REQUEST",
                    "version": result["version"],
                    "peer_id": state.PEER_ID_STUB,
                }
                _send_line(writer, followup_req)
                await writer.drain()

    async def _handle_file_response(
        self, result: models.FileResponseData, writer: asyncio.StreamWriter
    ) -> None:
        _send_line(writer, result.header)
        await writer.drain()

        async with aiofiles.open(result.filepath, "rb") as f:
            data = await f.read()
            writer.write(data)
            await writer.drain()

    async def _handle_file_receive(
        self,
        result: models.FileReceiveData,
        msg: dict,
        reader: asyncio.StreamReader,
    ) -> None:
        # ── receive raw bytes ──────────────────────────────────────────
        from src.connection.hash_check import verify_file_hash

        key = (msg["peer_id"], msg.get("file_id"))

        try:
            inc_file: bytes = await reader.readexactly(result.size)

            async with aiofiles.open(result.filepath, "wb") as f:
                await f.write(inc_file)

            expected_file_id: str = msg.get("file_id", "")
            if expected_file_id:
                ok = verify_file_hash(result.filepath, expected_file_id)
                if not ok:
                    future = state.pending_downloads.get(key)
                    if future is not None and not future.done():
                        future.set_exception(
                            ValueError("Downloaded file failed hash verification.")
                        )
                    return

            future = state.pending_downloads.get(key)
            if future is not None and not future.done():
                future.set_result(result.filepath)

        except Exception as exc:
            future = state.pending_downloads.get(key)
            if future is not None and not future.done():
                future.set_exception(exc)
            raise

    async def _handle_file_relay(
        self, result: models.FileRelayData, msg: dict, writer: asyncio.StreamWriter
    ) -> None:
        """
        Intermediate node: record the upstream writer and forward FILE_REQUEST to target.
        writer is the writer back toward the requester (C).
        """
        target_peer = state.peers.get(result.target_peer_id, {})
        target_writer: asyncio.StreamWriter | None = target_peer.get("writer")
        if target_writer is None or target_writer.is_closing():
            error: dict = {
                "type": "ERROR",
                "version": msg.get("version", "1.0"),
                "peer_id": state.PEER_ID_STUB,
                "file_id": msg.get("file_id", ""),
                "code": "PEER_NOT_REACHABLE",
                "message": f"Relay target {result.target_peer_id} is not connected",
            }
            _send_line(writer, error)
            await writer.drain()
            return

        state.download_routes[result.request_id] = writer

        # Forward without target_peer_id so the next hop treats it as a direct request
        forward_msg = {k: v for k, v in msg.items() if k != "target_peer_id"}
        _send_line(target_writer, forward_msg)
        await target_writer.drain()

    async def _handle_file_forward(
        self, result: models.FileForwardData, msg: dict, reader: asyncio.StreamReader
    ) -> None:
        """
        Intermediate node: read raw bytes from the sender and pipe them upstream to C.
        """
        request_id = msg.get("request_id", "")
        try:
            _send_line(result.upstream_writer, msg)
            await result.upstream_writer.drain()

            data = await reader.readexactly(result.size)
            result.upstream_writer.write(data)
            await result.upstream_writer.drain()
        finally:
            state.download_routes.pop(request_id, None)


class ConnectionHandler:
    def __init__(
        self,
        registry: PeerRegistry,
        dispatcher: MessageDispatcher,
        is_connector: bool = False,
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.is_connector = is_connector

    async def run(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        from src.protocol.message_handler_factory import (
            MessageHandlerFactory,
            MessageHandler,
        )

        connected_peer_id: str | None = None

        try:
            while True:
                line: bytes = await reader.readline()
                if not line:
                    break

                try:
                    msg: dict = codec.decode(line.decode("utf-8"))
                except Exception:
                    continue

                if not validator.validate(msg):
                    error_dict = {
                        "type": "ERROR",
                        "version": SUPPORTED_VERSIONS[0],
                        "peer_id": state.PEER_ID_STUB,
                        "code": "INCORRECT_PROTOCOL_FORMAT",
                        "message": "No protocol exists for the message.",
                    }
                    _send_line(writer, error_dict)
                    await writer.drain()
                    continue

                msg_peer_id: str = msg["peer_id"]

                # Lock the peer identity on the first message only.
                # Relayed messages (e.g. FILE_RESPONSE forwarded by an
                # intermediate node) carry a third-party peer_id — we must
                # not let those overwrite the connection's true identity or
                # register phantom peers.
                if connected_peer_id is None:
                    connected_peer_id = msg_peer_id
                    other_peer_ip, socket_port = writer.get_extra_info("peername")

                    existing = state.peers.get(msg_peer_id)
                    advertised_port = msg.get("port")

                    if advertised_port is None and existing is not None:
                        advertised_port = existing.get("port")

                    if advertised_port is None:
                        advertised_port = socket_port

                    self.registry.upsert(
                        msg_peer_id, other_peer_ip, advertised_port, reader, writer
                    )
                    peer = state.peers[msg_peer_id]
                    if not peer.get("heartbeat_started", False):
                        peer["heartbeat_started"] = True
                        start_heartbeat(msg_peer_id)

                protocol_handler: MessageHandler = MessageHandlerFactory.get_handler(
                    msg
                )
                result = protocol_handler.handle(msg)

                if msg.get("type") == "SEARCH_REQUEST":
                    from src.queries.search import handle_search_request

                    asyncio.create_task(handle_search_request(msg, writer))
                    continue

                if msg.get("type") == "SEARCH_RESPONSE":
                    from src.queries.search import handle_search_response

                    asyncio.create_task(handle_search_response(msg))
                    continue

                await self.dispatcher.dispatch(
                    result, msg, writer, reader, self.is_connector
                )

        finally:
            if connected_peer_id is not None:
                self.registry.remove_by_peer_id(connected_peer_id)

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    is_connector: bool = False,
) -> None:
    registry = PeerRegistry(state.peers)
    dispatcher = MessageDispatcher()
    handler = ConnectionHandler(registry, dispatcher, is_connector)
    await handler.run(reader, writer)


async def start_server() -> asyncio.Server:
    server = await asyncio.start_server(handle_connection, "0.0.0.0", state.port)
    return server


async def connect_to_peer(host: str, port: int) -> None:
    from src.connection.heartbeat import start_heartbeat

    for peer in state.peers.values():
        writer = peer.get("writer")
        if (
            peer.get("host") == host
            and peer.get("port") == port
            and writer is not None
            and not writer.is_closing()
        ):
            return

    reader, writer = await asyncio.open_connection(host, port)

    cat_req: dict = {
        "type": "CATALOG_REQUEST",
        "version": SUPPORTED_VERSIONS[0],
        "peer_id": state.PEER_ID_STUB,
        "port": state.port,
    }
    _send_line(writer, cat_req)
    await writer.drain()

    registry = PeerRegistry(state.peers)

    while True:
        line: bytes = await reader.readline()
        if not line:
            raise ConnectionError("Peer closed connection during handshake.")

        response: dict = codec.decode(line.decode("utf-8"))
        if not validator.validate(response):
            continue

        other_peer_id: str = response["peer_id"]
        registry.upsert(other_peer_id, host, port, reader, writer)

        if response.get("type") == "CATALOG_RESPONSE":
            state.peers[other_peer_id]["catalog"] = response.get("files")
            break

    # ── Feature 2: start heartbeat for this peer ───────────────────────────
    peer = state.peers[other_peer_id]
    if not peer.get("heartbeat_started", False):
        peer["heartbeat_started"] = True
        start_heartbeat(other_peer_id)

    asyncio.create_task(handle_connection(reader, writer, is_connector=True))
