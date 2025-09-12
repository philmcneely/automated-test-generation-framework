"""
Template-Based Test Generator

This module provides template-based test generation using Page Object Model patterns.
It generates Playwright tests by mapping Jira ticket acceptance criteria to predefined
templates and selectors from the knowledge base.

Features:
    ✓ Template-based test generation (fast, reliable, no API costs)
    ✓ Page Object Model pattern support
    ✓ Selector mapping from knowledge base
    ✓ Multiple action support (click, fill, goto, assert_text, wait_for_selector)
    ✓ Intelligent element name generation
    ✓ Advanced Playwright+Pytest code generation
    ✓ Proper error handling and validation
    ✓ Support for complex test flows and scenarios

Template Approach:
    - Uses predefined code templates with placeholder substitution
    - Maps acceptance criteria to known UI elements in knowledge base
    - Generates deterministic, consistent test code
    - No external API dependencies or costs
    - Ideal for well-defined, stable test scenarios

Usage Examples:
    # Generate test from ticket and knowledge base
    python src/agent/template_generator.py --ticket ticket.json --kb knowledge_base.json

    # Generate with specific output file
    python src/agent/template_generator.py --ticket ticket.json --kb kb.json --output test_login.py

    # Use in code
    from src.agent.template_generator import TemplateTestGenerator
    generator = TemplateTestGenerator()
    test_code = generator.generate_test(ticket_data, kb_data)

Dependencies:
    - json: JSON processing for ticket and knowledge base data
    - pathlib: File path operations
    - argparse: Command-line interface
    - typing: Type annotations for better code quality

Author: PMAC
Date: 2025-09-11
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TemplateTestGenerator:
    """
    Template-based test generator using Page Object Model patterns.

    This class generates Playwright tests by mapping ticket acceptance criteria
    to predefined templates and selectors from the knowledge base. It provides
    fast, reliable test generation without external API dependencies.
    """

    def __init__(self, template_version: str = "v1.0"):
        """Initialize the template test generator."""
        self.template_version = template_version
        self.supported_actions = {
            "click",
            "fill",
            "goto",
            "assert_text",
            "wait_for_selector",
            "assert_visible",
            "assert_not_visible",
            "assert_enabled",
            "assert_disabled",
        }

    def load_json(self, file_path: str) -> Any:
        """Load and parse JSON file."""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")

    def to_snake_case(self, text: str) -> str:
        """Convert text to snake_case for function names."""
        # Handle CamelCase: insert underscores before uppercase letters that follow lowercase
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
        # Handle consecutive uppercase letters followed by lowercase (e.g., HTMLParser -> HTML_Parser)
        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
        # Replace spaces, hyphens, and other special chars with underscores
        text = re.sub(r"[^\w\s]", "_", text)
        # Replace spaces with underscores
        text = re.sub(r"\s+", "_", text)
        # Convert to lowercase and remove multiple underscores
        text = re.sub(r"_+", "_", text.lower())
        # Remove leading/trailing underscores
        return text.strip("_")

    def resolve_selector(self, element: str, kb: Dict[str, Any]) -> Optional[str]:
        """
        Resolve element name to actual selector using knowledge base.

        Args:
            element: Element name (e.g., "login_button", "username_field")
            kb: Knowledge base containing page objects and selectors

        Returns:
            CSS selector string or None if not found
        """
        page_objects = kb.get("page_objects", [])

        for page_obj in page_objects:
            selectors = page_obj.get("selectors", [])
            for selector_info in selectors:
                if selector_info.get("element") == element:
                    selector = selector_info.get("selector")
                    return str(selector) if selector is not None else None

        # If no exact match, try fuzzy matching
        element_lower = element.lower()
        for page_obj in page_objects:
            selectors = page_obj.get("selectors", [])
            for selector_info in selectors:
                selector_element = selector_info.get("element", "").lower()
                if (
                    element_lower in selector_element
                    or selector_element in element_lower
                ):
                    selector = selector_info.get("selector")
                    return str(selector) if selector is not None else None

        return None

    def generate_selector_mapping(self, kb: Dict[str, Any]) -> Dict[str, str]:
        """Generate a mapping of element names to selectors."""
        mapping = {}
        page_objects = kb.get("page_objects", [])

        for page_obj in page_objects:
            selectors = page_obj.get("selectors", [])
            for selector_info in selectors:
                element = selector_info.get("element")
                selector = selector_info.get("selector")
                if element and selector:
                    mapping[element] = selector

        return mapping

    def generate_test_step(
        self, step: Dict[str, Any], selector_mapping: Dict[str, str], kb: Dict[str, Any]
    ) -> str:
        """Generate a single test step from acceptance criteria."""
        action = step.get("action", "").lower()
        target = step.get("target", "")
        value = step.get("value", "")

        if action not in self.supported_actions:
            logger.warning(f"Unsupported action: {action}")
            return f"    # TODO: Implement {action} action for {target}"

        # Try to find POM mapping for this target
        pom_call = self._generate_pom_call(action, target, value, kb)
        if pom_call:
            return f"    {pom_call}"

        # Fallback to direct Playwright calls
        selector = self.resolve_selector(
            target,
            {
                "page_objects": [
                    {
                        "selectors": [
                            {"element": k, "selector": v}
                            for k, v in selector_mapping.items()
                        ]
                    }
                ]
            },
        )
        if not selector:
            # Use target as-is if no mapping found
            selector = target

        # Generate step based on action
        if action == "click":
            return f"    await page.click('{selector}')"
        elif action == "fill":
            return f"    await page.fill('{selector}', '{value}')"
        elif action == "goto":
            url = value or target
            return f"    await page.goto('{url}')"
        elif action == "assert_text":
            return f"    await expect(page.locator('text={value}')).to_be_visible()"
        elif action == "wait_for_selector":
            return f"    await page.wait_for_selector('{selector}')"
        elif action == "assert_visible":
            return f"    await expect(page.locator('{selector}')).to_be_visible()"
        elif action == "assert_not_visible":
            return f"    await expect(page.locator('{selector}')).not_to_be_visible()"
        else:
            return f"    # TODO: Unsupported step: {action} {target}"

    def _generate_pom_call(
        self, action: str, target: str, value: str, kb: Dict[str, Any]
    ) -> Optional[str]:
        """Generate POM-style call if target maps to a page object method."""
        page_objects = kb.get("page_objects", [])

        for page_obj in page_objects:
            # Check both 'page_name' and 'name' fields for compatibility
            page_name = page_obj.get("page_name") or page_obj.get("name", "")
            if page_name:
                # Convert page name to snake_case for app attribute
                page_name = self.to_snake_case(page_name)

            selectors = page_obj.get("selectors", [])

            # Check if target matches any selector in this page object
            for selector_info in selectors:
                element = selector_info.get("element", "")
                if element == target:
                    # Found a match, generate POM call
                    if action == "click":
                        method_name = f"click_{element.replace('_button', '').replace('_link', '').replace('_field', '')}"
                        return f"await app.{page_name}.{method_name}()"
                    elif action == "fill":
                        method_name = f"enter_{element.replace('_field', '').replace('_input', '')}"
                        return f"await app.{page_name}.{method_name}('{value}')"
                    elif action == "navigate" and page_name:
                        return f"await app.{page_name}.navigate()"

        return None

    def _find_page_for_target(self, target: str, kb: Dict[str, Any]) -> Optional[str]:
        """Find which page object contains the given target element."""
        page_objects = kb.get("page_objects", [])

        for page_obj in page_objects:
            selectors = page_obj.get("selectors", [])
            for selector_info in selectors:
                element = selector_info.get("element", "")
                if element == target:
                    # Return the page name
                    page_name = page_obj.get("page_name") or page_obj.get("name", "")
                    return str(page_name) if page_name else None

        return None

    def generate_test(self, ticket: Dict[str, Any], kb: Dict[str, Any]) -> str:
        """
        Generate complete test code from ticket and knowledge base.

        Args:
            ticket: Jira ticket data with acceptance criteria
            kb: Knowledge base with page objects and selectors

        Returns:
            Complete Playwright test code as string
        """
        # Extract ticket information
        title = ticket.get("title", "Unknown Test")
        description = ticket.get("description", "")
        acceptance_criteria = ticket.get("acceptance_criteria", [])

        # Generate function name
        function_name = f"test_{self.to_snake_case(title)}"

        # Generate selector mapping
        selector_mapping = self.generate_selector_mapping(kb)

        # Generate test steps
        test_steps = []
        current_page = None  # Track which page we're currently on

        for criterion in acceptance_criteria:
            if isinstance(criterion, dict) and "steps" in criterion:
                # Handle structured acceptance criteria
                steps = criterion.get("steps", [])
                for step in steps:
                    # Check if we need to navigate to a different page
                    target = step.get("target", "")
                    page_for_target = self._find_page_for_target(target, kb)

                    if page_for_target and page_for_target != current_page:
                        # Need to navigate to this page first
                        page_name = self.to_snake_case(page_for_target)
                        test_steps.append(f"    await app.{page_name}.navigate()")
                        current_page = page_for_target

                    test_step = self.generate_test_step(step, selector_mapping, kb)
                    test_steps.append(test_step)
            elif isinstance(criterion, dict):
                # Handle single step criterion
                target = criterion.get("target", "")
                page_for_target = self._find_page_for_target(target, kb)

                if page_for_target and page_for_target != current_page:
                    # Need to navigate to this page first
                    page_name = self.to_snake_case(page_for_target)
                    test_steps.append(f"    await app.{page_name}.navigate()")
                    current_page = page_for_target

                test_step = self.generate_test_step(criterion, selector_mapping, kb)
                test_steps.append(test_step)
            else:
                # Handle string-based criteria (convert to comment)
                test_steps.append(f"    # {criterion}")

        # If no structured steps found, generate basic navigation
        if not test_steps:
            test_steps = [
                "    await page.goto('/')",
                "    # TODO: Add test steps based on acceptance criteria",
            ]

        # Combine all parts into complete test
        test_code = f'''"""
Generated test for: {title}

Description: {description}

This test was automatically generated from Jira ticket acceptance criteria
using the template-based test generator.
"""

import pytest
from playwright.async_api import expect


@pytest.mark.asyncio
@pytest.mark.generated
async def {function_name}(page, app):
    """
    Test case: {title}

    Generated from ticket acceptance criteria.
    """
{chr(10).join(test_steps)}
'''

        return test_code

    def generate_from_files(
        self, ticket_file: str, kb_file: str, output_file: Optional[str] = None
    ) -> str:
        """
        Generate test from ticket and knowledge base files.

        Args:
            ticket_file: Path to ticket JSON file
            kb_file: Path to knowledge base JSON file
            output_file: Optional output file path

        Returns:
            Generated test code as string
        """
        # Load input files
        ticket = self.load_json(ticket_file)
        kb = self.load_json(kb_file)

        # Generate the test
        test_code = self.generate_test(ticket, kb)

        # Save output if requested
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(test_code)

        return test_code


def main() -> None:
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Generate Playwright tests from ticket JSON and KB JSON using templates."
    )

    # Required arguments
    parser.add_argument("--ticket", required=True, help="Path to ticket JSON file")
    parser.add_argument("--kb", required=True, help="Path to knowledge base JSON file")
    parser.add_argument("--output", help="Output file path (optional)")

    # Optional arguments
    parser.add_argument(
        "--template-version", default="v1.0", help="Template version to use"
    )

    args = parser.parse_args()

    try:
        # Create generator and generate test
        generator = TemplateTestGenerator(args.template_version)
        test_code = generator.generate_from_files(args.ticket, args.kb, args.output)

        if args.output:
            print(f"✅ Test generated successfully and saved to: {args.output}")
        else:
            print("✅ Test generated successfully:")
            print("=" * 60)
            print(test_code)

    except Exception as e:
        print(f"❌ Error generating test: {e}")
        exit(1)


if __name__ == "__main__":
    main()
