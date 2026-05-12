import argparse
import asyncio
import logging

from config import MODE
from src.connection.download import download_file_from_fileId
from src.connection.manager import connect_to_peer, start_server
from src.protocol.Udp_Announce import periodic_announces
from src.protocol.Udp_Listen import start_udp_listener
from src.queries.search import flood_search
import src.state as state
from src.tui_textual import PeerLinkTextualApp

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="PeerLink (Textual UI)")
parser.add_argument("port", type=int, help="Port to listen on")
args = parser.parse_args()


async def main() -> None:
    state.init_state(args.port, MODE)

    server = await start_server()
    serve_task = asyncio.create_task(server.serve_forever())

    udp_transport, _protocol = await start_udp_listener()
    announce_task = asyncio.create_task(periodic_announces(args.port))

    app = PeerLinkTextualApp(
        state_ref=state,
        connect_fn=connect_to_peer,
        download_fn=download_file_from_fileId,
        search_fn=flood_search,
    )

    try:
        await app.run_async()
    finally:
        announce_task.cancel()
        server.close()
        await server.wait_closed()
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass
        udp_transport.close()


if __name__ == "__main__":
    asyncio.run(main())
