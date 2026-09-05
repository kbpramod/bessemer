import logging
from langgraph.graph import StateGraph, START, END

from agents.state import ForgeState
from agents.nodes.discover import discover_node
from agents.nodes.understanding import understanding_node
from agents.nodes.planner import planner_node
from agents.nodes.builder import builder_node

logger = logging.getLogger("forge.agent.onboarding_graph")


def create_onboarding_graph():
    """
    Constructs and compiles the LangGraph StateGraph for Forge onboarding:
    Discover -> Page Understanding -> Test Planner -> Test Builder -> END

    Contains only the four core onboarding nodes:
    - discover
    - understanding
    - planner
    - builder
    """
    builder = StateGraph(ForgeState)

    # Add core nodes
    builder.add_node("discover", discover_node)
    builder.add_node("understanding", understanding_node)
    builder.add_node("planner", planner_node)
    builder.add_node("builder", builder_node)

    # Add deterministic sequence edges
    builder.add_edge(START, "discover")
    builder.add_edge("discover", "understanding")
    builder.add_edge("understanding", "planner")
    builder.add_edge("planner", "builder")
    builder.add_edge("builder", END)

    graph = builder.compile()
    return graph
