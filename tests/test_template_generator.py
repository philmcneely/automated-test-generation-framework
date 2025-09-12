"""
Tests for Template-Based Test Generator

This module contains comprehensive unit tests for the TemplateTestGenerator class,
which provides template-based test generation using Page Object Model patterns.

Test Coverage:
    ✓ Generator initialization and configuration
    ✓ JSON file loading and validation
    ✓ Text processing and snake_case conversion
    ✓ Selector resolution from knowledge base
    ✓ Test step generation for various actions
    ✓ Complete test code generation
    ✓ File I/O operations and error handling
    ✓ Edge cases and error conditions

Test Structure:
    - TestTemplateTestGeneratorInitialization: Basic setup and configuration
    - TestTestGeneration: Core test generation functionality
    - TestFileOperations: File loading and saving operations
    - TestEdgeCases: Error handling and edge cases

Dependencies:
    - unittest.mock: Mocking for isolated unit tests
    - tempfile: Temporary file operations for testing
    - pathlib: File path operations
    - json: JSON data handling for test fixtures

Author: PMAC
Date: 2025-09-11
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.agent.template_generator import TemplateTestGenerator


class TestTemplateTestGeneratorInitialization:
    """Test TemplateTestGenerator class static methods and utilities."""

    def test_load_json_success(self) -> None:
        """Test successful JSON loading."""
        test_data = {"test": "data", "number": 123}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as temp_file:
            json.dump(test_data, temp_file)
            temp_path = temp_file.name

        try:
            generator = TemplateTestGenerator()
            result = generator.load_json(temp_path)
            assert result == test_data
        finally:
            Path(temp_path).unlink()

    def test_to_snake_case_conversion(self) -> None:
        """Test snake_case conversion from different formats."""
        generator = TemplateTestGenerator()

        assert generator.to_snake_case("CamelCase") == "camel_case"
        assert generator.to_snake_case("camelCase") == "camel_case"
        assert generator.to_snake_case("already_snake") == "already_snake"
        assert generator.to_snake_case("HTMLParser") == "html_parser"
        assert generator.to_snake_case("XMLHttpRequest") == "xml_http_request"


class TestTestGeneration:
    """Test the core test generation functionality."""

    def test_generate_simple_test(self) -> None:
        """Test generation of a simple test with basic actions."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Test login functionality",
            "acceptance_criteria": [
                {"action": "goto", "target": "https://example.com"},
                {"action": "click", "target": "login_button"},
                {"action": "fill", "target": "username_field", "value": "testuser"},
                {"action": "assert_text", "value": "Welcome"},
            ],
        }

        kb: Any = {
            "page_objects": [
                {
                    "name": "LoginPage",
                    "selectors": [
                        {"element": "login_button", "selector": "#login"},
                        {"element": "username_field", "selector": "#username"},
                    ],
                }
            ]
        }

        result = generator.generate_test(ticket, kb)

        # Verify test structure
        assert "async def test_test_login_functionality" in result
        assert "@pytest.mark.asyncio" in result
        assert "@pytest.mark.generated" in result
        assert "await page.goto('https://example.com')" in result
        assert "await app.login_page.click_login()" in result
        assert "await app.login_page.enter_username('testuser')" in result
        assert "await expect(page.locator('text=Welcome')).to_be_visible()" in result

    def test_generate_test_with_raw_selectors(self) -> None:
        """Test generation with raw CSS selectors not in knowledge base."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Test with raw selectors",
            "acceptance_criteria": [
                {"action": "click", "target": "#submit-btn"},
                {"action": "fill", "target": ".username-input", "value": "admin"},
            ],
        }

        kb: Any = {"page_objects": []}

        result = generator.generate_test(ticket, kb)

        # Verify raw selectors are used directly
        assert "await page.click('#submit-btn')" in result
        assert "await page.fill('.username-input', 'admin')" in result

    def test_generate_test_with_page_navigation(self) -> None:
        """Test that page navigation is handled correctly."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Multi-page test",
            "acceptance_criteria": [
                {"action": "click", "target": "login_button"},
                {"action": "click", "target": "dashboard_link"},
            ],
        }

        kb: Any = {
            "page_objects": [
                {
                    "name": "LoginPage",
                    "selectors": [{"element": "login_button", "selector": "#login"}],
                },
                {
                    "name": "DashboardPage",
                    "selectors": [
                        {"element": "dashboard_link", "selector": "#dashboard"}
                    ],
                },
            ]
        }

        result = generator.generate_test(ticket, kb)

        # Verify POM calls are generated correctly
        assert "await app.login_page.click_login()" in result
        assert "await app.dashboard_page.click_dashboard()" in result

    def test_generate_test_with_special_mappings(self) -> None:
        """Test special method name mappings for common elements."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Special mappings test",
            "acceptance_criteria": [
                {"action": "fill", "target": "username_field", "value": "admin"},
                {"action": "fill", "target": "password_field", "value": "secret"},
            ],
        }

        kb: Any = {
            "page_objects": [
                {
                    "name": "LoginPage",
                    "selectors": [
                        {"element": "username_field", "selector": "#username"},
                        {"element": "password_field", "selector": "#password"},
                    ],
                }
            ]
        }

        result = generator.generate_test(ticket, kb)

        # Verify special method mappings
        assert "await app.login_page.enter_username('admin')" in result
        assert "await app.login_page.enter_password('secret')" in result

    def test_generate_test_with_unsupported_action(self) -> None:
        """Test handling of unsupported actions."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Unsupported action test",
            "acceptance_criteria": [
                {"action": "hover", "target": "menu_item", "value": "something"},
            ],
        }

        kb: Any = {"page_objects": []}

        result = generator.generate_test(ticket, kb)

        # Verify unsupported action is handled with TODO comment
        assert "# TODO: Implement hover action for menu_item" in result

    def test_generate_test_function_name_sanitization(self) -> None:
        """Test that test function names are properly sanitized."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Test with Special Characters! & Symbols @#$%",
            "acceptance_criteria": [],
        }

        kb: Any = {"page_objects": []}

        result = generator.generate_test(ticket, kb)

        # Verify function name is sanitized (check for part of the name)
        assert "async def test_test_with_special_characters" in result

    def test_generate_test_with_empty_criteria(self) -> None:
        """Test generation with empty acceptance criteria."""
        generator = TemplateTestGenerator()

        ticket = {"title": "Empty test", "acceptance_criteria": []}

        kb: Any = {"page_objects": []}

        result = generator.generate_test(ticket, kb)

        # Verify basic test structure is still generated
        assert "async def test_empty_test" in result
        assert "@pytest.mark.asyncio" in result
        assert "@pytest.mark.generated" in result


class TestFileOperations:
    """Test file-based operations."""

    def test_generate_from_files_success(self) -> None:
        """Test successful generation from files."""
        generator = TemplateTestGenerator()

        ticket_data = {
            "title": "File test",
            "acceptance_criteria": [{"action": "click", "target": "#button"}],
        }

        kb_data: Any = {"page_objects": []}

        with tempfile.TemporaryDirectory() as tmpdir:
            ticket_path = Path(tmpdir) / "ticket.json"
            kb_path = Path(tmpdir) / "kb.json"

            # Create test files
            with open(ticket_path, "w") as f:
                json.dump(ticket_data, f)
            with open(kb_path, "w") as f:
                json.dump(kb_data, f)

            result = generator.generate_from_files(str(ticket_path), str(kb_path))

            assert "async def test_file_test" in result
            assert "await page.click('#button')" in result

    def test_generate_from_files_with_output(self) -> None:
        """Test generation with output file."""
        generator = TemplateTestGenerator()

        ticket_data = {
            "title": "Output test",
            "acceptance_criteria": [{"action": "goto", "target": "/"}],
        }

        kb_data: Any = {"page_objects": []}

        with tempfile.TemporaryDirectory() as tmpdir:
            ticket_path = Path(tmpdir) / "ticket.json"
            kb_path = Path(tmpdir) / "kb.json"
            output_path = Path(tmpdir) / "output" / "test_output.py"

            # Create test files
            with open(ticket_path, "w") as f:
                json.dump(ticket_data, f)
            with open(kb_path, "w") as f:
                json.dump(kb_data, f)

            result = generator.generate_from_files(
                str(ticket_path), str(kb_path), str(output_path)
            )

            # Verify output file was created
            assert output_path.exists()
            content = output_path.read_text()
            assert "async def test_output_test" in content
            assert content == result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_ticket_fields(self) -> None:
        """Test handling of missing ticket fields."""
        generator = TemplateTestGenerator()

        ticket: Any = {}  # Empty ticket
        kb: Any = {"page_objects": []}

        result = generator.generate_test(ticket, kb)

        # Verify default values are used
        assert "async def test_unknown_test" in result

    def test_missing_kb_fields(self) -> None:
        """Test handling of missing knowledge base fields."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Test with missing KB",
            "acceptance_criteria": [{"action": "click", "target": "unknown_element"}],
        }

        kb: Any = {}  # Empty KB

        result = generator.generate_test(ticket, kb)

        # Should not crash and should generate valid test
        assert "async def test_test_with_missing_kb" in result

    def test_malformed_selectors(self) -> None:
        """Test handling of malformed selectors in knowledge base."""
        generator = TemplateTestGenerator()

        ticket = {
            "title": "Malformed selector test",
            "acceptance_criteria": [{"action": "click", "target": "test_element"}],
        }

        kb: Any = {
            "page_objects": [
                {
                    "name": "TestPage",
                    "selectors": [
                        {"element": "test_element"},  # Missing selector field
                    ],
                }
            ]
        }

        result = generator.generate_test(ticket, kb)

        # Should handle gracefully without crashing
        assert "async def test_malformed_selector_test" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
