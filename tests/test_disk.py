"""Tests for disk capacity and bloat radar analysis."""

from pathlib import Path

from purge.core.disk import PartitionInfo, get_partition_for_path


def test_partition_info_calculations():
    part = PartitionInfo(
        mountpoint="/",
        device="/dev/sda1",
        fstype="ext4",
        total_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
        used_bytes=60 * 1024 * 1024 * 1024,   # 60 GB
        free_bytes=40 * 1024 * 1024 * 1024,   # 40 GB
        percent_used=60.0,
        bloat_bytes=10 * 1024 * 1024 * 1024,  # 10 GB
    )

    assert part.bloat_percent_of_total == 10.0
    assert round(part.bloat_percent_of_used, 1) == 16.7
    assert part.potential_free_gain_percent == 25.0
    d = part.to_dict()
    assert d["percent_used"] == 60.0
    assert d["bloat_percent_of_total"] == 10.0


def test_get_partition_for_path():
    part = get_partition_for_path(Path.cwd(), bloat_bytes=1024 * 1024)
    assert part is not None
    assert part.total_bytes > 0
    assert part.free_bytes >= 0
    assert part.bloat_bytes == 1024 * 1024


def test_get_partition_for_path_mocked(monkeypatch):
    import psutil

    class MockPart:
        def __init__(self, mountpoint, device, fstype):
            self.mountpoint = mountpoint
            self.device = device
            self.fstype = fstype

    def mock_partitions(all=False):
        return [
            MockPart("/", "/dev/sda1", "ext4"),
            MockPart("/mnt/data", "/dev/sdb1", "ext4"),
            MockPart("/mnt/data/other", "/dev/sdb2", "ext4"),
        ]

    class MockUsage:
        def __init__(self):
            self.total = 100
            self.used = 50
            self.free = 50
            self.percent = 50.0

    def mock_disk_usage(path):
        return MockUsage()

    monkeypatch.setattr(psutil, "disk_partitions", mock_partitions)
    monkeypatch.setattr(psutil, "disk_usage", mock_disk_usage)

    part1 = get_partition_for_path(Path("/home/user"), bloat_bytes=0)
    assert part1.mountpoint == "/"

    part2 = get_partition_for_path(Path("/mnt/data/myfiles"), bloat_bytes=0)
    assert part2.mountpoint == "/mnt/data"


def test_get_partition_for_existing_file():
    """Verify partition resolution for an existing file path on disk."""
    part = get_partition_for_path(Path(__file__), bloat_bytes=512)
    assert part is not None
    assert part.total_bytes > 0
    assert part.free_bytes >= 0
    assert part.bloat_bytes == 512


def test_get_partition_for_unc_path_mocked(monkeypatch):
    """Verify UNC share partition matching without relative/absolute path errors."""
    import psutil

    class MockPart:
        def __init__(self, mountpoint, device=r"\\server\share", fstype="SMB"):
            self.mountpoint = mountpoint
            self.device = device
            self.fstype = fstype

    class MockUsage:
        total = 1000
        used = 500
        free = 500
        percent = 50.0

    monkeypatch.setattr(psutil, "disk_partitions", lambda all=False: [MockPart(r"\\server\share")])
    monkeypatch.setattr(psutil, "disk_usage", lambda p: MockUsage())
    monkeypatch.setattr(Path, "resolve", lambda self: Path(r"\\server\share\sub\file.txt"))

    part = get_partition_for_path(Path("dummy"))
    assert part is not None
    assert part.mountpoint == r"\\server\share"


def test_get_partition_for_unresolvable_unc_path(monkeypatch):
    """Verify graceful handling when path.resolve() fails with WinError 53 on offline UNC."""
    def mock_resolve_fail(self):
        raise FileNotFoundError(53, "The network path was not found")

    monkeypatch.setattr(Path, "resolve", mock_resolve_fail)
    part = get_partition_for_path(Path(r"\\nonexistent_srv\share\file.txt"))
    assert part is None


def test_get_partition_for_nonexistent_path():
    """Verify ancestor traversal for a non-existent path in an existing directory tree."""
    nonexistent = Path.cwd() / "nonexistent_subfolder_xyz" / "nonexistent_file.txt"
    part = get_partition_for_path(nonexistent)
    assert part is not None
    assert part.total_bytes > 0

