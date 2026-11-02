import json
from unittest.mock import MagicMock

from typer.testing import CliRunner

from purge.cli import app
from purge.core.models import ZombieProcess, parse_size_to_bytes

runner = CliRunner()


def test_parse_size_to_bytes():
    assert parse_size_to_bytes("100B") == 100
    assert parse_size_to_bytes("1KB") == 1024
    assert parse_size_to_bytes("1MB") == 1024 * 1024
    assert parse_size_to_bytes("2GB") == 2 * 1024 * 1024 * 1024
    assert parse_size_to_bytes("invalid") == 0


def test_cli_scan_output_file(tmp_path):
    target_dir = tmp_path / "project"
    target_dir.mkdir()
    node_mods = target_dir / "node_modules"
    node_mods.mkdir()
    (node_mods / "pkg.js").write_text("console.log('hi')")

    out_file = tmp_path / "scan_results.json"
    res = runner.invoke(app, ["scan", str(target_dir), "--no-zombies", "-o", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "total_bytes" in data
    assert data["total_artifacts"] == 1


def test_cli_port_free_command(monkeypatch):
    dummy_proc = ZombieProcess(
        pid=5555,
        name="vite",
        cmdline="vite --port 5173",
        port=5173,
        url="http://localhost:5173",
        memory_mb=120.0,
    )
    from purge import cli
    monkeypatch.setattr(cli, "get_process_on_port", lambda port: dummy_proc if port == 5173 else None)
    mock_kill = MagicMock(return_value=1)
    monkeypatch.setattr(cli, "kill_zombie_tree", mock_kill)

    # Inspect port
    res_inspect = runner.invoke(app, ["port", "5173"])
    assert res_inspect.exit_code == 0
    assert "PORT :5173 OCCUPIED" in res_inspect.stdout
    assert "PID 5555" in res_inspect.stdout

    # Kill port with --force
    res_kill = runner.invoke(app, ["port", "5173", "--kill", "--force"])
    assert res_kill.exit_code == 0
    assert "Port :5173" in res_kill.stdout
    assert "FREE" in res_kill.stdout
    mock_kill.assert_called_with(5555, force=True)


def test_cli_stats_command():
    res = runner.invoke(app, ["stats"])
    assert res.exit_code == 0
    assert "LIFETIME PURGE RECLAMATION TELEMETRY" in res.stdout


def test_cli_init_command(tmp_path):
    res = runner.invoke(app, ["init", str(tmp_path)])
    assert res.exit_code == 0
    cfg = tmp_path / "purge.toml"
    assert cfg.exists()
    assert "[purge]" in cfg.read_text()

    # Second run should report already exists
    res2 = runner.invoke(app, ["init", str(tmp_path)])
    assert res2.exit_code == 0
    assert "already exists" in res2.stdout


def test_cli_cache_command(monkeypatch, tmp_path):
    from purge.core.models import Artifact
    from purge.core.scanner import DiskScanner
    dummy_cache = Artifact(
        path=tmp_path / "npm_cache",
        category="Global Cache: npm",
        size_bytes=1048576,
        is_global_cache=True,
    )
    monkeypatch.setattr(DiskScanner, "scan_global_caches", lambda self: [dummy_cache])

    res = runner.invoke(app, ["cache"])
    assert res.exit_code == 0
    assert "Global Developer Package Caches" in res.stdout


def test_cli_clean_interactive(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    nm = project / "node_modules"
    nm.mkdir()
    (nm / "index.js").write_text("hello")

    # Interactive choice "all"
    res = runner.invoke(app, ["clean", str(project), "--dry-run", "--interactive"], input="all\n")
    assert res.exit_code == 0
    assert "PURGE REAPER COMPLETED" in res.stdout
