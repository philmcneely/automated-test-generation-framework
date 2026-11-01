"""LLM-based Jira ticket parser -- extracts structured test requirements."""
import json
import os
import re
from typing import Optional

from src.models.test_requirement import TestRequirement

PARSER_PROMPT = '''You are a QA engineer extracting test scenarios from a Jira ticket.

Given the ticket below, extract ALL test scenarios as structured JSON.

## Ticket
**ID:** {ticket_id}
**Title:** {title}
**Description:**
{description}

## Instructions
For each scenario, provide:
- name: short descriptive name
- type: happy_path, negative, boundary, or security
- preconditions: what must be true before test
- steps: ordered list of {{action, target, value, assertion}}
  - action must be one of: click, fill, navigate, assert_text, assert_visible, wait
  - every scenario must include at least one assert_text or assert_visible step that checks its expected_result
  - target should be a CSS selector if identifiable, otherwise a description
  - value is the input data (for fill/select) or expected text (for assert)
- expected_result: what should be true after test
- test_data: list of {{field, type, constraints}} for required inputs
- edge_cases: negative/boundary scenarios identified

Rate your confidence (0.0-1.0) for:
- overall: general parsing quality
- steps: how confident you are in the step extraction
- selectors: how confident you are in element identification
- test_data: how confident you are in data requirements

Respond with ONLY valid JSON matching this schema:
{{
  "ticket_id": "{ticket_id}",
  "title": "{title}",
  "scenarios": [...],
  "edge_cases": [...],
  "confidence": {{"overall": 0.0, "steps": 0.0, "selectors": 0.0, "test_data": 0.0}},
  "raw_description": ""
}}'''


def build_parser_prompt(ticket_id: str, title: str, description: str) -> str:
    """Build the LLM prompt for parsing a Jira ticket into structured test requirements."""
    return PARSER_PROMPT.format(
        ticket_id=ticket_id,
        title=title,
        description=description,
    )


def parse_llm_response(response_text: str, ticket_id: str, title: str, description: str) -> Optional[TestRequirement]:
    """Parse LLM response into validated TestRequirement model."""
    # Try to extract JSON from response
    # Strategy 1: look for JSON code block
    match = re.search(r'```(?:json)?\s*({.*?})\s*```', response_text, re.DOTALL)
    if match:
        candidate = match.group(1)
    else:
        # Strategy 2: find outermost braces
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1:
            candidate = response_text[start:end + 1]
        else:
            return None

    try:
        data = json.loads(candidate)
        data["raw_description"] = description
        data["ticket_id"] = ticket_id
        data["title"] = title

        # Validate with Pydantic
        requirement = TestRequirement(**data)

        # Flag for human review if confidence too low
        threshold = float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.7"))
        if requirement.confidence.overall < threshold:
            requirement.needs_human_review = True

        return requirement
    except (json.JSONDecodeError, Exception) as e:
        print(f"Failed to parse LLM response for {ticket_id}: {e}")
        return None
