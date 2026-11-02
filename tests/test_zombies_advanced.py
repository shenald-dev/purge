from unittest.mock import MagicMock

from purge.core import zombies
from purge.core.models import ZombieProcess
from purge.core.zombies import get_process_on_port, kill_zombie_tree


def test_kill_zombie_tree_with_children(monkeypatch):
    mock_child = MagicMock()
    mock_child.kill = MagicMock()

    mock_parent = MagicMock()
    mock_parent.children.return_value = [mock_child]
    mock_parent.kill = MagicMock()

    mock_psutil = MagicMock()
    mock_psutil.Process.return_value = mock_parent
    monkeypatch.setattr(zombies, "psutil", mock_psutil)

    slain = kill_zombie_tree(12345, force=True)
    assert slain == 2  # 1 child + 1 parent
    mock_child.kill.assert_called_once()
    mock_parent.kill.assert_called_once()


def test_get_process_on_port_returns_match(monkeypatch):
    dummy_zombie = ZombieProcess(
        pid=9999,
        name="node",
        cmdline="next dev",
        port=3000,
        url="http://localhost:3000",
    )
    monkeypatch.setattr(zombies, "find_zombies", lambda target_port=None: [dummy_zombie] if target_port == 3000 else [])

    proc = get_process_on_port(3000)
    assert proc is not None
    assert proc.pid == 9999
    assert proc.port == 3000
    assert proc.url == "http://localhost:3000"

    none_proc = get_process_on_port(8080)
    assert none_proc is None
