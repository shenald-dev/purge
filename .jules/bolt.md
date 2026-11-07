
## 2023-10-27 — Fix Partition Mapping
- **Learning:** `os.path.splitdrive` returns empty strings for both strings on POSIX systems, and `os.path.normpath` + `startswith` string matching is unreliable for cross-platform partition detection (e.g. `C:\` vs `C:\Windows`).
- **Action:** For accurate cross-OS path resolution, dynamically select `ntpath` or `posixpath` based on path characteristics (slashes or drive letters) and use `commonpath` to robustly evaluate if a path resides within a mountpoint.
