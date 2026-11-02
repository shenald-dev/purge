"""Command-line interface for purge - Developer bloat & zombie process reaper."""

import json
from pathlib import Path
from typing import List, Optional

import typer

from purge import __version__
from purge.core.cleaner import PurgeCleaner
from purge.core.config import load_config
from purge.core.history import get_lifetime_stats
from purge.core.models import Artifact, parse_size_to_bytes
from purge.core.scanner import DiskScanner
from purge.core.zombies import find_zombies, get_process_on_port, kill_zombie_tree
from purge.ui.console import (
    console,
    print_banner,
    render_artifacts_table,
    render_clean_result,
    render_global_caches_table,
    render_lifetime_stats,
    render_port_status,
    render_scan_summary,
    render_zombies_table,
)

app = typer.Typer(
    name="purge",
    help="🧹 Zero-latency developer bloat and zombie process reaper. Reclaim 50GB in 3 seconds.",
    add_completion=False,
    no_args_is_help=False,
)


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
    git_aware: bool = typer.Option(True, "--git-aware/--no-git-aware", help="Check for uncommitted git changes and commit age."),
    include_global: bool = typer.Option(False, "--global/--local", help="Include global package manager caches (npm, pip, uv, cargo)."),
    zombies: bool = typer.Option(True, "--zombies/--no-zombies", help="Check for running zombie dev servers."),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Check for processes on a specific port."),
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
    effective_git = git_aware if git_aware else config.git_aware

    scanner = DiskScanner(
        categories=categories,
        min_stale_days=effective_stale,
        min_size_bytes=min_size_bytes,
        git_aware=effective_git,
        custom_rules=config.custom_rules,
        ignore_paths=config.ignore_paths,
    )
    report = scanner.scan(path, max_depth=config.max_depth, include_global_caches=include_global)

    if zombies:
        report.zombies = find_zombies(target_port=port)

    if json_output or output_file:
        json_data = json.dumps(report.to_dict(), indent=2)
        if output_file:
            output_file.write_text(json_data, encoding="utf-8")
        if json_output:
            print(json_data)
            return

    print_banner()
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
    kill_zombies_flag: bool = typer.Option(False, "--kill-zombies", "-k", help="Also terminate detected zombie dev servers."),
    skip_uncommitted: bool = typer.Option(False, "--skip-uncommitted", help="Safeguard: skip repos with uncommitted git changes."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Selectively pick which artifacts to delete."),
    min_size: Optional[str] = typer.Option(None, "--min-size", help="Only clean artifacts larger than size (e.g. 50MB)."),
    node: bool = typer.Option(False, "--node", help="Only clean Node.js / Web artifacts."),
    python: bool = typer.Option(False, "--python", help="Only clean Python artifacts."),
    rust: bool = typer.Option(False, "--rust", help="Only clean Rust / Cargo artifacts."),
    stale: float = typer.Option(0.0, "--stale", help="Only clean artifacts untouched for at least N days."),
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

    scanner = DiskScanner(
        categories=categories,
        min_stale_days=effective_stale,
        min_size_bytes=min_size_bytes,
        git_aware=True,
        custom_rules=config.custom_rules,
        ignore_paths=config.ignore_paths,
    )
    report = scanner.scan(path, max_depth=config.max_depth)

    # Filter out uncommitted repositories if requested
    target_artifacts: List[Artifact] = report.artifacts
    if skip_uncommitted:
        target_artifacts = [a for a in target_artifacts if not a.has_uncommitted]
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
            confirm = typer.confirm(
                f"Are you sure you want to permanently purge {len(target_artifacts)} target(s) ({report.human_total_size})?"
            )
            if not confirm:
                console.print("[yellow]Purge operation aborted by user.[/]")
                raise typer.Exit(0)

    cleaner = PurgeCleaner(dry_run=dry_run, to_trash=trash or config.default_trash)
    result = cleaner.purge(target_artifacts, zombies=zombies_to_kill)

    if json_output:
        console.print_json(json.dumps(result.to_dict()))
    else:
        render_clean_result(result, dry_run=dry_run)


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


@app.command(name="init")
def init_command(
    path: Path = typer.Argument(Path("."), help="Target directory to create purge.toml."),
):
    """Initialize a starter purge.toml configuration file."""
    target_file = path / "purge.toml"
    if target_file.exists():
        console.print(f"[bold yellow]Configuration file {target_file} already exists.[/]")
        raise typer.Exit(0)

    starter_config = """# PURGE Configuration File
# Documentation: https://github.com/shenald-dev/purge

[purge]
max_depth = 10
min_stale_days = 0.0
min_size_bytes = 0
git_aware = true
default_trash = false
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
