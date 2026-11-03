"""Tests for Purge v2.0 flagship CLI features."""

import json

from typer.testing import CliRunner

from purge.cli import app

runner = CliRunner()


def test_cli_scan_score_and_sorting(tmp_path):
    """Test scan with --min-score, --sort, and --top."""
    proj1 = tmp_path / "proj1"
    proj1.mkdir()
    (proj1 / "package.json").write_text("{}")
    nm1 = proj1 / "node_modules"
    nm1.mkdir()
    (nm1 / "file.txt").write_text("a" * 1024)

    proj2 = tmp_path / "proj2"
    proj2.mkdir()
    pyc = proj2 / "__pycache__"
    pyc.mkdir()
    (pyc / "test.pyc").write_text("b" * 100)

    # Scan with score filter and sorting
    res = runner.invoke(app, ["scan", str(tmp_path), "--sort", "score", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert len(data["artifacts"]) >= 2
    assert "purge_score" in data["artifacts"][0]

    # Scan with top limit and stale sort
    res_top = runner.invoke(app, ["scan", str(tmp_path), "--top", "1", "--sort", "stale", "--json"])
    assert res_top.exit_code == 0
    data_top = json.loads(res_top.stdout)
    assert len(data_top["artifacts"]) == 1

    # Scan with name sort
    res_name = runner.invoke(app, ["scan", str(tmp_path), "--sort", "name", "--json"])
    assert res_name.exit_code == 0


def test_cli_scan_disk_flag(tmp_path):
    """Test purge scan with --disk flag."""
    res = runner.invoke(app, ["scan", str(tmp_path), "--disk"])
    assert res.exit_code == 0
    assert "DISK CAPACITY & BLOAT RADAR" in res.stdout


def test_cli_scan_export_formats(tmp_path):
    """Test --format markdown and --format csv."""
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "file.txt").write_text("hello")

    res_md = runner.invoke(app, ["scan", str(tmp_path), "--format", "markdown"])
    assert res_md.exit_code == 0
    assert "# Purge Developer Bloat Audit Report" in res_md.stdout

    res_csv = runner.invoke(app, ["scan", str(tmp_path), "--format", "csv"])
    assert res_csv.exit_code == 0
    assert "category,path,size_bytes" in res_csv.stdout


def test_cli_export_command(tmp_path):
    """Test purge export command."""
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "lib.js").write_text("export const x = 1;")

    out_file = tmp_path / "audit.md"
    res = runner.invoke(app, ["export", str(tmp_path), "--output", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()
    assert "# Purge Developer Bloat" in out_file.read_text(encoding="utf-8")


def test_cli_disk_command(tmp_path):
    """Test purge disk command."""
    # JSON output
    res = runner.invoke(app, ["disk", str(tmp_path), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert "partition" in data
    assert "report_summary" in data

    # Terminal output
    res_term = runner.invoke(app, ["disk", str(tmp_path)])
    assert res_term.exit_code == 0
    assert "DISK CAPACITY & BLOAT RADAR" in res_term.stdout


def test_cli_clean_vault_and_restore(tmp_path, monkeypatch):
    """Test quarantine with purge clean --vault and restore with purge vault restore."""
    vault_dir = tmp_path / ".config" / "purge" / "vault"
    monkeypatch.setattr("purge.core.vault.DEFAULT_VAULT_ROOT", vault_dir)

    target_dir = tmp_path / "work"
    target_dir.mkdir()
    nm = target_dir / "node_modules"
    nm.mkdir()
    (nm / "package.json").write_text('{"name": "test"}')

    # Run clean with --vault and --force
    res_clean = runner.invoke(app, ["clean", str(target_dir), "--vault", "--force", "--json"])
    assert res_clean.exit_code == 0
    clean_data = json.loads(res_clean.stdout)
    assert clean_data["quarantined_count"] == 1
    vault_id = clean_data["vault_session_id"]
    assert vault_id is not None
    assert not nm.exists()

    # List vaults
    res_list = runner.invoke(app, ["vault", "list", "--json"])
    assert res_list.exit_code == 0
    vaults_data = json.loads(res_list.stdout)
    assert len(vaults_data) == 1
    assert vaults_data[0]["vault_id"] == vault_id

    # Show vault
    res_show = runner.invoke(app, ["vault", "show", vault_id, "--json"])
    assert res_show.exit_code == 0
    show_data = json.loads(res_show.stdout)
    assert show_data["vault_id"] == vault_id

    # Restore vault
    res_restore = runner.invoke(app, ["vault", "restore", vault_id, "--force", "--json"])
    assert res_restore.exit_code == 0
    restore_data = json.loads(res_restore.stdout)
    assert restore_data["restored_count"] == 1
    assert nm.exists()
    assert (nm / "package.json").read_text() == '{"name": "test"}'


def test_cli_vault_prune(tmp_path, monkeypatch):
    """Test purge vault prune command."""
    vault_dir = tmp_path / ".config" / "purge" / "vault"
    monkeypatch.setattr("purge.core.vault.DEFAULT_VAULT_ROOT", vault_dir)

    # Empty prune
    res = runner.invoke(app, ["vault", "prune", "--days", "0", "--force", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert "deleted_sessions" in data


def test_cli_vault_error_handling(tmp_path, monkeypatch):
    """Test vault commands with invalid IDs."""
    vault_dir = tmp_path / ".config" / "purge" / "vault"
    monkeypatch.setattr("purge.core.vault.DEFAULT_VAULT_ROOT", vault_dir)

    # Show nonexistent
    res_show = runner.invoke(app, ["vault", "show", "nonexistent"])
    assert res_show.exit_code == 1
    assert "not found" in res_show.stdout

    # Restore nonexistent
    res_restore = runner.invoke(app, ["vault", "restore", "nonexistent"])
    assert res_restore.exit_code == 1
    assert "not found" in res_restore.stdout


def test_cli_clean_auto_mode(tmp_path):
    """Test purge clean --auto mode."""
    target_dir = tmp_path / "proj"
    target_dir.mkdir()
    nm = target_dir / "node_modules"
    nm.mkdir()
    (nm / "dummy.js").write_text("x" * 2048)

    # Dry-run with --auto and explicit --min-score
    res = runner.invoke(app, ["clean", str(target_dir), "--auto", "--min-score", "25", "--dry-run", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["deleted_artifacts_count"] == 1
    assert nm.exists()
