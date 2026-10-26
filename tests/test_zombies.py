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


def test_kill_zombie_success():
    mock_proc = MagicMock()

    with patch("purge.core.zombies.psutil") as mock_ps:
        mock_ps.Process.return_value = mock_proc
        res = kill_zombie(1234, force=True)
        assert res is True
        mock_proc.kill.assert_called_once()
