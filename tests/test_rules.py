import os
from pathlib import Path

from purge.core.rules import (
    identify_artifact_category,
    is_protected_path,
)


def test_is_protected_path(tmp_path):
    # Git folder is protected
    git_dir = tmp_path / ".git"
    assert is_protected_path(git_dir) is True

    # Root filesystem is protected
    assert is_protected_path(Path("/")) is True

    # Platform specific critical system paths
    if os.name == "nt":
        assert is_protected_path(Path("C:\\Windows")) is True
    else:
        assert is_protected_path(Path("/etc")) is True

    # Standard dev project is not protected
    safe_project = tmp_path / "my_project"
    safe_project.mkdir()
    assert is_protected_path(safe_project) is False


def test_identify_artifact_category(tmp_path):
    proj = tmp_path / "web_app"
    proj.mkdir()

    # Standard node_modules
    assert identify_artifact_category("node_modules", proj) == "Node.js & Web"
    assert identify_artifact_category(".next", proj) == "Node.js & Web"

    # Python
    assert identify_artifact_category(".venv", proj) == "Python"
    assert identify_artifact_category("__pycache__", proj) == "Python"

    # Rust target requires Cargo.toml
    assert identify_artifact_category("target", proj) is None
    (proj / "Cargo.toml").write_text("[package]\nname = 'test'")
    assert identify_artifact_category("target", proj) == "Rust / Cargo"

    # Build / Dist requires manifest
    py_proj = tmp_path / "py_app"
    py_proj.mkdir()
    assert identify_artifact_category("dist", py_proj) is None
    (py_proj / "pyproject.toml").write_text("[project]\nname = 'test'")
    assert identify_artifact_category("dist", py_proj) == "Build Artifacts"
