"""Tests for audit report exporter (Markdown, CSV, JSON)."""

import json
from pathlib import Path

from purge.core.exporter import export_to_csv, export_to_json, export_to_markdown, save_export
from purge.core.models import Artifact, PurgeReport


def _create_sample_report():
    art = Artifact(
        path=Path("/tmp/demo/node_modules"),
        category="Node.js & Web",
        size_bytes=500 * 1024 * 1024,
        file_count=12000,
        days_stale=25.0,
        purge_score=85.0,
        safety_level="SAFE",
    )
    return PurgeReport(
        scan_path=Path("/tmp/demo"),
        artifacts=[art],
        total_bytes=500 * 1024 * 1024,
        total_files=12000,
        scanned_dirs_count=42,
        duration_seconds=0.123,
    )


def test_export_to_markdown():
    report = _create_sample_report()
    md = export_to_markdown(report)
    assert "# Purge Developer Bloat Audit Report" in md
    assert "Total Reclaimable Space" in md
    assert "Node.js & Web" in md
    assert "SAFE" in md
    assert "85/100" in md


def test_export_to_csv():
    report = _create_sample_report()
    csv_str = export_to_csv(report)
    lines = csv_str.strip().split("\n")
    assert len(lines) == 2  # header + 1 item
    assert "node_modules" in lines[1]
    assert "85.0" in lines[1]
    assert "SAFE" in lines[1]


def test_export_to_json():
    report = _create_sample_report()
    json_str = export_to_json(report)
    data = json.loads(json_str)
    assert data["total_bytes"] == 500 * 1024 * 1024
    assert len(data["artifacts"]) == 1


def test_save_export(tmp_path):
    report = _create_sample_report()
    out_md = tmp_path / "report.md"
    save_export(report, out_md)
    assert out_md.exists()
    assert "# Purge" in out_md.read_text(encoding="utf-8")

    out_csv = tmp_path / "report.csv"
    save_export(report, out_csv)
    assert out_csv.exists()
    assert "category,path" in out_csv.read_text(encoding="utf-8")
