import subprocess
from pathlib import Path

from purge.core.git_helper import inspect_git_project


def test_inspect_non_git_directory(tmp_path: Path):
    sub = tmp_path / "regular_dir"
    sub.mkdir()
    info = inspect_git_project(sub)
    assert info.is_git is False
    assert info.has_uncommitted is False


def test_inspect_real_git_project(tmp_path: Path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)

    # Initial commit
    f = tmp_path / "main.py"
    f.write_text("print('hello')")
    subprocess.run(["git", "add", "main.py"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True)

    # Clean repo check
    info_clean = inspect_git_project(tmp_path)
    assert info_clean.is_git is True
    assert info_clean.has_uncommitted is False
    assert info_clean.last_commit_time is not None
    assert info_clean.days_since_last_commit >= 0.0

    # Uncommitted changes check
    f.write_text("print('modified')")
    info_dirty = inspect_git_project(tmp_path)
    assert info_dirty.is_git is True
    assert info_dirty.has_uncommitted is True
