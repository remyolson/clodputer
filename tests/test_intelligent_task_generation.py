"""Tests for intelligent task generation during onboarding."""

from types import SimpleNamespace



def test_parse_mcp_list_output():
    """Test parsing of `claude mcp list` output."""
    from clodputer.onboarding import _parse_mcp_list_output

    output = """Checking MCP server health...

crawl4ai: /path/to/script.sh  - ✓ Connected
google-search: node /path/to/server.js - ✓ Connected
gmail: npx package - ✗ Failed to connect
"""

    mcps = _parse_mcp_list_output(output)

    assert len(mcps) == 3
    assert mcps[0] == {
        "name": "crawl4ai",
        "command": "/path/to/script.sh",
        "status": "connected",
    }
    assert mcps[1]["status"] == "connected"
    assert mcps[2]["status"] == "failed"


def test_parse_mcp_list_output_empty():
    """Test parsing empty MCP list output."""
    from clodputer.onboarding import _parse_mcp_list_output

    output = """Checking MCP server health...

"""
    mcps = _parse_mcp_list_output(output)
    assert mcps == []


def test_parse_mcp_list_output_malformed():
    """Test parsing malformed MCP list output."""
    from clodputer.onboarding import _parse_mcp_list_output

    output = """Some random output
without proper format
"""
    mcps = _parse_mcp_list_output(output)
    assert mcps == []


def test_build_task_generation_prompt_with_gmail():
    """Test prompt includes email guidance when Gmail MCP is present."""
    from clodputer.onboarding import _build_task_generation_prompt

    mcps = [
        {"name": "gmail", "command": "npx gmail", "status": "connected"}
    ]

    prompt = _build_task_generation_prompt(mcps)

    assert "gmail" in prompt.lower()
    assert "email" in prompt.lower()
    assert "triage" in prompt.lower() or "summarization" in prompt.lower()


def test_build_task_generation_prompt_with_calendar():
    """Test prompt includes calendar guidance when calendar MCP is present."""
    from clodputer.onboarding import _build_task_generation_prompt

    mcps = [
        {"name": "google-calendar", "command": "node calendar.js", "status": "connected"}
    ]

    prompt = _build_task_generation_prompt(mcps)

    assert "calendar" in prompt.lower()
    assert "meeting" in prompt.lower()


def test_build_task_generation_prompt_with_search():
    """Test prompt includes search guidance when search MCPs are present."""
    from clodputer.onboarding import _build_task_generation_prompt

    mcps = [
        {"name": "google-search", "command": "node search.js", "status": "connected"}
    ]

    prompt = _build_task_generation_prompt(mcps)

    assert "search" in prompt.lower()
    assert "research" in prompt.lower() or "monitoring" in prompt.lower()


def test_build_task_generation_prompt_no_mcps():
    """Test prompt includes fallback guidance when no MCPs are connected."""
    from clodputer.onboarding import _build_task_generation_prompt

    mcps = []

    prompt = _build_task_generation_prompt(mcps)

    assert "no mcps" in prompt.lower() or "not configured" in prompt.lower()
    assert "git" in prompt.lower() or "file" in prompt.lower()


def test_validate_generated_task_valid():
    """Test validation of a valid generated task."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "test-task",
        "description": "A test task",
        "yaml_config": """name: test-task
prompt: |
  This is a test prompt
allowed_tools:
  - Bash
  - Read
trigger:
  type: cron
  expression: "0 9 * * *"
enabled: true
""",
    }

    assert _validate_generated_task(task) is True


def test_validate_generated_task_missing_fields():
    """Test validation fails when required fields are missing."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "test-task",
        # Missing description and yaml_config
    }

    assert _validate_generated_task(task) is False


def test_validate_generated_task_invalid_filename():
    """Test validation fails for unsafe filenames."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "../evil-task",
        "description": "Bad task",
        "yaml_config": "name: test\nprompt: test\n",
    }

    assert _validate_generated_task(task) is False


def test_validate_generated_task_dangerous_commands():
    """Test validation fails for tasks with dangerous commands."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "evil-task",
        "description": "Dangerous task",
        "yaml_config": """name: evil-task
prompt: |
  Run rm -rf / to clean up
allowed_tools:
  - Bash
""",
    }

    assert _validate_generated_task(task) is False


def test_validate_generated_task_invalid_yaml():
    """Test validation fails for invalid YAML."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "test-task",
        "description": "Test",
        "yaml_config": "invalid: yaml: syntax: here:",
    }

    assert _validate_generated_task(task) is False


def test_validate_generated_task_no_prompt():
    """Test validation fails when YAML has no prompt."""
    from clodputer.onboarding import _validate_generated_task

    task = {
        "name": "test-task",
        "description": "Test",
        "yaml_config": """name: test-task
allowed_tools:
  - Bash
""",
    }

    assert _validate_generated_task(task) is False


def test_detect_available_mcps_command_not_found(monkeypatch):
    """Test MCP detection when claude command is not found."""
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: None)

    mcps = onboarding._detect_available_mcps()
    assert mcps == []


def test_detect_available_mcps_command_fails(monkeypatch):
    """Test MCP detection when command returns non-zero."""
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/usr/bin/claude")
    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=1, stdout="", stderr="error"),
    )

    mcps = onboarding._detect_available_mcps()
    assert mcps == []


def test_detect_available_mcps_success(monkeypatch):
    """Test successful MCP detection."""
    from clodputer import onboarding

    mock_output = """Checking MCP server health...

gmail: npx gmail - ✓ Connected
search: node search.js - ✗ Failed to connect
"""

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/usr/bin/claude")
    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout=mock_output, stderr=""),
    )

    mcps = onboarding._detect_available_mcps()
    assert len(mcps) == 2
    assert mcps[0]["name"] == "gmail"
    assert mcps[0]["status"] == "connected"


def test_generate_task_suggestions_no_cli_path(monkeypatch):
    """Test task generation when CLI path is not available."""
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: None)

    tasks = onboarding._generate_task_suggestions([])
    assert tasks is None


def test_generate_task_suggestions_timeout(monkeypatch):
    """Test task generation handles timeout."""
    from clodputer import onboarding
    import subprocess

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/usr/bin/claude")

    def mock_run(*_, **__):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=60)

    monkeypatch.setattr(onboarding.subprocess, "run", mock_run)

    tasks = onboarding._generate_task_suggestions([])
    assert tasks is None


def test_generate_task_suggestions_invalid_json(monkeypatch):
    """Test task generation handles invalid JSON response."""
    from clodputer import onboarding

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/usr/bin/claude")
    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout="not json", stderr=""),
    )

    tasks = onboarding._generate_task_suggestions([])
    assert tasks is None


def test_generate_task_suggestions_success(monkeypatch):
    """Test successful task generation."""
    from clodputer import onboarding

    mock_response = {
        "tasks": [
            {
                "name": "test-task",
                "description": "A test task",
                "yaml_config": """name: test-task
prompt: |
  Test prompt
allowed_tools:
  - Bash
trigger:
  type: cron
  expression: "0 9 * * *"
""",
                "reasoning": "Useful task",
            }
        ]
    }

    monkeypatch.setattr(onboarding, "claude_cli_path", lambda *_: "/usr/bin/claude")
    monkeypatch.setattr(
        onboarding.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(
            returncode=0,
            stdout=onboarding.json_module.dumps(mock_response),
            stderr="",
        ),
    )

    tasks = onboarding._generate_task_suggestions([])
    assert tasks is not None
    assert len(tasks) == 1
    assert tasks[0]["name"] == "test-task"
