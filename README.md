# Empress Family Feast – AI Agent System

A Python-based multi-agent AI system powered by Anthropic Claude. Includes a conversational chatbot, a task automation agent, and a multi-agent orchestrator that routes tasks to the best-suited agent.

## Features

- **Chatbot Agent** – Conversational AI assistant with tool access
- **Task Automation Agent** – Breaks down and executes multi-step tasks
- **ERIC Agent** – Escalating & Routing Intelligence Coordinator for delivery logistics
- **Multi-Agent Orchestrator** – Routes requests to specialised agents and synthesises results
- **Claude Vision** – AI-powered proof-of-delivery photo verification
- **Persistent Database** – SQLite storage for all delivery data, incidents, and verifications
- **Referral App** – Ambassador signup, referral tracking, and reward management
- **Tool System** – Extensible tool registry with built-in, logistics, and vision tools

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your Anthropic API key
```

## Usage

```bash
python main.py
```

Select a mode:
1. **Chatbot** – Interactive conversation
2. **Task Automation** – Execute structured tasks
3. **ERIC** – Logistics operations agent (driver check-ins, delivery verification, escalation)
4. **Orchestrator** – Multi-agent collaboration (includes all agents)

### Web dashboard (including Referral App)

```bash
python dashboard/app.py
```

Then open: `http://127.0.0.1:5000/referrals`

## Adding Custom Tools

```python
from tools.registry import Tool, ToolRegistry

def my_tool(**kwargs):
    return f"Hello, {kwargs['name']}!"

registry = ToolRegistry()
registry.register(Tool(
    name="greet",
    description="Greet someone by name",
    parameters={"name": {"type": "string", "description": "Name to greet"}},
    function=my_tool,
))
```

## Project Structure

```
├── agents/
│   ├── base.py          # Base agent with tool-use loop
│   ├── chatbot.py       # Conversational chatbot agent
│   ├── eric.py          # ERIC — logistics operations agent
│   ├── task_agent.py    # Task automation agent
│   └── orchestrator.py  # Multi-agent orchestrator
├── tools/
│   ├── registry.py      # Tool & ToolRegistry classes
│   ├── builtin.py       # Built-in tools
│   ├── logistics.py     # Logistics tools for ERIC (database-backed)
│   └── vision.py        # Claude Vision photo analysis
├── db/
│   ├── __init__.py      # Auto-selects Google Sheets or SQLite
│   ├── database.py      # SQLite database layer (fallback)
│   ├── google_sheets.py # Google Sheets database adapter
│   └── seed.py          # Seed data for drivers & deliveries
├── config/
│   └── settings.py      # Configuration
├── data/                # SQLite database files (gitignored)
├── main.py              # Entry point & demos
└── requirements.txt
```

## ERIC — Escalating & Routing Intelligence Coordinator

ERIC is the dedicated logistics agent for Empress Family Feast delivery operations. He acts as the **eyes and ears** of the operation.

### What ERIC does
- **Morning roll call** — Checks in with all drivers, confirms availability and vehicle readiness
- **Delivery verification** — Verifies proof-of-delivery photos against customer addresses
- **Silent driver detection** — Flags drivers who haven't reported in
- **Incident escalation** — Logs and escalates breakdowns, no-shows, wrong deliveries
- **End-of-day reports** — Compiles full delivery summaries for the ops team

### What ERIC never does
- Modify customer records, routes, or source data
- Make operational decisions — he flags and hands off to humans
- Wait until customers are affected — he alerts ops proactively

### ERIC's tools
| Tool | Description |
|------|-------------|
| `driver_roll_call` | Morning check-in with all drivers (database-backed) |
| `get_driver_status` | Status of a specific driver |
| `get_todays_deliveries` | All deliveries, optionally filtered by driver |
| `verify_delivery_photo` | **Claude Vision AI** — analyses delivery photos for address evidence, delivery proof, and quality |
| `analyse_photo` | General-purpose Claude Vision photo analysis |
| `check_silent_drivers` | Detect drivers who haven't reported in |
| `log_incident` | Log incidents with severity and timestamp |
| `send_ops_alert` | Send alerts to the operations team |
| `get_delivery_summary` | Full day summary (completed/failed/pending) |
| `log_delivery_outcome` | Record final delivery outcome |

### Claude Vision — How photo verification works

When a driver submits a proof-of-delivery photo, ERIC uses the `verify_delivery_photo` tool:

1. The photo is loaded and sent to Claude's vision model
2. Claude analyses the image for: visible addresses, house numbers, street names, postcodes
3. The detected address is compared against the expected customer address
4. Claude checks for delivery evidence (packages, food bags, doorstep placement)
5. A confidence score and match result (MATCH / MISMATCH / INCONCLUSIVE) is returned
6. The result is persisted to the `photo_verifications` table in SQLite
7. The delivery status is updated automatically based on the result

### Data Storage — Google Sheets or SQLite

Data can be stored in **Google Sheets** (recommended for team access) or **SQLite** (local fallback).

**Google Sheets** — set `GOOGLE_SHEET_ID` env var and the app auto-creates these tabs:

| Sheet Tab | Contents |
|-----------|----------|
| `Drivers` | Driver profiles, availability, vehicle status, WhatsApp group |
| `Schedule` | Weekly active days per driver |
| `Stops` | Delivery stops per driver |
| `Deliveries` | All deliveries with status, photo verification results |
| `Incidents` | Logged incidents with severity and timestamps |
| `OpsMessages` | All alerts sent to the operations team |
| `PhotoVerifications` | Claude Vision analysis results |

Your team can view and edit data directly in the Google Sheet.

**SQLite fallback** — if Google Sheets is not configured, data is stored locally in `data/empress.db`. Run `python -m db.seed --reset` to reset to defaults.

#### Google Sheets setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key file
4. Save it as `credentials.json` in the project root (or set `GOOGLE_CREDENTIALS_JSON` env var with the JSON contents)
5. Create a Google Sheet → share it with the service account email (the `client_email` in the JSON)
6. Copy the spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
7. Set env var: `GOOGLE_SHEET_ID=your-sheet-id-here`

