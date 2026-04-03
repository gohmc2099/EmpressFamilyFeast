"""Task automation agent – executes structured, multi-step tasks."""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from tools.registry import ToolRegistry

DEFAULT_TASK_PROMPT = """\
You are a task automation agent called {name}.
Your job is to break down a user's request into concrete steps and execute them
using the tools available to you.

When given a task:
1. Analyse the request and identify the steps required.
2. Execute each step using the appropriate tool.
3. Report the outcome of each step clearly.
4. Provide a final summary when all steps are complete.

Always be methodical and transparent about what you are doing.
"""


class TaskAutomationAgent(BaseAgent):
    """Agent specialised for executing multi-step automated tasks."""

    def __init__(
        self,
        name: str = "TaskAgent",
        system_prompt: str | None = None,
        tool_registry: ToolRegistry | None = None,
        **kwargs,
    ) -> None:
        prompt = system_prompt or DEFAULT_TASK_PROMPT.format(name=name)
        super().__init__(
            name=name,
            system_prompt=prompt,
            tool_registry=tool_registry,
            **kwargs,
        )

    def execute_task(self, task_description: str) -> dict[str, Any]:
        """Run a task and return structured results."""
        response = self.run(task_description)
        return {
            "agent": self.name,
            "task": task_description,
            "result": response,
            "steps_taken": len(self.conversation_history),
        }
