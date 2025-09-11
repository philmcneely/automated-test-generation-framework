#!/usr/bin/env python3
"""
Test Validator Unit Tests - Automated Test Generation Framework
This module contains comprehensive unit tests for the test validator service,
ensuring proper validation of generated Playwright tests against the
playwright-ai-framework submodule.

Features:
    ✓ Validator service initialization tests
    ✓ Test file validation tests
    ✓ Test preparation and modification tests
    ✓ Validation report generation tests
    ✓ Integration tests with realistic test structures

Test Coverage:
    - ValidatorService initialization with default and custom paths
    - Validation of nonexistent test files
    - Test preparation for validation environment
    - Validation report generation for various scenarios
    - Integration tests with realistic test structures

Dependencies:
    - pytest: Testing framework
    - tempfile: Temporary file management
    - os: Operating system interface

Author: PMAC
Date: 2025-09-11
"""

import os
import tempfile

import pytest

from src.validator.test_validator import ValidatorService


class TestValidatorUnit:
    """Test cases for the test validator functionality."""

    def test_validator_initialization(self) -> None:
        """Test validator initialization."""
        validator = ValidatorService()
        assert str(validator.playwright_path) == "playwright-ai-framework"

        validator_custom = ValidatorService("custom/path")
        assert str(validator_custom.playwright_path) == "custom/path"

    def test_validate_nonexistent_test(self) -> None:
        """Test validation of nonexistent test file."""
        validator = ValidatorService()
        result = validator.validate_test("nonexistent_test.py")

        assert result["success"] is False
        assert "Test file not found" in result["error"]
        assert result["test_file"] == "nonexistent_test.py"

    def test_validate_valid_test_structure(self) -> None:
        """Test validation of a properly structured test."""
        # Create a valid test file
        test_content = '''
import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
@pytest.mark.generated
async def test_valid_test(page, app):
    """Valid test case."""
    await page.goto("https://example.com")
    await expect(page.locator('text=Example')).to_be_visible()
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            validator = ValidatorService()
            result = validator.validate_test(temp_path)

            # The test will fail due to missing framework, but validation should complete
            # Check that the result contains the expected keys
            assert "test_file" in result
            assert "return_code" in result
            assert "execution_time" in result
            assert "validation_time" in result
            # The test file path should contain the original filename
            assert temp_path.split("/")[-1] in result["test_file"]

        finally:
            os.unlink(temp_path)

    def test_prepare_test_for_validation(self) -> None:
        """Test test preparation for validation."""
        validator = ValidatorService()

        test_content = """
import pytest
@pytest.mark.generated
async def test_something(page):
    pass
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            prepared_content = validator._prepare_test_for_validation(temp_path)

            # Should add validation marker
            assert "@pytest.mark.validation" in prepared_content
            assert "@pytest.mark.generated" in prepared_content

        finally:
            os.unlink(temp_path)

    def test_generate_validation_report_success(self) -> None:
        """Test validation report generation for successful tests."""
        validator = ValidatorService()

        results: list = [
            {"success": True, "test_file": "test1.py", "execution_time": 1.5},
            {"success": True, "test_file": "test2.py", "execution_time": 2.0},
        ]

        report = validator.generate_validation_report(results)

        assert "Total Tests: 2" in report
        assert "Passed: 2" in report
        assert "Failed: 0" in report
        assert "Success Rate: 100.0%" in report

    def test_generate_validation_report_mixed(self) -> None:
        """Test validation report generation for mixed results."""
        validator = ValidatorService()

        results: list = [
            {"success": True, "test_file": "test1.py", "execution_time": 1.5},
            {
                "success": False,
                "test_file": "test2.py",
                "error": "Test failed",
                "execution_time": 2.0,
            },
        ]

        report = validator.generate_validation_report(results)

        assert "Total Tests: 2" in report
        assert "Passed: 1" in report
        assert "Failed: 1" in report
        assert "Success Rate: 50.0%" in report
        assert "❌ test2.py" in report


class TestValidatorIntegration:
    """Integration tests for the validator."""

    def test_validator_with_real_test_structure(self) -> None:
        """Test validator with a realistic test structure."""
        # Create a test that matches our expected format
        test_content = '''
import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
@pytest.mark.generated
async def test_login_flow(page, app):
    """Login flow test."""
    await app.login_page.navigate()
    await app.login_page.enter_username("testuser")
    await app.login_page.enter_password("testpass")
    await app.login_page.click_login()
    await expect(page.locator('text=Welcome')).to_be_visible()
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            validator = ValidatorService()
            result = validator.validate_test(temp_path)

            # Should complete validation (may fail due to missing framework)
            assert "test_file" in result
            assert "execution_time" in result

        finally:
            os.unlink(temp_path)


def main() -> None:
    """Run the test suite."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    main()
