import asyncio
import shlex
from src.connection.manager import start_server, connect_to_peer
from src.connection.download import download_file_from_fileId
import src.state as state
from src.protocol.Udp_Listen import start_udp_listener
from src.protocol.Udp_Announce import periodic_announces
import logging
from src.queries.search import search_peer_with_file, flood_search
import argparse
from config import MODE

logger = logging.getLogger()

parser = argparse.ArgumentParser(description="P2P File Sharing")
parser.add_argument("port", type=int, help="Port to listen on")
args = parser.parse_args()

# ── UI Helpers ─────────────────────────────────────────────────────────────────

DIVIDER = "-" * 40


def print_banner() -> None:
    """Print the startup banner and available commands."""
    print("\n╔══════════════════════════════════════╗")
    print("║         P2P File Sharing App         ║")
    print("╚══════════════════════════════════════╝\n")
    print_help()


def print_help() -> None:
    """Print all available CLI commands."""
    print(" Commands:")
    print("   connect  <host> <port>     Connect to a peer")
    print("   search   <file_name>       Multihop search for a file")
    print("   msearch  <file_name>       Alias for search")
    print("   download <number>          Download from last search results")
    print("   download <file_id> <peer>  Download a file directly")
    print("   peers                      List connected peers")
    print("   catalog                    Show your local catalog")
    print("   id / whoami                Show your peer ID")
    print("   quit / exit                Shutdown\n")
    print(DIVIDER)


# ── CLI Handler ────────────────────────────────────────────────────────────────


class CLIHandler:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        shutdown_event: asyncio.Event,
        connect_fn,
        download_fn,
        search_fn,
        state_ref,
    ):
        self.loop = loop
        self.shutdown_event = shutdown_event
        self.connect_fn = connect_fn
        self.download_fn = download_fn
        self.search_fn = search_fn
        self.state = state_ref
        self.last_search_results: list[dict] = []

    def handle_quit(self) -> bool:
        """Signal the async event loop to shut down and exit the CLI."""
        print("\n Shutting down... Goodbye.")
        print(DIVIDER)
        self.loop.call_soon_threadsafe(self.shutdown_event.set)
        return False

    def handle_id(self) -> bool:
        """Display this node's peer ID."""
        print(f" Peer ID: {self.state.PEER_ID_STUB}")
        return True

    def handle_catalog(self) -> bool:
        """Display all files in the local shared catalog."""
        catalog = self.state.local_catalog
        if not catalog:
            print(" Local catalog is empty.")
        else:
            print(f" Local Catalog ({len(catalog)} file(s)):")
            for entry in catalog:
                print(f"   - {entry}")
        return True

    def handle_peers(self) -> bool:
        """Display all currently connected peers."""
        peers = self.state.peers
        if not peers:
            print(" No peers currently connected.")
        else:
            print(f" Connected Peers ({len(peers)}):")
            for peer_id, peer in peers.items():
                print(f"   - {peer_id}  |  {peer.get('host')}:{peer.get('port')}")
        return True

    def handle_connect(self, parts: list[str]) -> bool:
        """Initiate a TCP connection to a remote peer."""
        if len(parts) != 3:
            print(" Usage: connect <host> <port>")
            return True
        host = parts[1]
        try:
            port = int(parts[2])
        except ValueError:
            print(" Port must be an integer.")
            return True

        print(f" Connecting to {host}:{port} ...")
        fut = asyncio.run_coroutine_threadsafe(self.connect_fn(host, port), self.loop)
        try:
            fut.result()
            print(f" Connected to {host}:{port}")
        except Exception as exc:
            print(f" Connect failed: {exc}")
        return True

    def handle_search(self, parts: list[str]) -> bool:
        """Multihop search for a file by name across the network."""
        if len(parts) < 2:
            print(" Usage: search <file_name>")
            return True

        file_name = " ".join(parts[1:]).strip()
        if not file_name:
            print(" Usage: search <file_name>")
            return True

        print(f' Searching network for "{file_name}" (TTL=5, timeout=2s)...')
        fut = asyncio.run_coroutine_threadsafe(flood_search(file_name), self.loop)
        try:
            results: list[dict] = fut.result()
        except Exception as exc:
            print(f" Search failed: {exc}")
            return True

        self.last_search_results = results

        if not results:
            print("   No matching files found.")
            return True

        print(f"   {len(results)} result(s):")
        for index, result in enumerate(results, start=1):
            print(
                f'   {index}. {result["filename"]} | {result["size"]} bytes'
                f' | peer: {result["peer_id"]}'
                f' | file_id: {result["file_id"]}'
                f' | @ {result["host"]}:{result["port"]}'
            )

        print('   Type "download <number>" to download one of these results.')
        return True

    def handle_msearch(self, parts: list[str]) -> bool:
        """Alias for multihop search."""
        return self.handle_search(parts)

    def handle_download(self, parts: list[str]) -> bool:
        """Download a file from the most recent search or by file ID and peer ID."""
        if len(parts) == 2:
            try:
                selection = int(parts[1])
            except ValueError:
                print(" Usage: download <number>")
                print(" Or:    download <file_id> <peer_id>")
                return True

            if not self.last_search_results:
                print(' No saved search results. Run "search <file_name>" first.')
                return True

            if selection < 1 or selection > len(self.last_search_results):
                print(
                    f" Invalid selection. Choose a number between 1 and {len(self.last_search_results)}."
                )
                return True

            selected = self.last_search_results[selection - 1]
            file_id = selected["file_id"]
            peer_id = selected["peer_id"]
            print(
                f' Downloading result #{selection}: {selected["filename"]}'
                f" from peer: {peer_id} ..."
            )
        elif len(parts) == 3:
            file_id = parts[1]
            peer_id = parts[2]
            print(f" Downloading file ID: {file_id} from peer: {peer_id} ...")
        else:
            print(" Usage: download <number>")
            print(" Or:    download <file_id> <peer_id>")
            return True

        fut = asyncio.run_coroutine_threadsafe(
            self.download_fn(file_id, peer_id), self.loop
        )
        try:
            saved_path = fut.result()
            print(f" Download complete: {saved_path}")
        except Exception as exc:
            print(f" Download failed: {exc}")
        return True

    def run(self) -> None:
        """Main CLI loop — reads input and dispatches to the appropriate handler."""
        print_banner()
        while True:
            try:
                prompt = (
                    f"peerlink:{self.state.PORT} [{len(self.state.peers)} peers] > "
                )
                cmd = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                self.handle_quit()
                break

            if not cmd:
                continue

            try:
                parts = shlex.split(cmd)
            except ValueError as exc:
                print(f" Could not parse command: {exc}")
                print(" Tip: wrap file names with spaces in quotes.")
                continue
            command = parts[0]

            match command:
                case "quit" | "exit":
                    if not self.handle_quit():
                        break
                case "help":
                    print_help()
                case "id" | "whoami" | "print":
                    self.handle_id()
                case "catalog":
                    self.handle_catalog()
                case "peers":
                    self.handle_peers()
                case "connect":
                    self.handle_connect(parts)
                case "search":
                    self.handle_search(parts)
                case "msearch":
                    self.handle_msearch(parts)
                case "download":
                    self.handle_download(parts)
                case _:
                    print(
                        f' Unknown command: "{command}". Type "help" to see available commands.'
                    )


# ── Entry Point ────────────────────────────────────────────────────────────────


async def main() -> None:
    # Initialize shared application state
    state.init_state(args.port, MODE)
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # Start TCP server for incoming peer connections
    server = await start_server()
    serve_task = asyncio.create_task(server.serve_forever())

    # Start UDP listener for peer discovery
    udp_transport, protocol = await start_udp_listener()

    # Begin periodic UDP announces so other peers can discover us
    asyncio.create_task(periodic_announces(args.port))

    # Start the CLI in a thread so it doesn't block the event loop
    cli = CLIHandler(
        loop=loop,
        shutdown_event=shutdown_event,
        connect_fn=connect_to_peer,
        download_fn=download_file_from_fileId,
        search_fn=search_peer_with_file,
        state_ref=state,
    )
    cli_future = loop.run_in_executor(None, cli.run)

    # Wait until the user quits
    await shutdown_event.wait()

    # Graceful shutdown sequence
    server.close()
    await server.wait_closed()
    serve_task.cancel()
    try:
        await serve_task
    except asyncio.CancelledError:
        pass

    await asyncio.wrap_future(cli_future)


asyncio.run(main())
# Call state.init()
# Start the TCP server
# Start the UDP broadcaster
# Start the CLI
