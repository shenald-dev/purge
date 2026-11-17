"""Native Model Context Protocol server for purge.

Exposes purge's reclamation intelligence (scan, scoring, inspection,
cleaning, quarantine vault, zombie hunting, telemetry) as MCP tools so
any MCP host (Claude Desktop, IDE agents, CI bots) can drive disk
hygiene programmatically.

Transport: stdio by default. Requires the optional ``mcp`` extra
(``pip install purge-reaper[mcp]``, Python 3.11+).

Safety model:
- Every destructive tool defaults to dry-run; callers must pass an
  explicit ``confirm=True`` flag to execute real deletions.
- Paths are resolved and validated against protected system roots
  before any operation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from purge import __version__
from purge.core.api import PurgeEngine

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - guarded at CLI boundary
    raise ImportError(
        "The MCP server requires the optional 'mcp' package. "
        "Install it with: pip install 'purge-reaper[mcp]' (Python 3.11+)."
    ) from exc


mcp = MCPServer("purge")


def _engine(root: Optional[str] = None) -> PurgeEngine:
    """Build an engine rooted at the requested directory."""
    return PurgeEngine(root_path=Path(root) if root else None)


def _ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def _err(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": message}


def _require_confirm(confirm: bool, action: str) -> Optional[Dict[str, Any]]:
    """Return an error payload unless the caller explicitly confirmed."""
    if not confirm:
        return _err(
            f"Refusing to {action}: pass confirm=True to execute. "
            "This tool is dry-run by default."
        )
    return None


def _validate_root(path: str) -> Optional[Dict[str, Any]]:
    """Reject protected system roots before any tool touches them."""
    from purge.core.rules import is_protected_path

    candidate = Path(path)
    if is_protected_path(candidate, allow_home=False):
        return _err(f"Refusing to operate on protected system path: {path}")
    return None


@mcp.tool()
def scan(
    root: Optional[str] = None,
    categories: Optional[List[str]] = None,
    min_size: Optional[str] = None,
    min_score: Optional[float] = None,
    min_stale_days: Optional[float] = None,
    top: Optional[int] = None,
    git_aware: bool = True,
    include_global_caches: bool = False,
    sort_by: str = "size",
) -> Dict[str, Any]:
    """Scan a directory tree for reclaimable developer bloat.

    Returns artifacts with size, file counts, staleness, purge score
    (0-100 priority index), safety level, and git state. Read-only.
    """
    try:
        report = _engine(root).scan(
            path=Path(root) if root else None,
            categories=categories,
            min_size=min_size,
            min_score=min_score,
            min_stale_days=min_stale_days,
            top=top,
            git_aware=git_aware,
            include_global_caches=include_global_caches,
            sort_by=sort_by,
        )
        return _ok(report.to_dict())
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001 - surface any failure to the host
        return _err(f"Scan failed: {exc}")


@mcp.tool()
def inspect_path(path: str) -> Dict[str, Any]:
    """Inspect one artifact candidate (e.g. a node_modules folder).

    Reports size, staleness, category, purge score, and safety level
    without scanning a whole tree. Read-only.
    """
    try:
        guard = _validate_root(path)
        if guard:
            return guard
        return _ok(_engine(Path(path).parent).inspect(Path(path)))
    except Exception as exc:
        return _err(f"Inspect failed: {exc}")


@mcp.tool()
def clean(
    root: Optional[str] = None,
    min_score: Optional[float] = None,
    min_size: Optional[str] = None,
    min_stale_days: Optional[float] = None,
    categories: Optional[List[str]] = None,
    skip_uncommitted: bool = True,
    auto_min_score: Optional[float] = 65.0,
    mode: str = "delete",
    confirm: bool = False,
) -> Dict[str, Any]:
    """Purge discovered developer bloat.

    DANGEROUS: default is dry-run. Pass confirm=True to execute.
    mode: 'delete' (permanent), 'vault' (quarantine, reversible),
    or 'trash' (send2trash, requires purge-reaper[trash]).
    skip_uncommitted defaults to True: repos with uncommitted work are
    never touched unless explicitly disabled.
    """
    action = f"clean '{root or Path.cwd()}' in {mode} mode"
    guard = _require_confirm(confirm, action)
    if guard:
        return guard

    root_path = Path(root) if root else None
    if root_path is not None:
        guard = _validate_root(str(root_path))
        if guard:
            return guard

    engine = _engine(root)
    try:
        result = engine.clean(
            path=root_path,
            scan_kwargs={
                "categories": categories,
                "min_score": min_score,
                "min_size": min_size,
                "min_stale_days": min_stale_days,
            },
            dry_run=not confirm,
            to_vault=(mode == "vault"),
            to_trash=(mode == "trash"),
            skip_uncommitted=skip_uncommitted,
            auto_min_score=auto_min_score,
        )
        payload = result.to_dict()
        if not confirm:
            payload["note"] = "Dry-run only: nothing was deleted."
        return _ok(payload)
    except Exception as exc:
        return _err(f"Clean failed: {exc}")


@mcp.tool()
def kill_zombies(
    port: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Terminate zombie dev servers / port hog process trees.

    DANGEROUS: default is dry-run listing. Pass confirm=True to kill.
    With port=None, lists every listening dev port and matching process.
    """
    guard = _require_confirm(confirm, f"kill zombie processes (port={port})")
    if guard:
        return guard

    engine = _engine()
    try:
        if not confirm:
            zombies = engine.find_zombies(target_port=port)
            return _ok({"dry_run": True, "zombies": [z.to_dict() for z in zombies]})

        zombies = engine.find_zombies(target_port=port)
        slain = 0
        for z in zombies:
            if engine.kill_zombie_tree(z.pid) > 0:
                slain += 1
        return _ok({"slain": slain, "total": len(zombies)})
    except Exception as exc:
        return _err(f"Zombie hunt failed: {exc}")


@mcp.tool()
def port_status(port: int) -> Dict[str, Any]:
    """Report which process is listening on a port. Read-only."""
    try:
        proc = _engine().get_process_on_port(port)
        return _ok(proc.to_dict() if proc else {"port": port, "status": "free"})
    except Exception as exc:
        return _err(f"Port lookup failed: {exc}")


@mcp.tool()
def vault_list() -> Dict[str, Any]:
    """List quarantine vault sessions (reversible purges). Read-only."""
    try:
        sessions = _engine().vault_list_sessions()
        return _ok([s.to_dict() for s in sessions])
    except Exception as exc:
        return _err(f"Vault listing failed: {exc}")


@mcp.tool()
def vault_show(vault_id: str) -> Dict[str, Any]:
    """Show details of one vault session. Read-only."""
    try:
        session = _engine().vault_get_session(vault_id)
        if not session:
            return _err(f"Vault session '{vault_id}' not found")
        return _ok(session.to_dict())
    except Exception as exc:
        return _err(f"Vault lookup failed: {exc}")


@mcp.tool()
def vault_restore(
    vault_id: str,
    item_index: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Restore quarantined artifacts back to their original paths.

    DANGEROUS: default is dry-run. Pass confirm=True to restore.
    """
    guard = _require_confirm(confirm, f"restore vault session '{vault_id}'")
    if guard:
        return guard

    try:
        if not confirm:
            session = _engine().vault_get_session(vault_id)
            if not session:
                return _err(f"Vault session '{vault_id}' not found")
            items = (
                [session.items[item_index - 1]]
                if item_index is not None and 1 <= item_index <= len(session.items)
                else session.items
            )
            return _ok({
                "dry_run": True,
                "would_restore": len(items),
                "total_bytes": sum(i.size_bytes for i in items),
            })

        count, byte_count, errors = _engine().vault_restore(vault_id, item_index=item_index)
        return _ok({"restored": count, "restored_bytes": byte_count, "errors": errors})
    except Exception as exc:
        return _err(f"Vault restore failed: {exc}")


@mcp.tool()
def stats() -> Dict[str, Any]:
    """Lifetime reclamation telemetry (bytes reclaimed, zombies slain). Read-only."""
    try:
        return _ok(_engine().stats())
    except Exception as exc:
        return _err(f"Stats failed: {exc}")


@mcp.tool()
def server_info() -> Dict[str, Any]:
    """Report purge version and capability summary. Read-only."""
    return _ok({
        "name": "purge",
        "version": __version__,
        "capabilities": [
            "scan",
            "inspect_path",
            "clean",
            "kill_zombies",
            "port_status",
            "vault_list",
            "vault_show",
            "vault_restore",
            "stats",
        ],
        "safety": "destructive tools require explicit confirm=True; default dry-run",
    })


def serve(transport: str = "stdio", host: Optional[str] = None, port: Optional[int] = None) -> None:
    """Run the purge MCP server over the requested transport."""
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "streamable-http":
        mcp.run(transport="streamable-http", host=host or "127.0.0.1", port=port or 8000)
    else:
        raise ValueError(f"Unsupported transport: {transport!r} (use 'stdio' or 'streamable-http')")
