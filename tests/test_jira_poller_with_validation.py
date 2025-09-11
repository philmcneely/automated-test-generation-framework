"""
Comprehensive tests for the refactored JiraPollerWithValidation class.

This test suite validates the class-based implementation maintains all functionality
from the original functional approach while adding better testability and encapsulation.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.poller.jira_poller_with_validation import JiraPollerWithValidation


class TestJiraPollerInitialization:
    """Test JiraPollerWithValidation class initialization and configuration."""

    def test_init_with_all_params(self) -> None:
        """Test initialization with all parameters provided."""
        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
            jira_jql="project = TEST",
            poll_interval=30,
        )

        assert poller.jira_base == "https://test.atlassian.net"
        assert poller.jira_user == "testuser"
        assert poller.jira_token == "testtoken"
        assert poller.jira_jql == "project = TEST"
        assert poller.poll_interval == 30

    @patch.dict(
        "os.environ",
        {
            "JIRA_BASE": "https://env.atlassian.net",
            "JIRA_USER": "envuser",
            "JIRA_TOKEN": "envtoken",
            "JIRA_JQL": "project = ENV",
        },
    )
    def test_init_with_env_vars(self) -> None:
        """Test initialization using environment variables."""
        poller = JiraPollerWithValidation()

        assert poller.jira_base == "https://env.atlassian.net"
        assert poller.jira_user == "envuser"
        assert poller.jira_token == "envtoken"
        assert poller.jira_jql == "project = ENV"

    def test_init_without_credentials_raises_error(self) -> None:
        """Test that missing credentials raise ValueError."""
        with pytest.raises(ValueError, match="Missing required Jira configuration"):
            JiraPollerWithValidation()

    def test_init_with_defaults(self) -> None:
        """Test initialization with minimal parameters."""
        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        assert poller.jira_jql == 'project = ABC AND status in ("To Do", "In Progress")'
        assert poller.poll_interval == 60


class TestTicketFetching:
    """Test the fetch_tickets method."""

    @patch("requests.get")
    def test_fetch_tickets_success(self, mock_get: Any) -> None:
        """Test successful ticket fetching."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "issues": [
                {"key": "TEST-1", "fields": {"summary": "Test issue"}},
                {"key": "TEST-2", "fields": {"summary": "Another test"}},
            ]
        }
        mock_get.return_value = mock_response

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        tickets = poller.fetch_tickets()

        assert len(tickets) == 2
        assert tickets[0]["key"] == "TEST-1"
        assert tickets[1]["key"] == "TEST-2"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "https://test.atlassian.net/rest/api/3/search" in call_args[0][0]

    @patch("requests.get")
    def test_fetch_tickets_http_error(self, mock_get: Any) -> None:
        """Test handling of HTTP errors during ticket fetching."""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        with pytest.raises(requests.exceptions.HTTPError):
            poller.fetch_tickets()


class TestTestValidation:
    """Test the validate_and_save_test method."""

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("builtins.open")
    def test_validate_and_save_test_success(
        self, mock_open: Any, mock_makedirs: Any, mock_subprocess: Any
    ) -> None:
        """Test successful test validation and saving."""
        # Mock successful validation
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        test_content = "async def test_example(): pass"
        result = poller.validate_and_save_test(test_content, "TEST-123")

        assert result is True

        # Verify subprocess call
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "src/validator/test_validator.py" in call_args

        # Verify file writing
        mock_file.write.assert_called_with(test_content)

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("builtins.open")
    def test_validate_and_save_test_failure(
        self, mock_open: Any, mock_makedirs: Any, mock_subprocess: Any
    ) -> None:
        """Test handling of test validation failure."""
        # Mock failed validation
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Validation error"
        mock_result.stdout = "Error output"
        mock_subprocess.return_value = mock_result

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        test_content = "invalid test content"
        result = poller.validate_and_save_test(test_content, "TEST-123")

        assert result is False

        # Verify failed test is saved for debugging
        mock_file.write.assert_called_with(test_content)


class TestTicketProcessing:
    """Test the process_ticket method."""

    @patch("subprocess.run")
    @patch("os.unlink")
    @patch("tempfile.NamedTemporaryFile")
    def test_process_ticket_with_acceptance_criteria(
        self, mock_tempfile: Any, mock_unlink: Any, mock_subprocess: Any
    ) -> None:
        """Test processing ticket with acceptance criteria."""
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_ticket.json"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Mock successful test generation
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "# ===== Generated POM-based Playwright Test =====\nasync def test_example(): pass"
        mock_subprocess.return_value = mock_result

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        # Mock the validate_and_save_test method
        with patch.object(poller, "validate_and_save_test", return_value=True):
            ticket = {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test login functionality",
                    "description": "- Click login button\n- Enter credentials\n- Verify success",
                },
            }

            poller.process_ticket(ticket)

            # Verify test generation was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            assert "src/agent/agent_runner_pom.py" in call_args

            # Verify cleanup was called
            mock_unlink.assert_called_once_with("/tmp/test_ticket.json")

    @patch("subprocess.run")
    @patch("os.unlink")
    @patch("tempfile.NamedTemporaryFile")
    def test_process_ticket_without_acceptance_criteria(
        self, mock_tempfile: Any, mock_unlink: Any, mock_subprocess: Any
    ) -> None:
        """Test processing ticket without acceptance criteria creates default test."""
        # Mock temporary file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_ticket.json"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Mock successful test generation
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "async def test_default(): pass"
        mock_subprocess.return_value = mock_result

        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

        # Mock the validate_and_save_test method
        with patch.object(poller, "validate_and_save_test", return_value=True):
            ticket = {
                "key": "TEST-123",
                "fields": {"summary": "Test functionality", "description": ""},
            }

            poller.process_ticket(ticket)

            # Verify default acceptance criteria was used
            mock_subprocess.assert_called_once()

            # Verify cleanup was called
            mock_unlink.assert_called_once_with("/tmp/test_ticket.json")


class TestMainLoop:
    """Test the run method and main loop functionality."""

    @patch("time.sleep")
    def test_run_single_iteration(self, mock_sleep: Any) -> None:
        """Test single iteration of the main loop."""
        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
            poll_interval=1,
        )

        # Mock methods to avoid actual API calls
        with patch.object(
            poller, "fetch_tickets", return_value=[]
        ) as mock_fetch, patch.object(poller, "process_ticket"):
            # Mock sleep to raise an exception after first iteration
            mock_sleep.side_effect = KeyboardInterrupt("Stop test")

            with pytest.raises(KeyboardInterrupt):
                poller.run()

            # Verify methods were called
            mock_fetch.assert_called_once()
            mock_sleep.assert_called_once_with(1)

    @patch("time.sleep")
    def test_run_with_exception_handling(self, mock_sleep: Any) -> None:
        """Test exception handling in main loop."""
        poller = JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
            poll_interval=1,
        )

        # Mock fetch_tickets to raise an exception
        with patch.object(poller, "fetch_tickets", side_effect=Exception("API Error")):
            # Mock sleep to raise an exception after first iteration
            mock_sleep.side_effect = KeyboardInterrupt("Stop test")

            with pytest.raises(KeyboardInterrupt):
                poller.run()

            # Verify exception was handled and sleep was called
            mock_sleep.assert_called_once_with(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
