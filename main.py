"""Empress Family Feast – AI Agent System

Usage examples for the chatbot, task automation, and multi-agent orchestrator.
"""

from agents import ChatbotAgent, MultiAgentOrchestrator, TaskAutomationAgent
from tools.builtin import register_builtin_tools
from tools.registry import ToolRegistry


def create_tool_registry() -> ToolRegistry:
    """Create a tool registry with all built-in tools."""
    registry = ToolRegistry()
    register_builtin_tools(registry)
    return registry


def demo_chatbot() -> None:
    """Run an interactive chatbot session."""
    registry = create_tool_registry()
    chatbot = ChatbotAgent(name="EmpressBot", tool_registry=registry)
    print("=== Empress ChatBot ===")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue
        response = chatbot.run(user_input)
        print(f"\nEmpressBot: {response}\n")


def demo_task_agent() -> None:
    """Run a one-shot task automation example."""
    registry = create_tool_registry()
    agent = TaskAutomationAgent(name="TaskBot", tool_registry=registry)
    print("=== Task Automation Agent ===")
    task = input("Describe your task: ").strip()
    if not task:
        print("No task provided.")
        return
    result = agent.execute_task(task)
    print(f"\nResult: {result['result']}\n")
    print(f"Steps taken: {result['steps_taken']}")


def demo_orchestrator() -> None:
    """Run the multi-agent orchestrator."""
    registry = create_tool_registry()
    chatbot = ChatbotAgent(name="ChatBot", tool_registry=registry)
    task_agent = TaskAutomationAgent(name="TaskBot", tool_registry=registry)
    orchestrator = MultiAgentOrchestrator(agents=[chatbot, task_agent])

    print("=== Multi-Agent Orchestrator ===")
    print("The orchestrator will route your request to the best agent.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue
        response = orchestrator.run(user_input)
        print(f"\nOrchestrator: {response}\n")


if __name__ == "__main__":
    print("Empress Family Feast – AI Agent System")
    print("=" * 42)
    print("1. Chatbot Agent")
    print("2. Task Automation Agent")
    print("3. Multi-Agent Orchestrator")
    print()
    choice = input("Select a mode (1/2/3): ").strip()
    if choice == "1":
        demo_chatbot()
    elif choice == "2":
        demo_task_agent()
    elif choice == "3":
        demo_orchestrator()
    else:
        print("Invalid choice.")
