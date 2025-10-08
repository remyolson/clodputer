# MCP Authentication Best Practices

Clodputer relies on Model Context Protocol (MCP) tools to access external
services such as Gmail, Google Calendar, Notion, or Todoist. This guide
describes how to store credentials securely and surface them to Claude Code
tasks without leaking secrets.

## 1. Store secrets in `~/.clodputer/secrets.env`

Create a dedicated secrets file owned by your user:

```bash
install -m 600 /dev/null ~/.clodputer/secrets.env
```

Add credentials as environment variables:

```dotenv
GMAIL_REFRESH_TOKEN=...
GOOGLE_CALENDAR_SERVICE_ACCOUNT=...
NOTION_API_KEY=...
TODOIST_API_TOKEN=...
```

`clodputer` automatically loads this file before executing tasks. Variables are
available to YAML templates via Jinja placeholders, e.g.
`"{{ secrets.GOOGLE_CALENDAR_SERVICE_ACCOUNT }}"`.

## 2. Reference secrets in task configs

```yaml
task:
  allowed_tools:
    - mcp__google-calendar
  context:
    service_account: "{{ secrets.GOOGLE_CALENDAR_SERVICE_ACCOUNT }}"
```

Secrets **must not** be embedded directly in the YAML.

## 3. Configure MCP tool files

Some MCP integrations expect JSON configuration files. Store them inside
`~/.clodputer/mcp/` and reference the path in `task.mcp_config`. Example for
Notion:

```json
// ~/.clodputer/mcp/notion.json
{
  "auth": {
    "token": "{{ secrets.NOTION_API_KEY }}"
  },
  "workspace": "automation"
}
```

Then in the task:

```yaml
task:
  mcp_config: ~/.clodputer/mcp/notion.json
```

## 4. Rotate tokens regularly

1. Update `~/.clodputer/secrets.env` with the new value.
2. Restart queued jobs: `clodputer queue --clear` (optional).
3. Run `clodputer doctor` to ensure the configuration parses correctly.

## 5. Export for Claude Code

`clodputer update-docs` regenerates the CLAUDE.md instructions that teach Claude
Code where secrets live and how to reference them. Run it after adding new MCP
tools so the agent knows which environment variables to expect.

## 6. Example: Google Calendar + Notion

```yaml
task:
  allowed_tools:
    - mcp__google-calendar
    - mcp__notion
  context:
    calendar_email: "{{ secrets.GCAL_EMAIL }}"
    notion_database_id: "{{ secrets.NOTION_CALENDAR_DB }}"
```

- `GCAL_EMAIL` and `NOTION_CALENDAR_DB` are set in `secrets.env`.
- Additional OAuth secrets (client ID/secret) live in
  `~/.clodputer/mcp/google-calendar.json`.

Keep `secrets.env` and MCP configs out of version control. The default
`.gitignore` already excludes them.
