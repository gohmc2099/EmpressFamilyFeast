"""Chatbot agent – a conversational AI assistant."""

from __future__ import annotations

from agents.base import BaseAgent
from tools.registry import ToolRegistry

DEFAULT_CHATBOT_PROMPT = """\
You are a friendly, helpful AI assistant called {name}.
You engage in natural conversation, answer questions clearly, and help users
with a wide range of topics. Keep responses concise and useful.
If the user asks you to perform a task that requires tools, use the tools
available to you. Always explain what you did after using a tool.
"""


class ChatbotAgent(BaseAgent):
    """A conversational chatbot agent with optional tool access."""

    def __init__(
        self,
        name: str = "ChatBot",
        system_prompt: str | None = None,
        tool_registry: ToolRegistry | None = None,
        **kwargs,
    ) -> None:
        prompt = system_prompt or DEFAULT_CHATBOT_PROMPT.format(name=name)
        super().__init__(
            name=name,
            system_prompt=prompt,
            tool_registry=tool_registry,
            **kwargs,
        )
