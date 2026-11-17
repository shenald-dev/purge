"""End-to-end MCP protocol test: spawn the purge MCP server over stdio
and drive real tool calls through the official client SDK."""

import sys

import pytest

pytest.importorskip("mcp", reason="mcp SDK not installed")


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_stdio_end_to_end(tmp_path):
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    # Build a tiny workspace so scan returns real data
    web = tmp_path / "web"
    web.mkdir()
    (web / "package.json").write_text("{}", encoding="utf-8")
    nm = web / "node_modules"
    nm.mkdir()
    (nm / "pkg_a").write_text("z" * 500, encoding="utf-8")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from purge.mcp_server import mcp; mcp.run(transport='stdio')"],
    )

    async with Client(server_params) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "scan",
            "clean",
            "vault_restore",
            "server_info",
            "inspect_path",
            "kill_zombies",
        } <= tool_names

        result = await client.call_tool("server_info", {})
        payload = result.structured_content["result"]
        assert payload["ok"] is True
        assert payload["data"]["name"] == "purge"
        assert payload["data"]["version"].startswith("3.")

        scan_result = await client.call_tool("scan", {"root": str(tmp_path)})
        scan_payload = scan_result.structured_content["result"]
        assert scan_payload["ok"] is True
        assert scan_payload["data"]["total_artifacts"] >= 1

        # Safety: destructive tool refuses without confirm
        denied = await client.call_tool("clean", {"root": str(tmp_path)})
        denied_payload = denied.structured_content["result"]
        assert denied_payload["ok"] is False
        assert "confirm=True" in denied_payload["error"]
