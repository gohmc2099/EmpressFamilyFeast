# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a Python-based multi-agent AI system for "Empress Family Feast" delivery logistics, powered by the Anthropic Claude API. It has two entry points:

- **CLI agents** (`python main.py`) — interactive menu to select Chatbot, Task Automation, ERIC, or Orchestrator mode. Requires `ANTHROPIC_API_KEY`.
- **Web dashboard** (`python dashboard/app.py`) — Flask app on port 5000 for managing drivers, deliveries, incidents, and ops logs. Does **not** require `ANTHROPIC_API_KEY` for basic CRUD operations.

### Running the dashboard (dev mode)

```bash
python dashboard/app.py
# Serves on http://127.0.0.1:5000 with debug/hot-reload enabled
```

The database (SQLite at `data/empress.db`) is auto-created and seeded on first run via `db/seed.py`. No separate migration step needed.

### Key caveats

- **No linting or testing framework** is configured in this repo. Use `python -m py_compile <file>` for syntax checks.
- The CLI agents (`main.py`) require a valid `ANTHROPIC_API_KEY` in `.env` — they will fail at runtime without it. The dashboard works fine without the API key.
- Google Sheets integration is optional; the app falls back to SQLite automatically.
- The `.env` file is gitignored. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` to use the AI agents.
- Flask runs with `debug=True` in dev mode, so it auto-reloads on code changes. Restarting is needed only if you change dependencies.
