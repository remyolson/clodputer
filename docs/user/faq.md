# Frequently Asked Questions

**Q: Does Clodputer support Windows or Linux?**  
A: The MVP targets macOS only (cron, rumps, and certain CLI integrations are macOS-specific). Cross-platform support is on the phase 4 roadmap.

**Q: Can I run multiple tasks at the same time?**  
A: Not in the MVP. Tasks execute sequentially to simplify resource management and avoid MCP conflicts. You can prioritise urgent jobs with `--priority high`.

**Q: How do I create tasks automatically?**  
A: Ask Claude Code to generate YAML based on the [Configuration Reference](configuration.md). Claude can save files to `~/.clodputer/tasks/` directly.

**Q: Where are logs stored?**  
A: Structured execution logs live in `~/.clodputer/execution.log`. Cron output is in `~/.clodputer/cron.log`, and watcher activity in `~/.clodputer/watcher.log`.

**Q: How do I upgrade Clodputer?**  
A: Pull the latest changes and reinstall:
```bash
git pull origin main
pip install -e ".[dev]"
clodputer doctor
```

**Q: What happens if queue.json becomes corrupted?**  
A: The loader automatically archives the corrupt file (`queue.corrupt-*.json`) and starts fresh. You can inspect the archived file to manually requeue items if needed.

**Q: Are retries supported?**  
A: Automatic retries are not part of the MVP. Review failures via `clodputer logs` and re-run tasks manually after fixing the root cause.

**Q: Can I use custom MCP servers?**  
A: Yes. Tools that start with `mcp__` are accepted (e.g., `mcp__gmail`). Ensure the MCP is configured in your Claude environment.

**Q: How do I disable a task without deleting it?**  
A: Set `enabled: false` in the YAML. The task remains in the list but will not be scheduled or triggered.

**Q: Where can I get help?**  
A: Review the [Troubleshooting Guide](troubleshooting.md) and run `clodputer doctor`. If an issue persists, open a GitHub issue with logs and configuration details.
