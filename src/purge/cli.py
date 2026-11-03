"""Command-line interface for purge - Developer bloat & zombie process reaper."""

import json
from pathlib import Path
from typing import List, Optional

import typer

from purge import __version__
from purge.core.cleaner import PurgeCleaner
from purge.core.config import load_config
from purge.core.disk import get_partition_for_path
from purge.core.exporter import export_to_csv, export_to_markdown, save_export
from purge.core.history import get_lifetime_stats
from purge.core.models import Artifact, parse_size_to_bytes
from purge.core.scanner import DiskScanner
from purge.core.vault import QuarantineVault
from purge.core.zombies import find_zombies, get_process_on_port, kill_zombie_tree
from purge.ui.console import (
    console,
    print_banner,
    render_artifacts_table,
    render_clean_result,
    render_disk_status,
    render_global_caches_table,
    render_lifetime_stats,
    render_port_status,
    render_scan_summary,
    render_vault_details,
    render_vault_sessions_table,
    render_zombies_table,
)

app = typer.Typer(
    name="purge",
    help="🧹 Zero-latency developer bloat and zombie process reaper. Reclaim 50GB in 3 seconds.",
    add_completion=False,
    no_args_is_help=False,
)

vault_app = typer.Typer(
    name="vault",
    help="🛡️ Quarantine vault and safe undo engine. Safely stage and restore pruned artifacts.",
    no_args_is_help=True,
)
app.add_typer(vault_app, name="vault")


def version_callback(value: bool):
    if value:
        console.print(f"[bold bright_magenta]purge[/] version [bold cyan]{__version__}[/]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
):
    if ctx.invoked_subcommand is None:
        scan(Path("."))


@app.command(name="scan")
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Target root directory to scan for developer bloat.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    node: bool = typer.Option(False, "--node", help="Only scan for Node.js / Web bloat (node_modules, .next, etc.)."),
    python: bool = typer.Option(False, "--python", help="Only scan for Python bloat (.venv, __pycache__, etc.)."),
    rust: bool = typer.Option(False, "--rust", help="Only scan for Rust / Cargo bloat (target/)."),
    stale: float = typer.Option(0.0, "--stale", help="Only flag artifacts untouched for at least N days."),
    min_size: Optional[str] = typer.Option(None, "--min-size", help="Filter artifacts larger than size (e.g. 50MB, 1GB)."),
    min_score: float = typer.Option(0.0, "--min-score", help="Filter artifacts with Purge Score >= N (0-100)."),
    sort: str = typer.Option("size", "--sort", help="Sort artifacts by: size, score, stale, or name."),
    top: Optional[int] = typer.Option(None, "--top", help="Limit results to top N largest or highest-scoring targets."),
    git_aware: bool = typer.Option(True, "--git-aware/--no-git-aware", help="Check for uncommitted git changes and commit age."),
    include_global: bool = typer.Option(False, "--global/--local", help="Include global package manager caches (npm, pip, uv, cargo)."),
    zombies: bool = typer.Option(True, "--zombies/--no-zombies", help="Check for running zombie dev servers."),
    disk: bool = typer.Option(False, "--disk", help="Display drive capacity and bloat radar percentage."),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Check for processes on a specific port."),
    format_type: str = typer.Option("terminal", "--format", help="Output format: terminal, json, markdown, csv."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Save report to destination file."),
):
    """Scan directory, global caches, and running processes for developer bloat and port hogs."""
    config = load_config(path)

    categories: Optional[List[str]] = config.categories
    if node or python or rust:
        categories = []
        if node:
            categories.append("Node.js & Web")
        if python:
            categories.append("Python")
        if rust:
            categories.append("Rust / Cargo")

    min_size_bytes = parse_size_to_bytes(min_size) if min_size else config.min_size_bytes
    effective_stale = stale if stale > 0.0 else config.min_stale_days
    effective_score = min_score if min_score > 0.0 else config.min_score
    effective_git = git_aware if git_aware else config.git_aware
    sort_strategy = sort if sort != "size" else config.sort_by

    scanner = DiskScanner(
        categories=categories,
        min_stale_days=effective_stale,
        min_size_bytes=min_size_bytes,
        min_score=effective_score,
        sort_by=sort_strategy,
        top=top,
        git_aware=effective_git,
        custom_rules=config.custom_rules,
        ignore_paths=config.ignore_paths,
    )
    report = scanner.scan(path, max_depth=config.max_depth, include_global_caches=include_global)

    if zombies:
        report.zombies = find_zombies(target_port=port)

    # Save to file if requested
    if output_file:
        save_export(report, output_file, export_format=format_type if format_type != "terminal" else None)

    # Formatted non-terminal outputs
    fmt = "json" if json_output else format_type.lower()
    if fmt == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return
    elif fmt in ("md", "markdown"):
        print(export_to_markdown(report))
        return
    elif fmt == "csv":
        print(export_to_csv(report))
        return

    # Terminal UI output
    print_banner()

    if disk:
        part = get_partition_for_path(path, bloat_bytes=report.total_bytes)
        if part:
            render_disk_status(part)

    render_artifacts_table(report)
    if report.global_caches:
        render_global_caches_table(report.global_caches)
    if report.zombies:
        render_zombies_table(report.zombies)
    render_scan_summary(report)


@app.command(name="clean")
def clean(
    path: Path = typer.Argument(
        Path("."),
        help="Target root directory to clean.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate deletion without removing any files."),
    force: bool = typer.Option(False, "--force", "-y", help="Bypass interactive confirmation prompt."),
    trash: bool = typer.Option(False, "--trash", help="Move files to Recycle Bin / Trash instead of permanent deletion."),
    vault: bool = typer.Option(False, "--vault", "-v", help="Quarantine to local undo vault (~/.config/purge/vault) instead of permanent deletion."),
    auto: bool = typer.Option(False, "--auto", help="Autonomous mode: automatically select high-scoring targets (Score >= 65) without manual picking."),
    kill_zombies_flag: bool = typer.Option(False, "--kill-zombies", "-k", help="Also terminate detected zombie dev servers."),
    skip_uncommitted: bool = typer.Option(False, "--skip-uncommitted", help="Safeguard: skip repos with uncommitted git changes."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Selectively pick which artifacts to delete."),
    min_size: Optional[str] = typer.Option(None, "--min-size", help="Only clean artifacts larger than size (e.g. 50MB)."),
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Only clean artifacts with Purge Score >= N (0-100)."),
    node: bool = typer.Option(False, "--node", help="Only clean Node.js / Web artifacts."),
    python: bool = typer.Option(False, "--python", help="Only clean Python artifacts."),
    rust: bool = typer.Option(False, "--rust", help="Only clean Rust / Cargo artifacts."),
    stale: float = typer.Option(0.0, "--stale", help="Only clean artifacts untouched for at least N days."),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of concurrent worker threads for deletion."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Purge discovered developer bloat and optionally slay zombie processes."""
    config = load_config(path)

    categories: Optional[List[str]] = config.categories
    if node or python or rust:
        categories = []
        if node:
            categories.append("Node.js & Web")
        if python:
            categories.append("Python")
        if rust:
            categories.append("Rust / Cargo")

    min_size_bytes = parse_size_to_bytes(min_size) if min_size else config.min_size_bytes
    effective_stale = stale if stale > 0.0 else config.min_stale_days
    effective_score = min_score if min_score is not None else config.min_score

    scanner = DiskScanner(
        categories=categories,
        min_stale_days=effective_stale,
        min_size_bytes=min_size_bytes,
        min_score=effective_score,
        git_aware=True,
        custom_rules=config.custom_rules,
        ignore_paths=config.ignore_paths,
    )
    report = scanner.scan(path, max_depth=config.max_depth)

    # Filter out uncommitted repositories if requested
    target_artifacts: List[Artifact] = report.artifacts
    if skip_uncommitted:
        target_artifacts = [a for a in target_artifacts if not a.has_uncommitted]

    # Auto mode: filter high-scoring items (score >= 65 and safe)
    if auto:
        target_artifacts = [
            a for a in target_artifacts
            if getattr(a, "purge_score", 0.0) >= (min_score or 65.0) and not a.has_uncommitted
        ]

    report.artifacts = target_artifacts
    zombies_to_kill = find_zombies() if kill_zombies_flag else []
    report.zombies = zombies_to_kill

    if not target_artifacts and not zombies_to_kill:
        if json_output:
            console.print_json(json.dumps({"reclaimed_bytes": 0, "message": "Nothing to clean"}))
        else:
            print_banner()
            console.print("[bold green]✨ Nothing to purge. Everything is lean and clean.[/]\n")
        return

    # Interactive item selection mode
    if interactive and not force and not json_output:
        print_banner()
        render_artifacts_table(report)
        console.print("[bold cyan]Enter comma-separated item numbers to delete (e.g. '1, 3, 5'), or 'all':[/]")
        choice = typer.prompt("Select items to purge", default="all").strip()
        if choice.lower() != "all":
            try:
                selected_indices = [int(i.strip()) for i in choice.split(",") if i.strip().isdigit()]
                target_artifacts = [
                    art for idx, art in enumerate(report.artifacts, start=1)
                    if idx in selected_indices
                ]
                report.artifacts = target_artifacts
            except Exception:
                console.print("[red]Invalid selection. Aborting purge.[/]")
                raise typer.Exit(1)

    if not json_output:
        print_banner()
        render_artifacts_table(report)
        if zombies_to_kill:
            render_zombies_table(zombies_to_kill)
        render_scan_summary(report)

        if not force and not dry_run:
            action_desc = "quarantine to vault" if vault or config.default_vault else "permanently purge"
            confirm = typer.confirm(
                f"Are you sure you want to {action_desc} {len(target_artifacts)} target(s) ({report.human_total_size})?"
            )
            if not confirm:
                console.print("[yellow]Purge operation aborted by user.[/]")
                raise typer.Exit(0)

    cleaner = PurgeCleaner(
        dry_run=dry_run,
        to_trash=trash or config.default_trash,
        to_vault=vault or config.default_vault,
        workers=workers or config.workers,
    )
    result = cleaner.purge(target_artifacts, zombies=zombies_to_kill)

    if json_output:
        console.print_json(json.dumps(result.to_dict()))
    else:
        render_clean_result(result, dry_run=dry_run)


@app.command(name="disk")
@app.command(name="top")
def disk_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target root directory or drive mount point to inspect.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Disk capacity radar & top developer bloat footprint analyzer."""
    scanner = DiskScanner(git_aware=False)
    report = scanner.scan(path, max_depth=5)
    partition = get_partition_for_path(path, bloat_bytes=report.total_bytes)

    if json_output:
        data = {
            "partition": partition.to_dict() if partition else None,
            "report_summary": report.to_dict(),
        }
        console.print_json(json.dumps(data))
        return

    print_banner()
    if partition:
        render_disk_status(partition)
    render_artifacts_table(report, max_items=15)
    render_scan_summary(report)


@app.command(name="export")
def export_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target directory to audit and export.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Destination file path (.md, .csv, or .json)."),
    format_type: Optional[str] = typer.Option(None, "--format", "-f", help="Format: markdown, csv, json."),
):
    """Audit project and export formatted report directly to Markdown, CSV, or JSON."""
    scanner = DiskScanner(git_aware=True)
    report = scanner.scan(path)
    saved_path = save_export(report, output, export_format=format_type)
    console.print(f"[bold green]✔ Successfully exported purge audit report to {saved_path}[/]")


@app.command(name="port")
@app.command(name="free")
def port_command(
    port_number: int = typer.Argument(..., help="Port number to inspect or free (e.g. 3000, 8080)."),
    kill: bool = typer.Option(False, "--kill", "-k", help="Kill the process and all child trees occupying this port."),
    force: bool = typer.Option(False, "--force", "-y", help="Bypass confirmation prompt when killing."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Instant one-shot port inspector & tree-killing reaper. Free port 3000 in one command."""
    proc = get_process_on_port(port_number)

    if json_output:
        console.print_json(json.dumps(proc.to_dict() if proc else {"port": port_number, "status": "free"}))
        return

    print_banner()
    render_port_status(port_number, proc)

    if proc and kill:
        if not force:
            confirm = typer.confirm(f"Terminate process '{proc.name}' (PID {proc.pid}) and all its child trees?")
            if not confirm:
                console.print("[yellow]Operation aborted by user.[/]")
                raise typer.Exit(0)

        slain = kill_zombie_tree(proc.pid, force=True)
        if slain > 0:
            console.print(f"[bold green]✔ Successfully slayed PID {proc.pid} ({slain} total processes in tree). Port :{port_number} is now FREE![/]\n")
        else:
            console.print(f"[bold red]❌ Failed to terminate PID {proc.pid}. Try running with elevated permissions.[/]\n")


@app.command(name="zombies")
def zombies(
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Target a specific port (e.g. 3000)."),
    kill: bool = typer.Option(False, "--kill", "-k", help="Kill detected zombie dev server processes."),
    force: bool = typer.Option(False, "--force", "-y", help="Skip confirmation when killing."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Scan and slay zombie background developer processes and port hogs."""
    zombie_list = find_zombies(target_port=port)

    if json_output:
        console.print_json(json.dumps([z.to_dict() for z in zombie_list]))
        return

    print_banner()
    if not zombie_list:
        console.print("[bold green]✨ No zombie developer processes or port hogs detected.[/]\n")
        return

    render_zombies_table(zombie_list)

    if kill:
        if not force:
            confirm = typer.confirm(f"Terminate {len(zombie_list)} zombie process(es)?")
            if not confirm:
                console.print("[yellow]Termination aborted by user.[/]")
                raise typer.Exit(0)

        slain = 0
        for z in zombie_list:
            if kill_zombie_tree(z.pid, force=True) > 0:
                slain += 1
                console.print(f"[bold red]☠️ Slayed zombie PID {z.pid}[/] [dim]({z.name} on port {z.port or 'n/a'})[/]")
        console.print(f"\n[bold green]✨ Successfully terminated {slain} zombie process tree(s).[/]\n")


@app.command(name="cache")
def cache_command(
    clean_flag: bool = typer.Option(False, "--clean", "-c", help="Prune the discovered global package caches."),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate deletion without removing files."),
    force: bool = typer.Option(False, "--force", "-y", help="Skip confirmation prompt when cleaning."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Scan and prune global developer package manager caches (npm, pip, uv, cargo, etc.)."""
    scanner = DiskScanner()
    caches = scanner.scan_global_caches()

    if json_output:
        console.print_json(json.dumps([c.to_dict() for c in caches]))
        return

    print_banner()
    if not caches:
        console.print("[bold green]✨ No global developer caches found. Caches are clean.[/]\n")
        return

    render_global_caches_table(caches)
    total_size = sum(c.size_bytes for c in caches)
    from purge.core.models import format_bytes
    console.print(f"[bold bright_green]Total Global Cache Footprint: {format_bytes(total_size)}[/]\n")

    if clean_flag:
        if not force and not dry_run:
            confirm = typer.confirm(f"Are you sure you want to clean all {len(caches)} global package caches ({format_bytes(total_size)})?")
            if not confirm:
                console.print("[yellow]Cache cleaning aborted by user.[/]")
                raise typer.Exit(0)

        cleaner = PurgeCleaner(dry_run=dry_run)
        result = cleaner.purge(caches)
        render_clean_result(result, dry_run=dry_run)


@app.command(name="stats")
def stats_command(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Display cumulative lifetime disk space reclamation telemetry."""
    stats = get_lifetime_stats()

    if json_output:
        console.print_json(json.dumps(stats))
        return

    print_banner()
    render_lifetime_stats(stats)


# --- Quarantine Vault Commands ---


@vault_app.command(name="list")
def vault_list(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """List all available quarantine vault sessions."""
    vault = QuarantineVault()
    sessions = vault.list_sessions()

    if json_output:
        console.print_json(json.dumps([s.to_dict() for s in sessions]))
        return

    print_banner()
    render_vault_sessions_table(sessions)


@vault_app.command(name="show")
def vault_show(
    vault_id: str = typer.Argument(..., help="Vault session ID to inspect (e.g. vault_20261103_120000)."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Show detailed list of quarantined artifacts in a vault session."""
    vault = QuarantineVault()
    session = vault.get_session(vault_id)

    if not session:
        if json_output:
            console.print_json(json.dumps({"error": f"Session '{vault_id}' not found"}))
        else:
            console.print(f"[bold red]❌ Vault session '{vault_id}' not found.[/]")
        raise typer.Exit(1)

    if json_output:
        console.print_json(json.dumps(session.to_dict()))
        return

    print_banner()
    render_vault_details(session)


@vault_app.command(name="restore")
def vault_restore(
    vault_id: str = typer.Argument(..., help="Vault session ID to restore."),
    item: Optional[int] = typer.Option(None, "--item", "-i", help="Specific 1-based item index to restore (restores all if omitted)."),
    force: bool = typer.Option(False, "--force", "-y", help="Bypass confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Restore quarantined artifacts back to their original disk locations."""
    vault = QuarantineVault()
    session = vault.get_session(vault_id)

    if not session:
        console.print(f"[bold red]❌ Vault session '{vault_id}' not found.[/]")
        raise typer.Exit(1)

    if not force and not json_output:
        print_banner()
        render_vault_details(session)
        target_desc = f"item #{item}" if item is not None else f"all {len(session.items)} items"
        confirm = typer.confirm(f"Are you sure you want to restore {target_desc} back to disk?")
        if not confirm:
            console.print("[yellow]Restoration aborted by user.[/]")
            raise typer.Exit(0)

    restored_count, restored_bytes, errors = vault.restore_session(vault_id, item_index=item)

    if json_output:
        data = {
            "vault_id": vault_id,
            "restored_count": restored_count,
            "restored_bytes": restored_bytes,
            "errors": errors,
        }
        console.print_json(json.dumps(data))
        return

    from purge.core.models import format_bytes
    if restored_count > 0:
        console.print(
            f"[bold green]✔ Successfully restored {restored_count} artifact(s) ({format_bytes(restored_bytes)}) back to disk![/]\n"
        )
    if errors:
        for err in errors:
            console.print(f"[bold red]❌ Error: {err}[/]")


@vault_app.command(name="prune")
def vault_prune(
    days: float = typer.Option(14.0, "--days", "-d", help="Prune quarantine sessions older than N days."),
    vault_id: Optional[str] = typer.Option(None, "--vault-id", help="Target a specific vault session ID to prune immediately."),
    force: bool = typer.Option(False, "--force", "-y", help="Bypass confirmation prompt."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Permanently delete old quarantine sessions to reclaim disk space."""
    vault = QuarantineVault()
    if not force and not json_output:
        target_desc = f"session '{vault_id}'" if vault_id else f"sessions older than {days} days"
        confirm = typer.confirm(f"Permanently delete quarantine {target_desc}?")
        if not confirm:
            console.print("[yellow]Pruning aborted by user.[/]")
            raise typer.Exit(0)

    deleted_count, reclaimed_bytes = vault.prune_vault(older_than_days=days, vault_id=vault_id)

    if json_output:
        console.print_json(json.dumps({"deleted_sessions": deleted_count, "reclaimed_bytes": reclaimed_bytes}))
        return

    from purge.core.models import format_bytes
    console.print(
        f"[bold green]✔ Pruned {deleted_count} vault session(s), permanently freeing {format_bytes(reclaimed_bytes)}.[/]\n"
    )


@app.command(name="init")
def init_command(
    path: Path = typer.Argument(Path("."), help="Target directory to create purge.toml."),
):
    """Initialize a starter purge.toml configuration file."""
    target_file = path / "purge.toml"
    if target_file.exists():
        console.print(f"[bold yellow]Configuration file {target_file} already exists.[/]")
        raise typer.Exit(0)

    starter_config = """# PURGE Configuration File (v2.0)
# Documentation: https://github.com/shenald-dev/purge

[purge]
max_depth = 10
min_stale_days = 0.0
min_size_bytes = 0
min_score = 0.0
sort_by = "size"
workers = 4
git_aware = true
default_trash = false
default_vault = false
default_format = "terminal"

# Ignored paths or repositories
ignore_paths = [
    # "critical-project/*",
]

# Custom artifact target rules
[purge.custom_rules]
# "My Team Cache" = [".custom_cache", "temp_build"]
"""
    target_file.write_text(starter_config, encoding="utf-8")
    console.print(f"[bold green]✔ Initialized starter configuration at {target_file}[/]")


def main():
    app()


if __name__ == "__main__":
    main()
