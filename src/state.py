from src.catalog.local_catalog import build_local_catalog, CatalogEntry
from config import SHARED_FOLDER
from typing import TypedDict, NotRequired
import asyncio
from src.identification.main_Identity import create_Identity_Object
from dataclasses import dataclass, field


class Peer(TypedDict):
    peer_id: str
    host: str
    port: int
    catalog: list[CatalogEntry] | None
    last_pong: float | None
    reader: asyncio.StreamReader | None
    writer: asyncio.StreamWriter | None
    heartbeat_started: NotRequired[bool]


@dataclass
class AppState:
    PEER_ID_STUB: str = ""
    Public_Key: str = ""
    peers: dict = field(default_factory=dict)
    local_catalog: list[CatalogEntry] = field(default_factory=list)
    host: str = "127.0.0.1"
    port: int = 0
    seen_requests: set = field(default_factory=set)
    pending_searches: dict = field(default_factory=dict)
    request_routes: dict = field(default_factory=dict)

    pending_downloads: dict = field(default_factory=dict)
    connecting_peers: set[str] = field(default_factory=set)
    download_routes: dict = field(default_factory=dict)


app_state = AppState()


# Module-level aliases for backwards compatibility
def __getattr__(name):
    return getattr(app_state, name)


def init_state(
    portInc: int,
    mode: int,
    identity_fn=create_Identity_Object,
    catalog_fn=build_local_catalog,
) -> None:
    """
    Initialize application state.
    """
    app_state.PEER_ID_STUB = f"{identity_fn(mode)}:{portInc}"
    """
    if MODE == 1:
        global Public_Key
        if not Public_Key:
            Public_Key = f"{CreateKeys()}"
        if not PEER_ID_STUB:
            PEER_ID_STUB = f"STUB: {CreatePeerID(bytes.fromhex(Public_Key))}"
    else:
        if PEER_ID_STUB == "":
            PEER_ID_STUB = createPeerIdentity()
            print(f"Mine: {PEER_ID_STUB}")
"""
    app_state.local_catalog = catalog_fn(SHARED_FOLDER)
    app_state.port = portInc
    # In future We can implement the ip address if we go beyond phase 1


def reset():
    """
    ONLY FOR TESTING
    """
    app_state.PEER_ID_STUB = ""
    app_state.local_catalog = []
    app_state.seen_requests = set()
    app_state.pending_searches = {}
    app_state.request_routes = {}
    app_state.pending_downloads = {}
    app_state.connecting_peers = set()
    app_state.download_routes = {}


## Complete this shifan
