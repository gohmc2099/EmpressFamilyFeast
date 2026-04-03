"""Built-in tools that agents can use."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

from tools.registry import Tool, ToolRegistry


def get_current_time(**kwargs: str) -> str:
    fmt = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
    return datetime.datetime.now().strftime(fmt)


def read_file(**kwargs: str) -> str:
    path = kwargs["file_path"]
    if not os.path.isfile(path):
        return f"Error: file not found: {path}"
    return Path(path).read_text()


def write_file(**kwargs: str) -> str:
    path = kwargs["file_path"]
    content = kwargs["content"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content)
    return f"Successfully wrote to {path}"


def list_directory(**kwargs: str) -> str:
    path = kwargs.get("directory", ".")
    if not os.path.isdir(path):
        return f"Error: directory not found: {path}"
    entries = os.listdir(path)
    return json.dumps(entries, indent=2)


def calculate(**kwargs: str) -> str:
    expression = kwargs["expression"]
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return "Error: only basic arithmetic is allowed (digits, +, -, *, /, parentheses)"
    try:
        result = eval(expression)  # noqa: S307 – restricted to safe chars above
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def search_text(**kwargs: str) -> str:
    text = kwargs["text"]
    query = kwargs["query"]
    lines = text.splitlines()
    matches = [
        f"Line {i + 1}: {line}"
        for i, line in enumerate(lines)
        if query.lower() in line.lower()
    ]
    if not matches:
        return "No matches found."
    return "\n".join(matches)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register all built-in tools into the given registry."""
    registry.register(
        Tool(
            name="get_current_time",
            description="Get the current date and time.",
            parameters={
                "format": {
                    "type": "string",
                    "description": "strftime format string (default: %Y-%m-%d %H:%M:%S)",
                }
            },
            function=get_current_time,
        )
    )
    registry.register(
        Tool(
            name="read_file",
            description="Read the contents of a file.",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                }
            },
            function=read_file,
        )
    )
    registry.register(
        Tool(
            name="write_file",
            description="Write content to a file, creating directories as needed.",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            function=write_file,
        )
    )
    registry.register(
        Tool(
            name="list_directory",
            description="List the contents of a directory.",
            parameters={
                "directory": {
                    "type": "string",
                    "description": "Path to the directory to list (default: current dir)",
                }
            },
            function=list_directory,
        )
    )
    registry.register(
        Tool(
            name="calculate",
            description="Evaluate a basic arithmetic expression.",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate (e.g. '2 + 3 * 4')",
                }
            },
            function=calculate,
        )
    )
    registry.register(
        Tool(
            name="search_text",
            description="Search for a query string within a block of text.",
            parameters={
                "text": {"type": "string", "description": "The text to search through"},
                "query": {"type": "string", "description": "The search query"},
            },
            function=search_text,
        )
    )
