"""Tests for the native MCP server surface.

These tests exercise the tool functions directly (unit level). The
end-to-end stdio protocol handshake is covered separately in
tests/test_mcp_e2e.py.
"""

from pathlib import Path

import pytest

pytest.importorskip(
    "mcp",
    reason="mcp SDK not installed; run pip install 'purge-reaper[mcp]' to enable MCP tests",
)

from purge.mcp_server import (  # noqa: E402
    clean,
    inspect_path,
    kill_zombies,
    port_status,
    scan,
    server_info,
    stats,
    vault_list,
    vault_restore,
    vault_show,
)


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    node_root = tmp_path / "web"
    node_root.mkdir()
    (node_root / "package.json").write_text("{}", encoding="utf-8")
    nm = node_root / "node_modules"
    nm.mkdir()
    (nm / "pkg_a").write_text("y" * 200, encoding="utf-8")
    return tmp_path


class TestReadOnlyTools:
    def test_server_info(self):
        result = server_info()
        assert result["ok"] is True
        assert result["data"]["name"] == "purge"
        assert "scan" in result["data"]["capabilities"]
        assert result["data"]["safety"].startswith("destructive tools")

    def test_scan_tool_returns_report_dict(self, workspace: Path):
        result = scan(root=str(workspace))
        assert result["ok"] is True
        data = result["data"]
        assert data["total_artifacts"] >= 1
        assert any(a["path"].endswith("node_modules") for a in data["artifacts"])
        assert all(0 <= a["purge_score"] <= 100 for a in data["artifacts"])

    def test_scan_tool_rejects_protected_root(self):
        result = scan(root="/usr")
        assert result["ok"] is False
        assert "protected" in result["error"].lower()

    def test_scan_tool_error_is_structured(self, workspace: Path):
        result = scan(root=str(workspace), min_size="not-a-size-parseable")
        # invalid size strings degrade to 0 (no filter), not an error
        assert result["ok"] is True

    def test_inspect_path(self, workspace: Path):
        target = workspace / "web" / "node_modules"
        result = inspect_path(path=str(target))
        assert result["ok"] is True
        assert result["data"]["category"] == "Node.js & Web"
        assert result["data"]["file_count"] == 1

    def test_inspect_path_rejects_protected(self):
        result = inspect_path(path="/etc")
        assert result["ok"] is False

    def test_port_status_free_port(self):
        result = port_status(port=59999)
        assert result["ok"] is True
        assert result["data"]["status"] == "free" or "pid" in result["data"]

    def test_stats_tool(self):
        result = stats()
        assert result["ok"] is True
        assert "total_reclaimed_bytes" in result["data"]

    def test_vault_list_tool(self):
        result = vault_list()
        assert result["ok"] is True
        assert isinstance(result["data"], list)

    def test_vault_show_missing_session(self):
        result = vault_show(vault_id="vault_19700101_000000")
        assert result["ok"] is False
        assert "not found" in result["error"]


class TestDestructiveToolsRequireConfirm:
    """The MCP safety model: destructive tools refuse without confirm=True."""

    def test_clean_requires_confirm(self, workspace: Path):
        result = clean(root=str(workspace))
        assert result["ok"] is False
        assert "confirm=True" in result["error"]

    def test_clean_dry_run_deletes_nothing(self, workspace: Path):
        result = clean(root=str(workspace))
        assert result["ok"] is False
        assert (workspace / "web" / "node_modules").exists()

    def test_clean_rejects_protected_root_even_with_confirm(self):
        result = clean(root="/usr", confirm=True)
        assert result["ok"] is False

    def test_kill_zombies_requires_confirm(self):
        result = kill_zombies()
        assert result["ok"] is False
        assert "confirm=True" in result["error"]

    def test_vault_restore_requires_confirm(self):
        result = vault_restore(vault_id="vault_19700101_000000")
        assert result["ok"] is False
        assert "confirm=True" in result["error"]


class TestCleanExecution:
    def test_clean_confirmed_deletes(self, workspace: Path):
        result = clean(root=str(workspace), confirm=True, auto_min_score=0.0)
        assert result["ok"] is True
        payload = result["data"]
        assert payload["deleted_artifacts_count"] >= 1
        assert not (workspace / "web" / "node_modules").exists()

    def test_clean_vault_mode_is_reversible(self, workspace: Path, tmp_path: Path):
        result = clean(
            root=str(workspace),
            confirm=True,
            mode="vault",
            auto_min_score=0.0,
        )
        assert result["ok"] is True
        session_id = result["data"]["vault_session_id"]
        assert session_id is not None

        listing = vault_list()
        session_ids = [s["vault_id"] for s in listing["data"]]
        assert session_id in session_ids

        # Dry-run restore first: must not mutate
        peek = vault_restore(vault_id=session_id)
        assert peek["ok"] is False

        restored = vault_restore(vault_id=session_id, confirm=True)
        assert restored["ok"] is True
        assert restored["data"]["restored"] >= 1
        assert (workspace / "web" / "node_modules").exists()
