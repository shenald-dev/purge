# Changelog

All notable changes to **purge** (`purge-reaper`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **[Cross-Platform] Windows system path & symlink resilience**: Normalized POSIX system path matching in `is_protected_path` to prevent Windows drive mismatches, and guarded symlink loop traversal tests against WinError 1314 privilege errors.
- **[CLI & Tests] Validation & optional extra isolation**: Transport flag in `purge mcp` is now validated before loading optional MCP dependencies; mocked `send2trash` in security tests to run deterministically on lean environments.

## [3.0.0] - 2026-11-17 — Agent-Native Reclamation

### Added
- **Native MCP Server (`purge mcp`)**:
  - Full Model Context Protocol integration exposing 10 tools: `scan`, `inspect_path`, `clean`, `kill_zombies`, `port_status`, `vault_list`, `vault_show`, `vault_restore`, `stats`, `server_info`.
  - stdio and streamable-http transports; registers as an MCP host entry (`purge mcp --transport stdio`).
  - Safety model: destructive tools (`clean`, `kill_zombies`, `vault_restore`) are dry-run by default and require an explicit `confirm=True` argument to execute; protected system roots are rejected server-side.
  - Optional `[mcp]` extra (`pip install 'purge-reaper[mcp]'`, Python 3.11+) keeps the core dependency footprint unchanged.
- **PurgeEngine Headless API (`purge.core.api.PurgeEngine`)**:
  - Single programmatic facade for scan, inspection, cleaning, quarantine, zombie hunting, and telemetry — the exact semantics the CLI observes, callable from Python without a terminal.
  - Human-string size filters (`min_size="50MB"`), category specs, scoring gates, and vault round-trip management.
- **CI Bloat Budget Gate (`purge scan --fail-over 2GB`)**:
  - Exits with code 2 when total reclaimable size exceeds a threshold; CI pipelines can fail builds before debris accumulates. Works with `--json`, `--format`, and file exports.
- **`[trash]` optional extra**: `send2trash` is now a declared, documented dependency contract for `--trash` mode instead of an implicit runtime import.

### Changed
- **[Optimized] Git repository inspection** consolidated from 3 to 2 subprocess calls per repository (combined `git log` fetch + `GIT_OPTIONAL_LOCKS=0`), reducing cold inspection cost by ~39% (53.5ms → 32.7ms median across 15 repos, 5 interleaved rounds).
- **[Changed] Version bumped to 3.0.0** (breaking: new major feature surface; CLI and Python APIs remain backward compatible).
- Terminal banner and `--version` now derive from the package `__version__` (no more hardcoded strings drifting out of sync).

### Fixed
- **[Security] Vault manifest hardening**: `restore_session` now validates that manifest `original_path` values are absolute, outside the vault, and not inside critical system roots — a tampered or hand-edited manifest can no longer redirect restoration into arbitrary locations (`tests/test_security.py`).
- **[Fixed] Negative size parsing**: `parse_size_to_bytes("-5MB")` returned negative bytes, silently disabling size filters; malformed/negative inputs now resolve to 0. Added petabyte (`PB`) unit parsing for symmetry with `format_bytes`.
- **[Fixed] Trash error classification**: `--trash` failures previously surfaced as generic deletion errors; `ImportError` (missing package) is now distinct from runtime trash failures, with an actionable install hint referencing the `[trash]` extra.
- **[Fixed] Rich markup leak**: telemetry panel emitted literal `[bold]…[/]` markup in category breakdown lines.
- **[Fixed] The `test_cleaner_to_trash` unit test** now isolates the missing-`send2trash` path deterministically (previously dependent on the host environment's installed packages).

### Verified
- Test suite: **166 passed, 2 skipped** (baseline at v2.0.0: 89 passed, 1 failed, 2 skipped) — all pre-existing failures resolved, no regressions across 3 consecutive full-suite runs.
- End-to-end MCP protocol session verified against the installed `purge` binary via the official client SDK (tool listing, scan, safety-guard refusal, vault error surfacing, stats).
- Ruff lint: clean. Adversarial suite: symlink loops, permission-injected traversal, unicode paths, depth boundaries, fuzzed size/score inputs.

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
