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

        # LLM parsing is a separate subprocess call (covered by TestLLMParsing);
        # isolate it so only the template generator subprocess is observed here.
        # Mock the validate_and_save_test method
        with patch.object(poller, "parse_with_llm", return_value=None), patch.object(
            poller, "validate_and_save_test", return_value=True
        ):
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
            assert "src/agent/template_generator.py" in call_args

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
        with patch.object(poller, "parse_with_llm", return_value=None), patch.object(
            poller, "validate_and_save_test", return_value=True
        ):
            ticket = {
                "key": "TEST-123",
                "fields": {"summary": "Test functionality", "description": ""},
            }

            poller.process_ticket(ticket)

            # Verify default acceptance criteria was used
            mock_subprocess.assert_called_once()

            # Verify cleanup was called
            mock_unlink.assert_called_once_with("/tmp/test_ticket.json")


class TestLLMParsing:
    """Test the parse_with_llm method."""

    def _poller(self) -> JiraPollerWithValidation:
        return JiraPollerWithValidation(
            jira_base="https://test.atlassian.net",
            jira_user="testuser",
            jira_token="testtoken",
        )

    def test_parse_with_llm_skips_ticket_without_description(self) -> None:
        """No description means no LLM call and no requirement."""
        with patch("subprocess.run") as mock_run:
            ticket = {"key": "TEST-1", "fields": {"summary": "x", "description": ""}}
            assert self._poller().parse_with_llm(ticket) is None
            mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_parse_with_llm_returns_none_on_generator_failure(
        self, mock_run: Any
    ) -> None:
        """A failing LLM generator yields None so the caller can fall back."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        ticket = {
            "key": "TEST-1",
            "fields": {"summary": "x", "description": "- do a thing"},
        }
        assert self._poller().parse_with_llm(ticket) is None
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_process_ticket_runs_llm_parse_then_template_generator(
        self, mock_run: Any
    ) -> None:
        """With a description, the LLM parse call precedes template generation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="no json here", stderr="")
        poller = self._poller()
        ticket = {
            "key": "TEST-1",
            "fields": {"summary": "x", "description": "- Click login"},
        }
        with patch.object(poller, "validate_and_save_test", return_value=True):
            poller.process_ticket(ticket)

        assert mock_run.call_count == 2
        assert "src/agent/llm_generator.py" in mock_run.call_args_list[0][0][0]
        assert "src/agent/template_generator.py" in mock_run.call_args_list[1][0][0]


    def test_process_ticket_passes_scenarios_with_translated_actions(self) -> None:
        """Scenarios stay separate and actions use the generator vocabulary."""
        from src.models.test_requirement import TestRequirement

        req = TestRequirement.model_validate(
            {
                "ticket_id": "TEST-1",
                "title": "x",
                "scenarios": [
                    {
                        "name": "a",
                        "steps": [
                            {"action": "navigate", "target": "/login"},
                            {"action": "assert_visible", "target": "#d"},
                        ],
                        "expected_result": "ok",
                    },
                    {
                        "name": "b",
                        "steps": [
                            {"action": "wait", "target": "#x"},
                            {"action": "assert_text", "target": "", "value": "Err"},
                        ],
                        "expected_result": "err",
                    },
                ],
                "confidence": {"overall": 0.9, "steps": 0.9, "selectors": 0.9, "test_data": 0.9},
            }
        )
        poller = self._poller()
        captured: dict = {}

        def fake_dump(data: Any, fh: Any) -> None:
            captured.update(data)

        ticket = {"key": "TEST-1", "fields": {"summary": "x", "description": "d"}}
        with patch.object(poller, "parse_with_llm", return_value=req), patch(
            "subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")
        ), patch("json.dump", side_effect=fake_dump), patch.object(
            poller, "validate_and_save_test", return_value=True
        ):
            poller.process_ticket(ticket)

        assert len(captured["scenarios"]) == 2
        assert [s["action"] for s in captured["scenarios"][0]["steps"]] == ["goto", "assert_visible"]
        assert captured["scenarios"][1]["steps"][0]["action"] == "wait_for_selector"


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
