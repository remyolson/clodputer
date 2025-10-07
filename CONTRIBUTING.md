# Contributing to Clodputer

Welcome! This document will get you started on implementing Clodputer.

## 🚀 Quick Start for Engineers

### Prerequisites

- **Python 3.9+** (check with `python3 --version`)
- **Claude Code** installed and configured
- **macOS** (this is macOS-first for MVP)
- **Git** for version control

### Initial Setup

```bash
# 1. Clone the repository (if not already cloned)
git clone https://github.com/remyolson/clodputer.git
cd clodputer

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# 3. Install dependencies in development mode
pip install -e ".[dev]"

# 4. Verify installation
python -c "import clodputer; print('✅ Package imported successfully')"
```

## 📚 Where to Start

### 1. Read the Planning Docs (30 minutes)

**Essential reading** (in order):
1. **[docs/planning/00-START-HERE.md](docs/planning/00-START-HERE.md)** - Overview and navigation
2. **[docs/planning/05-finalized-specification.md](docs/planning/05-finalized-specification.md)** - Complete technical spec
3. **[docs/planning/10-implementation-details.md](docs/planning/10-implementation-details.md)** - Library choices and code examples

**Reference as needed**:
- **[docs/planning/09-safety-features.md](docs/planning/09-safety-features.md)** - Safety mechanisms
- **[docs/planning/SUMMARY.md](docs/planning/SUMMARY.md)** - Executive summary

### 2. Review the Implementation Tracker (10 minutes)

**Main working document**: [docs/implementation/PROGRESS.md](docs/implementation/PROGRESS.md)

This is your roadmap. It breaks down implementation into phases with checkboxes.

### 3. Follow the Tracer Bullet Approach

**Start here**: Phase 0 in PROGRESS.md - "Tracer Bullet - Prove Core Interaction"

**Goal**: Make `clodputer run <task>` work end-to-end with a single hardcoded task.

**Why?** This proves the single most critical and risky part works: the interaction with Claude Code and subsequent cleanup. Once this works, everything else is infrastructure around a proven core.

## 🎯 Implementation Strategy

### The "Tracer Bullet" Method

From expert engineer review:

> "Make a script that can: Load a single YAML, construct and run `claude -p ...`, capture output, perform PID-based cleanup, print a log message. Once you see that work once, the rest of the project becomes a matter of building the infrastructure around that proven core."

**Phases**:
1. **Phase 0**: Tracer bullet (prove core interaction)
2. **Phase 1**: Core implementation (queue, executor, logging, CLI)
3. **Phase 2**: Automation triggers (cron, file watcher)
4. **Phase 3**: Polish and release

### Build `doctor` Incrementally

Don't save diagnostics for the end. As you build each component, add corresponding checks to `clodputer doctor`:

- Queue manager built? → Add "check stale lockfile" diagnostic
- Config loader built? → Add "validate all YAMLs" diagnostic
- Cron installer built? → Add "check cron jobs installed" diagnostic

This makes `doctor` your primary debugging tool during development.

### Use Structured Logging from Day 1

Log events as JSON internally, format for display in CLI:

```python
# Log structured data
log.info({
    "event": "task_completed",
    "task_name": task.name,
    "duration_sec": duration,
    "status": "success"
})

# CLI formats for humans
print(f"✅ {timestamp} | {task_name} | {duration}s | Success")
```

This makes future dashboard trivial to build.

## 📂 Repository Structure

```
clodputer/
├── src/clodputer/          # Main package (write your code here)
│   ├── __init__.py
│   ├── cli.py              # Click-based CLI
│   ├── executor.py         # Task executor (start here!)
│   ├── cleanup.py          # PID-tracked process cleanup
│   ├── queue.py            # Queue manager
│   ├── config.py           # Pydantic config models
│   ├── logger.py           # Structured logging
│   ├── cron.py             # Cron integration
│   ├── watcher.py          # File watcher
│   └── menubar.py          # macOS menu bar app
│
├── tests/                  # Test suite
│   ├── test_executor.py
│   ├── test_queue.py
│   └── ...
│
├── docs/
│   ├── planning/           # A+ grade planning docs (read-only)
│   └── implementation/     # Working docs (update as you go)
│       ├── PROGRESS.md     # Main tracker ⭐
│       └── README.md
│
├── templates/              # Example task configs
│   └── (create example YAMLs here)
│
├── pyproject.toml          # Project configuration
└── README.md               # Project overview
```

## 🔧 Development Workflow

### Day-to-Day Process

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Check PROGRESS.md** for current status and next task

3. **Create feature branch** (optional but recommended):
   ```bash
   git checkout -b feature/task-executor
   ```

4. **Write code** following the implementation tracker

5. **Update PROGRESS.md**:
   - Check off completed tasks
   - Add notes about implementation approach
   - Document any deviations or decisions

6. **Commit regularly**:
   ```bash
   git add .
   git commit -m "Implement task executor core functionality

   - Load YAML configs
   - Build Claude Code command
   - Execute with subprocess
   - Capture output

   Progress: Phase 0 Tracer Bullet - 60% complete"
   ```

7. **Push to GitHub**:
   ```bash
   git push origin feature/task-executor
   # Or: git push origin main (if working directly on main)
   ```

### Testing Your Code

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=clodputer --cov-report=html

# Format code
black src/ tests/

# Lint code
ruff src/ tests/

# Type check
mypy src/
```

## 📝 Code Style Guidelines

### General Principles

- **Type hints**: Use throughout for better IDE support
- **Docstrings**: Add to all public functions/classes
- **Line length**: 100 characters (configured in pyproject.toml)
- **Error handling**: Be explicit, provide clear error messages
- **Logging**: Use structured logging (JSON) internally

### Example Code Style

```python
from pathlib import Path
from typing import Optional
import subprocess
import psutil

def execute_task(config_path: Path, timeout: int = 3600) -> dict:
    """
    Execute a task using Claude Code.

    Args:
        config_path: Path to task YAML configuration
        timeout: Maximum execution time in seconds

    Returns:
        Dictionary containing execution results

    Raises:
        ConfigError: If config is invalid
        ExecutionError: If task execution fails
    """
    # Implementation here
    pass
```

## 🐛 Debugging Tips

### Common Issues

**Issue**: `ImportError: No module named 'clodputer'`
**Fix**: Make sure you installed in development mode: `pip install -e .`

**Issue**: Tests can't find modules
**Fix**: Install test dependencies: `pip install -e ".[dev]"`

**Issue**: Claude Code not found
**Fix**: Verify Claude Code is installed: `which claude`

### Debugging Tracer Bullet

When debugging the core executor:

1. **Test Claude Code manually first**:
   ```bash
   claude -p "Say hello" --output-format json
   ```

2. **Check process cleanup**:
   ```bash
   # Before running your code
   ps aux | grep mcp

   # After running your code (should be no mcp processes)
   ps aux | grep mcp
   ```

3. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## 📊 Progress Tracking

### Updating PROGRESS.md

**When you complete a task**:
1. Change `- [ ]` to `- [x]`
2. Add notes in the "Notes:" section
3. Update "Last Updated" date at the bottom
4. Commit changes

**Example**:
```markdown
- [x] **Create minimal Task Executor**
  - [x] Load a single hardcoded YAML config
  - [x] Parse YAML with PyYAML
  - [x] Build `claude -p "..."` command
  - [x] Execute command with `subprocess.run()`
  - **Notes**:
    - Used Popen instead of run() to get PID for cleanup
    - Added timeout parameter (default 3600s)
    - JSON parsing works perfectly
```

### Documenting Decisions

Use the "Notes & Decisions" section at the bottom of PROGRESS.md to document:
- **Technical decisions**: Why you chose approach X over Y
- **Blockers**: What's blocking progress and why
- **Performance**: Any performance observations
- **Security**: Security considerations discovered

## 🚢 Getting Help

### Resources

- **Planning docs**: All in `docs/planning/`
- **Implementation tracker**: `docs/implementation/PROGRESS.md`
- **Expert engineer feedback**: In planning docs (search for "Engineer's")

### Questions?

If you're stuck or unsure:
1. Check the planning docs for the answer
2. Look at the implementation details doc for code examples
3. Document your question in PROGRESS.md under "Blockers & Issues"
4. Reach out to project maintainer

## 🎉 First Task

**Your first task**: Complete the tracer bullet!

1. Read Phase 0 in [PROGRESS.md](docs/implementation/PROGRESS.md)
2. Create `src/clodputer/executor.py`
3. Make a script that can run a single task end-to-end
4. Verify cleanup works (no orphaned processes)
5. Check off tasks in PROGRESS.md as you complete them

Once the tracer bullet works, you've proven the riskiest part. Everything else is building infrastructure around that core.

**Good luck! 🚀**

---

**Remember**: This is an A+ grade plan from an expert engineer. Trust the plan, follow the sequence, and you'll build something great.
