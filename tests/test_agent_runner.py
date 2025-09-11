#!/usr/bin/env python3
"""
Agent Runner Unit Tests - Automated Test Generation Framework
This module contains comprehensive unit tests for the agent runner modules,
testing both the core agent runner and POM-based test generation functionality.

Features:
    ✓ JSON loading and validation tests
    ✓ Snake case conversion utility tests
    ✓ POM-based test generation tests
    ✓ End-to-end integration tests
    ✓ Error handling and edge case tests

Test Coverage:
    - load_json function with valid and invalid JSON files
    - to_snake_case utility function
    - Basic POM test generation with various scenarios
    - Empty ticket handling
    - End-to-end test generation workflows
    - Error handling for missing targets and invalid actions

Dependencies:
    - pytest: Testing framework
    - json: JSON data processing
    - tempfile: Temporary file management
    - os: Operating system interface

Author: PMAC
Date: 2025-09-11
"""

import json
import os
import tempfile
from typing import Any, Dict

import pytest

from src.agent.agent_runner import load_json
from src.agent.agent_runner_pom import generate_pom_playwright_test as generate_test
from src.agent.agent_runner_pom import to_snake_case


class TestAgentRunner:
    """Test cases for the agent runner functionality."""

    @pytest.mark.unit  # type: ignore[misc]
    def test_load_json_valid(self) -> None:
        """Test loading valid JSON file."""
        test_data: Dict[str, Any] = {
            "title": "Test",
            "acceptance_criteria": [{"action": "click", "target": "button"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    @pytest.mark.unit  # type: ignore[misc]
    def test_load_json_invalid(self) -> None:
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_json(temp_path)
        finally:
            os.unlink(temp_path)

    @pytest.mark.unit  # type: ignore[misc]
    def test_to_snake_case(self) -> None:
        """Test snake case conversion function."""
        assert to_snake_case("LoginButton") == "login_button"
        assert to_snake_case("HomePage") == "home_page"
        assert to_snake_case("testButton") == "test_button"
        assert to_snake_case("AlreadySnake") == "already_snake"


class TestAgentRunnerPOM:
    """Test cases for the POM-based agent runner."""

    @pytest.mark.unit  # type: ignore[misc]
    def test_basic_pom_generation(self) -> None:
        """Test basic POM test generation."""
        ticket: Dict[str, Any] = {
            "title": "Test Login",
            "acceptance_criteria": [
                {"action": "click", "target": "login_button"},
                {"action": "fill", "target": "username_field", "value": "testuser"},
                {"action": "click", "target": "submit_button"},
            ],
        }

        kb: Dict[str, Any] = {
            "page_objects": [
                {
                    "id": "page_login",
                    "name": "LoginPage",
                    "selectors": [
                        {"element": "login_button", "selector": "#login"},
                        {"element": "username_field", "selector": "#username"},
                        {"element": "submit_button", "selector": "#submit"},
                    ],
                }
            ]
        }

        result = generate_test(ticket, kb)

        # Verify basic structure
        assert "@pytest.mark.asyncio" in result
        assert "@pytest.mark.generated" in result
        assert "async def test_test_login(page, app):" in result
        assert "await app.login_page.navigate()" in result
        assert "await app.login_page.click_login()" in result
        assert "await app.login_page.enter_username('testuser')" in result

    @pytest.mark.unit  # type: ignore[misc]
    def test_empty_ticket(self) -> None:
        """Test handling of empty ticket."""
        ticket: Dict[str, Any] = {"title": "Empty Test", "acceptance_criteria": []}
        kb: Dict[str, Any] = {"page_objects": []}

        result = generate_test(ticket, kb)

        # Should still generate a valid test structure
        assert "@pytest.mark.asyncio" in result
        assert "async def test_empty_test(page, app):" in result


class TestIntegration:
    """Integration tests for the agent runner."""

    @pytest.mark.unit  # type: ignore[misc]
    def test_end_to_end_test_generation(self) -> None:
        """Test end-to-end test generation workflow."""
        # Create a realistic ticket
        ticket: Dict[str, Any] = {
            "title": "User Login Flow",
            "acceptance_criteria": [
                {"action": "goto", "target": "/login"},
                {"action": "fill", "target": "username_field", "value": "testuser"},
                {"action": "fill", "target": "password_field", "value": "testpass"},
                {"action": "click", "target": "login_button"},
                {"action": "assert_text", "value": "Welcome"},
            ],
        }

        kb: Dict[str, Any] = {
            "page_objects": [
                {
                    "id": "page_login",
                    "name": "LoginPage",
                    "selectors": [
                        {"element": "username_field", "selector": "#username"},
                        {"element": "password_field", "selector": "#password"},
                        {"element": "login_button", "selector": "#submit"},
                    ],
                }
            ]
        }

        result = generate_test(ticket, kb)

        # Verify complete workflow
        assert "async def test_user_login_flow(page, app):" in result
        assert "await app.login_page.navigate()" in result
        assert "await app.login_page.enter_username('testuser')" in result
        assert "await app.login_page.enter_password('testpass')" in result
        assert "await app.login_page.click_login()" in result
        assert (
            "await expect(page.locator('text=Welcome'))" ".to_be_visible()"
        ) in result


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit  # type: ignore[misc]
    def test_missing_target_in_kb(self) -> None:
        """Test handling of targets not in knowledge base."""
        ticket: Dict[str, Any] = {
            "title": "Test Missing Target",
            "acceptance_criteria": [{"action": "click", "target": "unknown_element"}],
        }

        kb: Dict[str, Any] = {"page_objects": []}

        result = generate_test(ticket, kb)

        # Should handle gracefully with fallback
        assert "await page.click('unknown_element')" in result

    @pytest.mark.unit  # type: ignore[misc]
    def test_invalid_action(self) -> None:
        """Test handling of invalid actions."""
        ticket: Dict[str, Any] = {
            "title": "Test Invalid Action",
            "acceptance_criteria": [{"action": "invalid_action", "target": "button"}],
        }

        kb: Dict[str, Any] = {"page_objects": []}

        result = generate_test(ticket, kb)

        # Should handle gracefully with comment
        assert "# TODO: Unsupported step:" in result


def main() -> None:
    """Run the test suite."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()
