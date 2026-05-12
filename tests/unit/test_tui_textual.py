import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import src.tui_textual as tui


class FakeStatic:
    def __init__(self, widget_id=None):
        self.id = widget_id
        self.updated_text = None
        self.focus_called = False

    def update(self, value):
        self.updated_text = value

    def focus(self):
        self.focus_called = True


class FakeInput(FakeStatic):
    def __init__(self, widget_id=None):
        super().__init__(widget_id)
        self.value = ""


class FakeRichLog:
    def __init__(self):
        self.entries = []
        self.cleared = False

    def write(self, value):
        self.entries.append(value)

    def clear(self):
        self.cleared = True


class FakeDataTable:
    def __init__(self, widget_id=None):
        self.id = widget_id
        self.columns = []
        self.rows = []
        self.cursor_row = 0
        self.cursor_type = None
        self.zebra_stripes = False
        self.focus_called = False
        self.move_cursor_calls = []

    @property
    def row_count(self):
        return len(self.rows)

    def add_columns(self, *cols):
        self.columns.extend(cols)

    def add_row(self, *values, key=None):
        self.rows.append({"values": values, "key": key})

    def clear(self, columns=False):
        self.rows = []

    def move_cursor(self, row=0, column=0, scroll=False):
        self.cursor_row = row
        self.move_cursor_calls.append((row, column, scroll))

    def focus(self):
        self.focus_called = True


def make_writer(closing=False):
    writer = Mock()
    writer.is_closing.return_value = closing
    return writer


def make_app():
    state = SimpleNamespace()
    state.peers = {}
    state.local_catalog = []
    state.PEER_ID_STUB = "self-peer"
    state.port = 5001

    app = tui.PeerLinkTextualApp(
        state_ref=state,
        connect_fn=AsyncMock(),
        download_fn=AsyncMock(),
        search_fn=AsyncMock(),
    )
    return app


def make_widgets():
    return {
        "#status_panel": FakeStatic("status_panel"),
        "#catalog_table": FakeDataTable("catalog_table"),
        "#results_table": FakeDataTable("results_table"),
        "#downloads_table": FakeDataTable("downloads_table"),
        "#peers_table": FakeDataTable("peers_table"),
        "#peer_detail_panel": FakeStatic("peer_detail_panel"),
        "#heartbeat_monitor": Mock(),
        "#tabs": SimpleNamespace(active=None),
        "#command_input": FakeInput("command_input"),
        "#log_panel": FakeRichLog(),
    }


def bind_widgets(app, widgets):
    app.query_one = Mock(side_effect=lambda selector, *_args: widgets[selector])


def test_heartbeat_monitor_on_mount_sets_interval():
    monitor = tui.HeartbeatMonitor()

    with patch.object(monitor, "set_interval") as mock_interval:
        monitor.on_mount()

    mock_interval.assert_called_once_with(0.25, monitor.advance_frame)


def test_heartbeat_monitor_set_telemetry_updates_and_renders():
    monitor = tui.HeartbeatMonitor()

    with patch.object(monitor, "_render_status") as mock_render:
        monitor.set_telemetry(
            peer_label="peer1",
            endpoint_label="1.2.3.4:5001",
            status_label="ok",
            health_label="STABLE",
            mode="stable",
        )

    assert monitor.peer_label == "peer1"
    assert monitor.endpoint_label == "1.2.3.4:5001"
    assert monitor.status_label == "ok"
    assert monitor.health_label == "STABLE"
    assert monitor.mode == "stable"
    mock_render.assert_called_once()


def test_heartbeat_monitor_set_status_modes():
    monitor = tui.HeartbeatMonitor()

    with patch.object(monitor, "set_telemetry") as mock_set:
        monitor.set_status(
            peer_label="peer1",
            endpoint_label="1.1.1.1:9",
            state_label="linked",
            last_pong_label="1.0s ago",
            health_label="STABLE",
        )
        monitor.set_status(
            peer_label="peer1",
            endpoint_label="1.1.1.1:9",
            state_label="linked",
            last_pong_label="1.0s ago",
            health_label="STALE",
        )
        monitor.set_status(
            peer_label="peer1",
            endpoint_label="1.1.1.1:9",
            state_label="linked",
            last_pong_label="1.0s ago",
            health_label="OFFLINE",
        )
        monitor.set_status(
            peer_label="peer1",
            endpoint_label="1.1.1.1:9",
            state_label="linked",
            last_pong_label="1.0s ago",
            health_label="IDLE",
        )

    assert mock_set.call_args_list[0].kwargs["mode"] == "stable"
    assert mock_set.call_args_list[1].kwargs["mode"] == "stale"
    assert mock_set.call_args_list[2].kwargs["mode"] == "offline"
    assert mock_set.call_args_list[3].kwargs["mode"] == "idle"


def test_heartbeat_monitor_advance_frame_wraps():
    monitor = tui.HeartbeatMonitor()
    monitor._frame = 3

    with patch.object(monitor, "_render_status") as mock_render:
        monitor.advance_frame()

    assert monitor._frame == 0
    mock_render.assert_called_once()


def test_heartbeat_monitor_dots_and_render_status():
    monitor = tui.HeartbeatMonitor()
    monitor.peer_label = "peer1"
    monitor.endpoint_label = "1.2.3.4:5"
    monitor.status_label = "linked"
    monitor.health_label = "STABLE"
    monitor.mode = "stable"
    monitor._frame = 0

    assert monitor._dots() == "●○○"

    with patch.object(monitor, "update") as mock_update:
        monitor._render_status()

    text = mock_update.call_args[0][0]
    assert "peer1" in text
    assert "1.2.3.4:5" in text
    assert "linked" in text
    assert "health: STABLE" in text


def test_action_focus_methods_and_clear_log():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    with patch.object(app, "refresh_dashboard") as mock_refresh:
        app.action_focus_command()
        app.action_focus_results()
        app.action_focus_peers()
        app.action_refresh_dashboard()
        app.action_clear_log()

    assert widgets["#command_input"].focus_called is True
    assert widgets["#tabs"].active == "tab-peers"
    assert widgets["#results_table"].focus_called is True
    assert widgets["#peers_table"].focus_called is True
    assert widgets["#log_panel"].cleared is True
    mock_refresh.assert_called_once()
    assert widgets["#log_panel"].entries[-1] == "[cyan]Activity log cleared.[/cyan]"


def test_action_download_selected_and_connect_selected_peer():
    app = make_app()

    with patch.object(
        app, "get_selected_result_index", return_value=None
    ), patch.object(app, "log_error") as mock_error:
        app.action_download_selected()
        mock_error.assert_called_once_with("No search result is selected.")

    with patch.object(app, "get_selected_result_index", return_value=2), patch.object(
        app, "start_download_for_index"
    ) as mock_start:
        app.action_download_selected()
        mock_start.assert_called_once_with(2)

    with patch.object(app, "start_connect_for_selected_peer") as mock_connect:
        app.action_connect_selected_peer()
        mock_connect.assert_called_once()


def test_refresh_dashboard_calls_all_update_methods():
    app = make_app()

    with patch.object(app, "_update_status_panel") as a, patch.object(
        app, "_update_peers_table"
    ) as b, patch.object(app, "_update_peer_detail_panel") as c, patch.object(
        app, "_update_catalog_table"
    ) as d, patch.object(
        app, "_update_results_table"
    ) as e, patch.object(
        app, "_update_downloads_table"
    ) as f, patch.object(
        app, "_update_heartbeat_monitor"
    ) as g:
        app.refresh_dashboard()

    assert (
        a.called
        and b.called
        and c.called
        and d.called
        and e.called
        and f.called
        and g.called
    )


def test_is_live_peer():
    app = make_app()

    assert app._is_live_peer({"writer": make_writer(False)}) is True
    assert app._is_live_peer({"writer": make_writer(True)}) is False
    assert app._is_live_peer({"writer": None}) is False


def test_update_status_panel():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.state.peers = {
        "p1": {"writer": make_writer(False)},
        "p2": {"writer": make_writer(True)},
    }
    app.state.local_catalog = [{"name": "a"}, {"name": "b"}]
    app.last_search_results = [{"x": 1}]
    app.download_history = [
        {"status": "queued"},
        {"status": "done"},
        {"status": "failed"},
    ]

    app._update_status_panel()

    text = widgets["#status_panel"].updated_text
    assert "Peer ID: self-peer" in text
    assert "Connected peers: 1" in text
    assert "Known peers: 2" in text
    assert "Local files: 2" in text
    assert "Last search results: 1" in text
    assert "Active downloads: 1" in text
    assert "Download history: 3" in text


def test_update_peers_table_and_selection_restore():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    widgets["#peers_table"].cursor_row = 0
    app.state.peers = {
        "p1": {"host": "h1", "port": 1, "writer": make_writer(False)},
        "p2": {"host": "h2", "port": 2, "writer": make_writer(True)},
    }

    app._update_peers_table()

    assert len(app.peer_rows) == 1
    assert widgets["#peers_table"].rows[0]["values"] == ("p1", "h1", "1", "yes")
    assert widgets["#peers_table"].move_cursor_calls


def test_update_peer_detail_panel_no_selection_and_selected():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.peer_rows = []
    with patch.object(app, "get_selected_peer_info", return_value=None):
        app._update_peer_detail_panel()
    assert "No peers available yet" in widgets["#peer_detail_panel"].updated_text

    app.peer_rows = [("p1", {})]
    with patch.object(app, "get_selected_peer_info", return_value=None):
        app._update_peer_detail_panel()
    assert "Choose a peer" in widgets["#peer_detail_panel"].updated_text

    peer = {
        "host": "127.0.0.1",
        "port": 5001,
        "writer": make_writer(False),
        "catalog": [{"a": 1}],
        "last_pong": None,
    }
    with patch.object(app, "get_selected_peer_info", return_value=("p1", peer)):
        app._update_peer_detail_panel()
    assert "Known catalog items: 1" in widgets["#peer_detail_panel"].updated_text
    assert "Last pong: never" in widgets["#peer_detail_panel"].updated_text


def test_update_catalog_table_skip_and_fill():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.state.local_catalog = [{"name": "a.txt", "size": 10, "file_id": "f1"}]
    widgets["#catalog_table"].rows = [{"values": ("old",), "key": "old"}]

    app._update_catalog_table()
    assert widgets["#catalog_table"].rows == [{"values": ("old",), "key": "old"}]

    widgets["#catalog_table"].rows = []
    app._update_catalog_table()
    assert widgets["#catalog_table"].rows[0]["values"] == ("a.txt", "10", "f1")


def test_update_results_table_and_downloads_table():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.last_search_results = [
        {
            "filename": "a.txt",
            "size": 10,
            "peer_id": "p1",
            "host": "h",
            "port": 9,
            "file_id": "f1",
        }
    ]
    app.download_history = [
        {
            "id": "1",
            "file": "a.txt",
            "peer": "p1",
            "status": "queued",
            "details": "waiting",
        }
    ]

    app._update_results_table()
    app._update_downloads_table()

    assert widgets["#results_table"].rows[0]["values"] == (
        "1",
        "a.txt",
        "10",
        "p1",
        "h",
        "9",
        "f1",
    )
    assert widgets["#downloads_table"].rows[0]["values"] == (
        "1",
        "a.txt",
        "p1",
        "queued",
        "waiting",
    )


def test_update_heartbeat_monitor_branches():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)
    monitor = widgets["#heartbeat_monitor"]

    with patch.object(app, "get_selected_peer_info", return_value=None):
        app._update_heartbeat_monitor()
    monitor.set_status.assert_called()
    assert app._heartbeat_marker is None

    peer = {
        "host": "127.0.0.1",
        "port": 5001,
        "writer": make_writer(False),
        "last_pong": None,
    }
    with patch.object(app, "get_selected_peer_info", return_value=("p1", peer)):
        app._update_heartbeat_monitor()
    assert app._heartbeat_marker == "p1:waiting"

    peer["last_pong"] = 100.0
    with patch.object(app, "get_selected_peer_info", return_value=("p1", peer)), patch(
        "src.tui_textual.time.time", return_value=100.2
    ), patch.object(tui, "HEARTBEAT_INTERVAL_SECONDS", 1), patch.object(
        tui, "MAX_MISSED_HEARTBEATS", 3
    ):
        app._update_heartbeat_monitor()
    assert app._heartbeat_marker.startswith("p1:")


def test_create_download_entry_and_set_download_status():
    app = make_app()

    with patch.object(app, "refresh_dashboard") as mock_refresh:
        download_id = app._create_download_entry(
            file_name="a.txt",
            peer_label="p1",
            details="queued",
        )

    assert download_id == "1"
    assert app.download_history[0]["status"] == "queued"
    mock_refresh.assert_called_once()

    with patch.object(app, "refresh_dashboard") as mock_refresh:
        app._set_download_status("1", "done", "/tmp/a.txt")

    assert app.download_history[0]["status"] == "done"
    assert app.download_history[0]["details"] == "/tmp/a.txt"
    mock_refresh.assert_called_once()


def test_selected_peer_and_result_helpers():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.peer_rows = [("p1", {"host": "h"})]
    widgets["#peers_table"].cursor_row = 0
    assert app.get_selected_peer_info() == ("p1", {"host": "h"})

    widgets["#peers_table"].cursor_row = -1
    assert app.get_selected_peer_info() is None

    app.last_search_results = [{"file_id": "f1"}]
    widgets["#results_table"].cursor_row = 0
    assert app.get_selected_result_index() == 1

    widgets["#results_table"].cursor_row = 5
    assert app.get_selected_result_index() is None


def test_start_connect_for_selected_peer_branches():
    app = make_app()

    with patch.object(app, "get_selected_peer_info", return_value=None), patch.object(
        app, "log_error"
    ) as mock_error:
        app.start_connect_for_selected_peer()
    mock_error.assert_called_once_with("No peer is selected.")

    with patch.object(
        app,
        "get_selected_peer_info",
        return_value=("p1", {"host": "-", "port": "-", "writer": None}),
    ), patch.object(app, "log_error") as mock_error:
        app.start_connect_for_selected_peer()
    mock_error.assert_called_once_with("Peer p1 does not have a usable host/port yet.")

    with patch.object(
        app,
        "get_selected_peer_info",
        return_value=(
            "p1",
            {"host": "127.0.0.1", "port": 5001, "writer": make_writer(False)},
        ),
    ), patch.object(app, "log_info") as mock_info, patch.object(
        app, "run_connect"
    ) as mock_run:
        app.start_connect_for_selected_peer()
    mock_info.assert_called_once()
    mock_run.assert_called_once_with("127.0.0.1", 5001)


def test_start_download_for_index_branches():
    app = make_app()

    with patch.object(app, "log_error") as mock_error:
        app.start_download_for_index(1)
    mock_error.assert_called_once()

    app.last_search_results = [{"filename": "a.txt", "peer_id": "p1"}]
    with patch.object(app, "log_error") as mock_error:
        app.start_download_for_index(2)
    mock_error.assert_called_once()

    with patch.object(app, "log_info") as mock_info, patch.object(
        app, "run_download_from_search"
    ) as mock_run:
        app.start_download_for_index(1)
    mock_info.assert_called_once()
    mock_run.assert_called_once_with(1)


def test_log_info_and_error():
    app = make_app()
    widgets = make_widgets()
    bind_widgets(app, widgets)

    app.log_info("hello")
    app.log_error("oops")

    assert widgets["#log_panel"].entries[0] == "[cyan]hello[/cyan]"
    assert widgets["#log_panel"].entries[1] == "[bold #ff6600]oops[/bold #ff6600]"


def test_on_input_submitted_blank_and_normal():
    app = make_app()
    event = SimpleNamespace(value="   ", input=SimpleNamespace(value="abc"))

    async def runner_blank():
        with patch.object(app, "log_info") as mock_log, patch.object(
            app, "handle_command"
        ) as mock_handle:
            await app.on_input_submitted(event)
            mock_log.assert_not_called()
            mock_handle.assert_not_called()

    asyncio.run(runner_blank())

    event = SimpleNamespace(value="status", input=SimpleNamespace(value="status"))

    async def runner_normal():
        with patch.object(app, "log_info") as mock_log, patch.object(
            app, "handle_command"
        ) as mock_handle:
            await app.on_input_submitted(event)
            mock_log.assert_called_once_with("> status")
            mock_handle.assert_called_once_with("status")
            assert event.input.value == ""

    asyncio.run(runner_normal())


def test_on_data_table_row_highlighted_results_and_peers():
    app = make_app()
    app.last_search_results = [{"filename": "a.txt", "peer_id": "p1"}]

    event_results = SimpleNamespace(data_table=SimpleNamespace(id="results_table"))
    with patch.object(app, "get_selected_result_index", return_value=1), patch.object(
        app, "_update_results_table"
    ) as mock_update, patch.object(app, "log_info") as mock_log:
        app.on_data_table_row_highlighted(event_results)
    mock_update.assert_called_once()
    mock_log.assert_called_once()

    peer = {"host": "127.0.0.1", "port": 5001}
    app._last_logged_peer_selection = None
    event_peers = SimpleNamespace(data_table=SimpleNamespace(id="peers_table"))
    with patch.object(app, "_update_peer_detail_panel") as a, patch.object(
        app, "_update_heartbeat_monitor"
    ) as b, patch.object(
        app, "get_selected_peer_info", return_value=("p1", peer)
    ), patch.object(
        app, "log_info"
    ) as c:
        app.on_data_table_row_highlighted(event_peers)
    assert a.called and b.called and c.called


def test_on_data_table_row_selected():
    app = make_app()

    event_results = SimpleNamespace(data_table=SimpleNamespace(id="results_table"))
    with patch.object(
        app, "get_selected_result_index", return_value=None
    ), patch.object(app, "log_error") as mock_error:
        app.on_data_table_row_selected(event_results)
    mock_error.assert_called_once_with("No search result is selected.")

    with patch.object(app, "get_selected_result_index", return_value=2), patch.object(
        app, "start_download_for_index"
    ) as mock_start:
        app.on_data_table_row_selected(event_results)
    mock_start.assert_called_once_with(2)

    event_peers = SimpleNamespace(data_table=SimpleNamespace(id="peers_table"))
    with patch.object(app, "start_connect_for_selected_peer") as mock_connect:
        app.on_data_table_row_selected(event_peers)
    mock_connect.assert_called_once()


def test_handle_command_branches():
    app = make_app()

    with patch(
        "src.tui_textual.shlex.split", side_effect=ValueError("bad parse")
    ), patch.object(app, "log_error") as mock_error:
        app.handle_command('bad "cmd')
    mock_error.assert_called_once()

    with patch.object(app, "log_info") as mock_info:
        app.handle_command("help")
        app.handle_command("id")
    assert mock_info.call_count == 2

    with patch.object(app, "refresh_dashboard") as mock_refresh, patch.object(
        app, "log_info"
    ) as mock_info:
        app.handle_command("status")
        app.handle_command("peers")
        app.handle_command("catalog")
    assert mock_refresh.call_count == 3
    assert mock_info.call_count == 3

    app.last_search_results = [{"file_id": "x"}]
    with patch.object(app, "refresh_dashboard") as mock_refresh, patch.object(
        app, "log_info"
    ) as mock_info:
        app.handle_command("clear")
    assert app.last_search_results == []
    mock_refresh.assert_called_once()
    mock_info.assert_called_once_with("Search results cleared.")

    with patch.object(app, "log_error") as mock_error, patch.object(
        app, "run_connect"
    ) as mock_connect:
        app.handle_command("connect")
        app.handle_command("connect host nope")
        app.handle_command("connect host 5001")
    assert mock_error.call_count == 2
    mock_connect.assert_called_once_with("host", 5001)

    with patch.object(app, "log_error") as mock_error, patch.object(
        app, "run_search"
    ) as mock_search:
        app.handle_command("search")
        app.handle_command("search a.txt")
        app.handle_command("msearch another.txt")
    mock_error.assert_called_once()
    assert mock_search.call_count == 2

    with patch.object(app, "log_error") as mock_error, patch.object(
        app, "start_download_for_index"
    ) as mock_index, patch.object(app, "run_direct_download") as mock_direct:
        app.handle_command("download nope")
        app.handle_command("download 2")
        app.handle_command("download file1 peer1")
        app.handle_command("download a b c d")
    assert mock_error.call_count == 2
    mock_index.assert_called_once_with(2)
    mock_direct.assert_called_once_with("file1", "peer1")

    with patch.object(app, "exit") as mock_exit, patch.object(
        app, "log_error"
    ) as mock_error:
        app.handle_command("quit")
        app.handle_command("weirdcmd")
    mock_exit.assert_called_once()
    mock_error.assert_called_once()


def test_run_connect_success_and_failure():
    app = make_app()

    async def runner_success():
        with patch.object(app, "refresh_dashboard") as mock_refresh, patch.object(
            app, "log_info"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_connect.__wrapped__(app, "h", 1)
            mock_refresh.assert_called_once()
            mock_log.assert_called_once_with("Connected to h:1")

    asyncio.run(runner_success())

    app_fail = make_app()
    app_fail.connect_fn = AsyncMock(side_effect=Exception("boom"))

    async def runner_fail():
        with patch.object(app_fail, "log_error") as mock_log:
            await tui.PeerLinkTextualApp.run_connect.__wrapped__(app_fail, "h", 1)
            mock_log.assert_called_once()

    asyncio.run(runner_fail())


def test_run_search_success_no_results_and_failure():
    app = make_app()
    app.search_fn = AsyncMock(return_value=[{"filename": "a.txt"}])

    async def runner_success():
        with patch.object(app, "refresh_dashboard") as mock_refresh, patch.object(
            app, "log_info"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_search.__wrapped__(app, "a.txt")
            assert app.last_search_results == [{"filename": "a.txt"}]
            mock_refresh.assert_called_once()
            mock_log.assert_called_once()

    asyncio.run(runner_success())

    app2 = make_app()
    app2.search_fn = AsyncMock(return_value=[])

    async def runner_empty():
        with patch.object(app2, "refresh_dashboard") as mock_refresh, patch.object(
            app2, "log_info"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_search.__wrapped__(app2, "x.txt")
            mock_refresh.assert_called_once()
            mock_log.assert_called_once_with('No results for "x.txt".')

    asyncio.run(runner_empty())

    app3 = make_app()
    app3.search_fn = AsyncMock(side_effect=Exception("bad"))

    async def runner_fail():
        with patch.object(app3, "log_error") as mock_log:
            await tui.PeerLinkTextualApp.run_search.__wrapped__(app3, "x.txt")
            mock_log.assert_called_once()

    asyncio.run(runner_fail())


def test_run_download_from_search_and_direct_download():
    app = make_app()
    app.last_search_results = [
        {
            "file_id": "f1",
            "peer_id": "p1",
            "host": "h",
            "port": 9,
            "filename": "a.txt",
        }
    ]
    app.state.peers = {"p1": {"writer": make_writer(False)}}
    app.download_fn = AsyncMock(return_value="/tmp/a.txt")

    async def runner_success():
        with patch.object(
            app, "_create_download_entry", return_value="1"
        ), patch.object(app, "_set_download_status") as mock_status, patch.object(
            app, "refresh_dashboard"
        ) as mock_refresh, patch.object(
            app, "log_info"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_download_from_search.__wrapped__(app, 1)
            assert mock_status.call_count == 3
            mock_refresh.assert_called_once()
            mock_log.assert_called_once()

    asyncio.run(runner_success())

    app2 = make_app()

    async def runner_no_results():
        with patch.object(app2, "log_error") as mock_log:
            await tui.PeerLinkTextualApp.run_download_from_search.__wrapped__(app2, 1)
            mock_log.assert_called_once()

    asyncio.run(runner_no_results())

    app3 = make_app()
    app3.last_search_results = [
        {"file_id": "f1", "peer_id": "p1", "host": "h", "port": 9, "filename": "a.txt"}
    ]
    app3.download_fn = AsyncMock(side_effect=Exception("fail"))

    async def runner_fail():
        with patch.object(
            app3, "_create_download_entry", return_value="1"
        ), patch.object(app3, "_set_download_status") as mock_status, patch.object(
            app3, "log_error"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_download_from_search.__wrapped__(app3, 1)
            assert mock_status.call_count >= 2
            mock_log.assert_called_once()

    asyncio.run(runner_fail())

    app4 = make_app()
    app4.download_fn = AsyncMock(return_value="/tmp/b.txt")

    async def runner_direct():
        with patch.object(
            app4, "_create_download_entry", return_value="1"
        ), patch.object(app4, "_set_download_status") as mock_status, patch.object(
            app4, "log_info"
        ) as mock_log:
            await tui.PeerLinkTextualApp.run_direct_download.__wrapped__(
                app4, "f2", "p2"
            )
            assert mock_status.call_count == 2
            mock_log.assert_called_once_with("Download complete: /tmp/b.txt")

    asyncio.run(runner_direct())
