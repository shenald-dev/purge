"""Rules and signatures for identifying developer bloat and protected system paths."""

from pathlib import Path
from typing import Dict, List, Optional, Set

# Universal developer artifact targets grouped by ecosystem
ARTIFACT_TARGETS: Dict[str, List[str]] = {
    "Node.js & Web": [
        "node_modules",
        ".next",
        ".turbo",
        ".nuxt",
        ".parcel-cache",
        ".svelte-kit",
        ".docusaurus",
        "bower_components",
    ],
    "Python": [
        ".venv",
        "venv",
        "env",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        ".tox",
        ".nox",
    ],
    "Rust / Cargo": [
        "target",
    ],
    "Java / Gradle": [
        ".gradle",
    ],
    "Build Artifacts": [
        "dist",
        "build",
        "out",
        "coverage",
        ".nyc_output",
    ],
    "OS Clutter": [
        ".DS_Store",
        "Thumbs.db",
    ],
}

# Directories we should never traverse deeper into, or delete
PROTECTED_DIR_NAMES: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".gcloud",
}

# System directories that must NEVER be scanned or pruned
CRITICAL_SYSTEM_PATHS: Set[str] = {
    "/",
    "/bin",
    "/sbin",
    "/usr",
    "/usr/bin",
    "/usr/sbin",
    "/etc",
    "/var",
    "/System",
    "/Library",
    "/Applications",
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Users",
}


def is_protected_path(path: Path) -> bool:
    """Check if path is a protected root, user profile root, or system path."""
    try:
        resolved = path.resolve()
        str_path = str(resolved).rstrip("\\/")

        # Protect root directories across all platforms (e.g. '/', 'C:', 'D:')
        if resolved.parent == resolved or len(resolved.parts) <= 1 or str_path in CRITICAL_SYSTEM_PATHS or str_path == "":
            return True

        # Protect user home directory root itself (can scan inside it, but don't delete home!)
        home = str(Path.home().resolve()).rstrip("\\/")
        if str_path == home:
            return True

        # Protect critical directories
        for part in resolved.parts:
            if part in PROTECTED_DIR_NAMES:
                return True

        return False
    except Exception:
        return True


def identify_artifact_category(name: str, parent: Path) -> Optional[str]:
    """Identify if a folder or file matches a known developer artifact rule.

    Special heuristics:
    - 'target' is only marked as Rust / Cargo if parent has Cargo.toml or Cargo.lock
    - 'build' / 'dist' only if parent has package.json, pyproject.toml, Cargo.toml, or setup.py
    """
    for category, patterns in ARTIFACT_TARGETS.items():
        if name in patterns:
            # Special guard for generic names like 'target'
            if name == "target":
                if (parent / "Cargo.toml").exists() or (parent / "Cargo.lock").exists():
                    return "Rust / Cargo"
                # If no cargo, check if it's Maven/Java target
                if (parent / "pom.xml").exists():
                    return "Java / Maven"
                return None

            # Special guard for generic names like 'build' or 'dist'
            if name in ("build", "dist", "out"):
                has_manifest = any(
                    (parent / m).exists()
                    for m in [
                        "package.json",
                        "pyproject.toml",
                        "setup.py",
                        "Cargo.toml",
                        "CMakeLists.txt",
                        "Makefile",
                    ]
                )
                if has_manifest:
                    return category
                return None

            return category

    return None
