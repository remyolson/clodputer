# MCP Authentication (Advanced Overrides)

Clodputer runs automations on top of Claude Code. Claude Code already manages
Model Context Protocol (MCP) connections and the credentials required to access
them. **For most setups you should rely entirely on Claude Code’s configuration** –
Clodputer simply invokes the Claude CLI, so it inherits those MCP permissions
automatically.

Only follow the steps below if you have an advanced use case where Claude Code
cannot store a required credential (for example, a task that has to read a local
API key from disk). In that scenario, you can supply overrides via
`~/.clodputer/secrets.env` or auxiliary JSON files. Templates that reference
`{{ secrets.* }}` will look in that file if present.

## 1. Create a secrets file (optional)

```bash
install -m 600 /dev/null ~/.clodputer/secrets.env
```

Add only the values that cannot live in Claude Code:

```dotenv
NOTION_API_KEY=...
PRIVATE_API_TOKEN=...
```

Clodputer loads this file before executing tasks. Variables become available to
YAML templates as `{{ secrets.NAME }}`.

## 2. Reference secrets in task configs

```yaml
task:
  allowed_tools:
    - mcp__notion
  context:
    private_token: "{{ secrets.PRIVATE_API_TOKEN }}"
```

Keep the template prompt explicit so that Claude Code knows how to use the
secret once it is injected.

## 3. Optional MCP metadata files

Some MCP plugins expect JSON configuration. Store overrides in
`~/.clodputer/mcp/` if needed and point `task.mcp_config` at the file. Claude
Code will see the contents when the task runs.

## 4. Keep data fresh

When rotating secrets: update `~/.clodputer/secrets.env`, re-run
`clodputer doctor`, and optionally restart queued jobs.

## 5. Maintain CLAUDE.md

If you add new override secrets, regenerate the Clodputer section of CLAUDE.md
(`clodputer update-docs`) so Claude Code is aware of the new environment keys.

Remember: these overrides are optional. Prefer configuring MCP connections and
credentials inside Claude Code whenever possible.
