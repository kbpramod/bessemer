import json
import logging
from typing import Any, Dict, List
from agents.llm import get_chat_model
from agents.state import VerificationState
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("forge.verification.evaluator")

VERIFIER_EVALUATOR_SYSTEM_PROMPT = """You are a Principal Site Reliability Engineer (SRE) and Quality Arbiter.
A user journey test triggered a SUSPECTED_APP_FAILURE.
Your SOLE RESPONSIBILITY is to answer:
"Is this genuinely an application bug, based on both original failure evidence AND fresh browser execution evidence?"

YOU DO NOT DECIDE HEALING. You only judge ground truth reality:
- "CONFIRMED_APP_BUG": Genuine application defect or outage confirmed.
  Criteria:
  - Fresh smoke verification failed (e.g., HTTP 5xx, application crash, blank error page).
  - Server returned persistent internal errors during interaction.
  - Uncaught frontend runtime errors in application code prevent user capability.
- "NOT_CONFIRMED": The application is alive and functioning correctly against the current DOM.
  Criteria:
  - Fresh smoke verification passed cleanly.
  - Application accepted the interaction or rendered the page without critical error.
  - The original failure was a false alarm resulting from locator drift, timing, or automation divergence.

Strict Output Format (JSON ONLY):
{
  "verdict": "CONFIRMED_APP_BUG" | "NOT_CONFIRMED",
  "confidence": 0.0 to 1.0,
  "reason": "Detailed explanation justifying the verdict based on evidence",
  "evidence": [
    "Specific observation 1",
    "Specific observation 2"
  ]
}
Output ONLY valid JSON.
"""


def verifier_llm_node(state: VerificationState) -> Dict[str, Any]:
    """
    VERIFIER LLM node:
    Arbitrates between CONFIRMED_APP_BUG and NOT_CONFIRMED by weighing:
    1. Original failure evidence (FailureContext)
    2. Fresh live DOM discovery (DiscoveryData)
    3. Fresh browser execution outcome (SmokeResult)
    """
    failed_test_id = state.get("failed_test_id", "unknown_test")
    failure_ctx = state.get("failure_context") or {}
    smoke_res = state.get("smoke_result") or {}
    disc = state.get("discovery_data") or {}

    logger.info(f"[VERIFICATION - EVALUATOR] Evaluating evidence for '{failed_test_id}'...")

    eval_payload = {
        "failed_test_id": failed_test_id,
        "target_url": state.get("target_url"),
        "original_failure_context": {
            "failed_step": failure_ctx.get("failed_step"),
            "expected": failure_ctx.get("expected"),
            "actual": failure_ctx.get("actual"),
            "error": failure_ctx.get("error"),
            "console_errors": failure_ctx.get("console_errors", []),
            "network_errors": failure_ctx.get("network_errors", []),
        },
        "fresh_browser_execution_evidence": {
            "smoke_test_passed": smoke_res.get("passed", False),
            "smoke_test_exit_code": smoke_res.get("exit_code"),
            "smoke_test_stdout": (smoke_res.get("stdout") or "")[-1000:],
            "smoke_test_stderr": (smoke_res.get("stderr") or "")[-1500:],
        },
        "fresh_dom_discovery": {
            "page_title": disc.get("page", {}).get("title"),
            "current_url": disc.get("page", {}).get("url"),
        },
    }

    verdict = "NOT_CONFIRMED"
    confidence = 0.85
    reason = "Verification assessment completed."
    evidence: List[str] = []

    try:
        llm = get_chat_model()
        messages = [
            SystemMessage(content=VERIFIER_EVALUATOR_SYSTEM_PROMPT),
            HumanMessage(content=f"Telemetry & Evidence:\n{json.dumps(eval_payload, indent=2)}"),
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

        parsed = json.loads(content)
        raw_verdict = str(parsed.get("verdict", "")).strip().upper()
        if "CONFIRMED" in raw_verdict and "NOT" not in raw_verdict:
            verdict = "CONFIRMED_APP_BUG"
        else:
            verdict = "NOT_CONFIRMED"

        confidence = float(parsed.get("confidence", 0.90))
        reason = parsed.get("reason", "Evaluation concluded.")
        evidence = list(parsed.get("evidence", []))
    except Exception as err:
        logger.warning(f"[VERIFICATION - EVALUATOR] LLM evaluation failed ({err}). Using deterministic evidence heuristic.")
        smoke_passed = smoke_res.get("passed", False)
        stderr_text = smoke_res.get("stderr", "")
        if not smoke_passed or "500" in stderr_text or "Internal Server Error" in stderr_text:
            verdict = "CONFIRMED_APP_BUG"
            confidence = 0.92
            reason = f"Fresh smoke verification failed with exit code {smoke_res.get('exit_code')}. Application is malfunctioning."
            evidence = [
                f"Smoke verification exit code: {smoke_res.get('exit_code')}",
                f"Error snippet: {stderr_text[:200] or 'Process execution failure'}",
            ]
        else:
            verdict = "NOT_CONFIRMED"
            confidence = 0.88
            reason = "Fresh browser execution succeeded against live DOM. Original failure was an automation locator divergence."
            evidence = [
                "Smoke test executed and passed cleanly",
                "Target page is responsive with HTTP 200",
            ]

    logger.info(
        f"[VERIFICATION - EVALUATOR] Verdict: [{verdict}] (Confidence: {confidence:.2f}) — {reason}"
    )

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
    }
