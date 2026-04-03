"""Multi-agent orchestrator – routes tasks to specialised agents."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from agents.base import BaseAgent
from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_TOKENS

ORCHESTRATOR_PROMPT = """\
You are a multi-agent orchestrator. You coordinate a team of specialised AI
agents to solve complex tasks.

Available agents:
{agent_list}

When the user gives you a task:
1. Decide which agent(s) are best suited.
2. Use the "delegate_to_agent" tool to send sub-tasks to the right agent.
3. Collect the results and synthesise a final answer for the user.

If the task is simple enough for one agent, delegate to that agent directly.
If the task is complex, break it into sub-tasks and delegate each part.
Always provide a clear, consolidated response at the end.
"""


class MultiAgentOrchestrator:
    """Routes user requests to the most suitable agent(s)."""

    def __init__(
        self,
        agents: list[BaseAgent] | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.agents: dict[str, BaseAgent] = {}
        self.model = model
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history: list[dict[str, Any]] = []
        if agents:
            for agent in agents:
                self.register_agent(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.name] = agent

    def _build_system_prompt(self) -> str:
        lines = []
        for name, agent in self.agents.items():
            desc = agent.system_prompt.split("\n")[0]
            lines.append(f"- {name}: {desc}")
        agent_list = "\n".join(lines) if lines else "No agents registered."
        return ORCHESTRATOR_PROMPT.format(agent_list=agent_list)

    def _delegation_tool(self) -> dict:
        agent_names = list(self.agents.keys())
        return {
            "name": "delegate_to_agent",
            "description": (
                "Delegate a sub-task to a specialised agent. "
                f"Available agents: {', '.join(agent_names)}"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to delegate to",
                        "enum": agent_names,
                    },
                    "task": {
                        "type": "string",
                        "description": "The sub-task to send to the agent",
                    },
                },
                "required": ["agent_name", "task"],
            },
        }

    def run(self, user_message: str, max_iterations: int = 10) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})

        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self._build_system_prompt(),
                tools=[self._delegation_tool()],
                messages=self.conversation_history,
            )

            assistant_content = response.content
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_content}
            )

            if response.stop_reason == "end_turn":
                text_parts = [
                    block.text
                    for block in assistant_content
                    if block.type == "text"
                ]
                return "\n".join(text_parts)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use" and block.name == "delegate_to_agent":
                        agent_name = block.input["agent_name"]
                        task = block.input["task"]
                        agent = self.agents.get(agent_name)
                        if agent is None:
                            result = f"Error: agent '{agent_name}' not found."
                        else:
                            result = agent.run(task)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                self.conversation_history.append(
                    {"role": "user", "content": tool_results}
                )

        return "Orchestrator reached maximum iterations."

    def reset(self) -> None:
        self.conversation_history = []
        for agent in self.agents.values():
            agent.reset()
