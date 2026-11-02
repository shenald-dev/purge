# Changelog

All notable changes to **purge** (`purge-reaper`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-02

### Added
- **One-Shot Port Reaper (`purge free` / `purge port <PORT>`)**:
  - Instant inspection of any port with process details, active localhost URL, memory, and CPU usage.
  - Recursive process tree termination (`kill_zombie_tree`) that eradicates parent processes and all spawned child processes to permanently resolve `EADDRINUSE` port lockups.
- **Global Developer Cache Reaper (`purge cache` / `purge scan --global`)**:
  - Scans and prunes multi-gigabyte global package manager caches across npm (`~/.npm/_cacache`), pnpm store, Yarn cache, pip (`pip/cache`), Astral uv (`uv/cache`), Cargo crate & git caches (`~/.cargo`), Go build cache, and Gradle dependency caches.
- **Git-Aware Repository Intelligence**:
  - Accurate project dormancy tracking via `git log -1` commit timestamps.
  - Active workspace protection: detects repositories with uncommitted git changes and surfaces `⚠️ Uncommitted` badges.
  - `--skip-uncommitted` flag to prevent accidental deletion of build artifacts in active work-in-progress repos.
- **Interactive Deletion & Size Filtering**:
  - Added `--interactive / -i` mode to selectively choose which artifacts to purge.
  - Added `--min-size` filter (e.g. `--min-size 100MB`, `1GB`) with `parse_size_to_bytes` utility.
- **Cumulative Lifetime Reclamation Telemetry (`purge stats`)**:
  - Persistent tracking of cumulative gigabytes reclaimed across purge cycles in `~/.config/purge/history.json`.
  - Rich telemetry summary displaying lifetime space saved, total artifacts deleted, and historical purge events.
- **Project Configuration Engine (`purge.toml`)**:
  - Added `purge init` command to bootstrap project configuration.
  - Support for `purge.toml` and `pyproject.toml [tool.purge]`.
  - Configurable depth, minimum stale thresholds, custom artifact target rules, and path exclusion lists.
- **Expanded Ecosystem Coverage**:
  - Added detection for modern frameworks: Astro (`.astro`), SolidJS (`.solid`), Remix (`.remix`), Nitro (`.output`), Expo (`.expo`), CocoaPods (`Pods`), Dart/Flutter (`.dart_tool`), Xcode (`DerivedData`), Scala (`.bloop`, `.metals`), and Hypothesis (`.hypothesis`).
- **Test Suite Expansion**:
  - 30 new unit and integration tests covering CLI commands, configuration, git intelligence, global caches, process trees, and lifetime history (53 tests total).

### Changed
- Promoted package version to `1.0.0` with `Production/Stable` classification.
- Upgraded terminal UI to display git status badges, global cache tables, port inspection cards, and lifetime metrics.

### Fixed
- Fixed category breakdown size calculation in scan telemetry HUD where only the first artifact's size was previously displayed.
- Fixed symlink cleaner to avoid traversing or deleting target directories when cleaning broken or active symlinks.

---

## [0.1.0] - 2026-10-26

### Added
- **Initial Open Source Launch**: Zero-latency developer bloat and zombie process reaper.
- **Parallel Directory Crawler**: Sub-second discovery walk that prunes traversal at artifact boundaries (skips recursing into 100k+ nested files in `node_modules`).
- **Universal Ecosystem Coverage**:
  - Node.js & Web: `node_modules`, `.next`, `.turbo`, `.nuxt`, `.parcel-cache`, `.svelte-kit`, `.docusaurus`.
  - Python: `.venv`, `venv`, `env`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, `.tox`, `.nox`.
  - Rust & Cargo: `target/` (only when parent contains `Cargo.toml`).
  - Java & Gradle: `.gradle`.
  - Build Artifacts: `dist`, `build`, `out`, `coverage`.
  - OS Clutter: `.DS_Store`, `Thumbs.db`.
- **Zombie Dev Server Hunter**: Cross-platform port listener scan (`:3000`, `:5173`, `:8000`, `:8080`, etc.) and matching process analyzer (`node`, `python`, `vite`, `uvicorn`, `next`, `cargo-watch`).
- **Interactive Cyberpunk TUI**: Rich-rendered diagnostic tables, telemetry cards, and particle counters.
- **Safety Safeguards**: Root path detection, protected system directories (`/`, `C:\Windows`, `~/.ssh`), and non-destructive dry-run simulation mode (`--dry-run`).
- **JSON Telemetry Output**: `--json` flag for easy integration with scripts and CI.
- **Continuous Integration**: GitHub Actions CI test matrix across Python 3.10, 3.11, and 3.12.
