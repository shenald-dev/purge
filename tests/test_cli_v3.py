"""Tests for v3.0 CLI surface: MCP subcommand and --fail-over CI gate."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from purge.cli import app

runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    node_root = tmp_path / "web"
    node_root.mkdir()
    (node_root / "package.json").write_text("{}", encoding="utf-8")
    nm = node_root / "node_modules"
    nm.mkdir()
    (nm / "pkg_a").write_text("x" * 300, encoding="utf-8")
    return tmp_path


class TestFailOverGate:
    def test_fail_over_exceed_threshold_exits_2(self, workspace: Path):
        result = runner.invoke(app, ["scan", str(workspace), "--no-zombies", "--fail-over", "1B"])
        assert result.exit_code == 2
        assert "Bloat gate exceeded" in result.output

    def test_fail_over_under_threshold_exits_0(self, workspace: Path):
        result = runner.invoke(app, ["scan", str(workspace), "--no-zombies", "--fail-over", "10GB"])
        assert result.exit_code == 0

    def test_fail_over_invalid_threshold_ignored(self, workspace: Path):
        result = runner.invoke(app, ["scan", str(workspace), "--no-zombies", "--fail-over", "nonsense"])
        assert result.exit_code == 0

    def test_fail_over_with_json_still_reports(self, workspace: Path):
        result = runner.invoke(
            app, ["scan", str(workspace), "--no-zombies", "--json", "--fail-over", "1B"]
        )
        assert result.exit_code == 2
        # JSON payload was emitted before the gate verdict
        assert '"total_artifacts"' in result.output


class TestMcpSubcommand:
    def test_mcp_missing_package_reports_error(self, monkeypatch):
        """Simulate an environment without the mcp SDK installed."""
        import importlib.abc
        import sys

        # Remove the real mcp packages and purge.mcp_server from the cache
        for mod in list(sys.modules):
            if mod == "mcp" or mod.startswith("mcp.") or mod == "purge.mcp_server":
                monkeypatch.delitem(sys.modules, mod, raising=False)

        class _BlockMcp(importlib.abc.MetaPathFinder):
            """Raise ImportError for any 'mcp*' import, like an absent SDK."""

            def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
                if fullname == "mcp" or fullname.startswith("mcp."):
                    raise ImportError(f"No module named '{fullname}'")
                return None

        finder = _BlockMcp()
        monkeypatch.syspath_prepend(str(Path(__file__).parent))
        import purge.cli  # ensure the app object exists in this process

        # Prepend our blocker to the meta path so it wins over the real loader
        monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])

        result = runner.invoke(purge.cli.app, ["mcp"])
        assert result.exit_code == 1
        assert "purge-reaper[mcp]" in result.output

    def test_mcp_rejects_bad_transport(self):
        result = runner.invoke(app, ["mcp", "--transport", "ftp"])
        assert result.exit_code == 1
        assert "Unsupported transport" in result.output

    def test_mcp_help_shows_options(self):
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "stdio" in result.output
        assert "streamable-http" in result.output


class TestVersionBump:
    def test_version_reports_3(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "3.0.0" in result.output
