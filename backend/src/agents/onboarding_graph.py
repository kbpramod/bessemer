import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END

from agents.state import ForgeState
from agents.nodes.discover import discover_node
from agents.nodes.understanding import understanding_node
from agents.nodes.planner import planner_node
from agents.nodes.onboarding_scheduler import get_next_hypothesis_node
from agents.nodes.builder import builder_node

logger = logging.getLogger("forge.agent.onboarding_graph")


def route_get_next_hypothesis(state: ForgeState) -> Literal["builder", "__end__"]:
    """
    Checks if another planned test hypothesis is ready to be built:
    - If current_test is present: route to 'builder'.
    - If the hypothesis queue is exhausted: route to END.
    """
    if state.get("current_test"):
        return "builder"
    return "__end__"


def create_onboarding_graph():
    """
    Constructs and compiles the LangGraph StateGraph for Forge onboarding:
    Discover -> Page Understanding -> Test Planner -> [Get Next Hypothesis <-> Builder] -> END

    The planner emits several SMOKE and FLOW test hypotheses (test_plan). Get Next Hypothesis
    dispatches them to the builder one at a time and loops until every hypothesis has been
    turned into a persisted, runnable test script.
    """
    builder = StateGraph(ForgeState)

    # Add core nodes
    builder.add_node("discover", discover_node)
    builder.add_node("understanding", understanding_node)
    builder.add_node("planner", planner_node)
    builder.add_node("get_next_hypothesis", get_next_hypothesis_node)
    builder.add_node("builder", builder_node)

    # Add deterministic sequence edges
    builder.add_edge(START, "discover")
    builder.add_edge("discover", "understanding")
    builder.add_edge("understanding", "planner")
    builder.add_edge("planner", "get_next_hypothesis")

    # Dispatch loop: build every hypothesis in the plan, one at a time
    builder.add_conditional_edges(
        "get_next_hypothesis",
        route_get_next_hypothesis,
        {
            "builder": "builder",
            "__end__": END,
        },
    )
    builder.add_edge("builder", "get_next_hypothesis")

    graph = builder.compile()
    return graph
