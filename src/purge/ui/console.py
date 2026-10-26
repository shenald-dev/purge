"""Cyberpunk Rich terminal user interface for purge."""

import sys
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from purge.core.models import CleanResult, PurgeReport, ZombieProcess

# Windows UTF-8 encoding safeguard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

BANNER_ART = r"""
  ██████╗ ██╗   ██╗██████╗  ██████╗ ███████╗
  ██╔══██╗██║   ██║██╔══██╗██╔════╝ ██╔════╝
  ██████╔╝██║   ██║██████╔╝██║  ███╗█████╗
  ██╔═══╝ ██║   ██║██╔══██╗██║   ██║██╔══╝
  ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
  🧹 Developer Bloat & Zombie Process Reaper • Zero Bloat
"""


def print_banner():
    """Print glowing cyberpunk banner."""
    console.print(
        Panel(
            BANNER_ART.strip(),
            border_style="bright_magenta",
            subtitle="[dim cyan]v0.1.0 • https://github.com/shenald-dev/purge[/]",
        )
    )
    console.print()


def render_artifacts_table(report: PurgeReport, max_items: int = 50):
    """Render the table of discoverable bloat artifacts."""
    if not report.artifacts:
        console.print(
            Panel(
                "[bold green]✨ ZERO DEVELOPER BLOAT FOUND[/]\n\n"
                f"[dim]Scanned {report.scanned_dirs_count} directories in {report.duration_seconds:.2f}s.[/]\n"
                "Your workspace is 100% lean and pristine.",
                title="[bold green]STATUS: CLEAN[/]",
                border_style="green",
            )
        )
        return

    table = Table(
        title=f"[bold bright_magenta]📦 Reclaimable Bloat Targets ({len(report.artifacts)})[/]",
        border_style="bright_magenta",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Category", style="yellow", width=16)
    table.add_column("Path", style="white")
    table.add_column("Files", justify="right", style="dim", width=8)
    table.add_column("Stale", justify="right", style="dim cyan", width=10)
    table.add_column("Size", justify="right", style="bold green", width=12)

    for idx, a in enumerate(report.artifacts[:max_items], start=1):
        # Size styling
        if a.size_bytes >= 1024 * 1024 * 1024:  # >= 1GB
            size_str = f"[bold red]{a.human_size}[/]"
        elif a.size_bytes >= 100 * 1024 * 1024:  # >= 100MB
            size_str = f"[bold yellow]{a.human_size}[/]"
        else:
            size_str = f"[green]{a.human_size}[/]"

        stale_str = f"{int(a.days_stale)}d ago" if a.days_stale >= 1 else "Today"

        table.add_row(
            str(idx),
            a.category,
            str(a.path),
            str(a.file_count),
            stale_str,
            size_str,
        )

    if len(report.artifacts) > max_items:
        table.add_row(
            "...",
            "...",
            f"[dim italic]... and {len(report.artifacts) - max_items} more items[/]",
            "...",
            "...",
            "...",
        )

    console.print(table)
    console.print()


def render_zombies_table(zombies: List[ZombieProcess]):
    """Render the table of detected zombie developer processes."""
    if not zombies:
        return

    table = Table(
        title=f"[bold bright_red]🧟 Zombie Dev Servers & Port Hogs ({len(zombies)})[/]",
        border_style="red",
        header_style="bold red",
        show_lines=False,
    )
    table.add_column("PID", justify="right", style="dim", width=8)
    table.add_column("Name", style="bold white", width=14)
    table.add_column("Port", justify="center", style="bold cyan", width=10)
    table.add_column("Memory", justify="right", style="yellow", width=10)
    table.add_column("Command / Working Dir", style="dim")

    for z in zombies:
        port_str = f":{z.port}" if z.port else "—"
        mem_str = f"{z.memory_mb:.1f} MB"
        details = z.cwd or z.cmdline

        table.add_row(
            str(z.pid),
            z.name,
            port_str,
            mem_str,
            details,
        )

    console.print(table)
    console.print()


def render_scan_summary(report: PurgeReport):
    """Render summary telemetry radar card."""
    panel_text = Text()
    panel_text.append("Reclaimable Disk Space: ", style="bold")
    panel_text.append(f"{report.human_total_size}\n", style="bold bright_green")
    panel_text.append(f"• Total Targets: {len(report.artifacts)}    ", style="white")
    panel_text.append(f"• Total Files: {report.total_files:,}    ", style="dim")
    panel_text.append(f"• Zombie Servers: {len(report.zombies)}\n", style="bold bright_red" if report.zombies else "dim green")

    if report.category_breakdown:
        breakdown_parts = [
            f"{cat}: [bold]{from_bytes}[/]"
            for cat, from_bytes in [
                (c, a.human_size)
                for c in report.category_breakdown
                for a in [next(art for art in report.artifacts if art.category == c)]
            ][:4]
        ]
        panel_text.append("Breakdown: ", style="dim")
        panel_text.append(" | ".join(breakdown_parts) + "\n", style="dim yellow")

    panel_text.append(
        f"\nScanned {report.scanned_dirs_count} directories in {report.duration_seconds:.2f}s.",
        style="dim",
    )

    console.print(
        Panel(
            panel_text,
            title="[bold cyan]📊 PURGE REAPER TELEMETRY[/]",
            border_style="bright_magenta",
            padding=(1, 2),
        )
    )
    console.print()


def render_clean_result(result: CleanResult, dry_run: bool = False):
    """Render result of purge operation."""
    mode_tag = "[bold yellow][DRY-RUN SIMULATION][/] " if dry_run else ""
    title = f"{mode_tag}[bold green]✨ PURGE REAPER COMPLETED[/]"

    body = Text()
    body.append("Space Reclaimed: ", style="bold")
    body.append(f"{result.human_reclaimed_size}\n", style="bold bright_green")
    body.append(f"• Deleted Artifacts: {result.deleted_artifacts_count}\n", style="white")
    body.append(f"• Slayed Zombie Processes: {result.slain_zombies_count}\n", style="bold red" if result.slain_zombies_count else "dim")
    body.append(f"Operation finished in {result.duration_seconds:.2f}s.", style="dim")

    if result.errors:
        body.append(f"\n\n[bold red]Warnings / Errors ({len(result.errors)}):[/]\n")
        for err in result.errors[:5]:
            body.append(f" - {err}\n", style="dim red")

    console.print(
        Panel(
            body,
            title=title,
            border_style="green" if not dry_run else "yellow",
            padding=(1, 2),
        )
    )
    console.print()
