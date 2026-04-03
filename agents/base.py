"""Base agent class – the foundation for all AI agents."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY, DEFAULT_MODEL, MAX_TOKENS
from tools.registry import ToolRegistry


class BaseAgent:
    """Base agent that wraps the Anthropic Messages API with tool-use support.

    Subclass this to create specialised agents with their own system prompts,
    tools, and agentic loops.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = DEFAULT_MODEL,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        self.conversation_history: list[dict[str, Any]] = []
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _build_tools(self) -> list[dict] | None:
        schemas = self.tool_registry.list_schemas()
        return schemas if schemas else None

    def _handle_tool_use(self, tool_name: str, tool_input: dict) -> str:
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return f"Error: unknown tool '{tool_name}'"
        try:
            return tool.execute(**tool_input)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def run(self, user_message: str) -> str:
        """Send a message and let the agent loop until it produces a final text response."""
        self.conversation_history.append({"role": "user", "content": user_message})

        for _ in range(self.max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self.system_prompt,
                tools=self._build_tools() or [],
                messages=self.conversation_history,
            )

            # Collect assistant content blocks
            assistant_content = response.content
            self.conversation_history.append(
                {"role": "assistant", "content": assistant_content}
            )

            # If the model finished without requesting tools, return the text
            if response.stop_reason == "end_turn":
                text_parts = [
                    block.text
                    for block in assistant_content
                    if block.type == "text"
                ]
                return "\n".join(text_parts)

            # Process any tool_use blocks
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        result = self._handle_tool_use(block.name, block.input)
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

        return "Agent reached maximum iterations without a final response."

    def reset(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
