import json
import logging
from typing import Any, Dict, List
from agents.llm import get_chat_model
from agents.state import ForgeState, UserJourney
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger("forge.agent.planner")

PLANNER_SYSTEM_PROMPT = """You are a Senior Test Architect specializing in User Journey Validation.
Your task is to synthesize 2 to 4 high-value User Journeys to validate the core capabilities of this web application based on the discovered page model and understanding.

CORE PHILOSOPHY:
Forge validates real user capabilities through:
    ACTION -> STATE TRANSITION -> OUTCOME

CRITICAL RULE:
Do NOT generate tests that merely check if an element exists.
PROHIBITED: "Verify Contact Us button exists", "Verify Login button is visible", "Verify heading is present".
REQUIRED:
- "Verify Contact Us interaction opens the contact experience (page or modal)"
- "Verify a user can authenticate using the login UI"
- "Verify valid content can be submitted and reaches the expected review state"
- "Verify product navigation successfully transitions to the details view"

For each User Journey, provide:
- id: Slug like 'journey_contact_experience', 'journey_user_login', 'journey_search_flow'
- name: Human-readable name (e.g. 'Contact Company Journey')
- goal: What the user is trying to accomplish
- preconditions: List of prerequisites (e.g. ["Homepage is loaded in browser"])
- steps: Action sequence to perform the journey
- state_transitions: List of expected state transitions (e.g. ["anonymous_landing -> contact_experience_accessible"])
- expected_outcome: Clear functional outcome
- supported_viewports: ["desktop", "tablet", "mobile"]
- priority: 'high', 'medium', or 'low'
- category: 'capability', 'state_transition', 'happy_path', or 'validation'

Return strictly a JSON array of objects matching this schema:
[
  {
    "id": "journey_contact_experience",
    "name": "Contact Company Interaction",
    "goal": "Allow the user to access the contact experience",
    "preconditions": ["Target page is loaded"],
    "steps": [
      "Navigate to target URL",
      "Trigger Contact Us interaction (or mobile navigation if on mobile)",
      "Verify contact experience becomes accessible"
    ],
    "state_transitions": ["initial_page -> contact_experience_accessible"],
    "expected_outcome": "The contact experience becomes accessible either through page navigation or modal display",
    "supported_viewports": ["desktop", "tablet", "mobile"],
    "priority": "high",
    "category": "capability"
  }
]
Output ONLY valid JSON.
"""


def planner_node(state: ForgeState) -> Dict[str, Any]:
    """
    JOURNEY PLANNER node:
    Transforms discovered capabilities and application structure into meaningful User Journeys.
    Prioritizes: action -> state transition -> outcome.
    """
    disc = state.get("discovery_data") or {}
    page_info = disc.get("page", {})
    understanding = state.get("page_understanding") or {}
    elements = disc.get("elements", {})
    vp_summary = elements.get("viewports_summary", {})
    config_viewport = (state.get("config", {}).get("viewport") or "desktop").lower()

    logger.info(f"[JOURNEY PLANNER] Formulating user journeys for: {page_info.get('url')}")

    planner_input = {
        "url": page_info.get("url"),
        "title": page_info.get("title"),
        "page_type": understanding.get("page_type"),
        "purpose": understanding.get("purpose"),
        "capabilities": understanding.get("capabilities", []),
        "state_transitions": understanding.get("state_transitions", []),
        "primary_actions": understanding.get("primary_actions", []),
        "key_elements": understanding.get("key_interactive_elements", []),
        "viewports_summary": vp_summary,
        "available_buttons": [
            {"text": b.get("text"), "visible_viewports": b.get("visible_viewports", ["desktop"])}
            for b in elements.get("buttons", [])[:12]
        ],
        "available_links": [
            {"text": l.get("text"), "href": l.get("href"), "visible_viewports": l.get("visible_viewports", ["desktop"])}
            for l in elements.get("links", [])[:12]
        ],
        "available_inputs": [
            {"placeholder": i.get("placeholder"), "name": i.get("name")}
            for i in elements.get("inputs", [])[:8]
        ],
    }

    try:
        llm = get_chat_model()
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"Discovered Capabilities & Structure:\n{json.dumps(planner_input, indent=2)}")
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        raw_plan = json.loads(content)
        if not isinstance(raw_plan, list) or len(raw_plan) == 0:
            raise ValueError("Test plan output must be a non-empty list.")

        test_plan: List[UserJourney] = []
        for item in raw_plan:
            # Normalize title and description aliases
            item["title"] = item.get("name") or item.get("title") or item.get("id")
            item["description"] = item.get("goal") or item.get("description") or ""
            item["supported_viewports"] = item.get("supported_viewports") or ["desktop", "tablet", "mobile"]
            # Assign execution-specific viewport if not explicitly specified
            if "viewport" not in item or not item["viewport"]:
                item["viewport"] = config_viewport
            test_plan.append(item)

    except Exception as e:
        logger.warning(f"[JOURNEY PLANNER] LLM planner failed ({e}). Generating fallback capability journey.")
        test_plan = [
            {
                "id": "journey_primary_navigation",
                "name": f"Validate core navigation for {page_info.get('title', 'Target Page')}",
                "title": f"Validate core navigation for {page_info.get('title', 'Target Page')}",
                "goal": "Verify user can load the page and interact with the primary navigation link",
                "description": "Asserts the page loads successfully and clicking primary navigation transitions to the target view",
                "priority": "high",
                "category": "capability",
                "preconditions": ["Browser opens target page"],
                "steps": [
                    f"Navigate to {page_info.get('url')}",
                    "Perform interaction with primary navigational element",
                    "Verify target page state transition succeeds"
                ],
                "state_transitions": ["initial_load -> destination_accessible"],
                "expected_outcome": "User action triggers valid navigation state transition without application crash",
                "supported_viewports": ["desktop", "tablet", "mobile"],
                "viewport": config_viewport,
            }
        ]

    logger.info(f"[JOURNEY PLANNER] Planned {len(test_plan)} User Journeys. First: '{test_plan[0]['id']}'")

    return {
        "test_plan": test_plan,
        "current_test_idx": 0,
        "current_test": test_plan[0],
        "heal_attempt": 0,
        "healing_history": [],
    }
