<div align="center">

```
  ██████╗ ██╗   ██╗██████╗  ██████╗ ███████╗
  ██╔══██╗██║   ██║██╔══██╗██╔════╝ ██╔════╝
  ██████╔╝██║   ██║██████╔╝██║  ███╗█████╗  
  ██╔═══╝ ██║   ██║██╔══██╗██║   ██║██╔══╝  
  ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

### 🧹 The Zero-Latency Developer Bloat & Zombie Process Reaper

*Reclaim 50GB of dev debris and slay zombie dev servers in seconds. Now featuring intelligent priority scoring, quarantine undo vault, and drive capacity radar.*

[![GitHub Release](https://img.shields.io/github/v/release/shenald-dev/purge?color=00d4ff&style=flat-square&logo=github)](https://github.com/shenald-dev/purge/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![CI Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg?style=flat-square)](https://github.com/shenald-dev/purge/actions)
[![Speed](https://img.shields.io/badge/speed-%3C20ms-cyan.svg?style=flat-square)](#architecture)
[![Zero Bloat](https://img.shields.io/badge/bloat-zero-success.svg?style=flat-square)](#quick-start)

---

[The Problem](#-the-problem) •
[What's New in v2.0](#-whats-new-in-v20) •
[Key Features](#-key-features) •
[Terminal UI](#-terminal-ui) •
[Quick Start](#-quick-start) •
[Commands](#-commands--usage) •
[Quarantine Vault](#-quarantine-vault--undo) •
[Purge Scoring Engine](#-purge-scoring-engine) •
[Drive Radar](#-drive-capacity-radar) •
[Configuration](#-configuration) •
[Supported Artifacts](#-supported-bloat-targets) •
[Architecture](#-architecture)

---

</div>

## 💥 The Problem

Modern developers juggle dozens of repositories and tools every month. After a few weeks, engineering laptops silently hoard **40GB to 100GB+** of developer debris:

- **Abandoned `node_modules`** from tutorials and archived experiments.
- **Massive Rust `target/` directories** silently consuming 15GB each.
- **Dormant Python `.venv` environments** and build artifacts (`dist`, `.next`, `.turbo`, `.astro`).
- **Bloated Global Package Caches** (`npm`, `pnpm`, `pip`, `uv`, `cargo`, `bun`, `deno`) accumulating stale tarballs indefinitely.
- **Zombie Dev Servers** left running in background terminal tabs, holding ports `:3000`, `:5173`, or `:8000`, draining RAM, and causing frustrating `EADDRINUSE` errors.

Existing tools are fragmented: `npkill` only cleans npm; `cargo clean` requires manually visiting each repository; `docker prune` only handles containers; and finding port hogs requires cryptic `lsof -i :3000` and `kill -9` terminal dances.

**`purge` is a unified, blazing-fast reaper.** It scans your workspaces concurrently, prunes directory traversal at artifact boundaries, audits global caches, slays process trees holding your dev ports, and lets you reclaim 50GB in seconds.

---

## 🚀 What's New in v2.0

- 🎯 **Purge Priority Scoring Engine (0-100 Index):** Intelligent composite score weighting size footprint, staleness, ecosystem re-creation cost, and Git repository state. Easily target high-value bloat with `--min-score` or `--auto`.
- 🛡️ **Quarantine Undo Vault (`purge clean --vault` / `purge vault restore`):** Zero accidental data loss. Move targets to a local quarantine vault instead of permanent deletion, with instant 1-second one-command restoration.
- 💾 **Drive Capacity Radar (`purge disk` / `purge top`):** Visual partition health analysis displaying total/used/free space, developer bloat percentage, and potential free disk gain.
- 📑 **Multi-Format Audit Exporter (`purge export`):** Export comprehensive markdown reports, RFC-4180 CSV spreadsheets, or structured JSON for team audits and CI/CD pipelines.
- ⚡ **High-Concurrency Parallel Deletion (`--workers 4`):** Multi-threaded deletion pool with robust Windows file-lock retry backoff and readonly clearing.
- 🌐 **Expanded Ecosystem Support:** Native heuristic detection for Bun (`~/.bun/install/cache`), Deno (`~/.cache/deno`), Swift PM (`.build`), Zig (`.zig-cache`, `zig-out`), CMake (`CMakeFiles`), PHP Composer (`vendor`), and Ruby Bundler.

---

## ⚡ Key Features

- ⚡ **Sub-Second Parallel Crawl:** Never gets bogged down by millions of files inside `node_modules`—prunes traversal at candidate boundaries and sizes directories concurrently in <20ms.
- 🧟 **Process Tree Port Slayer (`purge free <PORT>`):** Free ports in one command. Recursively terminates parent processes and all orphaned child worker trees (`SIGTERM` -> `SIGKILL` cascade).
- 🌐 **Global Cache Auditing & Pruning (`purge cache`):** Discovers and purges multi-gigabyte package manager global caches (`npm`, `pnpm`, `yarn`, `bun`, `deno`, `pip`, `uv`, `cargo`, `go`, `gradle`, `composer`).
- 🌿 **Git Worktree Intelligence:** Non-destructive scan flags repositories with uncommitted changes (`--git-aware`, `--skip-uncommitted`) and displays last-commit age indicators.
- 📈 **Lifetime Reclamation Telemetry (`purge stats`):** Persistent local telemetry tracking cumulative bytes reclaimed and zombie processes terminated over time.
- 🎯 **Interactive Selection Mode (`-i / --interactive`):** Pick and choose specific artifacts via numbers or comma-separated lists before purging.
- 🤖 **Autonomous Reclamation (`--auto`):** Automatically selects and purges safe, high-scoring targets (Score ≥ 65) without manual picking.
- ⚙️ **Declarative Configuration (`purge init`):** Native `purge.toml` and `pyproject.toml [tool.purge]` support for team-level ignore paths, custom target rules, and depth limits.

---

## 💻 Terminal UI

When you run `purge scan` across your workspace:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│   🧹 Developer Bloat & Zombie Process Reaper • Zero Bloat                   │
└─────────────── v2.0.0 • https://github.com/shenald-dev/purge ───────────────┘

                       📦 Reclaimable Bloat Targets (4)                        
┌───┬──────────────────┬──────────────────────────┬──────────┬────────────┬─────────┬────────┬──────────────┐
│ # │ Category         │ Path                     │    Files │ Git Status │   Stale │  Score │         Size │
├───┼──────────────────┼──────────────────────────┼──────────┼────────────┼─────────┼────────┼──────────────┤
│ 1 │ Node.js & Web    │ ~/Projects/web/node_mod… │   48,120 │ Clean      │ 42d ago │ 92/100 │     1.42 GB  │
│ 2 │ Rust / Cargo     │ ~/Projects/engine/target │    4,890 │ Uncommitted│ 18d ago │ 45/100 │   820.50 MB  │
│ 3 │ Python           │ ~/Projects/ai/.venv      │    6,410 │ Clean      │ 89d ago │ 85/100 │   410.20 MB  │
│ 4 │ Node.js & Web    │ ~/Projects/app/.next     │    1,210 │ Clean      │   Today │ 35/100 │   120.00 MB  │
└───┴──────────────────┴──────────────────────────┴──────────┴────────────┴─────────┴────────┴──────────────┘

                    🧟 Zombie Dev Servers & Port Hogs (2)                     
┌──────────┬────────────────┬────────────┬────────────┬───────┬───────────────────────────────────────┐
│      PID │ Name           │    Port    │     Memory │ Trees │ Command / Working Dir                 │
├──────────┼────────────────┼────────────┼────────────┼───────┼───────────────────────────────────────┤
│    48210 │ node           │   :3000    │   142.0 MB │     3 │ ~/Projects/web (Next.js Dev Server)   │
│    19420 │ python         │   :8000    │    86.4 MB │     1 │ ~/Projects/ai (FastAPI Uvicorn)       │
└──────────┴────────────────┴────────────┴────────────┴───────┴───────────────────────────────────────┘

┌───────────────────────── 📊 PURGE REAPER TELEMETRY ─────────────────────────┐
│                                                                             │
│  Reclaimable Disk Space: 2.77 GB                                            │
│  • Total Targets: 4    • Total Files: 60,630    • Zombie Servers: 2         │
│  • 🎯 High Priority Targets (Score ≥ 65): 2                                │
│  Breakdown: Node.js: 1.54 GB | Rust: 820.50 MB | Python: 410.20 MB          │
│                                                                             │
│  Scanned 840 directories in 0.015s.                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation

Install directly via `pip`:

```bash
pip install "git+https://github.com/shenald-dev/purge.git"
```

Or install the pre-built wheel directly from the [latest GitHub Release](https://github.com/shenald-dev/purge/releases/latest):

```bash
pip install https://github.com/shenald-dev/purge/releases/download/v2.0.0/purge_reaper-2.0.0-py3-none-any.whl
```

Or run via `pipx` or `uv`:

```bash
pipx install "git+https://github.com/shenald-dev/purge.git"
# or
uv tool install "git+https://github.com/shenald-dev/purge.git"
```

---

## 🛠️ Commands & Usage

### 1. Scan Workspace for Bloat (`purge scan`)
Sweep the current project tree or an entire drive for dev artifacts and running servers:

```bash
# Scan current directory
purge scan

# Scan your entire Projects directory
purge scan ~/Projects

# Filter by ecosystem
purge scan --node       # Only Node.js/Web (.next, node_modules, .astro)
purge scan --python     # Only Python (.venv, __pycache__, .pytest_cache)
purge scan --rust       # Only Rust (target/)

# Filter by staleness, minimum size, or priority score
purge scan --stale 30         # Untouched for 30+ days
purge scan --min-size 100MB   # Only items larger than 100MB
purge scan --min-score 70     # Only high-yield targets (score ≥ 70)

# Sort & limit
purge scan --sort score --top 10   # Top 10 highest-scoring targets
purge scan --sort stale            # Sort by longest untouched

# Include drive capacity radar
purge scan --disk

# Include global package manager caches
purge scan --global
```

### 2. Clean & Reclaim Disk Space (`purge clean`)
Execute safe, verified cleanup:

```bash
# Dry run simulation (calculates space without deleting)
purge clean --dry-run

# Autonomous mode: automatically clean high-scoring safe targets (Score ≥ 65)
purge clean --auto

# Quarantine mode: move to undo vault instead of permanent deletion
purge clean --vault

# Interactive selection (pick items by number e.g. 1, 3, 5)
purge clean -i

# Safeguard: Skip repositories with uncommitted git changes
purge clean --skip-uncommitted

# High-concurrency parallel deletion (4 worker threads)
purge clean --workers 4 --force

# Force purge + terminate zombie dev servers
purge clean --force --kill-zombies

# Move files to OS Trash / Recycle Bin instead of permanent deletion
purge clean --trash
```

### 3. Quarantine Vault & Undo (`purge vault`)
Safe staging and instant restoration:

```bash
# List all quarantine sessions
purge vault list

# Show items in a specific vault session
purge vault show vault_20261103_120000

# Restore quarantined items back to their original disk locations
purge vault restore vault_20261103_120000

# Permanently prune quarantine sessions older than 14 days
purge vault prune --days 14
```

### 4. Drive Capacity Radar (`purge disk` / `purge top`)
Analyze drive partition health and bloat percentage:

```bash
# Inspect drive capacity and top space consumers
purge disk

# Output machine-readable JSON
purge disk --json
```

### 5. Instant One-Shot Port Slayer (`purge free` / `purge port`)
Free any occupied development port without manually looking up PIDs:

```bash
# Inspect what process is hogging port 3000
purge free 3000

# Terminate the process and its entire child process tree
purge free 3000 --kill -y

# Alias command
purge port 5173 -k -y
```

### 6. Audit Report Exporter (`purge export`)
Export audit results to Markdown, CSV, or JSON:

```bash
# Export Markdown audit report
purge export ~/Projects --output audit_report.md

# Export CSV spreadsheet for team reviews
purge export ~/Projects --output audit_report.csv
```

### 7. Global Package Manager Caches (`purge cache`)
Audit and reclaim multi-gigabyte caches from npm, pip, uv, cargo, and more:

```bash
# Scan all global caches and show disk usage
purge cache

# Clean all discovered caches with confirmation
purge cache --clean

# Simulate cleaning without deleting
purge cache --clean --dry-run
```

### 8. Lifetime Reclamation Telemetry (`purge stats`)
Check cumulative metrics across all cleanups:

```bash
purge stats
```

---

## 🎯 Purge Scoring Engine

The Purge Score is an intelligent 0-100 composite index calculated from four primary factors:

1. **Size Factor (0-35 pts):** Logarithmic scale rewarding larger space yields (≥2GB = 35pts).
2. **Staleness Factor (0-30 pts):** Based on last-modified timestamps (≥90 days = 30pts).
3. **Ephemerality / Rebuild Cost (0-20 pts):** Pure re-generable caches (`node_modules`, `.next`, `target/`) receive full marks; virtual environments require re-installation (+12pts).
4. **Git Repository Intelligence (0-15 pts / Safety Penalties):** Repos with uncommitted changes receive an automatic **-35 point penalty** and are flagged `CAUTION`. Clean, dormant repos receive a bonus.

| Score Range | Classification | Action Recommendation |
| :--- | :--- | :--- |
| **65 - 100** | `SAFE` / High Priority | Immediate candidate for automated reclamation. |
| **35 - 64** | `MODERATE` | Review if project is actively being developed. |
| **0 - 34** | `CAUTION` | Active repository, recently modified, or uncommitted work. |

---

## 🛡️ Quarantine Vault & Undo

Never worry about accidentally deleting an active development environment:

```text
Target Path  ─────────────► [ purge clean --vault ]
                                    │
                                    ▼
                ~/.config/purge/vault/<session_id>/
                     ├── item_1 (node_modules)
                     ├── item_2 (.venv)
                     └── manifest.json

                                    │
                                    ▼
               [ purge vault restore <session_id> ]
                                    │
                                    ▼
Target Path  ◄──────────── Restored in 1 Second!
```

---

## 💾 Drive Capacity Radar

```text
┌──────────────── 💾 DISK CAPACITY & BLOAT RADAR (D:\) ────────────────┐
│                                                                      │
│  Mount: D:\    Device: D: (NTFS)                                     │
│                                                                      │
│  [████████████████░░░░░░░░░░░░░░]  53.2% Used                        │
│                                                                      │
│  • Total Capacity: 953.87 GB                                         │
│  • Used Space:     507.45 GB                                         │
│  • Free Space:     446.42 GB (46.8%)                                 │
│                                                                      │
│  • Developer Bloat: 48.60 GB                                         │
│  • Bloat accounts for 5.1% of total drive capacity (9.6% of used)    │
│  • Purging this bloat will increase free space by +10.9%             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

Configure `purge` on a per-project or workspace basis via `purge.toml` or `pyproject.toml` (`[tool.purge]`):

```toml
# purge.toml
[purge]
max_depth = 10
min_stale_days = 0.0
min_size_bytes = 0
min_score = 0.0
sort_by = "size"
workers = 4
git_aware = true
default_trash = false
default_vault = false
default_format = "terminal"

# Ignored paths or projects
ignore_paths = [
    "production-app/*",
    "legacy-service/.venv",
]

# Custom artifact target rules
[purge.custom_rules]
"Internal Caches" = [".custom_cache", "temp_artifacts"]
```

---

## 📦 Supported Bloat Targets

### Local Project Bloat

| Ecosystem | Targets Detected |
| :--- | :--- |
| **Node.js & Modern Web** | `node_modules`, `.next`, `.turbo`, `.nuxt`, `.astro`, `.solid`, `.remix`, `.output`, `.nx`, `.contentlayer`, `.parcel-cache`, `.svelte-kit`, `.docusaurus`, `bower_components` |
| **Python** | `.venv`, `venv`, `env`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, `.tox`, `.nox`, `.hypothesis`, `.ipynb_checkpoints` |
| **Rust / Cargo** | `target` *(safeguarded: verified against `Cargo.toml`)* |
| **Systems & Native** | `.build` *(Swift PM)*, `.zig-cache`, `zig-out` *(Zig)*, `CMakeFiles` *(CMake)* |
| **PHP & Ruby** | `vendor` *(safeguarded: verified against `composer.json` or `Gemfile`)* |
| **Mobile & Cross-Platform** | `.expo`, `Pods`, `.dart_tool`, `DerivedData` |
| **JVM & Build Systems** | `.gradle`, `pom.xml` target dirs, `.bloop`, `.metals`, `.kotlinc` |
| **Universal Build Dirs** | `dist`, `build`, `out`, `coverage`, `.nyc_output` |
| **OS Clutter** | `.DS_Store`, `Thumbs.db` |
| **Dev Servers** | Zombie processes on `:3000`, `:3001`, `:5173`, `:8000`, `:8080`, `:9000` |

### Global Package Manager Caches

| Package Manager | Default Cache Locations Checked |
| :--- | :--- |
| **npm** | `~/.npm/_cacache` |
| **pnpm** | `~/.local/share/pnpm/store`, `~/AppData/Local/pnpm/store` |
| **yarn** | `~/.yarn/berry/cache`, `~/.cache/yarn`, `~/AppData/Local/Yarn/Cache` |
| **Bun** | `~/.bun/install/cache` |
| **Deno** | `~/.cache/deno`, `~/AppData/Local/deno` |
| **pip** | `~/.cache/pip`, `~/AppData/Local/pip/Cache` |
| **uv** | `~/.cache/uv`, `~/AppData/Local/uv/cache` |
| **cargo** | `~/.cargo/registry/cache`, `~/.cargo/git/db` |
| **go** | `~/go/pkg/mod/cache`, `~/AppData/Local/go-build` |
| **gradle** | `~/.gradle/caches` |
| **Composer** | `~/.cache/composer`, `~/AppData/Local/Composer/cache` |
| **Bundler** | `~/.bundle/cache` |

---

## ⚙️ Architecture

```
                    ┌─────────────────────────┐
                    │   User Target Path      │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Rapid Discovery Walk   │ (Sub-20ms pruning at
                    │    (os.scandir tree)    │  artifact boundaries)
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Parallel Stat    │  │ Git Intelligence │  │ Zombie Hunter    │
│ & Scoring Pool   │  │ (Dormancy/Dirty) │  │ (Dev port trees) │
└─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘
          │                     │                     │
          └────────────────┬────┴─────────────────────┘
                           │
                           ▼
               ┌─────────────────────────┐
               │ Purge Scoring Engine    │ (0-100 Priority Index)
               │ (Size, Age, Git State)  │
               └───────────┬─────────────┘
                           │
                           ▼
               ┌─────────────────────────┐
               │  Cyberpunk Terminal HUD │
               │ & Multi-Format Exporter │
               └───────────┬─────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
 ┌───────────────────────┐   ┌───────────────────────┐
 │ Parallel Fast Deletion│   │ Quarantine Undo Vault │
 │ (Retry & RO Clearing) │   │ (Instant Restoration) │
 └───────────────────────┘   └───────────────────────┘
```

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or PR on [GitHub](https://github.com/shenald-dev/purge).

```bash
git clone https://github.com/shenald-dev/purge.git
cd purge
pip install -e ".[dev]"
pytest
ruff check .
```

---

## 📜 License

MIT License. Designed and built with ❤️ by [shenald-dev](https://github.com/shenald-dev).
