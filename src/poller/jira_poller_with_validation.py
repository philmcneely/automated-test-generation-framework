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
import subprocess  # nosec B404 # Safe usage: controlled execution of agent/validator scripts
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

import requests

# Support direct-script launch (python src/poller/jira_poller_with_validation.py),
# where only src/poller is on sys.path and the repository root is not.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.poller.llm_parser import build_parser_prompt, parse_llm_response


# Parser vocabulary -> TemplateTestGenerator vocabulary.
LLM_ACTION_MAP = {"navigate": "goto", "wait": "wait_for_selector"}


class JiraPollerWithValidation:
    """
    Jira Poller with integrated test validation and automated test generation.

    This class provides automated polling of Jira tickets and generates validated
    Playwright tests using the POM-based test generation framework.
    """

    def __init__(
        self,
        jira_base: Optional[str] = None,
        jira_user: Optional[str] = None,
        jira_token: Optional[str] = None,
        jira_jql: Optional[str] = None,
        poll_interval: int = 60,
    ) -> None:
        """
        Initialize the Jira poller with configuration.

        Args:
            jira_base: Jira instance URL (defaults to JIRA_BASE env var)
            jira_user: Jira username (defaults to JIRA_USER env var)
            jira_token: Jira API token (defaults to JIRA_TOKEN env var)
            jira_jql: JQL query for filtering (defaults to JIRA_JQL env var)
            poll_interval: Polling interval in seconds (default: 60)
        """
        self.jira_base = jira_base or os.getenv("JIRA_BASE")
        self.jira_user = jira_user or os.getenv("JIRA_USER")
        self.jira_token = jira_token or os.getenv("JIRA_TOKEN")
        self.jira_jql = jira_jql or os.getenv(
            "JIRA_JQL", 'project = ABC AND status in ("To Do", "In Progress")'
        )
        self.poll_interval = poll_interval

        if not all([self.jira_base, self.jira_user, self.jira_token]):
            raise ValueError(
                "Missing required Jira configuration. Please provide jira_base, jira_user, "
                "and jira_token via parameters or environment variables (JIRA_BASE, JIRA_USER, JIRA_TOKEN)"
            )

        self.headers = {"Accept": "application/json"}

    def fetch_tickets(self) -> List[Dict[str, Any]]:
        """Fetch tickets from Jira using configured JQL query."""
        url = f"{self.jira_base}/rest/api/3/search"

        # Prepare auth - only use if both user and token are provided
        auth = None
        if self.jira_user and self.jira_token:
            auth = (self.jira_user, self.jira_token)

        response = requests.get(
            url,
            headers=self.headers,
            params={"jql": self.jira_jql, "maxResults": "50"},
            auth=auth,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("issues", [])  # type: ignore

    def validate_and_save_test(self, test_content: str, ticket_id: str) -> bool:
        """Validate generated test and save if it passes"""

        # Create temporary file for validation
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(test_content)
            temp_test_path = temp_file.name

        try:
            # Validate the generated test
            print(f"🔍 Validating generated test for ticket {ticket_id}")

            validation_result = subprocess.run(  # nosec B603 # Safe: controlled execution of internal validator
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

    def parse_with_llm(self, ticket: Dict[str, Any]) -> Optional["TestRequirement"]:
        """Parse a Jira ticket into structured test requirements using LLM.

        Builds a parser prompt from the ticket fields, invokes the LLM generator,
        and validates the response with Pydantic.

        Args:
            ticket: Raw Jira ticket dict from the API.

        Returns:
            Validated TestRequirement or None if parsing fails.
        """
        ticket_id = ticket.get("key", "unknown")
        fields = ticket.get("fields", {})
        title = fields.get("summary", "")
        description = fields.get("description", "")

        if not description:
            return None

        prompt = build_parser_prompt(ticket_id, title, description)

        try:
            # Call the existing LLM generator to get a response
            result = subprocess.run(  # nosec B603 # Safe: controlled execution of internal script
                [
                    sys.executable,
                    "src/agent/llm_generator.py",
                    "--prompt",
                    prompt,
                ],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=120,
            )

            if result.returncode == 0 and result.stdout.strip():
                return parse_llm_response(result.stdout, ticket_id, title, description)
            else:
                print(f"LLM generator failed for {ticket_id}: {result.stderr}")
                return None

        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"LLM parsing failed for {ticket_id}: {e}")
            return None

    def process_ticket(self, ticket: Dict[str, Any]) -> None:
        """Process a single ticket through the agent pipeline with validation"""

        # Extract relevant ticket information
        ticket_data = {
            "id": ticket.get("key", "unknown"),
            "title": ticket.get("fields", {}).get("summary", "generated_test"),
            "acceptance_criteria": [],
        }

        # Try LLM-based structured parsing first
        requirement = self.parse_with_llm(ticket)
        if requirement and not requirement.needs_human_review:
            # One entry per scenario so each becomes its own test function
            # (fresh browser context) with its own preconditions and assertions.
            ticket_data["scenarios"] = [
                {
                    "name": scenario.name,
                    "type": scenario.type,
                    "preconditions": scenario.preconditions,
                    "expected_result": scenario.expected_result,
                    "steps": [
                        {
                            "action": LLM_ACTION_MAP.get(step.action, step.action),
                            "target": step.target,
                            "value": step.value or "",
                            "assertion": step.assertion or "",
                        }
                        for step in scenario.steps
                    ],
                }
                for scenario in requirement.scenarios
            ]
            ticket_data["test_requirement"] = requirement.model_dump()
        else:
            # Fallback to naive parsing
            description = ticket.get("fields", {}).get("description", "")
            if description:
                # Simple parsing - look for bullet points or numbered lists
                lines = description.split("\n")
                for line in lines:
                    line = line.strip()
                    if (
                        line.startswith("-")
                        or line.startswith("*")
                        or line.startswith("1.")
                    ):
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
            result = subprocess.run(  # nosec B607 B603 # Safe: controlled execution of internal script
                [
                    "python",
                    "src/agent/template_generator.py",
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
                success = self.validate_and_save_test(test_content, ticket_data["id"])

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

    def run(self) -> None:
        """Run the continuous polling loop."""
        while True:
            try:
                issues = self.fetch_tickets()
                print(f"Fetched {len(issues)} issues")

                for issue in issues:
                    print(f"Processing ticket {issue.get('key', 'unknown')}")
                    self.process_ticket(issue)

            except Exception as e:
                print(f"Error in main loop: {e}")

            time.sleep(self.poll_interval)


def main() -> None:
    """Main entry point for command-line usage."""
    poller = JiraPollerWithValidation()
    poller.run()


if __name__ == "__main__":
    main()
