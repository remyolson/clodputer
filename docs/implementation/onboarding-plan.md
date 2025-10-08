# Clodputer Onboarding Experience – Implementation Plan

## Context

Current onboarding requires users to:

- Manually install Clodputer (PyPI/Homebrew/source).
- Export environment variables (`CLODPUTER_CLAUDE_BIN`, `CLODPUTER_EXTRA_ARGS`).
- Create the `~/.clodputer` hierarchy by hand, copy templates, and optionally craft an MCP secrets file.
- Manually run first tasks, install cron entries, start the watcher, and launch the dashboard.

This friction is highlighted in `docs/user/quick-start.md`, which guides users through many discrete shell commands. The aim is to collapse this into a guided CLI workflow that configures Clodputer, integrates with Claude Code, and validates the environment in one path.

## Goals

1. **Single-command onboarding** invoked as `clodputer init` (or similar).
2. **Zero duplication of MCP credentials** – reuse Claude Code’s configuration wherever possible.
3. **Automatic discovery of the Claude CLI binary and flags** without requiring env vars.
4. **Guided permissions** (e.g., Terminal automation for menu bar) with clear prompts.
5. **Self-service automation setup** – offer options to schedule a sample task, start the watcher, and launch the dashboard.
6. **Updated documentation** reflecting the new flow while retaining advanced manual steps as references.

## Proposed User Flow (CLI)

```
$ clodputer init
▶ Pre-flight checks (Python version, macOS version)
▶ Locate Claude CLI (search PATH, common install locations, optional manual entry)
▶ Detect existing Claude Code MCP registrations
▶ Offer to copy/update CLAUDE.md entry for Clodputer (if needed)
▶ Create ~/.clodputer/ directories & default config
▶ Prompt for optional features:
   • Import starter task (email summary, calendar sync, etc.)
   • Install cron job for the selected task
   • Enable file watcher for a chosen directory template
   • Launch dashboard & menu bar (will request automation permissions)
▶ Run basic smoke test (execute selected starter task once)
▶ Surface next steps + doctor report
```

Each step should provide “Skip” options and display the exact changes being made to give advanced users control.

## Implementation Breakdown

### 1. CLI Command (`clodputer init`)

- Add a Click command in `src/clodputer/cli.py`.
- Encapsulate onboarding logic in a new module (`src/clodputer/onboarding.py`) to keep CLI tidy.
- Use a state object to collect user choices and detected paths.
- Provide clear logging and dry-run mode for power users.

### 2. Claude CLI Discovery

- Use `shutil.which("claude")` as the default search.
- Fall back to known install locations (e.g., `~/.claude/local/claude`).
- Optionally spawn `claude --version` to validate the binary.
- Store the resolved path in `.clodputer/env` (or inject into exported cron entries) without requiring manual `export`.
- Update executor/cron modules to consume the persisted path if env vars are absent.

### 3. MCP Configuration Strategy

- Assume Claude Code already has MCP connections configured. Avoid duplicating secrets.
- When onboarding templates require MCP access, instruct Claude Code via the prompt (e.g., include helper text in CLAUDE.md).
- For context variables that previously referenced `{{ secrets.* }}`, switch templates to use prompts that rely on Claude Code’s existing MCP auth.
- Update docs to clarify that MCP changes are made through Claude Code, not Clodputer.

### 4. Filesystem Setup

- Automatically create `~/.clodputer/{tasks,logs,archive}` directories.
- Sync packaged templates from `src/clodputer/templates/` to the user directory on demand.
- Optionally prompt the user to rename/edit the starter task using guided questions (e.g., schedule time, directories to watch).

### 5. Automation Options

- Cron:
  - If the user opts in, call existing `install` helpers with the prepared configuration.
  - Report exact cron entries and allow preview before applying.
- Watcher:
  - Configure file paths interactively.
  - Offer to start the watcher in daemon mode immediately.
- Dashboard / Menu bar:
  - Launch the dashboard/menu app as part of the flow, catching AppleScript automation prompts.
  - Provide instructions if permissions are denied, including how to re-run the step.

### 6. Smoke Test & Diagnostics

- After configuration, execute a sample task to confirm the pipeline works (reuse `TaskExecutor`).
- Run `doctor` and display the results inline, highlighting any remaining actions (e.g., Claude CLI not reachable).
- Persist onboarding results to a log (`~/.clodputer/onboarding.log`) for support purposes.

### 7. Documentation Updates

- Quick Start should reference the single-command setup first, moving manual steps to an “Advanced” section.
- Add onboarding instructions to `README.md` and installation guide.
- Document the new CLI command in `docs/user/cli-reference.md` (create if missing).
- Update Troubleshooting to mention how to re-run onboarding or adjust detected paths.

## Technical Considerations

- **State persistence:** Consider a small config file (e.g., `~/.clodputer/env`) to store detected paths and onboarding answers so subsequent commands can reuse them.
- **Idempotency:** Re-running `clodputer init` should update existing config rather than duplicating work. Provide `--reset` to start fresh.
- **Modularity:** Implementation should keep existing modules decoupled. Onboarding can reuse functions from `config`, `cron`, `queue`, etc., rather than reimplementing logic.
- **Tests:** Add unit tests for onboarding helpers (path detection, template selection) and integration tests that simulate user responses with Click’s `CliRunner`.
- **Permissions:** The flow should clearly explain why automation permissions are needed and provide instructions if macOS prompts appear.

## Open Questions / Next Steps

- Can Clodputer query Claude Code for MCP configuration details programmatically (e.g., via Claude Code CLI commands) to tailor template prompts?
- How do we best integrate CLAUDE.md updates with onboarding to ensure Claude Code “knows” about Clodputer without manual steps?
- Should onboarding offer to create Homebrew/PyPI installs automatically when running from source (or simply recommend best practices)?
- What guardrails are needed for users who already have tasks and cron jobs configured (e.g., merge vs. overwrite)?

## Conclusion

This plan shifts Clodputer’s onboarding from a manual, documentation-driven checklist to a guided CLI experience. By leveraging existing modules for cron, watcher, and executor functionality, and persisting detected state, the user journey becomes: `brew tap && brew install`, then `clodputer init` – with the tool handling the rest. Implementation should proceed iteratively, beginning with the new CLI command and path detection before layering optional features like template selection and automation enablement.

---

## Implementation Phases & Checklists

### Phase 0 – Codebase Alignment & Cleanup
- [x] Remove or relocate legacy sample files (e.g., root-level `email-management.yaml`) in favor of packaged templates.
- [x] Wire the new `clodputer.templates` module into the CLI (list/export helper) so onboarding can reuse existing functions.
- [x] Centralize Claude CLI path resolution in a shared utility consumed by executor, cron, and onboarding.
- [x] Update cron/environment handling to read the persisted CLI path and avoid mandatory `CLODPUTER_CLAUDE_BIN` exports.
- [x] Review documentation references to manual MCP secret files (`docs/user/mcp-authentication.md`, quick start, installation) and align messaging with Claude Code–managed creds.
- [x] Run `ruff`, `pytest`, and `pytest --cov` to ensure a clean baseline before onboarding changes.

### Phase 1 – Foundations
- [ ] Introduce `clodputer.init` Click command with scaffolding and logging.
- [ ] Implement path detection helpers for Claude CLI (search PATH + common installs).
- [ ] Persist detected paths/settings to `~/.clodputer/env` for reuse.
- [ ] Update executor/cron to fallback to persisted paths when env vars are absent.

### Phase 2 – Guided Setup Workflow
- [ ] Build interactive prompts (yes/no/options) for key onboarding decisions.
- [ ] Implement directory creation (`tasks`, `logs`, `archive`) within onboarding.
- [ ] Sync packaged templates to user space with selection UI (choose starter task).
- [ ] Integrate CLAUDE.md update step, including diff preview before applying.

### Phase 3 – Automation Enablement
- [ ] Add cron setup option: show proposed entries, confirm, then install.
- [ ] Add file watcher setup: configure directory/pattern interactively, start daemon.
- [ ] Provide ability to launch dashboard/menu app with clear permission guidance.
- [ ] Run smoke test (execute chosen task once) and render results inline.

### Phase 4 – Diagnostics & Idempotency
- [ ] Trigger `clodputer doctor` at the end of onboarding and summarize key findings.
- [ ] Teach `clodputer doctor` to report persisted CLI path/onboarding state (warn when missing).
- [ ] Ensure re-running `clodputer init` updates existing config instead of duplicating.
- [ ] Add `--reset` flag to wipe onboarding cache and start fresh.
- [ ] Log onboarding transcript to `~/.clodputer/onboarding.log` for support.

### Phase 5 – Documentation & Tests
- [ ] Rewrite quick-start and installation docs to highlight `clodputer init`.
- [ ] Document the new command in CLI reference/user guides.
- [ ] Add unit tests for onboarding helpers (path detection, template sync).
- [ ] Add integration test covering the overall CLI flow with mocked user input.
