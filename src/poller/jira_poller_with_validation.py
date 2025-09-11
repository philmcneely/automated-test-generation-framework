#!/usr/bin/env python3
"""
Jira Poller with Test Validation - Automated Test Generation Pipeline
This module polls Jira for tickets and automatically generates, validates,
and saves Playwright tests using the POM-based test generation agent.

Features:
    ✓ Continuous polling of Jira tickets
    ✓ Automatic test generation from ticket acceptance criteria
    ✓ Test validation against playwright-ai-framework
    ✓ Automatic saving of validated tests
    ✓ Error handling and logging
    ✓ Failed test preservation for debugging

Environment Variables:
    JIRA_BASE: Jira instance URL
    JIRA_USER: Jira username
    JIRA_TOKEN: Jira API token
    JIRA_JQL: JQL query for ticket filtering
    POLL_INTERVAL: Polling interval in seconds

Dependencies:
    - requests: HTTP client for Jira API
    - subprocess: Process execution for test generation
    - tempfile: Temporary file management
    - json: JSON data processing

Author: PMAC
Date: 2025-09-11
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List

import requests

JIRA_BASE = os.getenv("JIRA_BASE")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
JQL = os.getenv("JIRA_JQL", 'project = ABC AND status in ("To Do", "In Progress")')
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
headers = {"Accept": "application/json"}


def fetch_tickets() -> List[Dict[str, Any]]:
    if not JIRA_BASE or not JIRA_USER or not JIRA_TOKEN:
        raise RuntimeError("Missing Jira configuration env vars")
    url = f"{JIRA_BASE}/rest/api/3/search"
    r = requests.get(
        url,
        headers=headers,
        params={"jql": JQL, "maxResults": "50"},
        auth=(JIRA_USER, JIRA_TOKEN),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("issues", [])  # type: ignore


def validate_and_save_test(test_content: str, ticket_id: str) -> bool:
    """Validate generated test and save if it passes"""

    # Create temporary file for validation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(test_content)
        temp_test_path = temp_file.name

    try:
        # Validate the generated test
        print(f"🔍 Validating generated test for ticket {ticket_id}")

        validation_result = subprocess.run(
            [
                sys.executable,
                "src/validator/test_validator.py",
                "--test",
                temp_test_path,
                "--framework-path",
                "playwright-ai-framework",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )

        if validation_result.returncode == 0:
            print(f"✅ Test validation PASSED for ticket {ticket_id}")

            # Save validated test to playwright-ai-framework
            test_filename = (
                f"playwright-ai-framework/tests/generated/"
                f"test_generated_"
                f"{ticket_id.lower().replace('-', '_')}.py"
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(test_filename), exist_ok=True)

            with open(test_filename, "w") as f:
                f.write(test_content)

            print(f"💾 Saved validated POM test to {test_filename}")
            return True

        else:
            print(f"❌ Test validation FAILED for ticket {ticket_id}")
            print(f"📋 Validation error: {validation_result.stderr}")
            print(f"📝 Validation output: {validation_result.stdout}")

            # Optionally save failed test for debugging
            failed_test_filename = (
                f"failed_tests/"
                f"test_generated_"
                f"{ticket_id.lower().replace('-', '_')}_failed.py"
            )
            os.makedirs(os.path.dirname(failed_test_filename), exist_ok=True)
            with open(failed_test_filename, "w") as f:
                f.write(test_content)
            print(f"🗂️  Saved failed test for analysis: {failed_test_filename}")
            return False

    finally:
        # Clean up temporary file
        if os.path.exists(temp_test_path):
            os.unlink(temp_test_path)


def process_ticket(ticket: Dict[str, Any]) -> None:
    """Process a single ticket through the agent pipeline with validation"""

    # Extract relevant ticket information
    ticket_data = {
        "id": ticket.get("key", "unknown"),
        "title": ticket.get("fields", {}).get("summary", "generated_test"),
        "acceptance_criteria": [],
    }

    # Parse acceptance criteria from description or custom fields
    description = ticket.get("fields", {}).get("description", "")
    if description:
        # Simple parsing - look for bullet points or numbered lists
        lines = description.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("1."):
                # Simple heuristic for acceptance criteria
                ticket_data["acceptance_criteria"].append(
                    {
                        "action": "click",  # Default action
                        "target": "unknown",
                        "value": line.strip("-* 1234567890."),
                    }
                )

    # If no acceptance criteria found, create a basic test
    if not ticket_data["acceptance_criteria"]:
        ticket_data["acceptance_criteria"] = [
            {"action": "goto", "target": "/"},
            {"action": "assert_text", "value": "Welcome"},
        ]

    # Create temporary files for processing
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as ticket_file:
        json.dump(ticket_data, ticket_file)
        ticket_path = ticket_file.name

    try:
        # Run POM agent to generate test compatible with existing framework
        result = subprocess.run(
            [
                "python",
                "src/agent/agent_runner_pom.py",
                "--ticket",
                ticket_path,
                "--kb",
                "knowledge_base_schema.json",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )

        if result.returncode == 0:
            print(f"Generated POM test for ticket {ticket_data['id']}")

            # Extract test content
            test_content = result.stdout.replace(
                "# ===== Generated POM-based Playwright Test =====\n", ""
            )

            # Validate and save the test
            success = validate_and_save_test(test_content, ticket_data["id"])

            if success:
                print(
                    f"🎉 Successfully generated and validated test for ticket {ticket_data['id']}"
                )
            else:
                print(
                    f"⚠️  Generated test for ticket {ticket_data['id']} but validation failed"
                )

        else:
            print(
                f"Error generating POM test for ticket "
                f"{ticket_data['id']}: {result.stderr}"
            )

    finally:
        # Clean up temporary file
        os.unlink(ticket_path)


def main() -> None:
    while True:
        try:
            issues = fetch_tickets()
            print(f"Fetched {len(issues)} issues")

            for issue in issues:
                print(f"Processing ticket {issue.get('key', 'unknown')}")
                process_ticket(issue)

        except Exception as e:
            print(f"Error in main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
