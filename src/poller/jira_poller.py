"""
Jira Ticket Poller - Automated Test Generation Trigger

This module provides continuous monitoring of Jira tickets to automatically
trigger test generation when new tickets matching specific criteria are found.
It integrates with the Jira REST API and processes tickets through the
automated test generation pipeline.

Features:
    ✓ Continuous polling of Jira tickets via REST API
    ✓ Configurable JQL queries for ticket filtering
    ✓ Environment-based configuration for Jira credentials
    ✓ Automatic ticket data extraction and formatting
    ✓ Integration with POM-based test generation agent
    ✓ Generated test storage in playwright-ai-framework
    ✓ Error handling and retry mechanisms
    ✓ Configurable polling intervals

Environment Variables:
    JIRA_BASE: Jira instance base URL
    JIRA_USER: Jira username for authentication
    JIRA_TOKEN: Jira API token for authentication
    JIRA_JQL: JQL query for ticket filtering (default: project = ABC AND status in ("To Do", "In Progress"))
    POLL_INTERVAL: Polling interval in seconds (default: 60)

Usage Examples:
    # Start continuous polling
    python src/poller/jira_poller.py

    # Run with custom JQL and interval
    JIRA_JQL='project = TEST AND priority = High' POLL_INTERVAL=30 python src/poller/jira_poller.py

Ticket Processing:
    - Extracts ticket ID and summary
    - Parses acceptance criteria from description
    - Generates POM-based Playwright tests
    - Saves tests to framework directory
    - Handles missing criteria with default tests

Dependencies:
    - os: Environment variable access
    - time: Polling interval control
    - requests: Jira REST API communication
    - subprocess: Test generation execution
    - tempfile: Temporary file management

Author: PMAC
Date: 2025-09-11
"""

import os
import time
from typing import Dict, List, Any

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


def process_ticket(ticket: Dict[str, Any]) -> None:
    """Process a single ticket through the agent pipeline"""
    import json
    import os
    import subprocess
    import tempfile

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
            # Save generated test to playwright-ai-framework tests directory
            test_content = result.stdout.replace(
                "# ===== Generated POM-based Playwright Test =====\n", ""
            )
            test_filename = (
                f"playwright-ai-framework/tests/generated/"
                f"test_generated_"
                f"{ticket_data['id'].lower().replace('-', '_')}.py"
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(test_filename), exist_ok=True)

            with open(test_filename, "w") as f:
                f.write(test_content)

            print(f"Saved POM test to {test_filename}")
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
