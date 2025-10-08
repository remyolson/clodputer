# Clodputer Implementation Roadmap – V2

This document charts the next wave of improvements, using the original planning package in `docs/planning/` as our north star. Each initiative references the relevant sections of the approved specs.

## Phase 4: Advanced Scheduling & Reliability

### 4.1 Multi-Trigger Scheduling (ref. 05-finalized-specification.md §“Future Enhancements”)
- [x] Extend cron parser to support named schedules (e.g., `@workdays`, `@weekends`).
- [x] Integrate interval-based triggers (`trigger.type: interval`) deferred from Phase 1.
- [x] Expose schedule simulation command (`clodputer schedule-preview <task>`).
- [x] Update `doctor` to validate upcoming runs across cron/interval triggers.
- **Deliverables**: Alias resolution with comments in crontab, interval → cron conversion, `schedule-preview` CLI with `croniter`, doctor checks for cron preview, docs/examples refreshed.

### 4.2 Smart Queue Management (ref. planning/09-safety-features.md “Resource Management”)
- [x] Add optional concurrency limits with resource heuristics (config-driven).
- [x] Implement exponential backoff retry policy (per task, default off).
- [x] Persist per-task metrics (success rate, avg duration) for reporting.
- [x] Enhance `clodputer queue` to display retry/backoff state.
- **Deliverables**: Added `~/.clodputer/config.yaml` settings loader, CPU/memory gating, automatic retry with exponential delay, structured logging of attempts, queue CLI shows attempt/not-before, doctor reports metrics. Metrics tracked in `metrics.json` with CLI summary.

## Phase 5: Observability & Dashboard

### 5.1 Structured Log Enhancements (ref. planning/05-finalized-specification.md “Logging System”)
- [x] Introduce log rotation policy retention (6 months) with CLI pruning.
- [x] Add contextual metadata (exit codes, MCP usage metrics) to JSON events.
- [x] Build `clodputer logs --json` for raw machine-readable output.
- **Notes**: Logger now records return codes, parse errors, and prunes archives to the 6 most recent files. `clodputer logs --json` exposes the structured stream for dashboards/scripting.

### 5.2 Terminal Dashboard (ref. planning/07-menu-bar-ui.md & 10-implementation-details.md)
- [x] Implement curses-based dashboard showing live queue/logs/resources.
- [x] Add hotkeys for task details, log tailing, and watcher status.
- [x] Integrate menu bar “Launch Dashboard” with full-screen UI.
- **Notes**: `clodputer dashboard` launches the full-screen curses UI with overlays for queue metrics, deep log tail, and watcher diagnostics; menu bar shortcut now runs the same command.

## Phase 6: Distribution & Ecosystem

### 6.1 Packaging (ref. planning/08-installation-and-integration.md “Installation Process”)
- [x] Publish Homebrew formula (`brew install clodputer`).
- [x] Package PyPI distribution with console entry points.
- [x] Provide signed binaries / notarization guidelines.
- [x] Ensure CI enforces ≥85% coverage and fails on regressions.
- **Notes**: Added `packaging/homebrew/Formula/clodputer.rb` plus the generator script, documented release steps in `docs/dev/packaging.md`, codified notarisation flow, and enforced the coverage gate via `--cov-fail-under=85`.

### 6.2 Template & MCP Ecosystem (ref. planning/SUMMARY.md “Use Cases”)
- [x] Expand template library (calendar automation, todo triage).
- [x] Document best practices for MCP authentication (guides + code samples).
- [x] Provide community-driven template submission process.
- **Notes**: Packaged templates now live under `src/clodputer/templates/` with symlinked browsing copies, new `calendar-sync` and `todo-triage` recipes, MCP auth guidance for secrets, and a contributor workflow in `docs/dev/templates.md`.

## Tracking & Metrics

- Maintain progress updates in this document and mirror them in `docs/implementation/PROGRESS.md`.
- For each phase, log manual test results and update diagnostics to cover new features.
- Revisit `docs/dev/release.md` before shipping each milestone, ensuring the release checklist is complete.
- Target ≥85% coverage across `src/clodputer` and keep `pytest --cov` green in CI.

---

_Revision date: 2025-10-07_  
_References: planning/05-finalized-specification.md, planning/07-menu-bar-ui.md, planning/09-safety-features.md, planning/SUMMARY.md_
