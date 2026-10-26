from datetime import datetime, timezone
from pathlib import Path

from purge.core.models import (
    Artifact,
    CleanResult,
    PurgeReport,
    ZombieProcess,
    format_bytes,
)


def test_format_bytes():
    assert format_bytes(500) == "500.00 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024 * 5) == "5.00 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.00 GB"


def test_artifact_model():
    p = Path("/test/app/node_modules")
    now = datetime.now(timezone.utc)
    art = Artifact(
        path=p,
        category="Node.js & Web",
        size_bytes=1024 * 1024 * 50,
        file_count=1200,
        last_modified=now,
        days_stale=14.5,
    )

    assert art.human_size == "50.00 MB"
    d = art.to_dict()
    assert d["category"] == "Node.js & Web"
    assert d["size_bytes"] == 1024 * 1024 * 50
    assert d["days_stale"] == 14.5


def test_zombie_model():
    z = ZombieProcess(
        pid=1234,
        name="node",
        cmdline="node server.js",
        port=3000,
        memory_mb=128.4,
        cpu_percent=1.5,
        cwd="/test/app",
    )
    d = z.to_dict()
    assert d["pid"] == 1234
    assert d["port"] == 3000
    assert d["memory_mb"] == 128.4


def test_purge_report_and_clean_result():
    report = PurgeReport(
        scan_path=Path("/test"),
        artifacts=[],
        total_bytes=1024 * 1024 * 1024 * 3,
        total_files=5000,
        scanned_dirs_count=45,
        duration_seconds=0.12,
    )
    assert report.human_total_size == "3.00 GB"

    result = CleanResult(
        reclaimed_bytes=1024 * 1024 * 500,
        deleted_artifacts_count=5,
        slain_zombies_count=2,
        duration_seconds=0.05,
    )
    assert result.human_reclaimed_size == "500.00 MB"
    assert result.deleted_artifacts_count == 5
    assert result.slain_zombies_count == 2
