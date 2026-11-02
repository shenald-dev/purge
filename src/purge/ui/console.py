"""Cyberpunk Rich terminal user interface for purge."""

import sys
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from purge.core.models import Artifact, CleanResult, PurgeReport, ZombieProcess, format_bytes

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
            subtitle="[dim cyan]v1.0.0 • https://github.com/shenald-dev/purge[/]",
        )
    )
    console.print()


def render_artifacts_table(report: PurgeReport, max_items: int = 50):
    """Render the table of discoverable bloat artifacts with Git-aware intelligence."""
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
    table.add_column("Status / Git", justify="center", width=14)
    table.add_column("Stale", justify="right", style="dim cyan", width=10)
    table.add_column("Size", justify="right", style="bold green", width=12)

    for idx, a in enumerate(report.artifacts[:max_items], start=1):
        if a.size_bytes >= 1024 * 1024 * 1024:  # >= 1GB
            size_str = f"[bold red]{a.human_size}[/]"
        elif a.size_bytes >= 100 * 1024 * 1024:  # >= 100MB
            size_str = f"[bold yellow]{a.human_size}[/]"
        else:
            size_str = f"[green]{a.human_size}[/]"

        stale_str = f"{int(a.days_stale)}d ago" if a.days_stale >= 1 else "Today"

        status_str = "[dim]Clean[/]"
        if a.has_uncommitted:
            status_str = "[bold yellow]⚠️ Uncommitted[/]"
        elif a.is_git_repo and a.days_since_commit > 0:
            status_str = f"[dim cyan]git: {int(a.days_since_commit)}d ago[/]"

        table.add_row(
            str(idx),
            a.category,
            str(a.path),
            str(a.file_count),
            status_str,
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
            "...",
        )

    console.print(table)
    console.print()


def render_global_caches_table(caches: List[Artifact]):
    """Render table of global package manager caches."""
    if not caches:
        return

    table = Table(
        title=f"[bold bright_cyan]🌐 Global Developer Package Caches ({len(caches)})[/]",
        border_style="cyan",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Ecosystem", style="bold yellow", width=18)
    table.add_column("Cache Location", style="white")
    table.add_column("Description", style="dim")
    table.add_column("Files", justify="right", style="dim", width=8)
    table.add_column("Size", justify="right", style="bold green", width=12)

    for idx, c in enumerate(caches, start=1):
        size_str = (
            f"[bold red]{c.human_size}[/]"
            if c.size_bytes >= 1024 * 1024 * 1024
            else f"[bold yellow]{c.human_size}[/]"
        )
        table.add_row(
            str(idx),
            c.category.replace("Global Cache: ", ""),
            str(c.path),
            c.description or "",
            f"{c.file_count:,}",
            size_str,
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
    table.add_column("Trees", justify="right", style="dim", width=6)
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
            str(z.children_count),
            details,
        )

    console.print(table)
    console.print()


def render_port_status(port: int, process: ZombieProcess | None):
    """Render status card for a specific port query."""
    if process:
        body = Text()
        body.append(f"Port :{port} is OCCUPIED by ", style="bold red")
        body.append(f"{process.name} (PID {process.pid})\n\n", style="bold white")
        body.append(f"• URL: {process.url}\n", style="bold cyan")
        body.append(f"• Memory: {process.memory_mb:.1f} MB    • CPU: {process.cpu_percent:.1f}%\n", style="yellow")
        body.append(f"• Child Processes: {process.children_count}\n", style="dim")
        if process.cwd:
            body.append(f"• Working Dir: {process.cwd}\n", style="white")
        body.append(f"• Command: {process.cmdline}\n", style="dim")

        console.print(
            Panel(
                body,
                title=f"[bold red]🚨 PORT :{port} OCCUPIED[/]",
                border_style="red",
                padding=(1, 2),
            )
        )
    else:
        console.print(
            Panel(
                f"[bold green]✔ Port :{port} is completely FREE and available for use.[/]",
                title=f"[bold green]PORT :{port} AVAILABLE[/]",
                border_style="green",
                padding=(1, 2),
            )
        )
    console.print()


def render_scan_summary(report: PurgeReport):
    """Render summary telemetry radar card."""
    panel_text = Text()
    panel_text.append("Reclaimable Disk Space: ", style="bold")
    panel_text.append(f"{report.human_total_size}\n", style="bold bright_green")
    panel_text.append(f"• Total Targets: {len(report.artifacts)}    ", style="white")
    panel_text.append(f"• Total Files: {report.total_files:,}    ", style="dim")
    panel_text.append(
        f"• Zombie Servers: {len(report.zombies)}\n",
        style="bold bright_red" if report.zombies else "dim green",
    )

    if report.uncommitted_repos_count > 0:
        panel_text.append(
            f"• ⚠️ Repos with Uncommitted Changes: {report.uncommitted_repos_count}\n",
            style="bold yellow",
        )

    if report.category_breakdown:
        breakdown_parts = [
            f"{cat}: [bold]{format_bytes(bytes_count)}[/]"
            for cat, bytes_count in sorted(
                report.category_breakdown.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]
        panel_text.append("Breakdown: ", style="dim")
        panel_text.append(" | ".join(breakdown_parts) + "\n", style="dim yellow")

    panel_text.append(
        f"\nScanned {report.scanned_dirs_count} directories in {report.duration_seconds:.3f}s.",
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
    body.append(
        f"• Slayed Zombie Processes: {result.slain_zombies_count}\n",
        style="bold red" if result.slain_zombies_count else "dim",
    )
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


def render_lifetime_stats(stats: Dict[str, Any]):
    """Render cumulative lifetime reclamation telemetry card."""
    body = Text()
    body.append("Lifetime Reclaimed Space: ", style="bold")
    body.append(f"{stats.get('human_total_reclaimed', '0 B')}\n\n", style="bold bright_green")
    body.append(f"• Total Purge Operations: {stats.get('total_purges_run', 0)}\n", style="white")
    body.append(f"• Total Artifacts Slayed: {stats.get('total_artifacts_deleted', 0)}\n", style="cyan")
    body.append(f"• Total Zombie Servers Slayed: {stats.get('total_zombies_slayed', 0)}\n", style="red")

    recent = stats.get("recent_events", [])
    if recent:
        body.append("\nRecent Purge Cycles:\n", style="bold yellow")
        for ev in recent[:5]:
            ts = ev.get("timestamp", "").split("T")[0]
            reclaimed = ev.get("human_reclaimed", "0 B")
            body.append(f"  • {ts}: Reclaimed {reclaimed} ({ev.get('artifacts_count', 0)} targets)\n", style="dim")

    console.print(
        Panel(
            body,
            title="[bold bright_magenta]🏆 LIFETIME PURGE RECLAMATION TELEMETRY[/]",
            border_style="bright_magenta",
            padding=(1, 2),
        )
    )
    console.print()
