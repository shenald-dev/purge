from unittest.mock import MagicMock, patch

from purge.core.zombies import find_zombies, kill_zombie


def test_find_zombies_with_mocked_psutil():
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    mock_proc.name.return_value = "node"
    mock_proc.cmdline.return_value = ["node", "server.js"]
    mock_proc.cwd.return_value = "/app"
    mock_proc.create_time.return_value = 1000.0

    mock_mem = MagicMock()
    mock_mem.rss = 1024 * 1024 * 250  # 250 MB
    mock_proc.memory_info.return_value = mock_mem
    mock_proc.cpu_percent.return_value = 2.5

    mock_conn = MagicMock()
    mock_conn.status = "LISTEN"
    mock_conn.laddr.port = 3000
    mock_conn.pid = 9999

    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.CONN_LISTEN = "LISTEN"
        mock_ps.net_connections.return_value = [mock_conn]
        mock_ps.Process.return_value = mock_proc
        mock_ps.process_iter.return_value = []

        zombies = find_zombies(target_port=3000)
        assert len(zombies) == 1
        z = zombies[0]
        assert z.pid == 9999
        assert z.name == "node"
        assert z.port == 3000
        assert z.memory_mb == 250.0


def test_missing_psutil():
    with patch("purge.core.zombies.psutil", None):
        assert find_zombies(target_port=3000) == []
        assert kill_zombie(1234, force=True) is False


def test_find_zombies_ignores_regular_python():
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 9999,
        "name": "python",
        "cmdline": ["python", "script.py"],
        "cwd": "/app",
        "create_time": 1000.0,
    }

    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.net_connections.return_value = []
        mock_ps.process_iter.return_value = [mock_proc]

        zombies = find_zombies()
        assert len(zombies) == 0


def test_find_zombies_identifies_dev_in_cmdline():
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    mock_proc.name.return_value = "python"
    mock_proc.cmdline.return_value = ["python", "-m", "uvicorn", "main:app", "--reload"]
    mock_proc.cwd.return_value = "/app"
    mock_proc.create_time.return_value = 1000.0

    mock_mem = MagicMock()
    mock_mem.rss = 1024 * 1024 * 250
    mock_proc.memory_info.return_value = mock_mem
    mock_proc.cpu_percent.return_value = 2.5

    mock_proc.info = {
        "pid": 9999,
        "name": "python",
        "cmdline": ["python", "-m", "uvicorn", "main:app", "--reload"],
        "cwd": "/app",
        "create_time": 1000.0,
    }

    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.net_connections.return_value = []
        mock_ps.process_iter.return_value = [mock_proc]
        mock_ps.Process.return_value = mock_proc

        zombies = find_zombies()
        assert len(zombies) == 1
        assert zombies[0].pid == 9999
        assert zombies[0].name == "python"


def test_find_zombies_net_connections_fallback():
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    mock_proc.name.return_value = "node"
    mock_proc.cmdline.return_value = ["node", "server.js"]
    mock_proc.cwd.return_value = "/app"
    mock_proc.create_time.return_value = 1000.0

    mock_mem = MagicMock()
    mock_mem.rss = 1024 * 1024 * 250
    mock_proc.memory_info.return_value = mock_mem
    mock_proc.cpu_percent.return_value = 2.5

    mock_conn = MagicMock()
    mock_conn.status = "LISTEN"
    mock_conn.laddr.port = 3000
    mock_proc.connections.return_value = [mock_conn]

    import psutil
    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.CONN_LISTEN = "LISTEN"
        # Raise AccessDenied to trigger fallback
        mock_ps.net_connections.side_effect = psutil.AccessDenied(pid=None)
        mock_ps.process_iter.return_value = [mock_proc]
        mock_ps.Process.return_value = mock_proc

        zombies = find_zombies(target_port=3000)

        assert len(zombies) == 1
        assert zombies[0].pid == 9999
        assert zombies[0].port == 3000
        mock_proc.connections.assert_called_once_with(kind="inet")


def test_kill_zombie_success():
    mock_proc = MagicMock()

    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.Process.return_value = mock_proc
        res = kill_zombie(1234, force=True)
        assert res is True
        mock_proc.kill.assert_called_once()
