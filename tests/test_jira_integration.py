"""
Tests for Jira integration and reporting functionality.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.integrations.jira_reporter import (
    JiraReporter,
    JiraTestResult,
    report_from_pytest_json,
)


class TestJiraReporter:
    """Test cases for JiraReporter class."""

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict(
            "os.environ",
            {
                "JIRA_BASE": "https://test.atlassian.net",
                "JIRA_USER": "test@example.com",
                "JIRA_TOKEN": "test-token",
            },
        ):
            reporter = JiraReporter(
                base_url=None,
                username=None,
                token=None,
                dry_run=True,
            )
            assert reporter.base_url == "https://test.atlassian.net"
            assert reporter.username == "test@example.com"
            assert reporter.token == "test-token"
            assert reporter.dry_run is True

    def test_init_with_parameters(self):
        """Test initialization with explicit parameters."""
        reporter = JiraReporter(
            base_url="https://custom.atlassian.net",
            username="custom@example.com",
            token="custom-token",
            dry_run=False,
        )
        assert reporter.base_url == "https://custom.atlassian.net"
        assert reporter.username == "custom@example.com"
        assert reporter.token == "custom-token"
        assert reporter.dry_run is False

    def test_init_missing_credentials_dry_run(self):
        """Test initialization with missing credentials in dry run mode."""
        # Should work in dry run mode even without credentials
        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )
        assert reporter.dry_run is True

    def test_init_missing_credentials_live_mode(self):
        """Test initialization with missing credentials in live mode."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Jira credentials must be provided"):
                JiraReporter(
                    base_url=None,
                    username=None,
                    token=None,
                    dry_run=False,
                )

    def test_format_test_result_comment_passed(self):
        """Test formatting of passed test result."""
        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login_flow",
            status="passed",
            duration_ms=1500,
            test_file="tests/test_login.py",
        )

        comment = reporter._format_test_result_comment(result)

        assert "✅ **Automated Test Result**" in comment
        assert "**Test:** test_login_flow" in comment
        assert "**Status:** PASSED" in comment
        assert "**Duration:** 1500ms" in comment
        assert "**Test File:** `tests/test_login.py`" in comment
        assert "Error Details" not in comment

    def test_format_test_result_comment_failed(self):
        """Test formatting of failed test result."""
        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login_flow",
            status="failed",
            duration_ms=2000,
            error_message="Element not found: #login-button",
            test_file="tests/test_login.py",
        )

        comment = reporter._format_test_result_comment(result)

        assert "❌ **Automated Test Result**" in comment
        assert "**Status:** FAILED" in comment
        assert "**Error Details:**" in comment
        assert "Element not found: #login-button" in comment

    def test_format_test_result_comment_skipped(self):
        """Test formatting of skipped test result."""
        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login_flow",
            status="skipped",
            duration_ms=0,
        )

        comment = reporter._format_test_result_comment(result)

        assert "⏭️ **Automated Test Result**" in comment
        assert "**Status:** SKIPPED" in comment

    def test_report_test_result_dry_run(self, caplog):
        """Test reporting test result in dry run mode."""
        import logging

        caplog.set_level(logging.INFO)

        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login_flow",
            status="passed",
            duration_ms=1500,
        )

        success = reporter.report_test_result(result)

        assert success is True
        assert "[DRY RUN] Would post to ABC-123:" in caplog.text

    @patch("src.integrations.jira_reporter.requests")
    def test_post_comment_to_ticket_success(self, mock_requests):
        """Test successful comment posting to Jira."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_requests.post.return_value = mock_response

        reporter = JiraReporter(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            token="test-token",
            dry_run=False,
        )

        success = reporter._post_comment_to_ticket("ABC-123", "Test comment")

        assert success is True
        mock_requests.post.assert_called_once()

        # Verify the call parameters
        call_args = mock_requests.post.call_args
        assert (
            call_args[0][0]
            == "https://test.atlassian.net/rest/api/2/issue/ABC-123/comment"
        )
        assert call_args[1]["auth"] == ("test@example.com", "test-token")
        assert call_args[1]["json"]["body"] == "Test comment"

    @patch("src.integrations.jira_reporter.requests")
    def test_post_comment_to_ticket_failure(self, mock_requests):
        """Test failed comment posting to Jira."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_requests.post.return_value = mock_response

        reporter = JiraReporter(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            token="test-token",
            dry_run=False,
        )

        success = reporter._post_comment_to_ticket("ABC-123", "Test comment")

        assert success is False

    @patch("src.integrations.jira_reporter.requests")
    def test_update_ticket_status_success(self, mock_requests):
        """Test successful ticket status update."""
        # Mock transitions response
        transitions_response = Mock()
        transitions_response.status_code = 200
        transitions_response.json.return_value = {
            "transitions": [
                {"id": "11", "name": "To Do"},
                {"id": "21", "name": "In Progress"},
                {"id": "31", "name": "Done"},
            ]
        }

        # Mock transition execution response
        transition_response = Mock()
        transition_response.status_code = 204

        mock_requests.get.return_value = transitions_response
        mock_requests.post.return_value = transition_response

        reporter = JiraReporter(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            token="test-token",
            dry_run=False,
        )

        success = reporter.update_ticket_status("ABC-123", "Done")

        assert success is True
        assert mock_requests.get.call_count == 1
        assert mock_requests.post.call_count == 1

    @patch("src.integrations.jira_reporter.requests")
    def test_update_ticket_status_transition_not_found(self, mock_requests):
        """Test ticket status update with invalid transition."""
        transitions_response = Mock()
        transitions_response.status_code = 200
        transitions_response.json.return_value = {
            "transitions": [
                {"id": "11", "name": "To Do"},
                {"id": "21", "name": "In Progress"},
            ]
        }

        mock_requests.get.return_value = transitions_response

        reporter = JiraReporter(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            token="test-token",
            dry_run=False,
        )

        success = reporter.update_ticket_status("ABC-123", "NonExistent")

        assert success is False

    def test_update_ticket_status_dry_run(self, caplog):
        """Test ticket status update in dry run mode."""
        import logging

        caplog.set_level(logging.INFO)

        reporter = JiraReporter(
            base_url="https://dummy.atlassian.net",
            username="dummy@example.com",
            token="dummy-token",
            dry_run=True,
        )

        success = reporter.update_ticket_status("ABC-123", "Done")

        assert success is True
        assert "[DRY RUN] Would transition ABC-123 to Done" in caplog.text


class TestJiraTestResult:
    """Test cases for JiraTestResult dataclass."""

    def test_test_result_creation(self):
        """Test JiraTestResult creation with required fields."""
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login",
            status="passed",
            duration_ms=1500,
        )

        assert result.ticket_id == "ABC-123"
        assert result.test_name == "test_login"
        assert result.status == "passed"
        assert result.duration_ms == 1500
        assert result.error_message is None
        assert result.test_file is None
        assert result.timestamp is not None

    def test_test_result_with_all_fields(self):
        """Test JiraTestResult creation with all fields."""
        timestamp = "2023-01-01T12:00:00"
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="test_login",
            status="failed",
            duration_ms=2000,
            error_message="Login failed",
            test_file="tests/test_login.py",
            timestamp=timestamp,
        )

        assert result.error_message == "Login failed"
        assert result.test_file == "tests/test_login.py"
        assert result.timestamp == timestamp


class TestReportFromPytestJson:
    """Test cases for pytest JSON reporting function."""

    def test_report_from_pytest_json_success(self, tmp_path):
        """Test reporting from pytest JSON output."""
        # Create mock pytest JSON output
        pytest_data = {
            "summary": {"total": 5, "passed": 4, "failed": 1, "skipped": 0},
            "duration": 12.5,
        }

        json_file = tmp_path / "pytest_output.json"
        with open(json_file, "w") as f:
            json.dump(pytest_data, f)

        with patch(
            "src.integrations.jira_reporter.JiraReporter"
        ) as mock_reporter_class:
            mock_reporter = Mock()
            mock_reporter.report_test_result.return_value = True
            mock_reporter_class.return_value = mock_reporter

            success = report_from_pytest_json(str(json_file), "ABC-123")

            assert success is True
            mock_reporter.report_test_result.assert_called_once()

            # Verify the reported result
            reported_result = mock_reporter.report_test_result.call_args[0][0]
            assert reported_result.ticket_id == "ABC-123"
            assert reported_result.status == "failed"  # Because there was 1 failure
            assert reported_result.duration_ms == 12500
            assert "Failed: 1, Passed: 4" in reported_result.error_message

    def test_report_from_pytest_json_all_passed(self, tmp_path):
        """Test reporting from pytest JSON output with all tests passing."""
        pytest_data = {
            "summary": {"total": 3, "passed": 3, "failed": 0, "skipped": 0},
            "duration": 8.2,
        }

        json_file = tmp_path / "pytest_output.json"
        with open(json_file, "w") as f:
            json.dump(pytest_data, f)

        with patch(
            "src.integrations.jira_reporter.JiraReporter"
        ) as mock_reporter_class:
            mock_reporter = Mock()
            mock_reporter.report_test_result.return_value = True
            mock_reporter_class.return_value = mock_reporter

            success = report_from_pytest_json(str(json_file), "ABC-123")

            assert success is True

            reported_result = mock_reporter.report_test_result.call_args[0][0]
            assert reported_result.status == "passed"
            assert reported_result.error_message is None

    def test_report_from_pytest_json_file_not_found(self):
        """Test reporting from non-existent pytest JSON file."""
        success = report_from_pytest_json("nonexistent.json", "ABC-123")
        assert success is False


class TestJiraIntegrationMocking:
    """Test the Jira integration with comprehensive mocking for CI."""

    @patch("src.integrations.jira_reporter.requests")
    def test_full_integration_workflow_mocked(self, mock_requests):
        """Test the complete workflow with mocked Jira responses."""
        # Mock successful responses for all Jira API calls
        comment_response = Mock()
        comment_response.status_code = 201

        transitions_response = Mock()
        transitions_response.status_code = 200
        transitions_response.json.return_value = {
            "transitions": [{"id": "31", "name": "Done"}]
        }

        transition_response = Mock()
        transition_response.status_code = 204

        # Configure mock to return different responses based on URL
        def mock_request_side_effect(url, **kwargs):
            if "transitions" in url and kwargs.get("json") is None:
                return transitions_response
            elif "transitions" in url and kwargs.get("json") is not None:
                return transition_response
            elif "comment" in url:
                return comment_response
            return Mock(status_code=404)

        mock_requests.get.return_value = transitions_response
        mock_requests.post.side_effect = mock_request_side_effect

        # Test the workflow
        reporter = JiraReporter(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            token="test-token",
            dry_run=False,
        )

        # Report test result
        result = JiraTestResult(
            ticket_id="ABC-123",
            test_name="Generated Acceptance Test",
            status="passed",
            duration_ms=1500,
        )

        comment_success = reporter.report_test_result(result)
        assert comment_success is True

        # Update ticket status
        status_success = reporter.update_ticket_status("ABC-123", "Done")
        assert status_success is True

        # Verify API calls were made
        assert mock_requests.get.call_count >= 1
        assert mock_requests.post.call_count >= 2
