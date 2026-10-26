"""Command-line interface for purge - Developer bloat & zombie process reaper."""

import json
from pathlib import Path
from typing import List, Optional

import typer

from purge import __version__
from purge.core.cleaner import PurgeCleaner
from purge.core.scanner import DiskScanner
from purge.core.zombies import find_zombies, kill_zombie
from purge.ui.console import (
    console,
    print_banner,
    render_artifacts_table,
    render_clean_result,
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
        # Default behavior when running 'purge' with no args: run interactive scan
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
    zombies: bool = typer.Option(True, "--zombies/--no-zombies", help="Check for running zombie dev servers."),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Check for processes on a specific port."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Scan directory and running processes for developer bloat and port hogs."""
    categories: Optional[List[str]] = None
    if node or python or rust:
        categories = []
        if node:
            categories.append("Node.js & Web")
        if python:
            categories.append("Python")
        if rust:
            categories.append("Rust / Cargo")

    scanner = DiskScanner(categories=categories, min_stale_days=stale)
    report = scanner.scan(path)

    if zombies:
        report.zombies = find_zombies(target_port=port)

    if json_output:
        console.print_json(json.dumps(report.to_dict()))
        return

    print_banner()
    render_artifacts_table(report)
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
    node: bool = typer.Option(False, "--node", help="Only clean Node.js / Web artifacts."),
    python: bool = typer.Option(False, "--python", help="Only clean Python artifacts."),
    rust: bool = typer.Option(False, "--rust", help="Only clean Rust / Cargo artifacts."),
    stale: float = typer.Option(0.0, "--stale", help="Only clean artifacts untouched for at least N days."),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON."),
):
    """Purge discovered developer bloat and optionally slay zombie processes."""
    categories: Optional[List[str]] = None
    if node or python or rust:
        categories = []
        if node:
            categories.append("Node.js & Web")
        if python:
            categories.append("Python")
        if rust:
            categories.append("Rust / Cargo")

    scanner = DiskScanner(categories=categories, min_stale_days=stale)
    report = scanner.scan(path)

    zombies_to_kill = find_zombies() if kill_zombies_flag else []
    report.zombies = zombies_to_kill

    if not report.artifacts and not zombies_to_kill:
        if json_output:
            console.print_json(json.dumps({"reclaimed_bytes": 0, "message": "Nothing to clean"}))
        else:
            print_banner()
            console.print("[bold green]✨ Nothing to purge. Everything is lean and clean.[/]\n")
        return

    if not json_output:
        print_banner()
        render_artifacts_table(report)
        if zombies_to_kill:
            render_zombies_table(zombies_to_kill)
        render_scan_summary(report)

        if not force and not dry_run:
            confirm = typer.confirm(
                f"Are you sure you want to permanently purge {len(report.artifacts)} target(s) ({report.human_total_size})?"
            )
            if not confirm:
                console.print("[yellow]Purge operation aborted by user.[/]")
                raise typer.Exit(0)

    cleaner = PurgeCleaner(dry_run=dry_run, to_trash=trash)
    result = cleaner.purge(report.artifacts, zombies=zombies_to_kill)

    if json_output:
        console.print_json(json.dumps(result.to_dict()))
    else:
        render_clean_result(result, dry_run=dry_run)


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
            if kill_zombie(z.pid, force=True):
                slain += 1
                console.print(f"[bold red]☠️ Slayed zombie PID {z.pid}[/] [dim]({z.name} on port {z.port or 'n/a'})[/]")
        console.print(f"\n[bold green]✨ Successfully terminated {slain} zombie process(es).[/]\n")


def main():
    app()


if __name__ == "__main__":
    main()
