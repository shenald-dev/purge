"""Additional high-coverage unit tests for Purge v2.0 engine features."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from purge.core.cleaner import PurgeCleaner
from purge.core.disk import PartitionInfo
from purge.core.models import Artifact, CleanResult, PurgeReport
from purge.core.rules import identify_artifact_category
from purge.core.scoring import calculate_purge_score
from purge.core.vault import QuarantineVault, VaultItem, VaultSession
from purge.ui.console import (
    render_artifacts_table,
    render_clean_result,
    render_disk_status,
    render_scan_summary,
    render_vault_details,
    render_vault_sessions_table,
)


def test_new_heuristics_swift(tmp_path):
    (tmp_path / "Package.swift").write_text("// swift")
    cat = identify_artifact_category(".build", tmp_path)
    assert cat == "Systems & Native"

    # Without Package.swift, should return None
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert identify_artifact_category(".build", empty_dir) is None


def test_new_heuristics_zig(tmp_path):
    (tmp_path / "build.zig").write_text("// zig")
    assert identify_artifact_category(".zig-cache", tmp_path) == "Systems & Native"
    assert identify_artifact_category("zig-out", tmp_path) == "Systems & Native"


def test_new_heuristics_cmake(tmp_path):
    (tmp_path / "CMakeLists.txt").write_text("# cmake")
    assert identify_artifact_category("CMakeFiles", tmp_path) == "Systems & Native"


def test_new_heuristics_php_and_ruby(tmp_path):
    php_dir = tmp_path / "php_proj"
    php_dir.mkdir()
    (php_dir / "composer.json").write_text("{}")
    assert identify_artifact_category("vendor", php_dir) == "PHP / Composer"

    ruby_dir = tmp_path / "ruby_proj"
    ruby_dir.mkdir()
    (ruby_dir / "Gemfile").write_text("gem 'rails'")
    assert identify_artifact_category("vendor", ruby_dir) == "Ruby / Bundler"


def test_cleaner_parallel_workers(tmp_path):
    """Test parallel worker execution in PurgeCleaner."""
    d1 = tmp_path / "art1"
    d1.mkdir()
    (d1 / "f.txt").write_text("data1")

    d2 = tmp_path / "art2"
    d2.mkdir()
    (d2 / "f.txt").write_text("data2")

    a1 = Artifact(path=d1, category="Build", size_bytes=100)
    a2 = Artifact(path=d2, category="Build", size_bytes=200)

    cleaner = PurgeCleaner(workers=2, record_history=False)
    result = cleaner.purge([a1, a2])

    assert result.deleted_artifacts_count == 2
    assert result.reclaimed_bytes == 300
    assert not d1.exists()
    assert not d2.exists()


def test_cleaner_protected_path():
    """Ensure cleaner refuses to delete root/protected paths."""
    cleaner = PurgeCleaner()
    res = cleaner.purge([Artifact(path=Path("/"), category="Root", size_bytes=1000)])
    assert res.deleted_artifacts_count == 0
    assert len(res.errors) >= 1


def test_cleaner_to_trash(tmp_path):
    """Test cleaner with send2trash mock or missing import error."""
    f = tmp_path / "file.txt"
    f.write_text("delete me")
    art = Artifact(path=f, category="Temp", size_bytes=10)

    cleaner = PurgeCleaner(to_trash=True, record_history=False)

    # 1. Missing module returns informative error
    ok, err, item = cleaner.delete_artifact(art)
    assert ok is False
    assert "send2trash" in err

    # 2. Mocking send2trash in sys.modules
    mock_s2t = MagicMock()
    with patch.dict("sys.modules", {"send2trash": mock_s2t}):
        ok, err, item = cleaner.delete_artifact(art)
        assert ok is True
        mock_s2t.send2trash.assert_called_once_with(str(f))


def test_vault_edge_cases(tmp_path):
    vault = QuarantineVault(vault_root=tmp_path / "vault")
    # Non existent session
    assert vault.get_session("non_existent") is None
    count, b, errs = vault.restore_session("non_existent")
    assert count == 0
    assert "not found" in errs[0]

    # Prune specific session ID
    session_id = vault.create_session()
    f = tmp_path / "temp.txt"
    f.write_text("hello")
    vault.quarantine(f, session_id, size_bytes=5)
    session = VaultSession(
        vault_id=session_id,
        created_at="2026-11-03T12:00:00Z",
        total_bytes=5,
        total_items=1,
        items=[
            VaultItem(
                item_id="i1",
                original_path=str(f),
                vault_path=str(tmp_path / "vault" / session_id / "i1"),
                size_bytes=5,
                is_dir=False,
                quarantined_at="2026-11-03T12:00:00Z",
            )
        ],
    )
    vault.save_session_manifest(session)

    del_count, freed = vault.prune_vault(vault_id=session_id)
    assert del_count == 1
    assert freed == 5


def test_console_renderers(capsys):
    """Test console render functions execute without error."""
    # Disk status
    part = PartitionInfo(
        mountpoint="C:\\",
        device="C:",
        fstype="NTFS",
        total_bytes=500 * 1024 * 1024 * 1024,
        used_bytes=300 * 1024 * 1024 * 1024,
        free_bytes=200 * 1024 * 1024 * 1024,
        percent_used=60.0,
        bloat_bytes=25 * 1024 * 1024 * 1024,
    )
    render_disk_status(part)

    # Clean result with vault
    res = CleanResult(
        reclaimed_bytes=1024 * 1024 * 100,
        quarantined_count=3,
        vault_session_id="vault_12345",
        duration_seconds=0.45,
    )
    render_clean_result(res)

    # Vault tables
    item = VaultItem("i1", "/path/to/thing", "/vault/i1", 1000, True, "2026-11-03T12:00:00Z")
    session = VaultSession("vault_12345", "2026-11-03T12:00:00Z", 1000, 1, [item])
    render_vault_sessions_table([session])
    render_vault_sessions_table([])
    render_vault_details(session)

    # Artifacts table with score
    art = Artifact(
        path=Path("/test/node_modules"),
        category="Node.js & Web",
        size_bytes=1024 * 1024 * 200,
        file_count=5000,
        days_stale=12.0,
        purge_score=75.0,
        safety_level="SAFE",
    )
    rep = PurgeReport(
        scan_path=Path("/test"),
        artifacts=[art] * 55,  # test max_items truncation
        total_bytes=1024 * 1024 * 200 * 55,
        total_files=275000,
        scanned_dirs_count=200,
        high_priority_count=55,
    )
    render_artifacts_table(rep)
    render_scan_summary(rep)


def test_scoring_edge_cases():
    # 0 bytes
    res0 = calculate_purge_score(0, 0, "Other", "temp")
    assert res0.size_score == 0.0

    # > 2GB
    res2g = calculate_purge_score(3 * 1024**3, 120, "Rust / Cargo", "target")
    assert res2g.size_score == 35.0
    assert res2g.stale_score == 30.0
