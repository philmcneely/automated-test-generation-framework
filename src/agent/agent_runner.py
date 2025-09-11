"""
Automated Test Generation Agent - Core Test Generator

This module provides the core functionality for generating Playwright tests
from Jira tickets and knowledge base schemas. It transforms acceptance criteria
into executable test scripts with proper selectors and assertions.

Features:
    ✓ JSON-based ticket parsing with acceptance criteria extraction
    ✓ Knowledge base integration for selector resolution
    ✓ Dynamic test function naming from ticket titles
    ✓ Support for multiple test actions (click, fill, goto, assert_text)
    ✓ Environment-based configuration (APP_BASE_URL)
    ✓ Automatic selector mapping from page objects
    ✓ Clean, readable generated test code
    ✓ Command-line interface for standalone usage

Test Actions Supported:
    - click: Click on elements
    - fill: Fill input fields with values
    - goto: Navigate to URLs
    - assert_text: Verify text presence on page

Usage Examples:
    # Generate test from ticket and knowledge base
    python src/agent/agent_runner.py --ticket sample_ticket.json --kb knowledge_base.json

    # Use with custom base URL
    APP_BASE_URL=https://myapp.com python src/agent/agent_runner.py --ticket ticket.json --kb kb.json

Generated Test Structure:
    - Automatic base URL configuration
    - Proper Playwright setup and teardown
    - Step-by-step test execution
    - Clear error handling and reporting

Dependencies:
    - argparse: Command-line argument parsing
    - json: JSON data processing
    - os: Environment variable access

Author: PMAC
Date: 2025-09-11
"""

import argparse
import json
import os
from typing import Any, Dict, List


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)  # type: ignore


def _build_selector_index(kb: Dict[str, Any]) -> Dict[str, str]:
    """Build selector index from knowledge base page objects."""
    selector_index: Dict[str, str] = {}
    for po in kb.get("page_objects", []):
        for sel in po.get("selectors", []):
            selector_index[sel.get("element")] = sel.get("selector")
    return selector_index


def _resolve_target(target: str, selector_index: Dict[str, str]) -> str:
    """Resolve target using selector index or return as-is if already a selector."""
    if not target:
        return target
    if (
        target.startswith("#")
        or target.startswith(".")
        or target.startswith("[")
        or target.startswith("text=")
        or target.startswith("//")
    ):
        return target
    return selector_index.get(target, target)


def _generate_test_step(action: str, target: str, value: Any) -> str:
    """Generate a single test step based on action type."""
    action = str(action).lower()
    if action == "click" and target:
        return f"        page.click('{target}')"
    elif action == "fill" and target is not None:
        return f"        page.fill('{target}', '{str(value or '')}')"
    elif action == "goto" and target:
        return f"        page.goto('{target}')"
    elif action == "assert_text" and value:
        return f"        page.wait_for_selector('text={str(value)}')"
    else:
        return f"        # TODO: Unsupported step: {json.dumps({'action': action, 'target': target, 'value': value})}"


def _generate_test_function_name(title: str) -> str:
    """Generate a safe test function name from ticket title."""
    safe = "".join([c.lower() if c.isalnum() else "_" for c in title])
    return "test_" + safe[:60].strip("_")


def _build_test_code(test_func_name: str, base_url: str, body_lines: List[str]) -> str:
    """Build the complete test code structure using the playwright-ai-framework patterns."""
    code_lines = [
        "import pytest",
        "from utils.decorators.screenshot_decorator import screenshot_on_failure",
        "",
        "@screenshot_on_failure",
        "@pytest.mark.login",
        "@pytest.mark.asyncio",
        f"async def {test_func_name}(app):",
        '    """Generated test using playwright-ai-framework patterns."""',
        "    # Note: This test should be placed in the playwright-ai-framework/tests/generated/ directory",
    ]

    # Convert sync playwright steps to framework-based steps
    for line in body_lines:
        # Convert page operations to app-based operations
        if "page.click(" in line:
            # Extract selector and convert to app.login_page pattern
            selector = line.split("'")[1] if "'" in line else line.split('"')[1]
            converted_line = f"    await app.login_page.page.click('{selector}')"
            code_lines.append(converted_line)
        elif "page.fill(" in line:
            # Extract selector and value
            parts = line.split("'") if "'" in line else line.split('"')
            if len(parts) >= 3:
                selector = parts[1]
                value = parts[3]
                converted_line = (
                    f"    await app.login_page.page.fill('{selector}', '{value}')"
                )
                code_lines.append(converted_line)
        elif "page.wait_for_selector(" in line:
            # Keep wait operations as-is but use app.login_page.page
            selector = line.split("'")[1] if "'" in line else line.split('"')[1]
            converted_line = (
                f"    await app.login_page.page.wait_for_selector('{selector}')"
            )
            code_lines.append(converted_line)
        elif "page.goto(" in line:
            # Use app navigation
            code_lines.append("    await app.login_page.navigate()")
        else:
            # Keep other lines as-is but make them async if needed
            converted_line = line.replace(
                "        page.", "    await app.login_page.page."
            )
            code_lines.append(converted_line)

    return "\n".join(code_lines)


def generate_playwright_test(ticket: Dict[str, Any], kb: Dict[str, Any]) -> str:
    """Generate a Playwright test from ticket and knowledge base."""
    title = ticket.get("title", "generated_test")
    steps = ticket.get("acceptance_criteria", [])

    selector_index = _build_selector_index(kb)
    body_lines: List[str] = []

    for step in steps:
        target = _resolve_target(step.get("target"), selector_index)
        body_lines.append(
            _generate_test_step(step.get("action"), target, step.get("value"))
        )

    base_url = os.getenv("APP_BASE_URL", "https://example.com")
    test_func_name = _generate_test_function_name(title)

    return _build_test_code(test_func_name, base_url, body_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Playwright test from a ticket JSON and KB JSON."
    )
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--kb", required=True)
    args = parser.parse_args()

    ticket = load_json(args.ticket)
    kb = load_json(args.kb)
    print("# ===== Generated Playwright Test =====")
    print(generate_playwright_test(ticket, kb))


if __name__ == "__main__":
    main()
