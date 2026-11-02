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

*Reclaim 50GB of dev debris and slay zombie dev servers in 3 seconds.*

[![GitHub Release](https://img.shields.io/github/v/release/shenald-dev/purge?color=00d4ff&style=flat-square&logo=github)](https://github.com/shenald-dev/purge/releases)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg?style=flat-square)](LICENSE)
[![CI Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg?style=flat-square)](https://github.com/shenald-dev/purge/actions)
[![Speed](https://img.shields.io/badge/speed-%3C1s-cyan.svg?style=flat-square)](#architecture)
[![Zero Bloat](https://img.shields.io/badge/bloat-zero-success.svg?style=flat-square)](#quick-start)

---

[The Problem](#-the-problem) •
[Features](#-key-features) •
[Terminal UI](#-terminal-ui) •
[Quick Start](#-quick-start) •
[Commands](#-commands--usage) •
[Configuration](#-configuration) •
[Supported Artifacts](#-supported-bloat-targets) •
[Safety Guarantees](#-safety--safeguards) •
[Architecture](#-architecture)

---

</div>

## 💥 The Problem

Modern developers juggle dozens of repositories and tools every month. After a few weeks, engineering laptops silently hoard **40GB to 100GB+** of developer debris:

- **Abandoned `node_modules`** from tutorials and archived experiments.
- **Massive Rust `target/` directories** silently consuming 15GB each.
- **Dormant Python `.venv` environments** and build artifacts (`dist`, `.next`, `.turbo`, `.astro`).
- **Bloated Global Package Caches** (`npm`, `pnpm`, `pip`, `uv`, `cargo`) accumulating stale tarballs indefinitely.
- **Zombie Dev Servers** left running in background terminal tabs, holding ports `:3000`, `:5173`, or `:8000`, draining RAM, and causing frustrating `EADDRINUSE` errors.

Existing tools are fragmented: `npkill` only cleans npm; `cargo clean` requires manually visiting each repository; `docker prune` only handles containers; and finding port hogs requires cryptic `lsof -i :3000` and `kill -9` terminal dances.

**`purge` is a unified, blazing-fast reaper.** It scans your workspaces concurrently, prunes directory traversal at artifact boundaries, audits global caches, slays process trees holding your dev ports, and lets you reclaim 50GB in seconds.

---

## ⚡ Key Features

- ⚡ **Sub-Second Parallel Crawl:** Never gets bogged down by millions of files inside `node_modules`—prunes traversal at candidate boundaries and sizes directories concurrently.
- 🧟 **Process Tree Port Slayer (`purge free <PORT>`):** Free ports in one command. Recursively terminates parent processes and all orphaned child worker trees (`SIGTERM` -> `SIGKILL` cascade).
- 🌐 **Global Cache Auditing & Pruning (`purge cache`):** Discovers and purges multi-gigabyte package manager global caches (`npm`, `pnpm`, `yarn`, `pip`, `uv`, `cargo`, `go`, `gradle`).
- 🌿 **Git Worktree Intelligence:** Non-destructive scan flags repositories with uncommitted changes (`--git-aware`, `--skip-uncommitted`) and displays last-commit age indicators.
- 📈 **Lifetime Reclamation Telemetry (`purge stats`):** Persistent local telemetry tracking cumulative bytes reclaimed and zombie processes terminated over time.
- 🎯 **Interactive Selection Mode (`-i / --interactive`):** Pick and choose specific artifacts via numbers or comma-separated lists before purging.
- ⚙️ **Declarative Configuration (`purge init`):** Native `purge.toml` and `pyproject.toml [tool.purge]` support for team-level ignore paths, custom target rules, and depth limits.
- 🛡️ **Zero Accidental Data Loss:** Built-in safeguards protect `.git`, root filesystems, OS directories, and user profile folders. Features non-destructive `--dry-run` simulation and trash bin movement (`--trash`).
- 🤖 **Machine-Readable JSON Mode:** Full `--json` flag on all commands for scripted automations, CI workflows, or custom devtool integration.

---

## 💻 Terminal UI

When you run `purge scan` across your workspace:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│   🧹 Developer Bloat & Zombie Process Reaper • Zero Bloat                   │
└─────────────── v1.0.0 • https://github.com/shenald-dev/purge ───────────────┘

                       📦 Reclaimable Bloat Targets (4)                        
┌───┬──────────────────┬──────────────────────────┬──────────┬────────────┬─────────────┬──────────────┐
│ # │ Category         │ Path                     │    Files │ Git Status │       Stale │         Size │
├───┼──────────────────┼──────────────────────────┼──────────┼────────────┼─────────────┼──────────────┤
│ 1 │ Node.js & Web    │ ~/Projects/web/node_mod… │   48,120 │ Clean      │     42d ago │     1.42 GB  │
│ 2 │ Rust / Cargo     │ ~/Projects/engine/target │    4,890 │ Uncommitted│     18d ago │   820.50 MB  │
│ 3 │ Python           │ ~/Projects/ai/.venv      │    6,410 │ Clean      │     89d ago │   410.20 MB  │
│ 4 │ Node.js & Web    │ ~/Projects/app/.next     │    1,210 │ Clean      │       Today │   120.00 MB  │
└───┴──────────────────┴──────────────────────────┴──────────┴────────────┴─────────────┴──────────────┘

                    🧟 Zombie Dev Servers & Port Hogs (2)                     
┌──────────┬────────────────┬────────────┬────────────┬───────────────────────────────────────┐
│      PID │ Name           │    Port    │     Memory │ Command / Working Dir                 │
├──────────┼────────────────┼────────────┼────────────┼───────────────────────────────────────┤
│    48210 │ node           │   :3000    │   142.0 MB │ ~/Projects/web (Next.js Dev Server)   │
│    19420 │ python         │   :8000    │    86.4 MB │ ~/Projects/ai (FastAPI Uvicorn)       │
└──────────┴────────────────┴────────────┴────────────┴───────────────────────────────────────┘

┌───────────────────────── 📊 PURGE REAPER TELEMETRY ─────────────────────────┐
│                                                                             │
│  Reclaimable Disk Space: 2.77 GB                                            │
│  • Total Targets: 4    • Total Files: 60,630    • Zombie Servers: 2         │
│  Breakdown: Node.js: 1.54 GB | Rust: 820.50 MB | Python: 410.20 MB          │
│                                                                             │
│  Scanned 840 directories in 0.42s.                                          │
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
pip install https://github.com/shenald-dev/purge/releases/download/v1.0.0/purge_reaper-1.0.0-py3-none-any.whl
```

Or run via `pipx` or `uv`:

```bash
pipx install "git+https://github.com/shenald-dev/purge.git"
# or
uv tool install "git+https://github.com/shenald-dev/purge.git"
```

---

## 🛠️ Commands & Usage

### 1. Scan Workspace for Bloat
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

# Filter by staleness or minimum size
purge scan --stale 30         # Untouched for 30+ days
purge scan --min-size 100MB   # Only items larger than 100MB

# Include global package manager caches
purge scan --global
```

### 2. Instant One-Shot Port Slayer (`free` / `port`)
Free any occupied development port without manually looking up PIDs:

```bash
# Inspect what process is hogging port 3000
purge free 3000

# Terminate the process and its entire child process tree
purge free 3000 --kill -y

# Alias command
purge port 5173 -k -y
```

### 3. Global Package Manager Caches (`cache`)
Audit and reclaim multi-gigabyte caches from npm, pip, uv, cargo, and more:

```bash
# Scan all global caches and show disk usage
purge cache

# Clean all discovered caches with confirmation
purge cache --clean

# Simulate cleaning without deleting
purge cache --clean --dry-run
```

### 4. Clean & Reclaim Disk Space (`clean`)
Execute safe, verified cleanup:

```bash
# Dry run simulation (calculates space without deleting)
purge clean --dry-run

# Interactive selection (pick items by number e.g. 1, 3, 5)
purge clean -i

# Safeguard: Skip repositories with uncommitted git changes
purge clean --skip-uncommitted

# Force purge + terminate zombie dev servers
purge clean --force --kill-zombies

# Move files to OS Trash / Recycle Bin instead of permanent deletion
purge clean --trash
```

### 5. Lifetime Reclamation Telemetry (`stats`)
Check cumulative metrics across all cleanups:

```bash
purge stats
```

### 6. Project Configuration (`init`)
Generate a starter `purge.toml` configuration:

```bash
purge init
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
git_aware = true
default_trash = false
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
| **Node.js & Modern Web** | `node_modules`, `.next`, `.turbo`, `.nuxt`, `.astro`, `.solid`, `.remix`, `.output`, `.parcel-cache`, `.svelte-kit`, `.docusaurus`, `bower_components` |
| **Python** | `.venv`, `venv`, `env`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, `.tox`, `.nox`, `.hypothesis` |
| **Rust / Cargo** | `target` *(safeguarded: verified against `Cargo.toml`)* |
| **Mobile & Cross-Platform** | `.expo`, `Pods`, `.dart_tool`, `DerivedData` |
| **JVM & Build Systems** | `.gradle`, `pom.xml` target dirs, `.bloop`, `.metals` |
| **Universal Build Dirs** | `dist`, `build`, `out`, `coverage`, `.nyc_output` |
| **OS Clutter** | `.DS_Store`, `Thumbs.db` |
| **Dev Servers** | Zombie processes on `:3000`, `:3001`, `:5173`, `:8000`, `:8080`, `:9000` |

### Global Package Manager Caches

| Package Manager | Default Cache Locations Checked |
| :--- | :--- |
| **npm** | `~/.npm/_cacache` |
| **pnpm** | `~/.local/share/pnpm/store`, `~/AppData/Local/pnpm/store` |
| **yarn** | `~/.yarn/berry/cache`, `~/.cache/yarn`, `~/AppData/Local/Yarn/Cache` |
| **pip** | `~/.cache/pip`, `~/AppData/Local/pip/Cache` |
| **uv** | `~/.cache/uv`, `~/AppData/Local/uv/cache` |
| **cargo** | `~/.cargo/registry/cache`, `~/.cargo/git/db` |
| **go** | `~/go/pkg/mod/cache` |
| **gradle** | `~/.gradle/caches` |

---

## 🛡️ Safety & Safeguards

`purge` is engineered with defensive guardrails to prevent accidental data loss:

1. **Immune Roots**: Will never delete or scan root paths (`/`, `C:\`, `C:\Windows`, `~/.ssh`).
2. **Git Awareness**: Directory traversal strictly ignores `.git`, preserving all repository histories and stashes. With `--skip-uncommitted`, repos with dirty working trees are automatically protected.
3. **Manifest Verification**: Ambiguous folder names like `target` or `build` are only flagged if a corresponding project manifest (`Cargo.toml`, `package.json`, `pyproject.toml`) exists.
4. **Process Tree Validation**: Port termination recursively walks the process family to prevent zombie orphaned processes while validating against system-critical PIDs.
5. **Dry-Run & Trash Bin Options**: Full simulation mode (`--dry-run`) and OS Recycle Bin support (`--trash`) ensure safety before permanent deletion.

---

## ⚙️ Architecture

```
                    ┌─────────────────────────┐
                    │   User Target Path      │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Rapid Discovery Walk   │ (Prunes traversal at
                    │    (os.scandir tree)    │  artifact boundaries)
                    └───────────┬─────────────┘
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
    ┌──────────────────────┐ ┌────────────────┐ ┌──────────────────────┐
    │ Parallel Stat Pool   │ │ Git Inspector  │ │ Zombie Hunter Pool   │
    │ (Concurrent threads) │ │ (Branch/Dirty) │ │ (psutil dev ports)   │
    └──────────┬───────────┘ └───────┬────────┘ └──────────┬───────────┘
               │                     │                     │
               └────────────────┬────┴─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Purge Telemetry HUD   │
                    │  (Rich Cyberpunk TUI)   │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Safe Cleaner & Sslayer │
                    │ (Process Tree Killing)  │
                    └─────────────────────────┘
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
