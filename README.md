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

[![PyPI Version](https://img.shields.io/pypi/v/purge-reaper.svg?color=brightgreen&style=flat-square)](https://pypi.org/project/purge-reaper/)
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
[Supported Artifacts](#-supported-bloat-targets) •
[Safety Guarantees](#-safety--safeguards) •
[Architecture](#-architecture)

---

</div>

## 💥 The Problem

Developers work across dozens of repositories every year. After 6 months, their laptops hoard **40GB to 80GB** of forgotten developer debris:

- **Dormant `node_modules`** from tutorials or projects untouched in 9 months.
- **Massive Rust `target/` folders** silently holding 15GB each.
- **Abandoned Python `.venv` environments** and build artifacts (`dist`, `.next`, `.turbo`).
- **Zombie Dev Servers** left running in background tabs, hogging port `3000` or `:8000`, draining RAM, and causing annoying `EADDRINUSE` errors.

Existing tools are fragmented: `npkill` only cleans npm; `cargo clean` requires entering each folder individually; Docker system prunes only touch containers; and finding port hogs requires cryptic `lsof -i :3000` and `kill -9` terminal incantations.

**`purge` is a unified, blazing-fast reaper.** It scans your projects in parallel, prunes traversal at artifact boundaries, identifies live zombie server processes, and lets you reclaim 50GB in a single command.

---

## ⚡ Key Features

- ⚡ **Sub-Second Parallel Crawl:** Never waits for 100,000 files inside `node_modules`—prunes traversal at candidate boundaries and calculates sizes concurrently.
- 🧟 **Zombie Process & Port Hog Reaper:** Instantly uncovers orphaned Node, Python, Vite, and Next.js servers clinging to ports `:3000`, `:5173`, or `:8000`.
- 🛡️ **Zero Accidental Data Loss:** Built-in safeguards protect `.git`, root filesystems, OS directories, and user profile folders. Features non-destructive `--dry-run` simulation.
- 🕒 **Stale Age Intelligence:** Spot abandoned projects at a glance with `--stale 30` (only flag artifacts untouched for 30+ days).
- 🎨 **Cyberpunk Terminal Radar:** High-density Rich diagnostic tables, size-coded color badges, and particle counters.
- 🤖 **Machine-Readable JSON Mode:** Use `--json` for scripted automations, CI workflows, or custom devtool integration.

---

## 💻 Terminal UI

When you run `purge scan` across your workspace:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│   🧹 Developer Bloat & Zombie Process Reaper • Zero Bloat                   │
└─────────────── v0.1.0 • https://github.com/shenald-dev/purge ───────────────┘

                       📦 Reclaimable Bloat Targets (4)                        
┌──────┬──────────────────┬─────────────────────────┬──────────┬────────────┬──────────────┐
│    # │ Category         │ Path                    │    Files │      Stale │         Size │
├──────┼──────────────────┼─────────────────────────┼──────────┼────────────┼──────────────┤
│    1 │ Node.js & Web    │ ~/Projects/web/node_mod…│   48,120 │    42d ago │     1.42 GB  │
│    2 │ Rust / Cargo     │ ~/Projects/engine/target│    4,890 │    18d ago │   820.50 MB  │
│    3 │ Python           │ ~/Projects/ai/.venv     │    6,410 │    89d ago │   410.20 MB  │
│    4 │ Node.js & Web    │ ~/Projects/app/.next    │    1,210 │      Today │   120.00 MB  │
└──────┴──────────────────┴─────────────────────────┴──────────┴────────────┴──────────────┘

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
│  Breakdown: Node.js: 1.54 GB | Rust: 820.5 MB | Python: 410.2 MB            │
│                                                                             │
│  Scanned 840 directories in 0.42s.                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation

Install via pip:

```bash
pip install purge-reaper
```

Or install with `uv` / `pipx`:

```bash
uv tool install purge-reaper
# or
pipx install purge-reaper
```

---

## 🛠️ Commands & Usage

### 1. Scan Current Directory
Sweep the current project tree for bloat and running dev servers:

```bash
purge scan
```

### 2. Scan an Entire Drive or Projects Folder
Point `purge` to your root workspace:

```bash
purge scan ~/Projects
# or on Windows
purge scan D:\Projects
```

### 3. Filter by Ecosystem
Focus on specific technology stacks:

```bash
purge scan --node       # Only Node.js/Web (.next, node_modules)
purge scan --python     # Only Python (.venv, __pycache__)
purge scan --rust       # Only Rust (target/)
```

### 4. Target Stale Projects
Only find artifacts that haven't been modified in 30+ days:

```bash
purge scan --stale 30
```

### 5. Find & Slay Port Hogs
Instantly see what process is hogging port 3000:

```bash
purge zombies --port 3000
# Slay it:
purge zombies --port 3000 --kill -y
```

### 6. Clean / Reclaim Disk Space
Execute cleanup with safety checks:

```bash
# Dry run simulation (calculates space without deleting)
purge clean --dry-run

# Interactive purge (prompts before deleting)
purge clean

# Force purge + terminate zombie dev servers
purge clean --force --kill-zombies
```

---

## 📦 Supported Bloat Targets

| Ecosystem | Targets Detected |
| :--- | :--- |
| **Node.js & Web** | `node_modules`, `.next`, `.turbo`, `.nuxt`, `.parcel-cache`, `.svelte-kit`, `.docusaurus`, `bower_components` |
| **Python** | `.venv`, `venv`, `env`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `__pycache__`, `.tox`, `.nox` |
| **Rust / Cargo** | `target` *(safeguarded: verified against `Cargo.toml`)* |
| **Java & Gradle** | `.gradle`, `pom.xml` target dirs |
| **Build Artifacts** | `dist`, `build`, `out`, `coverage`, `.nyc_output` |
| **OS Clutter** | `.DS_Store`, `Thumbs.db` |
| **Dev Servers** | Zombie processes on `:3000`, `:3001`, `:5173`, `:8000`, `:8080`, `:9000` |

---

## 🛡️ Safety & Safeguards

`purge` is engineered with defensive guardrails to prevent accidental data loss:

1. **Immune Roots**: Will never delete or scan root paths (`/`, `C:\`, `C:\Windows`, `~/.ssh`).
2. **Git Invariant**: Directory traversal strictly ignores `.git`, preserving all repository histories and stashes.
3. **Manifest Verification**: Ambiguous folder names like `target` or `build` are only flagged if a corresponding project manifest (`Cargo.toml`, `package.json`, `pyproject.toml`) exists.
4. **Dry-Run by Default**: Review the exact path and byte delta before confirming deletion.

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
               ┌────────────────┴────────────────┐
               ▼                                 ▼
    ┌──────────────────────┐          ┌──────────────────────┐
    │ Parallel Stat Pool   │          │ Zombie Hunter Pool   │
    │ (Concurrent threads) │          │ (psutil dev ports)   │
    └──────────┬───────────┘          └──────────┬───────────┘
               │                                 │
               └────────────────┬────────────────┘
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
                    │ (Readonly unblocker)    │
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
