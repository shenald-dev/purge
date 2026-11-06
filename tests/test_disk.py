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
