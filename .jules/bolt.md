
## 2026-11-06 — Security Vulnerability Fix
- **Learning:** Path resolution before checking `is_protected_path` can mutate cross-platform paths (e.g., `PureWindowsPath('C:\')` resolving to a local posix path like `/app/C:\`), bypassing the critical system path checks.
- **Action:** Always check paths with `is_protected_path` *before* calling `.resolve()` to maintain cross-platform safety against malicious or accidental scanning of root partitions like `C:\`.
