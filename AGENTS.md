# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Empress Family Feast is a Python 3.12 multi-agent AI system for food delivery logistics in London. It has two entry points:

- **CLI** (`python3 main.py`) — interactive agent selector (chatbot, task automation, ERIC logistics agent, orchestrator). Requires `ANTHROPIC_API_KEY`.
- **Web Dashboard** (`python3 dashboard/app.py`) — Flask UI on port 5000 for managing drivers, deliveries, incidents, schedules, and ops logs. Works without `ANTHROPIC_API_KEY` (data-only features).

### Running the application

- **Dashboard (dev):** `python3 dashboard/app.py` — starts Flask dev server on `http://127.0.0.1:5000`
- **Dashboard (prod-like):** `gunicorn dashboard.app:app --bind 0.0.0.0:5000`
- **CLI agents:** `python3 main.py` — interactive; requires TTY and `ANTHROPIC_API_KEY`
- Use `python3` not `python` — the VM has no `python` symlink.

### Database

SQLite at `data/empress.db` (auto-created on first run). Seed data is auto-inserted if the DB is empty. To reset: `python3 -m db.seed --reset` from the project root.

### Environment variables

Copy `.env.example` to `.env`. The only required variable for AI features is `ANTHROPIC_API_KEY`. The Flask dashboard works without it. See `config/settings.py` for all config.

### Testing / linting

This codebase has no formal test suite (no pytest) and no linting configuration. The only test file is `db/test_sheets.py` which tests Google Sheets connectivity (optional). To validate the codebase, use import checks:

```
python3 -c "import agents, tools, db, dashboard.app, config; print('OK')"
```

### Key gotchas

- `dashboard/app.py` calls `_init_db()` at module scope (line 262), so importing the module triggers DB creation.
- Google Sheets is optional; the app falls back to SQLite gracefully.
- The `data/` directory is gitignored; SQLite DB is ephemeral across clean checkouts.
