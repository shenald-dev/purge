"""Audit report exporter for purge.

Exports scan and clean telemetry to Markdown, CSV, and JSON for
developer documentation, team reporting, and CI/CD pipelines.
"""

import csv
import io
import json
from pathlib import Path
from typing import Optional

from purge.core.models import PurgeReport, format_bytes


def export_to_markdown(report: PurgeReport, title: str = "Purge Developer Bloat Audit Report") -> str:
    """Generate a GitHub Flavored Markdown audit report from a PurgeReport."""
    lines = [
        f"# {title}",
        "",
        f"**Target Root Path:** `{report.scan_path}`  ",
        f"**Scan Duration:** `{report.duration_seconds:.3f}s`  ",
        f"**Directories Traversed:** `{report.scanned_dirs_count:,}`  ",
        "",
        "## 📊 Executive Summary",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Total Reclaimable Space** | **`{report.human_total_size}`** |",
        f"| **Total Artifact Targets** | `{len(report.artifacts)}` |",
        f"| **Total Files Detected** | `{report.total_files:,}` |",
        f"| **Zombie Server Processes** | `{len(report.zombies)}` |",
        f"| **Repositories with Uncommitted Changes** | `{report.uncommitted_repos_count}` |",
        "",
        "## 📦 Ecosystem Footprint Breakdown",
        "",
        "| Ecosystem / Category | Size | Reclaim % |",
        "| :--- | :--- | :--- |",
    ]

    total_b = max(1, report.total_bytes)
    for cat, b in sorted(report.category_breakdown.items(), key=lambda x: x[1], reverse=True):
        pct = (b / total_b) * 100.0
        lines.append(f"| **{cat}** | `{format_bytes(b)}` | `{pct:.1f}%` |")

    lines.extend([
        "",
        "## 🎯 Top Reclaimable Bloat Targets",
        "",
        "| # | Category | Path | Files | Stale | Purge Score | Safety | Size |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for idx, a in enumerate(report.artifacts[:100], start=1):
        stale_str = f"{int(a.days_stale)}d" if a.days_stale >= 1 else "Today"
        score_str = f"{a.purge_score:.0f}/100" if hasattr(a, "purge_score") else "N/A"
        safety_str = a.safety_level if hasattr(a, "safety_level") else "SAFE"
        lines.append(
            f"| {idx} | {a.category} | `{a.path}` | {a.file_count:,} | {stale_str} | {score_str} | `{safety_str}` | **{a.human_size}** |"
        )

    if report.zombies:
        lines.extend([
            "",
            "## 🧟 Zombie Dev Server Processes",
            "",
            "| PID | Name | Port | Memory | Children | Working Dir / Command |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for z in report.zombies:
            port_str = f":{z.port}" if z.port else "—"
            lines.append(
                f"| `{z.pid}` | `{z.name}` | `{port_str}` | `{z.memory_mb:.1f} MB` | `{z.children_count}` | `{z.cwd or z.cmdline}` |"
            )

    lines.extend([
        "",
        "---",
        "*Generated automatically by [purge](https://github.com/shenald-dev/purge) — Zero-latency developer bloat and zombie process reaper.*",
    ])

    return "\n".join(lines)


def export_to_csv(report: PurgeReport) -> str:
    """Generate RFC-4180 CSV spreadsheet format from a PurgeReport."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow([
        "index",
        "category",
        "path",
        "size_bytes",
        "human_size",
        "file_count",
        "days_stale",
        "is_git_repo",
        "has_uncommitted",
        "days_since_commit",
        "purge_score",
        "safety_level",
    ])

    for idx, a in enumerate(report.artifacts, start=1):
        writer.writerow([
            idx,
            a.category,
            str(a.path),
            a.size_bytes,
            a.human_size,
            a.file_count,
            round(a.days_stale, 1),
            a.is_git_repo,
            a.has_uncommitted,
            round(a.days_since_commit, 1) if a.is_git_repo else 0.0,
            round(getattr(a, "purge_score", 0.0), 1),
            getattr(a, "safety_level", "SAFE"),
        ])

    return output.getvalue()


def export_to_json(report: PurgeReport, indent: int = 2) -> str:
    """Generate structured JSON representation from a PurgeReport."""
    return json.dumps(report.to_dict(), indent=indent)


def save_export(
    report: PurgeReport,
    destination: Path,
    export_format: Optional[str] = None,
) -> Path:
    """Save report to destination file inferring format from extension if omitted."""
    fmt = (export_format or destination.suffix.lstrip(".").lower()).strip()
    if fmt in ("md", "markdown"):
        content = export_to_markdown(report)
    elif fmt == "csv":
        content = export_to_csv(report)
    else:
        content = export_to_json(report)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination
