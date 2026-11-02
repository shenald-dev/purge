import json
from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from purge.cli import app
from purge.core.models import ZombieProcess

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "purge version" in res.stdout


def test_cli_scan_filters(tmp_path: Path):
    proj = tmp_path / "app"
    proj.mkdir()
    (proj / "node_modules").mkdir()
    (proj / ".venv").mkdir()
    cargo = proj / "cargo_proj"
    cargo.mkdir()
    (cargo / "Cargo.toml").write_text("[package]")
    (cargo / "target").mkdir()

    # Filter --node
    res_node = runner.invoke(app, ["scan", str(proj), "--node", "--no-zombies", "--json"])
    assert res_node.exit_code == 0
    data_node = json.loads(res_node.stdout)
    cats_node = {a["category"] for a in data_node["artifacts"]}
    assert "Node.js & Web" in cats_node
    assert "Python" not in cats_node

    # Filter --python
    res_py = runner.invoke(app, ["scan", str(proj), "--python", "--no-zombies", "--json"])
    assert res_py.exit_code == 0
    data_py = json.loads(res_py.stdout)
    cats_py = {a["category"] for a in data_py["artifacts"]}
    assert "Python" in cats_py
    assert "Node.js & Web" not in cats_py

    # Filter --rust
    res_rust = runner.invoke(app, ["scan", str(proj), "--rust", "--no-zombies", "--json"])
    assert res_rust.exit_code == 0
    data_rust = json.loads(res_rust.stdout)
    cats_rust = {a["category"] for a in data_rust["artifacts"]}
    assert "Rust / Cargo" in cats_rust


def test_cli_port_free_available(monkeypatch):
    from purge import cli
    monkeypatch.setattr(cli, "get_process_on_port", lambda port: None)

    res = runner.invoke(app, ["port", "9999"])
    assert res.exit_code == 0
    assert "AVAILABLE" in res.stdout or "FREE" in res.stdout


def test_cli_port_json_output(monkeypatch):
    dummy_proc = ZombieProcess(
        pid=1234,
        name="python",
        cmdline="uvicorn main:app",
        port=8000,
    )
    from purge import cli
    monkeypatch.setattr(cli, "get_process_on_port", lambda port: dummy_proc)

    res = runner.invoke(app, ["port", "8000", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["pid"] == 1234
    assert data["port"] == 8000


def test_cli_zombies_json_and_kill(monkeypatch):
    dummy_zombie = ZombieProcess(
        pid=7777,
        name="flask",
        cmdline="flask run",
        port=5000,
    )
    from purge import cli
    monkeypatch.setattr(cli, "find_zombies", lambda target_port=None: [dummy_zombie])
    mock_kill = MagicMock(return_value=1)
    monkeypatch.setattr(cli, "kill_zombie_tree", mock_kill)

    # JSON listing
    res_json = runner.invoke(app, ["zombies", "--json"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert len(data) == 1
    assert data[0]["pid"] == 7777

    # Kill command
    res_kill = runner.invoke(app, ["zombies", "--kill", "--force"])
    assert res_kill.exit_code == 0
    assert "Successfully terminated" in res_kill.stdout
