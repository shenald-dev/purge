# Changelog

All notable changes to **purge** (`purge-reaper`) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
