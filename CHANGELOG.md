# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-10-07

### Added
- Sequential task queue with atomic persistence and lockfile protection.
- Task executor with PID-tracked cleanup and structured logging.
- Cron integration (`clodputer install/uninstall`) with diagnostics.
- File watcher daemon with CLI controls and metadata-enriched queue entries.
- macOS menu bar application (`clodputer menu`).
- Comprehensive CLI (`run`, `status`, `logs`, `queue`, `watch`, `doctor`, etc.).
- User and developer documentation plus ready-to-use task templates.
- GitHub Actions CI running linting and tests.

### Changed
- Enhanced configuration validation with readable error messages and tool checks.
- Automatic queue recovery when `queue.json` becomes corrupted.

### Known Issues
- Scheduled jobs require the Claude CLI binary to be accessible in cron's environment. Export `CLODPUTER_CLAUDE_BIN` before running `clodputer install`.
