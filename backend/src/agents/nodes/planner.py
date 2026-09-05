import json
import logging
from typing import Any, Dict, List
from agents.llm import get_chat_model
from agents.state import ForgeState, UserJourney
from storage.local import save_hypotheses
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger("forge.agent.planner")

PLANNER_SYSTEM_PROMPT = """You are a Senior Test Architect specializing in User Journey Validation.
Your task is to synthesize high-value test hypotheses to validate this web application based on the discovered page model and understanding.

TEST CATEGORIZATION:
You MUST divide your test hypotheses into two distinct categories:
1. "SMOKE" (1 to 2 tests):
   - Fast sanity checks validating that the target page loads cleanly, primary navigation is functional, and core entry points / modals open without JavaScript crashes.
   - Example: Verify landing page loads and clicking primary navigation / contact link successfully transitions state.
2. "FLOW" (2 to 3 tests):
   - Multi-step end-to-end user journeys validating real capabilities:
     ACTION -> STATE TRANSITION -> OUTCOME
   - Example: Complete form submission, user authentication, search and filter flow, or multi-step checkout/interaction.

CRITICAL RULE:
Do NOT generate tests that merely check if a static element exists.
PROHIBITED: "Verify Contact Us button exists", "Verify Login button is visible", "Verify heading is present".
REQUIRED: Real user interactions that test state transitions and functional outcomes.

For each test hypothesis, provide strictly:
- id: Descriptive slug prefixed with type, e.g. "smoke_primary_navigation", "flow_login", "flow_contact_submission"
- type: Exactly "SMOKE" or "FLOW"
- intent: Clear intent of the user/system (e.g. "A user can log into the application")
- preconditions: List of prerequisites (e.g. ["valid credentials are available", "homepage is loaded"])
- steps: Action sequence to execute the journey
- expected: List of expected outcomes/assertions (e.g. ["user reaches authenticated application state"])
- evidence: Grounding evidence observed from DOM elements and routes (e.g. ["element:email", "element:password", "element:login_button", "navigation:/dashboard"])
- supported_viewports: ["desktop", "tablet", "mobile"]
- priority: "high", "medium", or "low"

Return strictly a JSON array of objects matching this schema:
[
  {
    "id": "smoke_navigation_header",
    "type": "SMOKE",
    "intent": "Verify page loads and main navigation responds cleanly",
    "preconditions": ["Homepage is loaded in browser"],
    "steps": [
      "Navigate to target URL",
      "Interact with primary navigation menu",
      "Verify navigation destination responds without application crash"
    ],
    "expected": [
      "Target view transitions cleanly without runtime console errors"
    ],
    "evidence": [
      "element:nav_bar",
      "element:nav_link",
      "navigation:/about"
    ],
    "supported_viewports": ["desktop", "tablet", "mobile"],
    "priority": "high"
  },
  {
    "id": "flow_login",
    "type": "FLOW",
    "intent": "A user can log into the application",
    "preconditions": [
      "valid credentials are available"
    ],
    "steps": [
      "enter email",
      "enter password",
      "submit login"
    ],
    "expected": [
      "user reaches authenticated application state"
    ],
    "evidence": [
      "element:email",
      "element:password",
      "element:login_button",
      "navigation:/dashboard"
    ],
    "supported_viewports": ["desktop", "tablet", "mobile"],
    "priority": "high"
  }
]
Output ONLY valid JSON.
"""


def planner_node(state: ForgeState) -> Dict[str, Any]:
    """
    JOURNEY PLANNER node:
    Transforms discovered capabilities into structured test hypotheses divided into SMOKE and FLOW tests.
    Saves hypotheses to <storage_root>/<domain>/planner/hypotheses.json and category folders.
    """
    disc = state.get("discovery_data") or {}
    page_info = disc.get("page", {})
    target_url = page_info.get("url") or state.get("target_url", "")
    understanding = state.get("page_understanding") or {}
    elements = disc.get("elements", {})
    vp_summary = elements.get("viewports_summary", {})
    config_viewport = (state.get("config", {}).get("viewport") or "desktop").lower()

    logger.info(f"[JOURNEY PLANNER] Formulating SMOKE and FLOW hypotheses for: {target_url}")

    planner_input = {
        "url": target_url,
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
            {"placeholder": i.get("placeholder"), "name": i.get("name"), "type": i.get("type")}
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
            # Normalize and enforce schema
            test_type = str(item.get("type") or "FLOW").strip().upper()
            if test_type not in ("SMOKE", "FLOW"):
                test_type = "SMOKE" if "smoke" in str(item.get("id", "")).lower() else "FLOW"
            item["type"] = test_type

            # Normalize intent / goal / title / name
            intent = item.get("intent") or item.get("goal") or item.get("description") or item.get("name") or "User Journey"
            item["intent"] = intent
            item["goal"] = intent
            item["name"] = item.get("name") or intent
            item["title"] = item.get("title") or item["name"]
            item["description"] = item.get("description") or intent

            # Normalize expected
            raw_expected = item.get("expected")
            if isinstance(raw_expected, list):
                expected_list = [str(e) for e in raw_expected]
            elif isinstance(raw_expected, str):
                expected_list = [raw_expected]
            else:
                expected_list = [item.get("expected_outcome", "State transition succeeds cleanly")]
            item["expected"] = expected_list
            item["expected_outcome"] = "; ".join(expected_list)

            # Normalize evidence
            raw_evidence = item.get("evidence")
            if isinstance(raw_evidence, list):
                item["evidence"] = [str(ev) for ev in raw_evidence]
            else:
                item["evidence"] = []

            # Preconditions & steps
            item["preconditions"] = item.get("preconditions") or ["Target page is loaded"]
            item["steps"] = item.get("steps") or ["Navigate to target URL", "Perform interaction", "Verify expected state"]

            # Viewports & category
            item["supported_viewports"] = item.get("supported_viewports") or ["desktop", "tablet", "mobile"]
            if "viewport" not in item or not item["viewport"]:
                item["viewport"] = config_viewport
            item["category"] = item.get("category") or test_type.lower()
            item["priority"] = item.get("priority") or ("high" if test_type == "SMOKE" else "medium")

            test_plan.append(item)

    except Exception as e:
        logger.warning(f"[JOURNEY PLANNER] LLM planner failed ({e}). Generating fallback SMOKE and FLOW hypotheses.")
        page_title = page_info.get("title") or "Target Page"
        test_plan = [
            {
                "id": "smoke_primary_navigation",
                "type": "SMOKE",
                "intent": f"Verify {page_title} loads and primary navigation is responsive",
                "name": f"Smoke Test: {page_title} Navigation",
                "title": f"Smoke Test: {page_title} Navigation",
                "goal": f"Verify {page_title} loads and primary navigation is responsive",
                "description": f"Smoke check verifying page loads and primary navigational elements respond",
                "priority": "high",
                "category": "smoke",
                "preconditions": ["Browser opens target page"],
                "steps": [
                    f"Navigate to {target_url}",
                    "Check page loads without fatal runtime errors",
                    "Interact with primary navigation element"
                ],
                "expected": ["Page renders successfully and navigation transitions cleanly"],
                "expected_outcome": "Page renders successfully and navigation transitions cleanly",
                "evidence": ["element:navbar", "navigation:/"],
                "supported_viewports": ["desktop", "tablet", "mobile"],
                "viewport": config_viewport,
            },
            {
                "id": "flow_core_interaction",
                "type": "FLOW",
                "intent": f"Validate core capability workflow for {page_title}",
                "name": f"Core Journey Flow: {page_title}",
                "title": f"Core Journey Flow: {page_title}",
                "goal": f"Validate core capability workflow for {page_title}",
                "description": f"End-to-end journey validating capability state transitions",
                "priority": "high",
                "category": "flow",
                "preconditions": ["Browser opens target page"],
                "steps": [
                    f"Navigate to {target_url}",
                    "Perform core interaction sequence",
                    "Verify target state transition is reached"
                ],
                "expected": ["Application reaches expected interactive state transition without crash"],
                "expected_outcome": "Application reaches expected interactive state transition without crash",
                "evidence": ["element:button", "element:input"],
                "supported_viewports": ["desktop", "tablet", "mobile"],
                "viewport": config_viewport,
            }
        ]

    # Persist hypotheses to storage folder
    if target_url:
        try:
            saved_path = save_hypotheses(target_url, test_plan)
            logger.info(f"[JOURNEY PLANNER] Hypotheses persisted to: {saved_path}")
        except Exception as save_err:
            logger.warning(f"[JOURNEY PLANNER] Could not save hypotheses to storage: {save_err}")

    smoke_count = sum(1 for t in test_plan if t.get("type") == "SMOKE")
    flow_count = sum(1 for t in test_plan if t.get("type") == "FLOW")
    logger.info(
        f"[JOURNEY PLANNER] Planned {len(test_plan)} total hypotheses "
        f"({smoke_count} SMOKE, {flow_count} FLOW). First: '{test_plan[0]['id']}' [{test_plan[0].get('type')}]"
    )

    return {
        "test_plan": test_plan,
        "current_test_idx": 0,
        "current_test": test_plan[0],
        "heal_attempt": 0,
        "healing_history": [],
    }
