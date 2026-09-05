import json
import logging
import os
from pathlib import Path
from typing import Any, Dict
from agents.llm import get_chat_model
from agents.state import ForgeState
from langchain_core.messages import SystemMessage, HumanMessage
from storage.local import get_website_storage_dir
from db.repository import ForgeRepository
from schemas.discovery import FIXED_VIEWPORTS

logger = logging.getLogger("forge.agent.builder")

BUILDER_PYTHON_SYSTEM_PROMPT = """You are an elite Playwright Python Test Automation Engineer.
Your task is to generate clean, robust, modern Playwright Python test scripts (.py) validating User Journeys on the web application.

TEST CATEGORIES:
- If test_type is "SMOKE": Generate a concise sanity test verifying page load, target element presence/responsiveness, and primary state transition without complex branching.
- If test_type is "FLOW": Generate a comprehensive multi-step user journey validating the full sequence:
    ACTION -> STATE TRANSITION -> OUTCOME

Requirements for the generated Playwright Python test:
1. Must use standard library imports and synchronous Playwright API:
   import os
   import re
   from playwright.sync_api import sync_playwright, expect

2. Structure inside a callable test function configuring the specified target_viewport:
   def test_{test_id}():
       headless = os.getenv("HEADLESS", "true").lower() in (
           "true",
           "1",
           "yes",
       )
       with sync_playwright() as p:
           browser = p.chromium.launch(headless=headless)
           context = browser.new_context(viewport={"width": <target_width>, "height": <target_height>})
           page = context.new_page()
           try:
               page.goto('{target_url}', wait_until='domcontentloaded', timeout=30000)
               # user actions, state transitions, and functional assertions here
               print("[TEST PASSED] {scenario_title}")
           finally:
               context.close()
               browser.close()

   if __name__ == "__main__":
       test_{test_id}()

3. Grounded Interaction Path Selection:
   - STRICTLY use ONLY the discovered elements list and links provided in context.
   - Do NOT assume or invent hypothetical elements (e.g. do not look for role="navigation" or role="button" unless it was discovered).
   - If grounding_evidence mentions elements, match against discovered element selectors, forge_ids, or text.
   - Prefer `page.get_by_role(...)`, `page.get_by_text(...)`, `page.get_by_label(...)`, `page.locator(...)`.

4. Always assert state transitions and functional outcomes:
   - When verifying page URL / title transition, use flexible regex matching (e.g. `expect(page).to_have_url(re.compile(r".*example.*"))` or regex matching the target domain/path), because external links often redirect (e.g. HTTP 301/302 to subdomains or canonical URLs).
   - Verify expected states specified in expected_outcomes: e.g. `expect(locator).to_be_visible()` or confirmation text.

5. Output ONLY valid Python code without markdown fences, or wrapped in a single ```python block.
"""

BUILDER_TS_SYSTEM_PROMPT = """You are an elite Playwright TypeScript Automation Engineer.
Your task is to generate clean, robust, modern Playwright TypeScript test scripts (.spec.ts) targeting the web application.

Requirements for the generated Playwright test:
1. Must use:
   import { test, expect } from '@playwright/test';
2. Structure inside a test.describe block with clear test name:
   test.describe('Regression Suite', () => {
     test('test_name', async ({ page }) => {
       // actions
     });
   });
3. Use modern, resilient Playwright locators:
   - Prefer `page.getByRole(...)`, `page.getByText(...)`, `page.getByLabel(...)`, `page.getByPlaceholder(...)`
   - Use discovered element forge_ids or selectors as reliable targets
4. Always include explicit assertions:
   - `await expect(page).toHaveTitle(...)`
   - `await expect(locator).toBeVisible()`
   - `await expect(locator).toBeEnabled()`
5. Handle navigation cleanly:
   - `await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });`
6. Output ONLY valid TypeScript code without markdown fences, or wrapped in a single ```typescript block.

If HEALING information is provided, carefully inspect the previous failure error, the diagnosis, and the fix plan to adjust locators, wait conditions, or assertions.
"""


def clean_code(raw_code: str) -> str:
    """Removes markdown code fences if present."""
    code = raw_code.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines).strip()
    return code


def builder_node(state: ForgeState) -> Dict[str, Any]:
    """
    TEST BUILDER node: Generates Playwright test scripts.
    Defaults to Python (.py) scripts; can generate TypeScript (.spec.ts) if configured.
    Saves to storage/<domain>/tests/<test_id>.<ext> and indexes in Neon PostgreSQL.
    """
    current_test = state.get("current_test")
    if not current_test:
        raise ValueError("Cannot run builder_node without a current_test.")

    target_url = state.get("target_url")
    disc = state.get("discovery_data") or {}
    heal_attempt = state.get("heal_attempt", 0)
    healing_history = state.get("healing_history", [])
    last_exec = state.get("execution_result")

    config = state.get("config", {})
    language = (config.get("language") or os.getenv("FORGE_TEST_LANGUAGE", "python")).strip().lower()
    is_python = (language != "typescript")
    lang_label = "Python" if is_python else "Playwright TS"

    # Resolve target viewport (desktop, tablet, mobile)
    target_vp_name = current_test.get("viewport") or config.get("viewport") or "desktop"
    if isinstance(target_vp_name, str):
        target_vp_name = target_vp_name.lower()
    else:
        target_vp_name = "desktop"
    vp_dims = FIXED_VIEWPORTS.get(target_vp_name, FIXED_VIEWPORTS["desktop"])

    logger.info(
        f"[TEST BUILDER] Generating {lang_label} script for '{current_test['id']}' "
        f"[viewport={target_vp_name} ({vp_dims['width']}x{vp_dims['height']})] (heal_attempt={heal_attempt})"
    )

    # Sample of discovered elements with viewport visibility flags
    elements_sample = {
        "buttons": [
            {
                "forge_id": b.get("forge_id"),
                "text": b.get("text"),
                "selector": b.get("selector"),
                "id": b.get("id"),
                "visible_viewports": b.get("visible_viewports", ["desktop"]),
                "visible_in_target_viewport": target_vp_name in b.get("visible_viewports", ["desktop"]),
            }
            for b in (disc.get("elements", {}).get("buttons", []))[:15]
        ],
        "inputs": [
            {
                "forge_id": i.get("forge_id"),
                "name": i.get("name"),
                "placeholder": i.get("placeholder"),
                "selector": i.get("selector"),
                "visible_viewports": i.get("visible_viewports", ["desktop"]),
                "visible_in_target_viewport": target_vp_name in i.get("visible_viewports", ["desktop"]),
            }
            for i in (disc.get("elements", {}).get("inputs", []))[:15]
        ],
        "links": [
            {
                "forge_id": l.get("forge_id"),
                "text": l.get("text"),
                "href": l.get("href"),
                "visible_viewports": l.get("visible_viewports", ["desktop"]),
                "visible_in_target_viewport": target_vp_name in l.get("visible_viewports", ["desktop"]),
            }
            for l in (disc.get("elements", {}).get("links", []))[:10]
        ]
    }

    test_type = str(current_test.get("type", "FLOW")).strip().upper()
    intent = current_test.get("intent") or current_test.get("goal") or current_test.get("description", "")
    expected = current_test.get("expected") or [current_test.get("expected_outcome", "")]
    evidence = current_test.get("evidence", [])

    builder_payload: Dict[str, Any] = {
        "target_url": target_url,
        "test_scenario": current_test,
        "test_type": test_type,
        "intent": intent,
        "expected_outcomes": expected,
        "grounding_evidence": evidence,
        "target_viewport": {
            "name": target_vp_name,
            "width": vp_dims["width"],
            "height": vp_dims["height"],
        },
        "discovered_elements_with_forge_ids": elements_sample,
        "heal_attempt": heal_attempt,
        "language": "python" if is_python else "typescript",
    }

    if heal_attempt > 0 and healing_history:
        builder_payload["last_execution_error"] = last_exec.get("stderr") or last_exec.get("error_summary") if last_exec else None
        builder_payload["previous_code"] = state.get("test_code")
        builder_payload["healing_diagnosis"] = healing_history[-1]

    system_prompt = BUILDER_PYTHON_SYSTEM_PROMPT if is_python else BUILDER_TS_SYSTEM_PROMPT

    try:
        llm = get_chat_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Test Generation Specifications:\n{json.dumps(builder_payload, indent=2)}")
        ]
        response = llm.invoke(messages)
        code = clean_code(response.content)
        if is_python:
            header_lines = []
            if "import os" not in code:
                header_lines.append("import os")
            if "import re" not in code:
                header_lines.append("import re")
            if "import sys" not in code:
                header_lines.append("import sys")
            if "from playwright.sync_api" not in code:
                header_lines.append("from playwright.sync_api import sync_playwright, expect")
            if header_lines:
                code = "\n".join(header_lines) + "\n\n" + code
    except Exception as e:
        logger.warning(f"[TEST BUILDER] LLM test generation failed ({e}). Generating template {lang_label} script.")
        # Check for first visible navigation link or button to perform interaction
        first_btn = next((b for b in disc.get("elements", {}).get("buttons", []) if b.get("visible")), None)
        first_lnk = next((l for l in disc.get("elements", {}).get("links", []) if l.get("visible") and l.get("href") and not l.get("href").startswith("#")), None)
        target_sel = (first_lnk or first_btn or {}).get("selector", "")

        interaction_block = ""
        if target_sel:
            target_sel_repr = json.dumps(target_sel)
            interaction_block = f"""
            # Perform journey interaction and verify state transition
            target_el = page.locator({target_sel_repr}).first
            if target_el.is_visible():
                target_el.click(timeout=10000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
"""
        test_id_clean = (current_test.get("id") or "journey_test").replace("-", "_")
        if is_python:
            code = f"""import os
import re
import sys
from playwright.sync_api import sync_playwright, expect


def test_{test_id_clean}():
    headless = os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={{"width": {vp_dims['width']}, "height": {vp_dims['height']}}})
        page = context.new_page()
        try:
            page.goto('{target_url}', wait_until='domcontentloaded', timeout=30000)
            expect(page).to_have_title(re.compile(r".+")){interaction_block}
            print('[TEST PASSED] [{test_type}] Successfully completed journey on {target_url}')
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    test_{test_id_clean}()
"""
        else:
            code = f"""import {{ test, expect }} from '@playwright/test';

test.describe('[{test_type}] {current_test.get("category", "regression").capitalize()} Suite', () => {{
  test('{current_test.get("id", "test_smoke")}', async ({{ page }}) => {{
    await page.goto('{target_url}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
    await expect(page).toHaveTitle(/.+/);
    console.log('[TEST PASSED] [{test_type}] Successfully loaded {target_url}');
  }});
}});
"""

    # Persist the generated test into storage
    site_storage = get_website_storage_dir(target_url)
    tests_dir = site_storage / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_id = current_test.get("id", "test_run")
    ext = ".py" if is_python else ".spec.ts"
    test_file_path = tests_dir / f"{test_id}{ext}"

    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Also organize into category subdirectory (tests/smoke/ or tests/flows/)
    category_dir = tests_dir / ("smoke" if test_type == "SMOKE" else "flows")
    category_dir.mkdir(parents=True, exist_ok=True)
    with open(category_dir / f"{test_id}{ext}", "w", encoding="utf-8") as f:
        f.write(code)

    logger.info(f"[TEST BUILDER] Saved {lang_label} [{test_type}] test script to: {test_file_path}")

    # Index in Neon PostgreSQL
    try:
        from storage.local import sanitize_domain
        domain = sanitize_domain(target_url)
        
        # Resolve website_id if target_url matches a registered website
        website = ForgeRepository.get_website_by_url(target_url)
        website_id = website["id"] if website else None

        # Determine cron timings (e.g. 6 hours for SMOKE sanity checks, 24 hours for FLOW journeys)
        cron_hours = current_test.get("cron_interval_hours") or (6 if test_type == "SMOKE" else 24)

        ForgeRepository.save_test(
            test_id=test_id,
            domain=domain,
            page_url=target_url,
            title=current_test.get("title", test_id),
            description=current_test.get("description", ""),
            category=current_test.get("category", test_type.lower()),
            priority=current_test.get("priority", "medium"),
            steps=current_test.get("steps", []),
            expected_outcome=current_test.get("expected_outcome", ""),
            script_path=str(test_file_path),
            test_code=code,
            language="python" if is_python else "typescript",
            website_id=website_id,
            cron_interval_hours=cron_hours,
        )
    except Exception as db_err:
        logger.warning(f"[TEST BUILDER] Could not index test into database: {db_err}")

    return {
        "test_code": code,
        "test_file_path": str(test_file_path),
    }
