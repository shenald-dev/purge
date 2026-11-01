import pytest

from purge.core.scanner import DiskScanner, get_path_stats


def test_get_path_stats(tmp_path):
    sub = tmp_path / "subfolder"
    sub.mkdir()
    f1 = sub / "file1.txt"
    f1.write_text("Hello " * 100)  # ~600 bytes
    f2 = sub / "file2.txt"
    f2.write_text("World " * 100)

    total_bytes, file_count, last_mod, days_stale = get_path_stats(sub)
    assert file_count == 2
    assert total_bytes > 1000
    assert last_mod is not None
    assert days_stale >= 0.0


def test_scanner_discovers_artifacts(tmp_path):
    # Setup mock project structure
    p1 = tmp_path / "node_project"
    p1.mkdir()
    nm = p1 / "node_modules"
    nm.mkdir()
    (nm / "package.json").write_text("{}")
    (nm / "index.js").write_text("console.log('hi')")

    p2 = tmp_path / "python_project"
    p2.mkdir()
    venv = p2 / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin")

    # Run scanner
    scanner = DiskScanner()
    report = scanner.scan(tmp_path)

    assert len(report.artifacts) == 2
    categories = {a.category for a in report.artifacts}
    assert "Node.js & Web" in categories
    assert "Python" in categories
    assert report.total_files == 3
    assert report.total_bytes > 0


def test_scanner_category_filter(tmp_path):
    p1 = tmp_path / "node_project"
    p1.mkdir()
    nm = p1 / "node_modules"
    nm.mkdir()
    (nm / "a.js").write_text("1")

    p2 = tmp_path / "python_project"
    p2.mkdir()
    venv = p2 / ".venv"
    venv.mkdir()
    (venv / "b.txt").write_text("2")

    # Filter only Python
    scanner = DiskScanner(categories=["Python"])
    report = scanner.scan(tmp_path)

    assert len(report.artifacts) == 1
    assert report.artifacts[0].category == "Python"


def test_get_path_stats_permission_error(tmp_path):
    import os
    from unittest.mock import patch

    sub = tmp_path / "subfolder"
    sub.mkdir()
    f1 = sub / "file1.txt"
    f1.write_text("Hello")

    # Force a permission error on os.scandir inside the directory traversal
    with patch("os.scandir", side_effect=PermissionError):
        total_bytes, file_count, last_mod, days_stale = get_path_stats(sub)

    # Since we can't scan, it should fall back gracefully
    assert total_bytes == 0
    assert file_count == 0
    assert last_mod is None
    assert days_stale == 0.0


def test_scanner_discovers_symlinked_artifacts(tmp_path):
    import os

    # Setup the actual modules target
    target = tmp_path / "actual_modules"
    target.mkdir()
    (target / "big_file.js").write_text("x" * 1024 * 1024)

    # Setup the project with a symlink
    project = tmp_path / "web_project"
    project.mkdir()

    link = project / "node_modules"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("Symlink creation not permitted without privileges")

    # Run scanner on the project
    scanner = DiskScanner()
    report = scanner.scan(project)

    assert len(report.artifacts) == 1
    assert report.artifacts[0].category == "Node.js & Web"

    # The size should be the size of the symlink, not the 1MB target
    assert report.artifacts[0].size_bytes < 1000
    assert report.artifacts[0].file_count == 1
