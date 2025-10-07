# Implementation Details & Technical Decisions

**Date**: October 7, 2025
**Status**: Technical Specification
**Purpose**: Concrete library choices, repo structure, and extensibility design

---

## Philosophy

**Principle**: Choose boring, battle-tested technologies over cutting-edge but less mature options.

**Goals**:
1. **Easy to build** - Minimal dependencies, well-documented libraries
2. **Easy to maintain** - Standard patterns, widely-used tools
3. **Easy to extend** - Clear extension points for Phase 2 features
4. **Easy to debug** - Simple architecture, good error messages

---

## Technology Stack

### Core Language: Python 3.9+

**Choice**: Python 3.9 as minimum version

**Rationale**:
- **3.9+** gives us modern features (type hints with `list[str]`, dict merge `|` operator)
- Still widely available on macOS (Monterey+ ships with 3.9)
- Not cutting-edge (3.13 is latest) - mature and stable
- Good balance of modern syntax without forcing users to upgrade

**Type Hints**: Use throughout for better IDE support and maintainability

---

## Dependency Choices

### 1. CLI Framework: Click

**Library**: [Click](https://click.palletsprojects.com/) 8.x
**Installation**: `pip install click`

**Why Click over alternatives**:
- ✅ **Battle-tested** - Used by Flask, pip, black, pytest
- ✅ **Decorator-based** - Clean, readable syntax
- ✅ **Auto-generated help** - Beautiful help pages out of the box
- ✅ **Nested commands** - Perfect for `clodputer status`, `clodputer run`, etc.
- ✅ **Wide adoption** - Most Python developers know Click

**Alternatives considered**:
- **argparse** (stdlib) - Too verbose, poor UX
- **Typer** - Nice but adds pydantic dependency, less mature
- **Docopt** - Too magical, harder to maintain

**Example Usage**:
```python
import click

@click.group()
def cli():
    """Clodputer: Autonomous Claude Code automation"""
    pass

@cli.command()
def status():
    """Show queue status and recent executions"""
    # Implementation here
    click.echo("✅ Queue: 2 tasks running")

@cli.command()
@click.argument('task_name')
@click.option('--priority', type=click.Choice(['normal', 'high']), default='normal')
def run(task_name, priority):
    """Run a task immediately"""
    click.echo(f"Enqueuing {task_name} with {priority} priority...")

@cli.command()
def doctor():
    """Run system diagnostics for troubleshooting"""
    click.echo("🩺 Clodputer System Diagnostics\n")

    checks_passed = 0
    warnings = []

    # Check 1: Installation
    click.echo("CHECKING INSTALLATION:")
    if check_directory_exists():
        click.echo("  ✅ ~/.clodputer directory exists")
        checks_passed += 1
    else:
        click.echo("  ❌ ~/.clodputer directory missing")

    # Check 2: Dependencies
    click.echo("\nCHECKING DEPENDENCIES:")
    if check_claude_installed():
        version = get_claude_version()
        click.echo(f"  ✅ Claude Code installed (version {version})")
        checks_passed += 1
    else:
        click.echo("  ❌ Claude Code not found")

    # Check 3: Configuration
    click.echo("\nCHECKING CONFIGURATION:")
    task_count, invalid_tasks = validate_all_task_configs()
    if not invalid_tasks:
        click.echo(f"  ✅ Found {task_count} task configs")
        click.echo("  ✅ All YAML files valid")
        checks_passed += 2
    else:
        click.echo(f"  ❌ {len(invalid_tasks)} invalid task configs")
        for task, error in invalid_tasks:
            click.echo(f"      {task}: {error}")

    # Check 4: Process State
    click.echo("\nCHECKING PROCESS STATE:")
    if not check_stale_lockfile():
        click.echo("  ✅ No stale lock file")
        checks_passed += 1
    else:
        click.echo("  ⚠️  Stale lock file detected")
        warnings.append("Run: clodputer queue reset")

    # Summary
    click.echo(f"\nSUMMARY: {checks_passed} checks passed, {len(warnings)} warnings")

    if warnings:
        click.echo("\n⚠️  WARNINGS:")
        for warning in warnings:
            click.echo(f"  • {warning}")
```

---

### 2. YAML Parsing: PyYAML

**Library**: [PyYAML](https://pyyaml.org/) 6.x
**Installation**: `pip install pyyaml`

**Why PyYAML over alternatives**:
- ✅ **Industry standard** - Most widely used Python YAML library
- ✅ **Simple API** - `yaml.safe_load()` / `yaml.safe_dump()`
- ✅ **Well-maintained** - Active development, security updates
- ✅ **Fast enough** - Performance adequate for config files

**Safety**: Always use `safe_load()` / `safe_dump()` (never `load()`)

**Alternatives considered**:
- **ruamel.yaml** - Preserves comments/formatting, but overkill for our needs
- **StrictYAML** - Too opinionated, limited feature set

**Example Usage**:
```python
import yaml
from pathlib import Path

def load_task_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def save_task_config(path: Path, config: dict):
    with open(path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
```

---

### 3. Process Management: psutil

**Library**: [psutil](https://github.com/giampaolo/psutil) 6.x
**Installation**: `pip install psutil`

**Why psutil**:
- ✅ **Cross-platform** - macOS, Linux, Windows
- ✅ **Comprehensive** - Process trees, CPU/memory monitoring, process killing
- ✅ **Well-maintained** - Active development since 2009
- ✅ **stdlib supplement** - Works alongside `subprocess` module

**Use cases**:
- Find processes by name pattern (`mcp__*`)
- Kill process trees (parent + children)
- Monitor system resources before task execution
- Graceful shutdown with fallback to force kill

**Example Usage**:
```python
import psutil
import signal
import time

def cleanup_mcp_processes():
    """Find and kill all MCP processes"""
    killed = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if process name matches MCP pattern
            if proc.info['name'] and 'mcp__' in proc.info['name']:
                proc.terminate()  # SIGTERM
                killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Wait for graceful shutdown
    time.sleep(5)

    # Force kill any still running
    for pid in killed:
        try:
            proc = psutil.Process(pid)
            if proc.is_running():
                proc.kill()  # SIGKILL
        except psutil.NoSuchProcess:
            continue

    return killed

def check_system_resources() -> bool:
    """Check if system has resources available"""
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    return cpu < 80 and memory < 80
```

---

### 4. File Watching: watchdog

**Library**: [watchdog](https://github.com/gorakhargosh/watchdog) 4.x
**Installation**: `pip install watchdog`

**Why watchdog over fswatch**:
- ✅ **Pure Python** - No external fswatch dependency
- ✅ **Cross-platform** - macOS (FSEvents), Linux (inotify), Windows
- ✅ **Event-based API** - Clean observer pattern
- ✅ **Well-maintained** - Active development, 11k+ stars
- ✅ **Better than raw fswatch** - Built-in debouncing, filtering

**Note**: While we initially considered raw `fswatch`, watchdog is more Pythonic and easier to maintain.

**Example Usage**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
import time
from pathlib import Path

class TaskTriggerHandler(FileSystemEventHandler):
    def __init__(self, task_name: str, pattern: str):
        self.task_name = task_name
        self.pattern = pattern
        self.processed = set()

    def on_created(self, event: FileCreatedEvent):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.match(self.pattern) and path not in self.processed:
            self.processed.add(path)
            enqueue_task(self.task_name, context={'filepath': str(path)})

def watch_directory(path: str, task_name: str, pattern: str):
    """Start watching directory for file changes"""
    handler = TaskTriggerHandler(task_name, pattern)
    observer = Observer()
    observer.schedule(handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

---

### 5. macOS Menu Bar: rumps

**Library**: [rumps](https://github.com/jaredks/rumps) 0.4.x
**Installation**: `pip install rumps`

**Why rumps**:
- ✅ **macOS-specific** - Built for macOS status bar apps
- ✅ **Simple API** - Minimal boilerplate
- ✅ **PyObjC wrapper** - Abstracts Cocoa complexity
- ✅ **Proven** - Used by many macOS Python apps
- ✅ **Maintained** - Active development

**Limitation**: macOS only (acceptable for MVP)

**Example Usage**:
```python
import rumps

class ClodputerApp(rumps.App):
    def __init__(self):
        super().__init__("Clodputer", icon="🤖")
        self.menu = [
            "Status",
            "Open Dashboard",
            None,  # Separator
            "Recent Executions"
        ]

    @rumps.clicked("Status")
    def show_status(self, _):
        status = get_queue_status()
        rumps.alert("Status", f"Running: {status['running']}\nQueued: {len(status['queued'])}")

    @rumps.clicked("Open Dashboard")
    def open_dashboard(self, _):
        # Open terminal with curses dashboard
        import subprocess
        subprocess.Popen(['open', '-a', 'Terminal', 'clodputer-dashboard'])

if __name__ == '__main__':
    ClodputerApp().run()
```

---

### 6. Configuration Validation: Pydantic

**Library**: [Pydantic](https://docs.pydantic.dev/) 2.x
**Installation**: `pip install pydantic`

**Why Pydantic**:
- ✅ **Automatic validation** - Type checking + constraints
- ✅ **Clear error messages** - User-friendly validation errors
- ✅ **IDE support** - Autocomplete for config fields
- ✅ **Zero boilerplate** - Dataclasses that validate themselves
- ✅ **Industry standard** - Used by FastAPI, many major projects

**Use case**: Parse and validate YAML task configs with structured models

**Example Usage**:
```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from pathlib import Path
from typing import Optional, List

class Priority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"

class TriggerType(str, Enum):
    CRON = "cron"
    FILE_WATCH = "file_watch"
    MANUAL = "manual"

class FileWatchTrigger(BaseModel):
    type: TriggerType = TriggerType.FILE_WATCH
    path: Path
    pattern: str = "*.md"
    event: str = "created"
    debounce: int = Field(default=1000, ge=0)

    @field_validator('path')
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        if not v.expanduser().exists():
            raise ValueError(f"Path does not exist: {v}")
        return v.expanduser()

class TaskConfig(BaseModel):
    """Task configuration with automatic validation"""
    name: str = Field(min_length=1, max_length=100)
    description: str
    enabled: bool = True
    priority: Priority = Priority.NORMAL
    trigger: FileWatchTrigger | dict  # Union of trigger types

    class Config:
        extra = "forbid"  # Reject unknown fields

# Usage
def load_task_config(yaml_path: Path) -> TaskConfig:
    """Load and validate task config"""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    try:
        config = TaskConfig(**data)
        return config
    except ValidationError as e:
        # Beautiful error messages
        print(f"Invalid configuration in {yaml_path}:")
        print(e)
        raise
```

**Benefits for Users**:
```
# Invalid config:
name: ""  # Too short
priority: "urgent"  # Invalid value

# Error message:
Invalid configuration in email-management.yaml:
2 validation errors for TaskConfig
name
  String should have at least 1 character [type=string_too_short]
priority
  Input should be 'normal' or 'high' [type=enum, input_value='urgent']
```

---

### 7. Testing: pytest + pytest-mock

**Libraries**:
- [pytest](https://pytest.org/) 8.x - Testing framework
- [pytest-mock](https://github.com/pytest-dev/pytest-mock/) 3.x - Mocking helper

**Installation**: `pip install pytest pytest-mock`

**Why pytest over unittest**:
- ✅ **Industry standard** - Most popular Python testing framework
- ✅ **Less boilerplate** - Simple assertions, fixtures
- ✅ **Rich ecosystem** - Plugins for coverage, mocking, fixtures
- ✅ **Better output** - Clear test failure messages

**Why pytest-mock**:
- ✅ **Cleaner than unittest.mock** - Fixture-based mocking
- ✅ **Automatic cleanup** - Mocks reset after each test
- ✅ **Better pytest integration** - Works with fixtures

**Example Test Structure**:
```python
# tests/test_queue.py
import pytest
from clodputer.queue import QueueManager

@pytest.fixture
def queue_manager(tmp_path):
    """Create a queue manager with temporary state file"""
    return QueueManager(state_path=tmp_path / "queue.json")

def test_enqueue_task(queue_manager):
    """Test adding task to queue"""
    task_id = queue_manager.enqueue("email-management", priority="normal")
    assert task_id is not None
    assert queue_manager.queue_depth() == 1

def test_sequential_execution(queue_manager, mocker):
    """Test that only one task runs at a time"""
    # Mock the executor
    mock_executor = mocker.patch('clodputer.executor.execute_task')

    # Enqueue two tasks
    queue_manager.enqueue("task1")
    queue_manager.enqueue("task2")

    # Process queue
    queue_manager.process_next()

    # Only one task should start
    assert mock_executor.call_count == 1
    assert queue_manager.get_running_task() is not None
```

---

## Package Management & Distribution

### Build System: pyproject.toml + setuptools

**Modern Standard**: `pyproject.toml` (PEP 621)
**Build Backend**: setuptools 70.x (most widely used)

**Why pyproject.toml over setup.py**:
- ✅ **Modern standard** - PEP 621, PEP 517
- ✅ **Declarative** - No Python code execution
- ✅ **Single source of truth** - All metadata in one place
- ✅ **Tool agnostic** - Works with pip, uv, poetry

**Why setuptools over alternatives**:
- ✅ **Most compatible** - Works everywhere
- ✅ **Stable** - 20+ years of development
- ✅ **Well-documented** - Extensive guides
- ✅ **pip-compatible** - No surprises

**Example pyproject.toml**:
```toml
[build-system]
requires = ["setuptools>=70.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "clodputer"
version = "0.1.0"
description = "Autonomous Claude Code automation system"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "Rémy Olson", email = "olson.remy@gmail.com"}
]
keywords = ["claude", "automation", "ai", "assistant"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "click>=8.0.0,<9.0.0",
    "pyyaml>=6.0.0,<7.0.0",
    "psutil>=6.0.0,<7.0.0",
    "watchdog>=4.0.0,<5.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "rumps>=0.4.0,<0.5.0; sys_platform == 'darwin'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.0.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
]

[project.scripts]
clodputer = "clodputer.cli:main"
clodputer-queue = "clodputer.queue:daemon"
clodputer-run = "clodputer.executor:run_task"
clodputer-watch = "clodputer.watcher:watch_daemon"

[project.urls]
Homepage = "https://github.com/username/clodputer"
Documentation = "https://github.com/username/clodputer#readme"
Repository = "https://github.com/username/clodputer"
Issues = "https://github.com/username/clodputer/issues"

[tool.setuptools]
packages = ["clodputer"]

[tool.setuptools.package-data]
clodputer = ["templates/*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --cov=clodputer --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I"]
```

---

### Installation Tool: uv (recommended) or pip

**Primary**: [uv](https://github.com/astral-sh/uv) - Next-gen Python package installer
**Fallback**: pip (universal compatibility)

**Why recommend uv**:
- ✅ **10-100x faster** than pip
- ✅ **Drop-in replacement** - Same commands (`uv pip install`)
- ✅ **Written in Rust** - Blazing fast, single binary
- ✅ **By Astral** - Same team as Ruff (trusted)
- ✅ **pip-compatible** - Works with existing requirements.txt
- ✅ **Growing adoption** - Becoming Python standard in 2025

**For users**:
```bash
# Fast installation with uv (recommended)
uv pip install clodputer

# Traditional installation with pip
pip install clodputer
```

**For development**:
```bash
# Clone and install in editable mode with uv
git clone https://github.com/username/clodputer
cd clodputer
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

---

## Repository Structure

```
clodputer/                          # Repository root
├── .github/
│   └── workflows/
│       ├── test.yml                # Run tests on push
│       └── release.yml             # Build and publish releases
│
├── src/                            # Source code (src-layout)
│   └── clodputer/
│       ├── __init__.py             # Package init, version
│       ├── __main__.py             # Entry point for `python -m clodputer`
│       │
│       ├── cli.py                  # Click CLI commands
│       ├── queue.py                # Queue manager
│       ├── executor.py             # Task executor
│       ├── watcher.py              # File watcher
│       ├── logger.py               # Logging system
│       ├── cleanup.py              # Process cleanup
│       ├── config.py               # Config loading/validation
│       ├── setup.py                # Initial setup script
│       │
│       ├── models.py               # Data models (Task, QueueState, etc.)
│       ├── exceptions.py           # Custom exceptions
│       ├── utils.py                # Helper functions
│       │
│       └── templates/              # Task templates
│           ├── daily-email.yaml
│           ├── file-watcher.yaml
│           └── manual-task.yaml
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   │
│   ├── unit/                       # Unit tests
│   │   ├── test_queue.py
│   │   ├── test_executor.py
│   │   ├── test_cleanup.py
│   │   └── test_config.py
│   │
│   └── integration/                # Integration tests
│       ├── test_end_to_end.py
│       └── test_cron_integration.py
│
├── docs/                           # Documentation
│   ├── installation.md
│   ├── quickstart.md
│   ├── configuration.md
│   ├── troubleshooting.md
│   └── examples/
│       ├── email-management.md
│       ├── project-watcher.md
│       └── custom-tasks.md
│
├── scripts/                        # Helper scripts
│   ├── install.sh                  # Installation script
│   └── uninstall.sh                # Cleanup script
│
├── .gitignore
├── .python-version                 # Pin Python version (3.9)
├── LICENSE                         # MIT License
├── README.md                       # Main documentation
├── CONTRIBUTING.md                 # Contribution guidelines
├── CHANGELOG.md                    # Version history
├── pyproject.toml                  # Package metadata + dependencies
└── requirements-dev.txt            # Dev dependencies (alternative)
```

### Why src-layout?

**Benefits**:
- ✅ **Import correctness** - Forces installed package testing
- ✅ **No accidental imports** - Can't import from repo root
- ✅ **Industry best practice** - Used by major projects
- ✅ **Better for editable installs** - Clear separation

---

## Data Models & Type Hints

**Use Python dataclasses** for structured data:

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List

class Priority(Enum):
    NORMAL = "normal"
    HIGH = "high"

class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    """Represents a task in the queue"""
    id: str
    name: str
    config_path: Path
    priority: Priority
    status: TaskStatus
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    pid: Optional[int] = None

    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING

    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

@dataclass
class QueueState:
    """Current state of the task queue"""
    running: Optional[Task] = None
    queued: List[Task] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict"""
        return {
            'running': self.running.__dict__ if self.running else None,
            'queued': [task.__dict__ for task in self.queued]
        }
```

---

## Extension Points for Phase 2

### 1. Multi-Turn Conversations

**Current**: Single-turn prompts
**Future**: Session continuity

**Extension Point**:
```python
# In executor.py
class TaskExecutor:
    def execute_single_turn(self, task: Task) -> Result:
        """Current implementation"""
        pass

    def execute_multi_turn(self, task: Task, session: Session) -> Result:
        """Phase 2: Add session management"""
        # TODO: Implement session reuse
        pass
```

**Design Consideration**: Add `session_id` field to Task model

---

### 2. Session Pooling

**Current**: On-demand spawning
**Future**: Warm session pool

**Extension Point**:
```python
# New file: session_pool.py
class SessionPool:
    """Manage pool of warm Claude Code sessions"""

    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self.sessions: List[Session] = []

    def get_session(self) -> Session:
        """Get or create session from pool"""
        pass

    def return_session(self, session: Session):
        """Return session to pool for reuse"""
        pass
```

**Config Addition**:
```yaml
# ~/.clodputer/config.yaml (Phase 2)
session_pooling:
  enabled: true
  pool_size: 2
  max_session_age: 3600  # 1 hour
```

---

### 3. Retry Logic

**Current**: Fail once, user retries manually
**Future**: Automatic retry with exponential backoff

**Extension Point**:
```python
# In config.py - add to task schema
@dataclass
class RetryConfig:
    enabled: bool = False
    max_attempts: int = 3
    backoff_seconds: int = 60
    backoff_multiplier: float = 2.0

# In task config YAML (Phase 2)
on_failure:
  - log: "Task failed: {{error}}"
  - notify: true
  - retry:
      max_attempts: 3
      backoff: exponential
```

---

### 4. Cost Tracking

**Current**: No cost tracking
**Future**: Per-task token usage and cost

**Extension Point**:
```python
# In models.py
@dataclass
class ExecutionResult:
    success: bool
    output: dict
    duration: float
    tokens_used: Optional[int] = None  # Phase 2
    cost_usd: Optional[float] = None   # Phase 2

# In logger.py - extend log format
EXECUTION_LOG_FORMAT = """
Task: {task_name}
Status: {status}
Duration: {duration}s
Tokens: {tokens}      # Phase 2
Cost: ${cost}         # Phase 2
"""
```

---

### 5. Web Dashboard

**Current**: Terminal dashboard (curses)
**Future**: Optional web UI

**Extension Point**:
```python
# New file: server.py (Phase 2)
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/status')
def api_status():
    """JSON API for web dashboard"""
    state = get_queue_state()
    return jsonify(state.to_dict())

# New command in cli.py
@cli.command()
@click.option('--port', default=8080)
def serve(port):
    """Start web dashboard (Phase 2)"""
    app.run(port=port)
```

---

## Error Handling Strategy

### Exception Hierarchy

```python
# exceptions.py
class ClodputerError(Exception):
    """Base exception for all Clodputer errors"""
    pass

class TaskExecutionError(ClodputerError):
    """Task failed during execution"""
    pass

class CleanupError(ClodputerError):
    """Process cleanup failed"""
    pass

class ConfigError(ClodputerError):
    """Invalid configuration"""
    pass

class QueueError(ClodputerError):
    """Queue operation failed"""
    pass
```

### Error Handling Pattern

```python
# executor.py
import logging
from clodputer.exceptions import TaskExecutionError, CleanupError

logger = logging.getLogger(__name__)

def execute_task(task: Task) -> Result:
    try:
        # Execute task
        result = run_claude_code(task)
        return result

    except subprocess.TimeoutExpired:
        logger.error(f"Task {task.name} timed out")
        raise TaskExecutionError(f"Timeout after {task.timeout}s")

    except Exception as e:
        logger.exception(f"Task {task.name} failed")
        raise TaskExecutionError(f"Execution failed: {e}")

    finally:
        # Always cleanup, even if task failed
        try:
            cleanup_claude_instance(task.pid)
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            # Don't raise - log but continue
```

---

## Testing Strategy

### Test Organization

**Unit Tests** (`tests/unit/`):
- Test individual functions/classes in isolation
- Mock external dependencies (subprocess, file I/O)
- Fast execution (<1 second total)

**Integration Tests** (`tests/integration/`):
- Test component interactions
- May use real file system (tmp_path fixture)
- Slower execution (acceptable if <10 seconds total)

**Mock Strategy**:
```python
# tests/unit/test_executor.py
def test_execute_task_success(mocker):
    """Test successful task execution"""
    # Mock subprocess.run to avoid real Claude Code execution
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MockCompletedProcess(
        returncode=0,
        stdout='{"success": true}'
    )

    # Mock cleanup
    mock_cleanup = mocker.patch('clodputer.cleanup.cleanup_claude_instance')

    # Execute
    result = execute_task(create_test_task())

    # Verify
    assert result.success is True
    mock_cleanup.assert_called_once()
```

### CI/CD

**GitHub Actions** workflow:
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: uv pip install -e ".[dev]"

    - name: Run tests
      run: pytest

    - name: Run ruff
      run: ruff check .
```

---

## Configuration Management

### Precedence Order

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`CLODPUTER_*`)
3. **Local config** (`~/.clodputer/config.yaml`)
4. **Defaults** (lowest priority)

**Example**:
```python
# config.py
import os
from pathlib import Path
from typing import Optional

def get_config_path() -> Path:
    """Get config directory path"""
    # Environment variable takes precedence
    if env_path := os.getenv('CLODPUTER_CONFIG_DIR'):
        return Path(env_path)

    # Default to ~/.clodputer
    return Path.home() / '.clodputer'

def load_config() -> dict:
    """Load configuration with precedence"""
    config_path = get_config_path() / 'config.yaml'

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Override with file config
    if config_path.exists():
        file_config = yaml.safe_load(config_path.read_text())
        config.update(file_config)

    # Override with environment variables
    if queue_dir := os.getenv('CLODPUTER_QUEUE_DIR'):
        config['queue_dir'] = queue_dir

    return config
```

---

## Security Considerations

### 1. YAML Safety

**Always use `safe_load()`**:
```python
# ✅ GOOD
config = yaml.safe_load(file)

# ❌ BAD - allows arbitrary Python object instantiation
config = yaml.load(file)
```

### 2. Path Validation

**Validate user-provided paths**:
```python
def validate_task_path(path: Path) -> Path:
    """Validate task config path is within allowed directory"""
    config_dir = get_config_path() / 'tasks'

    # Resolve to absolute path
    abs_path = path.resolve()

    # Check it's within config directory
    if not abs_path.is_relative_to(config_dir):
        raise ConfigError(f"Task path must be in {config_dir}")

    return abs_path
```

### 3. Command Injection Prevention

**Never use shell=True**:
```python
# ✅ GOOD - arguments as list
subprocess.run(['claude', '-p', prompt_text], shell=False)

# ❌ BAD - vulnerable to injection
subprocess.run(f'claude -p "{prompt_text}"', shell=True)
```

### 4. Secret Management

**Problem**: Task configs may need API keys or other secrets. Don't hardcode them in YAML files.

**Solution**: Environment variable substitution pattern.

**In Task Config (YAML)**:
```yaml
name: "notion-sync"
description: "Sync data with Notion API"
prompt: |
  Use the Notion API to sync our project database.
  API Key: {{ env.NOTION_API_KEY }}
  Database ID: {{ env.NOTION_DATABASE_ID }}

allowed_tools:
  - Read
  - Write
  - mcp__http
```

**In Task Executor**:
```python
import os
import re

def substitute_env_vars(text: str) -> str:
    """
    Replace {{ env.VAR_NAME }} with environment variable values.

    Raises:
        ConfigError: If required environment variable is not set
    """
    pattern = r'\{\{\s*env\.([A-Z_]+)\s*\}\}'

    def replacer(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)

        if value is None:
            raise ConfigError(
                f"Environment variable {var_name} is not set. "
                f"Set it with: export {var_name}=your_value"
            )

        return value

    return re.sub(pattern, replacer, text)

def load_task_config(config_path: Path) -> TaskConfig:
    """Load task config and substitute environment variables"""
    raw_yaml = config_path.read_text()

    # Substitute environment variables in YAML content
    processed_yaml = substitute_env_vars(raw_yaml)

    # Parse YAML
    config_dict = yaml.safe_load(processed_yaml)

    # Validate with Pydantic
    return TaskConfig(**config_dict)
```

**User Workflow**:
```bash
# 1. User sets environment variable once
export NOTION_API_KEY="secret_abc123..."

# 2. Add to shell profile for persistence
echo 'export NOTION_API_KEY="secret_abc123..."' >> ~/.zshrc

# 3. Claude Code generates task config with template
# (User never sees the actual secret in config files)

# 4. Task runs with secret automatically substituted
clodputer run notion-sync
```

**Benefits**:
- Secrets never stored in plaintext config files
- Configs can be shared/version controlled safely
- Standard Unix environment variable pattern
- Clear error messages if secrets not set

**Phase 2 Enhancement**: Support `.env` files for easier secret management:
```python
# Load .env file if present
dotenv_path = get_config_path() / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)  # Using python-dotenv library
```

---

## Performance Optimizations

### 1. Lazy Imports

**Import heavy modules only when needed**:
```python
def open_dashboard():
    """Open terminal dashboard (imports curses lazily)"""
    import curses  # Only import when dashboard opens
    from clodputer.dashboard import Dashboard

    dashboard = Dashboard()
    curses.wrapper(dashboard.run)
```

### 2. Caching

**Cache expensive operations**:
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def detect_system_config():
    """Detect system configuration (cached)"""
    return {
        'cpu_cores': psutil.cpu_count(),
        'memory_gb': psutil.virtual_memory().total / (1024**3),
        'claude_version': get_claude_version(),  # Slow
    }
```

### 3. Structured Logging (Recommended)

**Problem**: Human-readable logs are great for users but hard to parse programmatically.

**Solution**: Log structured data internally, format for display in CLI.

**Implementation**:
```python
import json
import logging
from datetime import datetime
from pathlib import Path

class StructuredLogger:
    """
    Logs structured JSON internally, provides human-readable output via CLI.

    Makes future dashboard trivial to build - just parse JSON instead of
    regex'ing human-readable strings.
    """

    def __init__(self, log_file: Path):
        self.log_file = log_file

    def log(self, event: str, **kwargs):
        """Log structured event as JSON"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            **kwargs
        }

        with self.log_file.open('a') as f:
            f.write(json.dumps(entry) + '\n')

    def task_started(self, task_name: str, task_id: str):
        self.log("task_started", task_name=task_name, task_id=task_id)

    def task_completed(self, task_name: str, duration_sec: float, status: str):
        self.log("task_completed",
                 task_name=task_name,
                 duration_sec=duration_sec,
                 status=status)

    def task_failed(self, task_name: str, error: str, duration_sec: float):
        self.log("task_failed",
                 task_name=task_name,
                 error=error,
                 duration_sec=duration_sec)

# Usage in CLI (format for humans):
def format_log_entry(entry: dict) -> str:
    """Convert structured log to human-readable format"""
    if entry['event'] == 'task_completed':
        return (f"✅ {entry['timestamp']} | {entry['task_name']} | "
                f"{entry['duration_sec']}s | {entry['status']}")
    elif entry['event'] == 'task_failed':
        return (f"❌ {entry['timestamp']} | {entry['task_name']} | "
                f"{entry['duration_sec']}s | {entry['error']}")
    # ... other event types

def show_logs():
    """CLI command to show logs in human-readable format"""
    log_file = Path("~/.clodputer/execution.log").expanduser()

    with log_file.open('r') as f:
        for line in f:
            entry = json.loads(line)
            print(format_log_entry(entry))
```

**Benefits**:
- User sees nice formatted output in CLI
- Future web dashboard can parse JSON directly
- Easy to filter/query logs programmatically
- No regex parsing of human-readable strings
- Can add fields without breaking existing parsers

**Engineer's Recommendation**: "While you are deferring a web dashboard, structured logs make building such a tool trivial in the future."

---

## Summary: Key Technical Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **CLI Framework** | Click 8.x | Battle-tested, decorator-based, great UX |
| **YAML Parser** | PyYAML 6.x | Industry standard, simple, fast enough |
| **Config Validation** | Pydantic 2.x | Automatic validation, clear errors, IDE support |
| **Process Mgmt** | psutil 6.x | Cross-platform, comprehensive, well-maintained |
| **File Watching** | watchdog 4.x | Pure Python, event-based, better than fswatch |
| **Menu Bar** | rumps 0.4.x | macOS-specific, simple API, proven |
| **Testing** | pytest + pytest-mock | Industry standard, less boilerplate |
| **Build System** | pyproject.toml + setuptools | Modern standard, most compatible |
| **Package Tool** | uv (recommend), pip (fallback) | 10-100x faster, growing adoption |
| **Python Version** | 3.9+ | Modern features, widely available |
| **Type Hints** | Yes, throughout | Better IDE support, maintainability |
| **Repo Layout** | src-layout | Import correctness, best practice |
| **Queue Writes** | Atomic (temp file + rename) | Prevents corruption from crashes |
| **Secret Management** | Env var substitution ({{ env.VAR }}) | Keeps secrets out of config files |
| **Diagnostics** | `clodputer doctor` command | Troubleshooting and health checks |
| **Logging** | Structured JSON (recommended) | Easy parsing for future dashboard, human-readable CLI |

---

## Migration Path

### From Planning to Implementation

**Week 1: Core Components**
```bash
# Day 1: Setup
mkdir -p clodputer/src/clodputer clodputer/tests
cd clodputer
echo "3.9" > .python-version

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=70.0"]
build-backend = "setuptools.build_meta"

[project]
name = "clodputer"
version = "0.1.0"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
    "psutil>=6.0",
    "watchdog>=4.0",
]
EOF

# Install in dev mode
uv pip install -e ".[dev]"

# Day 2-3: Implement queue.py, executor.py
# Day 4-5: Implement logger.py, cli.py
# Day 6-7: Testing and cleanup verification
```

---

## Open Questions for Engineer Review

1. **Is src-layout acceptable?** Or prefer flat layout?
2. **pytest vs unittest?** Strong preference either way?
3. **Type hints everywhere?** Or just public APIs?
4. **Click vs Typer?** Any concerns with Click?
5. **watchdog vs raw fswatch?** Performance concerns?
6. **uv recommendation?** Too new, or good to recommend?

---

**All technical decisions documented! Ready for implementation.**
