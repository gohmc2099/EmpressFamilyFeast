"""Empress Family Feast – AI Agent System

Usage examples for the chatbot, task automation, and multi-agent orchestrator.
"""

from agents import ChatbotAgent, ERICAgent, MultiAgentOrchestrator, TaskAutomationAgent
from db import get_db
from db.seed import seed_database
from tools.builtin import register_builtin_tools
from tools.logistics import register_logistics_tools
from tools.registry import ToolRegistry


def init_database() -> None:
    """Ensure the database exists and is seeded with initial data."""
    get_db()
    seed_database()


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


def demo_eric() -> None:
    """Run ERIC — the logistics operations agent."""
    registry = ToolRegistry()
    register_builtin_tools(registry)
    register_logistics_tools(registry)
    eric = ERICAgent(tool_registry=registry)

    print("=== ERIC — Escalating & Routing Intelligence Coordinator ===")
    print("Logistics agent for Empress Family Feast delivery operations.")
    print("Powered by Claude Vision + SQLite persistent database.")
    print()
    print("Quick commands:")
    print("  roll call   — Morning driver check-in")
    print("  silent      — Check for silent drivers")
    print("  summary     — End-of-day delivery summary")
    print("  verify      — Verify a delivery photo")
    print("  quit        — Exit")
    print()

    while True:
        user_input = input("Ops> ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("ERIC signing off.")
            break
        if not user_input:
            continue

        # Shortcut commands
        if user_input.lower() == "roll call":
            response = eric.morning_roll_call()
        elif user_input.lower() == "silent":
            response = eric.check_silent_drivers()
        elif user_input.lower() == "summary":
            response = eric.end_of_day_report()
        elif user_input.lower() == "verify":
            delivery_id = input("  Delivery ID (e.g. DEL-001): ").strip()
            photo_path = input("  Photo file path: ").strip()
            response = eric.run(
                f"Verify the proof-of-delivery photo for delivery {delivery_id}. "
                f"The photo is at: {photo_path}"
            )
        else:
            response = eric.run(user_input)

        print(f"\nERIC: {response}\n")


def demo_orchestrator() -> None:
    """Run the multi-agent orchestrator."""
    registry = create_tool_registry()
    logistics_registry = ToolRegistry()
    register_builtin_tools(logistics_registry)
    register_logistics_tools(logistics_registry)
    chatbot = ChatbotAgent(name="ChatBot", tool_registry=registry)
    task_agent = TaskAutomationAgent(name="TaskBot", tool_registry=registry)
    eric = ERICAgent(tool_registry=logistics_registry)
    orchestrator = MultiAgentOrchestrator(agents=[chatbot, task_agent, eric])

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
    init_database()
    print()
    print("Empress Family Feast – AI Agent System")
    print("=" * 42)
    print("1. Chatbot Agent")
    print("2. Task Automation Agent")
    print("3. ERIC — Logistics Operations Agent")
    print("4. Multi-Agent Orchestrator (all agents)")
    print()
    choice = input("Select a mode (1/2/3/4): ").strip()
    if choice == "1":
        demo_chatbot()
    elif choice == "2":
        demo_task_agent()
    elif choice == "3":
        demo_eric()
    elif choice == "4":
        demo_orchestrator()
    else:
        print("Invalid choice.")
