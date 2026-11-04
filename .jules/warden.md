## 2024-05-18 — Lifecycle & Assurance Ledger
- **QA & Veto Actions:** Fixed a regression where `is_protected_path(Path("C:\\"))` was returning False. Unresolved paths (e.g. PureWindowsPath) could bypass the root protection rule since they resolved differently on POSIX. Added check for `str(path)` and `str(path).rstrip("\\/")` against `CRITICAL_SYSTEM_PATHS`. Verified that tests now pass successfully.
- **Entropy Pruned:** Checked codebase using vulture, the reported "unused" items are mostly callbacks required by Typer and mock objects used in tests. Did not remove them as they are functionally necessary.
- **Deferred / Blocked:** None.

## 2026-11-03 — Lifecycle & Assurance Ledger
- **QA & Veto Actions:** Added edge-case unit tests to `test_rules_advanced.py` to ensure `is_protected_path` handles `str(path)` combinations robustly (testing `PureWindowsPath` on Posix and vice versa), and `test_cli_coverage.py` to verify `render_port_status` properly accepts `None` for the newly modified `Optional[ZombieProcess]` typing.
- **Entropy Pruned:** Checked codebase using vulture. No dead code found to prune; existing items flagged are false positive Typer callbacks and mock attributes.
- **Deferred / Blocked:** Skipped dependency hygiene (Safe Patch/Minor) as no `.lock` file exists in the repository to verify safe upgrades.

## 2026-11-04 — Lifecycle & Assurance Ledger
- **QA & Veto Actions:** Verified recent commits adding test coverage for vault and zombies.
- **Entropy Pruned:** Removed unused PROTECTED from SafetyLevel and quarantined_at from VaultItem (3 lines deleted).
- **Deferred / Blocked:** Skipped dependency hygiene since no lockfile exists.
