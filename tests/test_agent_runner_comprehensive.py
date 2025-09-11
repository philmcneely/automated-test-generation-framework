"""
Comprehensive Test Suite for Agent Runner Modules

This module provides comprehensive unit tests for the agent runner modules
to achieve high code coverage and ensure robust test generation functionality.

Features:
    ✓ Complete coverage of agent_runner.py helper functions
    ✓ Complete coverage of agent_runner_pom.py functionality
    ✓ Edge case testing for empty inputs and error conditions
    ✓ Realistic test data scenarios
    ✓ Environment variable mocking
    ✓ Comprehensive assertion testing

Test Categories:
    - JSON loading and validation
    - Selector index building and resolution
    - Test step generation for all actions
    - Function name generation with edge cases
    - Complete test code generation
    - POM-based test generation with method mapping
    - Fallback method generation
    - Unsupported action handling

Coverage Targets:
    - Agent Runner: >85% coverage
    - POM Agent Runner: >80% coverage
    - Overall: >80% coverage

Dependencies:
    - pytest: Testing framework
    - unittest.mock: Mocking capabilities
    - tempfile: Temporary file management
    - json: JSON data handling

Author: PMAC
Date: 2025-09-11
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.agent.agent_runner import (
    _build_selector_index,
    _build_test_code,
    _generate_test_function_name,
    _generate_test_step,
    _resolve_target,
    generate_playwright_test,
    load_json,
)
from src.agent.agent_runner_pom import (
    generate_pom_playwright_test,
)
from src.agent.agent_runner_pom import load_json as load_json_pom
from src.agent.agent_runner_pom import (
    to_snake_case,
)


class TestAgentRunnerComprehensive:
    """Comprehensive tests for agent_runner.py"""

    def test_load_json_valid(self):
        """Test loading valid JSON file."""
        test_data = {"key": "value", "nested": {"inner": "data"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_json(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_load_json_file_not_found(self):
        """Test loading non-existent JSON file."""
        with pytest.raises(FileNotFoundError):
            load_json("nonexistent_file.json")

    def test_build_selector_index_empty_kb(self):
        """Test building selector index with empty knowledge base."""
        kb = {"page_objects": []}
        result = _build_selector_index(kb)
        assert result == {}

    def test_build_selector_index_with_data(self):
        """Test building selector index with valid data."""
        kb = {
            "page_objects": [
                {
                    "selectors": [
                        {"element": "login_button", "selector": "#login-btn"},
                        {"element": "username_field", "selector": "#username"},
                    ]
                }
            ]
        }
        result = _build_selector_index(kb)
        expected = {
            "login_button": "#login-btn",
            "username_field": "#username",
        }
        assert result == expected

    def test_resolve_target_with_selectors(self):
        """Test target resolution with various selector types."""
        selector_index = {"button": "#btn", "field": ".input"}

        # Test CSS selectors
        assert _resolve_target("#id", selector_index) == "#id"
        assert _resolve_target(".class", selector_index) == ".class"
        assert _resolve_target("[attr]", selector_index) == "[attr]"

        # Test XPath and text selectors
        assert _resolve_target("//div", selector_index) == "//div"
        assert _resolve_target("text=Hello", selector_index) == "text=Hello"

        # Test mapped elements
        assert _resolve_target("button", selector_index) == "#btn"
        assert _resolve_target("field", selector_index) == ".input"

        # Test unknown elements
        assert _resolve_target("unknown", selector_index) == "unknown"

        # Test None/empty
        assert _resolve_target(None, selector_index) is None
        assert _resolve_target("", selector_index) == ""

    def test_generate_test_step_all_actions(self):
        """Test test step generation for all supported actions."""
        # Test click action
        result = _generate_test_step("click", "#button", None)
        assert result == "        page.click('#button')"

        # Test fill action
        result = _generate_test_step("fill", "#input", "test value")
        assert result == "        page.fill('#input', 'test value')"

        # Test goto action
        result = _generate_test_step("goto", "/login", None)
        assert result == "        page.goto('/login')"

        # Test assert_text action
        result = _generate_test_step("assert_text", None, "Welcome")
        assert result == "        page.wait_for_selector('text=Welcome')"

        # Test unsupported action
        result = _generate_test_step("hover", "#element", None)
        assert "TODO: Unsupported step" in result
        assert "hover" in result

    def test_generate_test_function_name(self):
        """Test test function name generation."""
        # Test normal title
        result = _generate_test_function_name("User Login Test")
        assert result == "test_user_login_test"

        # Test title with special characters
        result = _generate_test_function_name("Test: User@Login (Special)!")
        assert result == "test_test__user_login__special"

        # Test very long title
        long_title = "This is a very long test title that should be truncated to fit within reasonable function name limits"
        result = _generate_test_function_name(long_title)
        assert len(result) <= 65  # test_ + 60 chars
        assert result.startswith("test_")

    def test_build_test_code(self):
        """Test complete test code building."""
        test_func_name = "test_user_login"
        base_url = "https://example.com"
        body_lines = [
            "        page.click('#login')",
            "        page.fill('#user', 'test')",
        ]

        result = _build_test_code(test_func_name, base_url, body_lines)

        assert "import os" in result
        assert "import pytest" in result
        assert "from playwright.sync_api import sync_playwright" in result
        assert 'BASE_URL = os.getenv("APP_BASE_URL", "https://example.com")' in result
        assert "@pytest.mark.e2e" in result
        assert "def test_user_login():" in result
        assert "page.click('#login')" in result
        assert "page.fill('#user', 'test')" in result
        assert "browser.close()" in result

    def test_generate_playwright_test_complete(self):
        """Test complete test generation with realistic data."""
        ticket = {
            "title": "User Login Flow",
            "acceptance_criteria": [
                {"action": "goto", "target": "/login"},
                {"action": "fill", "target": "username_field", "value": "testuser"},
                {"action": "fill", "target": "password_field", "value": "testpass"},
                {"action": "click", "target": "login_button"},
                {"action": "assert_text", "value": "Welcome"},
            ],
        }

        kb = {
            "page_objects": [
                {
                    "selectors": [
                        {"element": "username_field", "selector": "#username"},
                        {"element": "password_field", "selector": "#password"},
                        {"element": "login_button", "selector": "#login-btn"},
                    ]
                }
            ]
        }

        with patch.dict(os.environ, {"APP_BASE_URL": "https://myapp.com"}):
            result = generate_playwright_test(ticket, kb)

        # Check structure
        assert "import os" in result
        assert "import pytest" in result
        assert "@pytest.mark.e2e" in result
        assert "def test_user_login_flow():" in result

        # Check content
        assert 'BASE_URL = os.getenv("APP_BASE_URL", "https://myapp.com")' in result
        assert "page.goto('/login')" in result
        assert "page.fill('#username', 'testuser')" in result
        assert "page.fill('#password', 'testpass')" in result
        assert "page.click('#login-btn')" in result
        assert "page.wait_for_selector('text=Welcome')" in result

    def test_generate_playwright_test_empty_ticket(self):
        """Test test generation with empty ticket."""
        ticket = {"title": "", "acceptance_criteria": []}
        kb = {"page_objects": []}

        result = generate_playwright_test(ticket, kb)

        assert "def test_():" in result  # Empty title results in test_()
        assert "page.goto(BASE_URL)" in result
        assert "browser.close()" in result

    def test_generate_playwright_test_unsupported_actions(self):
        """Test test generation with unsupported actions."""
        ticket = {
            "title": "Complex Test",
            "acceptance_criteria": [
                {"action": "hover", "target": "#element"},
                {"action": "drag", "target": "#source", "value": "#target"},
            ],
        }
        kb = {"page_objects": []}

        result = generate_playwright_test(ticket, kb)

        assert "TODO: Unsupported step" in result
        assert "hover" in result
        assert "drag" in result


class TestAgentRunnerPOMComprehensive:
    """Comprehensive tests for agent_runner_pom.py"""

    def test_load_json_pom(self):
        """Test JSON loading for POM agent."""
        test_data = {"test": "data"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            result = load_json_pom(temp_path)
            assert result == test_data
        finally:
            os.unlink(temp_path)

    def test_to_snake_case_conversions(self):
        """Test various snake_case conversions."""
        test_cases = [
            ("CamelCase", "camel_case"),
            ("PascalCase", "pascal_case"),
            ("camelCase", "camel_case"),
            ("HTTPSConnection", "https_connection"),
            ("UserID", "user_id"),
            ("SimpleTest", "simple_test"),
            ("XMLHttpRequest", "xml_http_request"),
            ("URLPattern", "url_pattern"),
        ]

        for input_str, expected in test_cases:
            result = to_snake_case(input_str)
            assert (
                result == expected
            ), f"Failed for {input_str}: got {result}, expected {expected}"

    def test_generate_pom_playwright_test_basic(self):
        """Test basic POM test generation."""
        ticket = {
            "title": "Login Test",
            "acceptance_criteria": [
                {"action": "goto", "target": "/login"},
                {"action": "fill", "target": "username_field", "value": "user"},
                {"action": "fill", "target": "password_field", "value": "pass"},
                {"action": "click", "target": "login_button"},
            ],
        }

        kb = {
            "page_objects": [
                {
                    "name": "LoginPage",
                    "selectors": [
                        {"element": "username_field", "selector": "#username"},
                        {"element": "password_field", "selector": "#password"},
                        {"element": "login_button", "selector": "#login-btn"},
                    ],
                }
            ]
        }

        result = generate_pom_playwright_test(ticket, kb)

        # Check structure
        assert "@pytest.mark.asyncio" in result
        assert "@pytest.mark.generated" in result
        assert "async def test_login_test(page, app):" in result
        assert "await app.login_page.navigate()" in result
        assert "await app.login_page.enter_username('user')" in result
        assert "await app.login_page.enter_password('pass')" in result
        assert "await app.login_page.click_login()" in result

    def test_generate_pom_playwright_test_with_assertions(self):
        """Test POM test generation with assertions."""
        ticket = {
            "title": "Welcome Test",
            "acceptance_criteria": [
                {"action": "assert_text", "value": "Welcome to the app"},
            ],
        }
        kb = {"page_objects": []}

        result = generate_pom_playwright_test(ticket, kb)

        assert (
            "await expect(page.locator('text=Welcome to the app')).to_be_visible()"
            in result
        )

    def test_generate_pom_playwright_test_fallback_methods(self):
        """Test POM test generation with fallback to generic methods."""
        ticket = {
            "title": "Custom Action Test",
            "acceptance_criteria": [
                {"action": "click", "target": "submit_form"},
                {
                    "action": "fill",
                    "target": "email_field",
                    "value": "test@example.com",
                },
            ],
        }

        kb = {
            "page_objects": [
                {
                    "name": "FormPage",
                    "selectors": [
                        {"element": "submit_form", "selector": "#submit"},
                        {"element": "email_field", "selector": "#email"},
                    ],
                }
            ]
        }

        result = generate_pom_playwright_test(ticket, kb)

        # Should use fallback method names
        assert "await app.form_page.click_submit_form()" in result
        assert "await app.form_page.enter_email_field('test@example.com')" in result

    def test_generate_pom_playwright_test_empty_ticket(self):
        """Test POM test generation with empty ticket."""
        ticket = {"title": "", "acceptance_criteria": []}
        kb = {"page_objects": []}

        result = generate_pom_playwright_test(ticket, kb)

        assert "async def test_(page, app):" in result  # Empty title results in test_()
        assert "This test was automatically generated" in result

    def test_generate_pom_playwright_test_unsupported_actions(self):
        """Test POM test generation with unsupported actions."""
        ticket = {
            "title": "Complex Actions",
            "acceptance_criteria": [
                {"action": "hover", "target": "#element"},
                {"action": "double_click", "target": "#button"},
            ],
        }
        kb = {"page_objects": []}

        result = generate_pom_playwright_test(ticket, kb)

        assert "# TODO: Unsupported step" in result
        assert "hover" in result
        assert "double_click" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
