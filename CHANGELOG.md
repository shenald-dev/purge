# Changelog

All notable changes to **purge** (`purge-reaper`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- **[Pruned]:** Removed unused `PROTECTED` safety level and `quarantined_at` tracking variable.
- **[Pruned]:** Removed unused `default_format` from `PurgeConfig`, and dead functions `list_system_partitions` and `kill_zombie` from core components.

---

## [2.0.0] - 2026-11-03

### Added
- **Purge Priority Scoring Engine (0-100 Index)**:
  - Multi-factor heuristic engine evaluating size footprint (up to 35 pts), staleness (up to 30 pts), ecosystem rebuild cost (up to 20 pts), and Git dormancy (up to 15 pts).
  - Built-in safety penalty (-35 pts) and `CAUTION` flag for repositories with uncommitted changes.
  - Safety classification levels: `SAFE` (≥ 65), `MODERATE` (35-64), `CAUTION` (< 35).
  - Added `--min-score` filtering and `--auto` mode for autonomous high-yield reclamation.
- **Quarantine Undo Vault (`purge clean --vault` / `purge vault`)**:
  - Safe staging mode moving artifacts to local quarantine vault (`~/.config/purge/vault/<session_id>`) with JSON manifests.
  - Instant one-command restoration (`purge vault restore <ID>`) back to original disk paths.
  - Vault management commands: `purge vault list`, `purge vault show`, and `purge vault prune`.
- **Drive Capacity Radar (`purge disk` / `purge top`)**:
  - Partition health analyzer computing total, used, and free disk space.
  - Visual terminal ASCII/Unicode capacity bar showing developer bloat percentage and potential free space gain.
- **Multi-Format Audit Exporter (`purge export` / `--format`)**:
  - Comprehensive GitHub Flavored Markdown audit report generator.
  - RFC-4180 compliant CSV export for spreadsheet analysis.
  - Structured JSON export for CI/CD pipelines and automated tooling.
- **High-Concurrency Parallel Deletion**:
  - Multi-threaded deletion pool (`--workers 4`) for rapid pruning of large directory trees.
  - Robust Windows file-lock retry backoff with automatic readonly attribute clearing.
- **Multi-Ecosystem Expansion**:
  - Added support for Bun (`~/.bun/install/cache`), Deno (`~/.cache/deno`), Swift Package Manager (`.build`), Zig (`.zig-cache`, `zig-out`), CMake (`CMakeFiles`), PHP Composer (`vendor`), and Ruby Bundler.
- **Sorting & Top-N Limiting**:
  - Added `--sort (size|score|stale|name)` and `--top <N>` across scan and clean workflows.
- **Expanded Test Suite**:
  - 33 new automated tests (88 tests total) covering scoring, quarantine vaults, disk analysis, markdown/csv exporters, and parallel execution.

### Changed
- Promoted package version to `2.0.0` major release.
- Updated terminal UI to display Purge Score badges (`[bold green]92/100[/]`) and telemetry radar summary.
- Enhanced `clean` command to support `--auto`, `--vault`, `--min-score`, and `--workers`.

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

---

## [0.1.0] - 2026-10-26

### Added
- **Initial Open Source Launch**: Zero-latency developer bloat and zombie process reaper.
- **Parallel Directory Crawler**: Sub-second discovery walk that prunes traversal at artifact boundaries (skips recursing into 100k+ nested files in `node_modules`).
- **Universal Ecosystem Coverage**: Node.js, Python, Rust, Gradle, Build Artifacts, and OS Clutter.
- **Zombie Dev Server Hunter**: Cross-platform port listener scan (`:3000`, `:5173`, `:8000`, `:8080`, etc.) and matching process analyzer.
- **Interactive Cyberpunk TUI**: Rich-rendered diagnostic tables, telemetry cards, and particle counters.
- **Safety Safeguards**: Root path detection, protected system directories (`/`, `C:\Windows`, `~/.ssh`), and non-destructive dry-run simulation mode (`--dry-run`).
- **JSON Telemetry Output**: `--json` flag for easy integration with scripts and CI.
