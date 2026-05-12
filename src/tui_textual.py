from __future__ import annotations

import shlex
import time
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from config import HEARTBEAT_INTERVAL_SECONDS, MAX_MISSED_HEARTBEATS


class HeartbeatMonitor(Static):
    """Lightweight animated heartbeat box."""

    DEFAULT_CSS = """
    HeartbeatMonitor {
        height: 8;
        border: round #00eeff;
        padding: 1 2;
        background: #00100d;
        margin-bottom: 1;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.peer_label = "network"
        self.endpoint_label = "--"
        self.status_label = "waiting for telemetry"
        self.health_label = "IDLE"
        self.mode = "idle"
        self._frame = 0

    def on_mount(self) -> None:
        self.set_interval(0.25, self.advance_frame)

    def set_telemetry(
        self,
        *,
        peer_label: str,
        endpoint_label: str,
        status_label: str,
        health_label: str,
        mode: str,
    ) -> None:
        self.peer_label = peer_label
        self.endpoint_label = endpoint_label
        self.status_label = status_label
        self.health_label = health_label
        self.mode = mode
        self._render_status()

    def set_status(
        self,
        *,
        peer_label: str,
        endpoint_label: str,
        state_label: str,
        last_pong_label: str,
        health_label: str,
    ) -> None:
        if health_label in {"STABLE", "WATCHING"}:
            mode = "stable"
        elif health_label == "STALE":
            mode = "stale"
        elif health_label == "OFFLINE":
            mode = "offline"
        else:
            mode = "idle"

        self.set_telemetry(
            peer_label=peer_label,
            endpoint_label=endpoint_label,
            status_label=f"{state_label} | last pong {last_pong_label}",
            health_label=health_label,
            mode=mode,
        )

    def advance_frame(self) -> None:
        self._frame = (self._frame + 1) % 4
        self._render_status()

    def _dots(self) -> str:
        if self.mode == "stable":
            frames = ["●○○", "○●○", "○○●", "○●○"]
        elif self.mode == "stale":
            frames = ["●○○", "○○○", "○●○", "○○○"]
        elif self.mode == "offline":
            frames = ["○○○", "○○○", "○○○", "○○○"]
        else:
            frames = ["·○○", "○·○", "○○·", "○·○"]
        return frames[self._frame]

    def _render_status(self) -> None:
        self.update(
            "\n".join(
                [
                    f"[b]{self.peer_label}[/b]",
                    f"{self.endpoint_label}",
                    f"{self.status_label}",
                    f"health: {self.health_label}",
                    f"pulse: {self._dots()}",
                ]
            )
        )


class PeerLinkTextualApp(App[None]):
    """Textual UI shell for the PeerLink file sharing app."""

    CSS_PATH = "tui_textual.tcss"
    TITLE = "PeerLink"
    SUB_TITLE = "Peer-to-Peer File Sharing"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+l", "focus_command", "Command"),
        ("ctrl+f", "focus_results", "Search"),
        ("ctrl+e", "focus_peers", "Peers"),
        ("ctrl+r", "refresh_dashboard", "Refresh"),
        ("ctrl+k", "clear_log", "Clear Log"),
        ("d", "download_selected", "Download"),
        ("c", "connect_selected_peer", "Connect Peer"),
    ]

    def __init__(
        self,
        *,
        state_ref,
        connect_fn,
        download_fn,
        search_fn,
    ) -> None:
        super().__init__()
        self.state = state_ref
        self.connect_fn = connect_fn
        self.download_fn = download_fn
        self.search_fn = search_fn
        self.last_search_results: list[dict[str, Any]] = []
        self.download_history: list[dict[str, str]] = []
        self.peer_rows: list[tuple[str, dict[str, Any]]] = []
        self._next_download_id = 1
        self._heartbeat_marker: str | None = None
        self._heartbeat_source: str | None = None
        self._last_logged_peer_selection: str | None = None
        self._last_logged_result_selection: int | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs", initial="tab-status"):
            with TabPane("Status", id="tab-status"):
                yield Static(id="status_panel")
                yield Static("Local Catalog", classes="section_title")
                yield DataTable(id="catalog_table")
            with TabPane("Peers", id="tab-peers"):
                yield Static("Heartbeat Telemetry", classes="section_title")
                yield HeartbeatMonitor(id="heartbeat_monitor")
                yield Static("Peers", classes="section_title")
                yield Static(
                    "Tip: Tab here, use arrows, then press Enter or C to connect / reconnect.",
                    id="peers_hint",
                )
                yield DataTable(id="peers_table")
                yield Static("Selected Peer", classes="section_title")
                yield Static(id="peer_detail_panel")
            with TabPane("Search", id="tab-search"):
                yield Static(
                    "Tip: Tab to the table, use arrows, then press Enter or D to download.",
                    id="results_hint",
                )
                yield DataTable(id="results_table")
            with TabPane("Downloads", id="tab-downloads"):
                yield Static(
                    "Status phases: queued → connecting → downloading → done / failed",
                    id="downloads_hint",
                )
                yield DataTable(id="downloads_table")
            with TabPane("Activity", id="tab-activity"):
                yield RichLog(id="log_panel", markup=True, wrap=True, highlight=True)
        yield Input(
            placeholder=('Type a command or "help"'),
            id="command_input",
        )
        yield Footer()

    def on_mount(self) -> None:
        peers_table = self.query_one("#peers_table", DataTable)
        peers_table.add_columns("Peer ID", "Host", "Port", "Connected")
        peers_table.cursor_type = "row"
        peers_table.zebra_stripes = True

        catalog_table = self.query_one("#catalog_table", DataTable)
        catalog_table.add_columns("Name", "Size", "File ID")
        catalog_table.cursor_type = "row"
        catalog_table.zebra_stripes = True

        results_table = self.query_one("#results_table", DataTable)
        results_table.add_columns(
            "#", "File", "Size", "Peer", "Host", "Port", "File ID"
        )
        results_table.cursor_type = "row"
        results_table.zebra_stripes = True

        downloads_table = self.query_one("#downloads_table", DataTable)
        downloads_table.add_columns("#", "File", "Peer", "Status", "Details")
        downloads_table.cursor_type = "row"
        downloads_table.zebra_stripes = True

        self.set_interval(1.0, self.refresh_dashboard)
        self.refresh_dashboard()
        self.log_info("PeerLink started. Press Ctrl+L to focus the command line.")
        self.log_info("Use the tabs or Ctrl+E / Ctrl+F to navigate between views.")
        self.log_info(
            "Press Enter or C on a peer to connect. Press Enter or D on a result to download."
        )

    def action_focus_command(self) -> None:
        self.query_one("#command_input", Input).focus()

    def action_focus_results(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-search"
        self.query_one("#results_table", DataTable).focus()

    def action_focus_peers(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-peers"
        self.query_one("#peers_table", DataTable).focus()

    def action_refresh_dashboard(self) -> None:
        self.refresh_dashboard()
        self.log_info("Dashboard refreshed.")

    def action_clear_log(self) -> None:
        self.query_one("#log_panel", RichLog).clear()
        self.log_info("Activity log cleared.")

    def action_download_selected(self) -> None:
        selection = self.get_selected_result_index()
        if selection is None:
            self.log_error("No search result is selected.")
            return
        self.start_download_for_index(selection)

    def action_connect_selected_peer(self) -> None:
        self.start_connect_for_selected_peer()

    def refresh_dashboard(self) -> None:
        self._update_status_panel()
        self._update_peers_table()
        self._update_peer_detail_panel()
        self._update_catalog_table()
        self._update_results_table()
        self._update_downloads_table()
        self._update_heartbeat_monitor()

    def _is_live_peer(self, peer: dict[str, Any]) -> bool:
        writer = peer.get("writer")
        return writer is not None and not writer.is_closing()

    def _update_status_panel(self) -> None:
        status = self.query_one("#status_panel", Static)
        connected_peer_count = sum(
            1 for peer in self.state.peers.values() if self._is_live_peer(peer)
        )
        known_peer_count = len(self.state.peers)
        local_files = len(self.state.local_catalog)
        search_count = len(self.last_search_results)
        active_downloads = sum(
            1
            for entry in self.download_history
            if entry["status"] not in {"done", "failed"}
        )
        total_downloads = len(self.download_history)
        status.update(
            "\n".join(
                [
                    "[b]PeerLink Status[/b]",
                    f"Peer ID: {self.state.PEER_ID_STUB or '-'}",
                    f"Port: {getattr(self.state, 'port', '-')}",
                    f"Connected peers: {connected_peer_count}",
                    f"Known peers: {known_peer_count}",
                    f"Local files: {local_files}",
                    f"Last search results: {search_count}",
                    f"Active downloads: {active_downloads}",
                    f"Download history: {total_downloads}",
                    "",
                    "[b]Quick help[/b]",
                    "connect <host> <port>",
                    "search <file>",
                    "download <number>",
                    "id | status | clear | help",
                ]
            )
        )

    def _update_peers_table(self) -> None:
        table = self.query_one("#peers_table", DataTable)
        previous_cursor_row = table.cursor_row
        table.clear(columns=False)
        self.peer_rows = [
            (peer_id, peer)
            for peer_id, peer in self.state.peers.items()
            if self._is_live_peer(peer)
        ]
        for peer_id, peer in self.peer_rows:
            writer = peer.get("writer")
            connected = (
                "yes" if writer is not None and not writer.is_closing() else "no"
            )
            table.add_row(
                str(peer_id),
                str(peer.get("host", "-")),
                str(peer.get("port", "-")),
                connected,
                key=str(peer_id),
            )

        if self.peer_rows:
            safe_row = (
                0
                if previous_cursor_row is None or previous_cursor_row < 0
                else min(previous_cursor_row, len(self.peer_rows) - 1)
            )
            table.move_cursor(row=safe_row, column=0, scroll=False)

    def _update_peer_detail_panel(self) -> None:
        panel = self.query_one("#peer_detail_panel", Static)
        selected = self.get_selected_peer_info()
        if selected is None:
            if self.peer_rows:
                panel.update(
                    "\n".join(
                        [
                            "Choose a peer in the table above.",
                            "",
                            "Actions:",
                            "• Enter = connect / reconnect",
                            "• C = connect / reconnect",
                        ]
                    )
                )
            else:
                panel.update(
                    "No peers available yet. Wait for discovery or use connect <host> <port>."
                )
            return

        peer_id, peer = selected
        writer = peer.get("writer")
        connected = writer is not None and not writer.is_closing()
        catalog = peer.get("catalog")
        catalog_count = len(catalog) if isinstance(catalog, list) else 0
        raw_last_pong = peer.get("last_pong")

        try:
            last_pong_value = (
                None if raw_last_pong in (None, "", "-") else float(raw_last_pong)
            )
        except (TypeError, ValueError):
            last_pong_value = None

        if last_pong_value is None:
            pong_text = "never"
        else:
            pong_text = f"{time.time() - last_pong_value:.1f}s ago"
        panel.update(
            "\n".join(
                [
                    f"[b]{peer_id}[/b]",
                    f"Host: {peer.get('host', '-')}",
                    f"Port: {peer.get('port', '-')}",
                    f"Connected: {'yes' if connected else 'no'}",
                    f"Known catalog items: {catalog_count}",
                    f"Last pong: {pong_text}",
                    "",
                    "Press Enter or C to connect / reconnect this peer.",
                ]
            )
        )

    def _update_catalog_table(self) -> None:
        table = self.query_one("#catalog_table", DataTable)
        if table.row_count == len(self.state.local_catalog):
            return
        table.clear(columns=False)
        for entry in self.state.local_catalog:
            table.add_row(
                str(entry.get("name", "-")),
                str(entry.get("size", "-")),
                str(entry.get("file_id", "-")),
                key=str(entry.get("name", entry.get("file_id", "row"))),
            )

    def _update_results_table(self) -> None:
        table = self.query_one("#results_table", DataTable)
        previous_cursor_row = table.cursor_row
        table.clear(columns=False)
        for index, result in enumerate(self.last_search_results, start=1):
            table.add_row(
                str(index),
                str(result.get("filename", "-")),
                str(result.get("size", "-")),
                str(result.get("peer_id", "-")),
                str(result.get("host", "-")),
                str(result.get("port", "-")),
                str(result.get("file_id", "-")),
                key=str(index),
            )

        if self.last_search_results:
            safe_row = (
                0
                if previous_cursor_row is None or previous_cursor_row < 0
                else min(previous_cursor_row, len(self.last_search_results) - 1)
            )
            table.move_cursor(row=safe_row, column=0, scroll=False)

    def _update_downloads_table(self) -> None:
        table = self.query_one("#downloads_table", DataTable)
        previous_cursor_row = table.cursor_row
        table.clear(columns=False)
        for entry in self.download_history:
            table.add_row(
                entry["id"],
                entry["file"],
                entry["peer"],
                entry["status"],
                entry["details"],
                key=entry["id"],
            )

        if self.download_history:
            safe_row = (
                0
                if previous_cursor_row is None or previous_cursor_row < 0
                else min(previous_cursor_row, len(self.download_history) - 1)
            )
            table.move_cursor(row=safe_row, column=0, scroll=False)

    def _update_heartbeat_monitor(self) -> None:
        monitor = self.query_one("#heartbeat_monitor", HeartbeatMonitor)
        selected = self.get_selected_peer_info()

        if selected is None:
            monitor.set_status(
                peer_label="No peer selected",
                endpoint_label="--",
                state_label="idle",
                last_pong_label="--",
                health_label="IDLE",
            )
            self._heartbeat_marker = None
            self._heartbeat_source = None
            return

        peer_id, peer = selected
        raw_last_pong = peer.get("last_pong")
        writer = peer.get("writer")
        connected = writer is not None and not writer.is_closing()

        try:
            last_pong_value = (
                None if raw_last_pong in (None, "", "-") else float(raw_last_pong)
            )
        except (TypeError, ValueError):
            last_pong_value = None

        host = str(peer.get("host", "-"))
        port = str(peer.get("port", "-"))

        state_label = "linked" if connected else "idle"

        if last_pong_value is None:
            last_pong_label = "never"
            health_label = "WATCHING" if connected else "IDLE"
            marker = f"{peer_id}:waiting"
        else:
            age = max(0.0, time.time() - last_pong_value)
            last_pong_label = f"{age:.1f}s ago"

            if age <= HEARTBEAT_INTERVAL_SECONDS * 1.25:
                health_label = "STABLE"
            elif age <= HEARTBEAT_INTERVAL_SECONDS * MAX_MISSED_HEARTBEATS:
                health_label = "STALE"
            else:
                health_label = "OFFLINE"

            marker = f"{peer_id}:{last_pong_value:.6f}"

        monitor.set_status(
            peer_label=str(peer_id),
            endpoint_label=f"{host}:{port}",
            state_label=state_label,
            last_pong_label=last_pong_label,
            health_label=health_label,
        )

        self._heartbeat_marker = marker

    def _create_download_entry(
        self, *, file_name: str, peer_label: str, details: str
    ) -> str:
        download_id = str(self._next_download_id)
        self._next_download_id += 1
        self.download_history.insert(
            0,
            {
                "id": download_id,
                "file": file_name,
                "peer": peer_label,
                "status": "queued",
                "details": details,
            },
        )
        self.download_history = self.download_history[:20]
        self.refresh_dashboard()
        return download_id

    def _set_download_status(self, download_id: str, status: str, details: str) -> None:
        for entry in self.download_history:
            if entry["id"] == download_id:
                entry["status"] = status
                entry["details"] = details
                break
        self.refresh_dashboard()

    def get_selected_peer_info(self) -> tuple[str, dict[str, Any]] | None:
        table = self.query_one("#peers_table", DataTable)
        if not self.peer_rows:
            return None
        cursor_row = table.cursor_row
        if cursor_row is None or cursor_row < 0 or cursor_row >= len(self.peer_rows):
            return None
        return self.peer_rows[cursor_row]

    def get_selected_result_index(self) -> int | None:
        table = self.query_one("#results_table", DataTable)
        if not self.last_search_results:
            return None
        cursor_row = table.cursor_row
        if (
            cursor_row is None
            or cursor_row < 0
            or cursor_row >= len(self.last_search_results)
        ):
            return None
        return cursor_row + 1

    def start_connect_for_selected_peer(self) -> None:
        selected = self.get_selected_peer_info()
        if selected is None:
            self.log_error("No peer is selected.")
            return

        peer_id, peer = selected

        raw_host = peer.get("host")
        raw_port = peer.get("port")

        host_value: str | None
        if raw_host in (None, "-"):
            host_value = None
        else:
            host_value = str(raw_host)

        port_value: int | None
        try:
            if raw_port in (None, "-"):
                port_value = None
            else:
                port_value = int(raw_port)
        except (TypeError, ValueError):
            port_value = None

        if host_value is None or port_value is None:
            self.log_error(f"Peer {peer_id} does not have a usable host/port yet.")
            return

        writer = peer.get("writer")
        already_connected = writer is not None and not writer.is_closing()
        if already_connected:
            self.log_info(
                f"Selected peer {peer_id} is already connected. Running a safe reconnect check to {host_value}:{port_value}."
            )
        else:
            self.log_info(
                f"Connecting to selected peer {peer_id} at {host_value}:{port_value}."
            )

        self.run_connect(host_value, port_value)

    def start_download_for_index(self, index: int) -> None:
        if not self.last_search_results:
            self.log_error('No saved search results. Run "search <file_name>" first.')
            return
        if index < 1 or index > len(self.last_search_results):
            self.log_error(
                f"Invalid selection. Choose a number between 1 and {len(self.last_search_results)}."
            )
            return

        selected = self.last_search_results[index - 1]
        self.log_info(
            f'Starting download for result #{index}: {selected.get("filename", "-")} from {selected.get("peer_id", "-")}. '
            f"See the Downloads tab for status."
        )
        self.run_download_from_search(index)

    def log_info(self, message: str) -> None:
        self.query_one("#log_panel", RichLog).write(f"[cyan]{message}[/cyan]")

    def log_error(self, message: str) -> None:
        self.query_one("#log_panel", RichLog).write(
            f"[bold #ff6600]{message}[/bold #ff6600]"
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return
        self.log_info(f"> {command}")
        self.handle_command(command)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "results_table":
            index = self.get_selected_result_index()
            if index is None:
                return

            self._update_results_table()

            if self._last_logged_result_selection != index:
                selected = self.last_search_results[index - 1]
                self.log_info(
                    f'Selected result #{index}: {selected.get("filename", "-")} from {selected.get("peer_id", "-")}. '
                    f"Press Enter or D to download."
                )
                self._last_logged_result_selection = index
            return

        if event.data_table.id == "peers_table":
            self._update_peer_detail_panel()
            self._update_heartbeat_monitor()

            selected = self.get_selected_peer_info()
            if selected is None:
                self._last_logged_peer_selection = None
                return

            peer_id, peer = selected
            if self._last_logged_peer_selection != str(peer_id):
                self.log_info(
                    f"Selected peer {peer_id} at {peer.get('host', '-')}:{peer.get('port', '-')}. Press Enter or C to connect / reconnect."
                )
                self._last_logged_peer_selection = str(peer_id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "results_table":
            index = self.get_selected_result_index()
            if index is None:
                self.log_error("No search result is selected.")
                return
            self.start_download_for_index(index)
            return

        if event.data_table.id == "peers_table":
            self.start_connect_for_selected_peer()

    def handle_command(self, command: str) -> None:
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            self.log_error(f"Could not parse command: {exc}")
            return

        if not parts:
            return

        action = parts[0].lower()

        if action in {"help", "?"}:
            self.log_info(
                "Commands: connect <host> <port> | search <file> | download <number> | "
                "download <file_id> <peer_id> | peers | catalog | id | status | clear | quit"
            )
        elif action in {"id", "whoami", "print"}:
            self.log_info(f"Peer ID: {self.state.PEER_ID_STUB}")
        elif action == "status":
            self.refresh_dashboard()
            self.log_info("PeerLink status refreshed.")
        elif action == "peers":
            self.refresh_dashboard()
            live_peer_count = sum(
                1 for peer in self.state.peers.values() if self._is_live_peer(peer)
            )
            self.log_info(f"Live peers shown: {live_peer_count}")
        elif action == "catalog":
            self.refresh_dashboard()
            self.log_info(f"Local files shown: {len(self.state.local_catalog)}")
        elif action == "clear":
            self.last_search_results = []
            self.refresh_dashboard()
            self.log_info("Search results cleared.")
        elif action == "connect":
            if len(parts) != 3:
                self.log_error("Usage: connect <host> <port>")
                return
            host = parts[1]
            try:
                port = int(parts[2])
            except ValueError:
                self.log_error("Port must be an integer.")
                return
            self.run_connect(host, port)
        elif action in {"search", "msearch"}:
            if len(parts) < 2:
                self.log_error("Usage: search <file_name>")
                return
            file_name = " ".join(parts[1:]).strip()
            self.run_search(file_name)
        elif action == "download":
            if len(parts) == 2:
                try:
                    index = int(parts[1])
                except ValueError:
                    self.log_error("Usage: download <number>")
                    return
                self.start_download_for_index(index)
            elif len(parts) == 3:
                self.run_direct_download(parts[1], parts[2])
            else:
                self.log_error(
                    "Usage: download <number> OR download <file_id> <peer_id>"
                )
        elif action in {"quit", "exit"}:
            self.exit()
        else:
            self.log_error(f'Unknown command: "{action}"')

    @work(exclusive=False, exit_on_error=False)
    async def run_connect(self, host: str, port: int) -> None:
        try:
            await self.connect_fn(host, port)
            self.refresh_dashboard()
            self.log_info(f"Connected to {host}:{port}")
        except Exception as exc:
            self.log_error(f"Connect failed: {exc}")

    @work(exclusive=True, exit_on_error=False)
    async def run_search(self, file_name: str) -> None:
        try:
            results = await self.search_fn(file_name)
            self.last_search_results = list(results)
            self.refresh_dashboard()
            if results:
                self.log_info(
                    f'Found {len(results)} result(s) for "{file_name}". Use Enter, D, or download <number>.'
                )
            else:
                self.log_info(f'No results for "{file_name}".')
        except Exception as exc:
            self.log_error(f"Search failed: {exc}")

    @work(exclusive=False, exit_on_error=False)
    async def run_download_from_search(self, index: int) -> None:
        if not self.last_search_results:
            self.log_error('No saved search results. Run "search <file_name>" first.')
            return
        if index < 1 or index > len(self.last_search_results):
            self.log_error(
                f"Invalid selection. Choose a number between 1 and {len(self.last_search_results)}."
            )
            return

        selected = self.last_search_results[index - 1]
        file_id = selected["file_id"]
        peer_id = selected["peer_id"]
        host = selected["host"]
        port = selected["port"]
        file_name = str(selected.get("filename", file_id))
        peer_label = str(peer_id)
        download_id = self._create_download_entry(
            file_name=file_name,
            peer_label=peer_label,
            details=f"Waiting to start via {host}:{port}",
        )

        try:
            peer = self.state.peers.get(peer_id)
            writer = None if peer is None else peer.get("writer")
            if writer is not None and not writer.is_closing():
                self._set_download_status(
                    download_id, "connecting", "Using existing direct connection"
                )
            else:
                self._set_download_status(
                    download_id, "connecting", "Routing via relay peer"
                )

            self._set_download_status(
                download_id, "downloading", f"Requesting file_id {file_id}"
            )
            saved_path = await self.download_fn(file_id, peer_id)
            self._set_download_status(download_id, "done", str(saved_path))
            self.refresh_dashboard()
            self.log_info(f'Download complete: {selected["filename"]} -> {saved_path}')
        except Exception as exc:
            self._set_download_status(download_id, "failed", str(exc))
            self.log_error(f"Download failed: {exc}")

    @work(exclusive=False, exit_on_error=False)
    async def run_direct_download(self, file_id: str, peer_id: str) -> None:
        download_id = self._create_download_entry(
            file_name=file_id,
            peer_label=peer_id,
            details="Starting direct download",
        )
        try:
            self._set_download_status(
                download_id, "downloading", f"Requesting file_id {file_id}"
            )
            saved_path = await self.download_fn(file_id, peer_id)
            self._set_download_status(download_id, "done", str(saved_path))
            self.log_info(f"Download complete: {saved_path}")
        except Exception as exc:
            self._set_download_status(download_id, "failed", str(exc))
            self.log_error(f"Download failed: {exc}")
