"""Rules and signatures for identifying developer bloat, global caches, and protected system paths."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
        ".astro",
        ".solid",
        ".remix",
        ".output",
        ".contentlayer",
        ".nx",
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
        ".hypothesis",
        ".ipynb_checkpoints",
    ],
    "Rust / Cargo": [
        "target",
    ],
    "Java / Gradle / Scala": [
        ".gradle",
        ".bloop",
        ".metals",
        ".kotlinc",
    ],
    "Mobile / Cross-Platform": [
        "Pods",
        ".dart_tool",
        "DerivedData",
        ".expo",
    ],
    "Systems & Native": [
        ".build",
        ".zig-cache",
        "zig-out",
        "CMakeFiles",
    ],
    "Ruby & PHP": [
        "vendor",
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

_ARTIFACT_MAP: Dict[str, str] = {}
for cat, patterns in ARTIFACT_TARGETS.items():
    for pat in patterns:
        _ARTIFACT_MAP[pat] = cat

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


def is_protected_path(path: Path, allow_home: bool = False) -> bool:
    """Check if path is a protected root, user profile root, or system path."""
    try:
        resolved = path.resolve()
        str_path = str(resolved).rstrip("\\/")

        # Protect root directories across all platforms (e.g. '/', 'C:', 'D:')
        if (
            resolved.parent == resolved
            or len(resolved.parts) <= 1
            or str_path in CRITICAL_SYSTEM_PATHS
            or str(path) in CRITICAL_SYSTEM_PATHS
            or str(path).rstrip("\\/") in CRITICAL_SYSTEM_PATHS
            or str_path == ""
            or str(path) in CRITICAL_SYSTEM_PATHS
        ):
            return True

        # Protect user home directory root itself (can scan inside it, but don't delete home!)
        home = str(Path.home().resolve()).rstrip("\\/")
        if str_path == home:
            return not allow_home

        # Protect critical directories
        for part in resolved.parts:
            if part in PROTECTED_DIR_NAMES:
                return True

        return False
    except Exception:
        return True


def identify_artifact_category(
    name: str, parent: Path, custom_rules: Optional[Dict[str, List[str]]] = None
) -> Optional[str]:
    """Identify if a folder or file matches a known developer artifact rule.

    Special heuristics:
    - 'target' is only marked as Rust / Cargo if parent has Cargo.toml or Cargo.lock (or Maven pom.xml)
    - 'build' / 'dist' only if parent has recognized build manifest
    - '.build' only if parent has Package.swift (Swift PM)
    - 'zig-out' / '.zig-cache' only if parent has build.zig
    - 'CMakeFiles' only if parent has CMakeLists.txt
    - 'vendor' only if parent has composer.json/lock (PHP) or Gemfile (Ruby)
    """
    # Check custom rules first if provided
    if custom_rules:
        for cat, patterns in custom_rules.items():
            if name in patterns:
                return cat

    category = _ARTIFACT_MAP.get(name)
    if category:
        # Special guard for generic names like 'target'
        if name == "target":
            if (parent / "Cargo.toml").exists() or (parent / "Cargo.lock").exists():
                return "Rust / Cargo"
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

        # Guard for Swift Package Manager .build
        if name == ".build":
            if (parent / "Package.swift").exists():
                return "Systems & Native"
            return None

        # Guard for Zig
        if name in (".zig-cache", "zig-out"):
            if (parent / "build.zig").exists():
                return "Systems & Native"
            return None

        # Guard for CMake
        if name == "CMakeFiles":
            if (parent / "CMakeLists.txt").exists():
                return "Systems & Native"
            return None

        # Guard for PHP / Ruby vendor
        if name == "vendor":
            if (parent / "composer.json").exists() or (parent / "composer.lock").exists():
                return "PHP / Composer"
            if (parent / "Gemfile").exists():
                return "Ruby / Bundler"
            return None

        return category

    return None


def get_global_cache_targets() -> List[Tuple[Path, str, str]]:
    """Return list of (path, category, description) for global developer package manager caches."""
    home = Path.home()
    local_appdata = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))

    candidates = [
        # npm
        (home / ".npm" / "_cacache", "Global Cache: npm", "npm HTTP & tarball cache"),
        # pnpm
        (local_appdata / "pnpm" / "store", "Global Cache: pnpm", "pnpm content-addressable store"),
        (home / ".local" / "share" / "pnpm" / "store", "Global Cache: pnpm", "pnpm content-addressable store"),
        # yarn
        (home / ".yarn" / "berry" / "cache", "Global Cache: Yarn", "Yarn Berry package cache"),
        (home / ".cache" / "yarn", "Global Cache: Yarn", "Yarn v1 classic cache"),
        # Bun
        (home / ".bun" / "install" / "cache", "Global Cache: Bun", "Bun package install cache"),
        # Deno
        (home / ".cache" / "deno", "Global Cache: Deno", "Deno remote dependency cache"),
        (local_appdata / "deno", "Global Cache: Deno", "Deno dependency cache"),
        # pip
        (local_appdata / "pip" / "cache", "Global Cache: pip", "Python pip HTTP & wheel cache"),
        (home / ".cache" / "pip", "Global Cache: pip", "Python pip HTTP & wheel cache"),
        # uv
        (local_appdata / "uv" / "cache", "Global Cache: uv", "Astral uv package & wheel cache"),
        (home / ".cache" / "uv", "Global Cache: uv", "Astral uv package & wheel cache"),
        # cargo
        (home / ".cargo" / "registry" / "cache", "Global Cache: Cargo", "Rust crate download cache"),
        (home / ".cargo" / "git" / "db", "Global Cache: Cargo", "Rust git repository cache"),
        # go
        (home / ".cache" / "go-build", "Global Cache: Go", "Go compiler build cache"),
        (local_appdata / "go-build", "Global Cache: Go", "Go compiler build cache"),
        # gradle
        (home / ".gradle" / "caches", "Global Cache: Gradle", "Gradle dependency cache"),
        # Composer (PHP)
        (home / ".cache" / "composer", "Global Cache: Composer", "Composer package cache"),
        (local_appdata / "Composer" / "cache", "Global Cache: Composer", "Composer package cache"),
        # Bundler (Ruby)
        (home / ".bundle" / "cache", "Global Cache: Bundler", "Ruby gem download cache"),
    ]

    existing = []
    seen = set()
    for p, cat, desc in candidates:
        try:
            if p.is_dir() and str(p.resolve()) not in seen:
                existing.append((p.resolve(), cat, desc))
                seen.add(str(p.resolve()))
        except Exception:
            continue

    return existing
