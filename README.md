# Empress Family Feast – AI Agent System

A Python-based multi-agent AI system powered by Anthropic Claude. Includes a conversational chatbot, a task automation agent, and a multi-agent orchestrator that routes tasks to the best-suited agent.

## Features

- **Chatbot Agent** – Conversational AI assistant with tool access
- **Task Automation Agent** – Breaks down and executes multi-step tasks
- **Multi-Agent Orchestrator** – Routes requests to specialised agents and synthesises results
- **Tool System** – Extensible tool registry with built-in tools (file I/O, calculator, search, time)

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
3. **Orchestrator** – Multi-agent collaboration

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
│   ├── task_agent.py    # Task automation agent
│   └── orchestrator.py  # Multi-agent orchestrator
├── tools/
│   ├── registry.py      # Tool & ToolRegistry classes
│   └── builtin.py       # Built-in tools
├── config/
│   └── settings.py      # Configuration
├── main.py              # Entry point & demos
└── requirements.txt
```
