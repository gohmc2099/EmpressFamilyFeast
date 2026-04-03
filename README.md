# Empress Family Feast – AI Agent System

A Python-based multi-agent AI system powered by Anthropic Claude. Includes a conversational chatbot, a task automation agent, and a multi-agent orchestrator that routes tasks to the best-suited agent.

## Features

- **Chatbot Agent** – Conversational AI assistant with tool access
- **Task Automation Agent** – Breaks down and executes multi-step tasks
- **ERIC Agent** – Escalating & Routing Intelligence Coordinator for delivery logistics
- **Multi-Agent Orchestrator** – Routes requests to specialised agents and synthesises results
- **Tool System** – Extensible tool registry with built-in tools and logistics-specific tools

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
│   └── logistics.py     # Logistics tools for ERIC
├── config/
│   └── settings.py      # Configuration
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
| `driver_roll_call` | Morning check-in with all drivers |
| `get_driver_status` | Status of a specific driver |
| `get_todays_deliveries` | All deliveries, optionally filtered by driver |
| `verify_proof_of_delivery` | CV-based address verification for delivery photos |
| `check_silent_drivers` | Detect drivers who haven't reported in |
| `log_incident` | Log incidents with severity and timestamp |
| `send_ops_alert` | Send alerts to the operations team |
| `get_delivery_summary` | Full day summary (completed/failed/pending) |
| `log_delivery_outcome` | Record final delivery outcome |

