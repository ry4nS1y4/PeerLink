from abc import ABC, abstractmethod
import asyncio
import time

from src.connection.manager import connect_to_peer
import src.state as state
from src.protocol import models
from src.catalog.local_catalog import CatalogEntry
from config import SHARED_FOLDER, DOWNLOADS_FOLDER
import logging

logger = logging.getLogger(__name__)


# Defines the standard contract that all protocol message handlers must follow.
class MessageHandler(ABC):
    @abstractmethod
    def handle(self, msg: dict) -> dict:
        pass


class PingHandler(MessageHandler):
    def handle(self, inp: dict) -> dict:
        msg: dict = {
            "type": "PONG",
            "version": inp["version"],
            "peer_id": state.PEER_ID_STUB,
        }
        return msg


class PongHandler(MessageHandler):
    def handle(self, inp: dict) -> None:
        """Record the timestamp of the latest PONG from this peer."""
        try:
            state.peers[inp["peer_id"]]["last_pong"] = time.time()
            logger.debug(f"[PONG] received from {inp['peer_id']!r}")
        except KeyError:
            pass


class CatalogReqHandler(MessageHandler):
    def handle(self, inp: dict) -> dict:
        msg: dict = {
            "type": "CATALOG_RESPONSE",
            "version": inp["version"],
            "peer_id": state.PEER_ID_STUB,
            "port": state.port,
            "files": state.local_catalog,
        }
        return msg


class CatalogResHandler(MessageHandler):
    def handle(self, inp: dict) -> None:
        try:
            state.peers[inp["peer_id"]]["catalog"] = inp["files"]
        except KeyError:
            pass


class FileReqHandler(MessageHandler):
    def handle(
        self, inp: dict
    ) -> models.FileResponseData | models.FileRelayData | dict:
        target_peer_id = inp.get("target_peer_id")
        request_id = inp.get("request_id", "")

        # Relay: request is destined for a different peer
        if target_peer_id and target_peer_id != state.PEER_ID_STUB:
            target_peer = state.peers.get(target_peer_id)
            target_writer = None if target_peer is None else target_peer.get("writer")
            if target_writer is None or target_writer.is_closing():
                return {
                    "type": "ERROR",
                    "version": inp["version"],
                    "peer_id": state.PEER_ID_STUB,
                    "file_id": inp["file_id"],
                    "code": "PEER_NOT_REACHABLE",
                    "message": f"Cannot relay to {target_peer_id}: not connected",
                }
            return models.FileRelayData(target_peer_id, request_id)

        # Direct: serve file from local catalog
        found_file: CatalogEntry | None = None
        for file in state.local_catalog:
            if file["file_id"] == inp["file_id"]:
                found_file = file
                break
        else:
            return {
                "type": "ERROR",
                "version": inp["version"],
                "peer_id": state.PEER_ID_STUB,
                "file_id": inp["file_id"],
                "code": "FILE_NOT_FOUND",
                "message": "No file with that file_id exists on this peer",
            }
        assert found_file is not None
        headers: dict = {
            "type": "FILE_RESPONSE",
            "version": inp["version"],
            "peer_id": state.PEER_ID_STUB,
            "file_id": found_file["file_id"],
            "name": found_file["name"],
            "size": found_file["size"],
            "request_id": request_id,
        }
        return models.FileResponseData(headers, f"{SHARED_FOLDER}/{found_file['name']}")


class FileResHandler(MessageHandler):
    def handle(self, inp: dict) -> models.FileReceiveData | models.FileForwardData:
        request_id = inp.get("request_id", "")
        upstream_writer = state.download_routes.get(request_id) if request_id else None
        if upstream_writer is not None and not upstream_writer.is_closing():
            return models.FileForwardData(inp["size"], upstream_writer)
        return models.FileReceiveData(inp["size"], f"{DOWNLOADS_FOLDER}/{inp['name']}")


class SearchReqHandler(MessageHandler):
    """
    Handles an incoming SEARCH_REQUEST at an intermediate or destination node.

    Flow:
      1. Deduplicate via seen_requests — drop if already seen.
      2. Check our own local_catalog for the filename.
         If found → send SEARCH_RESPONSE back on the arriving writer (stored via request_routes).
      3. If TTL > 1, decrement and flood to all connected peers EXCEPT the one
         the request arrived on (stored in request_routes so we can skip them).
      4. Record request_id → incoming writer in request_routes so SEARCH_RESPONSE
         messages can be routed back toward the origin.
    """

    def handle(self, inp: dict) -> None:
        # Deduplication is handled in manager.py before this is called,
        # but the actual flood + local check logic runs as an asyncio task
        # so we can await writers.  Return None here; manager dispatches the task.
        return None


class SearchResHandler(MessageHandler):
    """
    Handles an incoming SEARCH_RESPONSE travelling back hop-by-hop.

    If we are the origin (request_id is in pending_searches) → collect the result.
    Otherwise → look up request_routes[request_id] and forward the message.
    """

    def handle(self, inp: dict) -> None:
        return None


class ErrorHandler(MessageHandler):
    def handle(self, inp: dict) -> None:
        logger.error(
            f"Received error from {inp['peer_id']}: [{inp['code']}] {inp['message']}"
        )

        file_id = inp.get("file_id")
        if file_id is not None:
            key = (inp["peer_id"], file_id)
            future = state.pending_downloads.get(key)
            if future is not None and not future.done():
                future.set_exception(FileNotFoundError(inp["message"]))


async def _connect_announced_peer(host: str, port: int, peer_id: str) -> None:
    try:
        await connect_to_peer(host, port)
    except Exception as exc:
        logger.debug(f"Connect to announced peer {peer_id} failed: {exc}")
    finally:
        state.connecting_peers.discard(peer_id)


class AnnounceHandler(MessageHandler):
    def handle(self, inp: dict) -> None:
        if inp["peer_id"] == state.PEER_ID_STUB:
            return

        peer = state.peers.get(inp["peer_id"])

        if peer is None:
            state.peers[inp["peer_id"]] = {
                "peer_id": inp["peer_id"],
                "host": inp["host"],
                "port": inp["port"],
                "catalog": None,
                "last_pong": None,
                "reader": None,
                "writer": None,
            }
            peer = state.peers[inp["peer_id"]]
        else:
            peer["host"] = inp["host"]
            peer["port"] = inp["port"]

        writer = peer.get("writer")
        if writer is not None and not writer.is_closing():
            return

        if inp["peer_id"] in state.connecting_peers:
            return

        state.connecting_peers.add(inp["peer_id"])
        asyncio.create_task(
            _connect_announced_peer(inp["host"], inp["port"], inp["peer_id"])
        )


# =============================================================================
# DESIGN PATTERN: Factory Method
# Dynamically instantiates the appropriate MessageHandler subclass based on the
# incoming JSON 'type', decoupling connection logic from specific message processing.
# =============================================================================
class MessageHandlerFactory:
    @staticmethod
    def get_handler(msg: dict) -> MessageHandler:
        match (msg["type"]):
            case "PING":
                return PingHandler()
            case "PONG":
                return PongHandler()
            case "CATALOG_REQUEST":
                return CatalogReqHandler()
            case "CATALOG_RESPONSE":
                return CatalogResHandler()
            case "FILE_REQUEST":
                return FileReqHandler()
            case "FILE_RESPONSE":
                return FileResHandler()
            case "SEARCH_REQUEST":
                return SearchReqHandler()
            case "SEARCH_RESPONSE":
                return SearchResHandler()
            case "ANNOUNCE":
                return AnnounceHandler()
            case "ERROR":
                return ErrorHandler()
            case _:
                return ErrorHandler()
