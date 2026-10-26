import json

from typer.testing import CliRunner

from purge.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "purge version" in res.stdout


def test_cli_scan(tmp_path):
    p = tmp_path / "app"
    p.mkdir()
    nm = p / "node_modules"
    nm.mkdir()
    (nm / "index.js").write_text("console.log(1)")

    res = runner.invoke(app, ["scan", str(tmp_path), "--no-zombies"])
    assert res.exit_code == 0
    assert "Reclaimable Bloat Targets" in res.stdout
    assert "Node.js & Web" in res.stdout


def test_cli_scan_json(tmp_path):
    p = tmp_path / "app"
    p.mkdir()
    venv = p / ".venv"
    venv.mkdir()
    (venv / "cfg.txt").write_text("v=1")

    res = runner.invoke(app, ["scan", str(tmp_path), "--no-zombies", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert "total_bytes" in data
    assert len(data["artifacts"]) == 1
    assert data["artifacts"][0]["category"] == "Python"


def test_cli_clean_dry_run(tmp_path):
    p = tmp_path / "app"
    p.mkdir()
    nm = p / "node_modules"
    nm.mkdir()
    (nm / "index.js").write_text("console.log(1)")

    res = runner.invoke(app, ["clean", str(tmp_path), "--dry-run"])
    assert res.exit_code == 0
    assert "DRY-RUN SIMULATION" in res.stdout
    assert nm.exists()


def test_cli_clean_force(tmp_path):
    p = tmp_path / "app"
    p.mkdir()
    nm = p / "node_modules"
    nm.mkdir()
    (nm / "index.js").write_text("console.log(1)")

    res = runner.invoke(app, ["clean", str(tmp_path), "--force"])
    assert res.exit_code == 0
    assert "PURGE REAPER COMPLETED" in res.stdout
    assert not nm.exists()
