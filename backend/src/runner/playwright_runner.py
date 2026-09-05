import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import is_headless, DEFAULT_TEST_TIMEOUT_S


def run_playwright_ts_test(
    test_file_path: str,
    timeout_s: int = DEFAULT_TEST_TIMEOUT_S,
    headed: Optional[bool] = None,
    cwd: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Executes a Playwright TypeScript (.spec.ts) or JavaScript (.spec.js) test
    using npx playwright test.
    Honors headed/headless mode and captures stdout, stderr, exit code, and screenshots.
    """
    test_path = Path(test_file_path).resolve()
    if not test_path.exists():
        return {
            "exit_code": 1,
            "passed": False,
            "stdout": "",
            "stderr": f"Test script file not found: {test_path}",
            "duration_s": 0.0,
            "error_summary": "Test file not found",
            "trace_path": None,
            "screenshot_paths": [],
        }

    working_dir = cwd or str(test_path.parent)
    if headed is None and env_vars and "HEADLESS" in env_vars:
        headed = env_vars["HEADLESS"].lower() not in ("true", "1", "yes")

    run_headless = is_headless(override=None if headed is None else not headed)

    # Construct the npx playwright command
    # Windows uses cmd.exe /c npx or npx.cmd
    cmd = ["npx", "playwright", "test", str(test_path)]
    if not run_headless:
        cmd.append("--headed")

    run_env = os.environ.copy()
    run_env["CI"] = "1" if run_headless else ""
    if env_vars:
        run_env.update(env_vars)

    start_time = time.time()
    try:
        # Use shell=True on Windows for npx resolution
        process = subprocess.run(
            cmd,
            cwd=working_dir,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            shell=True if sys.platform == "win32" else False,
        )
        duration = time.time() - start_time
        exit_code = process.returncode
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        passed = (exit_code == 0)

        # Parse error summary from output
        error_summary = None
        if not passed:
            lines = [l.strip() for l in (stderr or stdout).splitlines() if l.strip()]
            error_lines = [
                l for l in lines
                if any(k in l.lower() for k in ("error:", "expect(", "failed", "timeout", "timed out"))
            ]
            error_summary = error_lines[-1] if error_lines else (lines[-1] if lines else "Test failed")

        # Discover any screenshots produced in the test folder
        screenshots: List[str] = []
        for img in Path(working_dir).glob("**/*.png"):
            screenshots.append(str(img))

        # Discover any traces
        traces = list(Path(working_dir).glob("**/*.zip"))
        trace_path = str(traces[0]) if traces else None

        return {
            "exit_code": exit_code,
            "passed": passed,
            "stdout": stdout,
            "stderr": stderr,
            "duration_s": round(duration, 2),
            "error_summary": error_summary,
            "trace_path": trace_path,
            "screenshot_paths": screenshots,
        }

    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return {
            "exit_code": 124,
            "passed": False,
            "stdout": e.stdout or "",
            "stderr": f"Test timed out after {timeout_s} seconds.",
            "duration_s": round(duration, 2),
            "error_summary": f"Execution timed out ({timeout_s}s)",
            "trace_path": None,
            "screenshot_paths": [],
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "exit_code": 1,
            "passed": False,
            "stdout": "",
            "stderr": str(e),
            "duration_s": round(duration, 2),
            "error_summary": str(e),
            "trace_path": None,
            "screenshot_paths": [],
        }


def run_test_script(
    test_file_path: str,
    timeout_s: int = DEFAULT_TEST_TIMEOUT_S,
    env_vars: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    headed: Optional[bool] = None,
) -> Dict[str, Any]:
    """Unified entry point dispatching to Playwright TS runner or Python runner."""
    if test_file_path.endswith(".ts") or test_file_path.endswith(".js"):
        return run_playwright_ts_test(
            test_file_path,
            timeout_s=timeout_s,
            headed=headed,
            cwd=cwd,
            env_vars=env_vars,
        )

    # Fallback to python script execution if file is .py
    from runner.python_runner import run_python_test_script
    return run_python_test_script(
        test_file_path,
        timeout_s=timeout_s,
        cwd=cwd,
        env_vars=env_vars,
        headed=headed,
    )
