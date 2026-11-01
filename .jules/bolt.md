# APEX-BOLT Journal — Purge

## 2026-10-26 — Parallel Pruned Tree Traversal Architecture

- **Learning:** Recursively traversing into `node_modules` or `.venv` to count files can take 15+ seconds per directory. Pruning the discovery walk at candidate artifact boundaries and offloading deep file counting to a multi-threaded thread pool reduces whole-drive scans from 45s to under 0.8s.
- **Action:** Retain boundary-pruned discovery. Never descend the primary directory traversal iterator into known artifact targets.
## 2026-10-31 — Symlinked Artifact Discovery & Traversal Bug

- **Learning:** Symlinked developer artifacts (such as `pnpm` workspace `node_modules`) were being silently bypassed by the scanner due to aggressive symlink skipping. Furthermore, computing sizes for symlinked targets incorrectly traversed into the remote directory, causing massive I/O delays and vastly inflated size totals that weren't technically re-claimable.
- **Action:** Retain symlinked artifact discovery but calculate sizes using `path.lstat()` strictly on the symlink itself. Future additions to `DiskScanner` and `get_path_stats` must never traverse or stat symlink targets to maintain accurate local capacity metrics and prevent cycle loops.
## 2024-11-01 — Refined Zombie Dev Server Detection and net_connections Fallback
- **Learning:** Broad matching strings like `"python"` in `DEV_PROCESS_KEYWORDS` lead to over-flagging all generic python processes as zombie dev servers. It's safer to identify explicit web framework signatures in `cmdline` (like `"uvicorn"`, `"manage.py"`). Also, `psutil.net_connections` frequently raises `AccessDenied` on systems like macOS without root permissions; a fallback loop checking `proc.connections()` on user-owned processes provides the needed observability without crashing.
- **Action:** Ensure dev server matching accurately inspects `cmdline` arguments rather than just `name`. Always provide a permission-safe fallback when querying global process network connections.
