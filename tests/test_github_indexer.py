"""
Comprehensive tests for the refactored GitHubIndexer class.

This test suite validates the class-based implementation maintains all functionality
from the original functional approach while adding better testability and encapsulation.
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.indexer.github_indexer import GitHubIndexer


class TestGitHubIndexerInitialization:
    """Test GitHubIndexer class initialization and configuration."""

    def test_init_with_all_params(self) -> None:
        """Test initialization with all parameters provided."""
        indexer = GitHubIndexer(
            repo_url="https://github.com/test/repo.git",
            branch="develop",
            clone_dir="/tmp/test",
            kb_path="/tmp/kb.json",
        )

        assert indexer.repo_url == "https://github.com/test/repo.git"
        assert indexer.branch == "develop"
        assert indexer.clone_dir == Path("/tmp/test")
        assert indexer.kb_path == Path("/tmp/kb.json")

    def test_init_with_minimal_params(self) -> None:
        """Test initialization with only required repo_url."""
        indexer = GitHubIndexer(repo_url="https://github.com/test/repo.git")

        assert indexer.repo_url == "https://github.com/test/repo.git"
        assert indexer.branch == "main"
        assert indexer.clone_dir == Path("./tmp_repo")
        assert indexer.kb_path == Path("knowledge_base_schema.json")

    @patch.dict(
        "os.environ",
        {
            "GITHUB_REPO_URL": "https://github.com/env/repo.git",
            "GITHUB_BRANCH": "env-branch",
            "GITHUB_CLONE_DIR": "/env/clone",
            "KB_PATH": "/env/kb.json",
        },
    )
    def test_init_with_env_vars(self) -> None:
        """Test initialization using environment variables."""
        indexer = GitHubIndexer()

        assert indexer.repo_url == "https://github.com/env/repo.git"
        assert indexer.branch == "env-branch"
        assert indexer.clone_dir == Path("/env/clone")
        assert indexer.kb_path == Path("/env/kb.json")

    def test_init_without_repo_url_raises_error(self) -> None:
        """Test that missing repo_url raises ValueError."""
        with pytest.raises(ValueError, match="Repository URL must be provided"):
            GitHubIndexer()


class TestElementNameGeneration:
    """Test the generate_element_name static method."""

    def test_id_selector_button(self) -> None:
        """Test ID selector that should be identified as button."""
        assert GitHubIndexer.generate_element_name("#submit") == "submit_button"
        assert GitHubIndexer.generate_element_name("#login-btn") == "login-btn_button"
        assert GitHubIndexer.generate_element_name("#click-me") == "click-me_button"

    def test_id_selector_field(self) -> None:
        """Test ID selector that should be identified as field."""
        assert (
            GitHubIndexer.generate_element_name("#username-input")
            == "username-input_field"
        )
        assert (
            GitHubIndexer.generate_element_name("#email-field") == "email-field_field"
        )
        assert GitHubIndexer.generate_element_name("#password") == "password_field"

    def test_id_selector_element(self) -> None:
        """Test ID selector that should be generic element."""
        assert GitHubIndexer.generate_element_name("#login") == "login_element"
        assert GitHubIndexer.generate_element_name("#username") == "username_element"

    def test_class_selector(self) -> None:
        """Test class selector generation."""
        assert (
            GitHubIndexer.generate_element_name(".btn-primary") == "btn_primary_button"
        )
        assert GitHubIndexer.generate_element_name(".nav-item") == "nav_item_element"

    def test_text_selector(self) -> None:
        """Test text selector generation."""
        assert (
            GitHubIndexer.generate_element_name("text=Welcome User")
            == "welcome_user_text"
        )
        assert GitHubIndexer.generate_element_name("text=Sign-In") == "sign_in_text"

    def test_attribute_selector(self) -> None:
        """Test attribute selector generation."""
        assert (
            GitHubIndexer.generate_element_name('[data-testid="submit"]')
            == "submit_element"
        )
        assert (
            GitHubIndexer.generate_element_name('[name="username"]')
            == "username_element"
        )

    def test_tag_selector(self) -> None:
        """Test tag selector generation."""
        assert GitHubIndexer.generate_element_name("button") == "button_element"
        assert GitHubIndexer.generate_element_name("input") == "input_element"


class TestSelectorExtraction:
    """Test the extract_selectors static method."""

    def test_extract_id_selectors(self) -> None:
        """Test extraction of ID selectors from content."""
        content = """
        page.click("#login")
        page.fill("#username", "test")
        """
        selectors = GitHubIndexer.extract_selectors(content)

        expected = [
            {"element": "login_element", "selector": "#login"},
            {"element": "username_element", "selector": "#username"},
        ]
        assert selectors == expected

    def test_extract_class_selectors(self) -> None:
        """Test extraction of class selectors from content."""
        content = """
        page.click(".btn-primary")
        page.wait_for_selector(".loading")
        """
        selectors = GitHubIndexer.extract_selectors(content)

        expected = [
            {"element": "btn_primary_button", "selector": ".btn-primary"},
            {"element": "loading_element", "selector": ".loading"},
        ]
        assert selectors == expected

    def test_extract_mixed_selectors(self) -> None:
        """Test extraction of mixed selector types."""
        content = """
        page.click("#submit")
        page.fill(".username-input", "test")
        page.click("text=Sign In")
        page.click("button")
        """
        selectors = GitHubIndexer.extract_selectors(content)

        assert len(selectors) == 4
        assert any(s["selector"] == "#submit" for s in selectors)
        assert any(s["selector"] == ".username-input" for s in selectors)
        assert any(s["selector"] == "text=Sign In" for s in selectors)
        assert any(s["selector"] == "button" for s in selectors)

    def test_no_duplicate_selectors(self) -> None:
        """Test that duplicate selectors are not added."""
        content = """
        page.click("#login")
        page.click("#login")
        page.fill("#login", "test")
        """
        selectors = GitHubIndexer.extract_selectors(content)

        # Should only have one entry for #login
        login_selectors = [s for s in selectors if s["selector"] == "#login"]
        assert len(login_selectors) == 1


class TestPageActionParsing:
    """Test the parse_page_action static method."""

    def test_parse_click_action(self) -> None:
        """Test parsing of click actions."""
        action = GitHubIndexer.parse_page_action('page.click("#submit")')
        expected = {"action": "click", "target": "submit_button"}
        assert action == expected

    def test_parse_fill_action(self) -> None:
        """Test parsing of fill actions."""
        action = GitHubIndexer.parse_page_action('page.fill("#username", "testuser")')
        expected = {
            "action": "fill",
            "target": "username_element",
            "value": "{username}",
        }
        assert action == expected

    def test_parse_fill_action_with_email(self) -> None:
        """Test parsing of fill actions with email values."""
        action = GitHubIndexer.parse_page_action(
            'page.fill("#email", "test@example.com")'
        )
        expected = {"action": "fill", "target": "email_field", "value": "{email}"}
        assert action == expected

    def test_parse_goto_action(self) -> None:
        """Test parsing of goto actions."""
        action = GitHubIndexer.parse_page_action('page.goto("https://example.com")')
        expected = {"action": "goto", "target": "page", "value": "{base_url}"}
        assert action == expected

    def test_parse_wait_action(self) -> None:
        """Test parsing of wait_for_selector actions."""
        action = GitHubIndexer.parse_page_action('page.wait_for_selector("#loading")')
        expected = {"action": "wait_for_selector", "target": "loading_element"}
        assert action == expected

    def test_parse_expect_action(self) -> None:
        """Test parsing of expect actions."""
        action = GitHubIndexer.parse_page_action(
            'page.expect.to_be_visible("#welcome")'
        )
        expected = {"action": "assert_visible", "target": "welcome_element"}
        assert action == expected

    def test_parse_unknown_action(self) -> None:
        """Test parsing of unrecognized actions."""
        action = GitHubIndexer.parse_page_action("page.custom_action()")
        expected = {"action": "raw", "target": "page.custom_action()"}
        assert action == expected


class TestGitOperations:
    """Test git-related operations."""

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_shallow_clone_new_repo(self, mock_exists: Any, mock_run: Any) -> None:
        """Test cloning a new repository."""
        indexer = GitHubIndexer(repo_url="https://github.com/test/repo.git")
        mock_exists.return_value = False

        indexer.shallow_clone_or_update()

        # Should call git clone
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "git"
        assert call_args[1] == "clone"
        assert "https://github.com/test/repo.git" in call_args

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_shallow_clone_update_existing(
        self, mock_exists: Any, mock_run: Any
    ) -> None:
        """Test updating an existing repository."""
        indexer = GitHubIndexer(repo_url="https://github.com/test/repo.git")
        mock_exists.return_value = True

        indexer.shallow_clone_or_update()

        # Should call git fetch and reset
        assert mock_run.call_count == 2
        fetch_call = mock_run.call_args_list[0][0][0]
        reset_call = mock_run.call_args_list[1][0][0]

        assert "fetch" in fetch_call
        assert "reset" in reset_call


class TestKnowledgeBaseUpdate:
    """Test knowledge base update functionality."""

    def test_update_kb_new_file(self) -> None:
        """Test updating knowledge base when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "test_kb.json"
            indexer = GitHubIndexer(
                repo_url="https://github.com/test/repo.git", kb_path=str(kb_path)
            )

            selectors = [{"element": "login_button", "selector": "#login"}]
            flows = [
                {
                    "file": "test_login.py",
                    "steps": [{"action": "click", "target": "login_button"}],
                }
            ]

            indexer.update_kb(selectors, flows)

            # Verify file was created and contains expected data
            assert kb_path.exists()
            with open(kb_path) as f:
                kb_data = json.load(f)

            assert len(kb_data["page_objects"]) == 1
            assert len(kb_data["page_objects"][0]["selectors"]) == 1
            assert len(kb_data["test_flows"]) == 1

    def test_update_kb_existing_file(self) -> None:
        """Test updating knowledge base when file already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "test_kb.json"

            # Create existing KB file
            existing_kb = {
                "page_objects": [
                    {
                        "id": "page_auto",
                        "name": "AutoIndexed",
                        "selectors": [
                            {"element": "existing_button", "selector": "#existing"}
                        ],
                    }
                ],
                "test_flows": [],
                "test_data": [],
            }
            with open(kb_path, "w") as f:
                json.dump(existing_kb, f)

            indexer = GitHubIndexer(
                repo_url="https://github.com/test/repo.git", kb_path=str(kb_path)
            )

            new_selectors = [{"element": "login_button", "selector": "#login"}]
            new_flows: Any = []

            indexer.update_kb(new_selectors, new_flows)

            # Verify existing data is preserved and new data is added
            with open(kb_path) as f:
                kb_data = json.load(f)

            assert len(kb_data["page_objects"][0]["selectors"]) == 2
            existing_selectors = [
                s["selector"] for s in kb_data["page_objects"][0]["selectors"]
            ]
            assert "#existing" in existing_selectors
            assert "#login" in existing_selectors

    def test_update_kb_no_duplicates(self) -> None:
        """Test that duplicate selectors are not added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "test_kb.json"

            # Create existing KB file with a selector
            existing_kb = {
                "page_objects": [
                    {
                        "id": "page_auto",
                        "name": "AutoIndexed",
                        "selectors": [
                            {"element": "login_button", "selector": "#login"}
                        ],
                    }
                ],
                "test_flows": [],
                "test_data": [],
            }
            with open(kb_path, "w") as f:
                json.dump(existing_kb, f)

            indexer = GitHubIndexer(
                repo_url="https://github.com/test/repo.git", kb_path=str(kb_path)
            )

            # Try to add the same selector again
            duplicate_selectors = [{"element": "login_button", "selector": "#login"}]
            indexer.update_kb(duplicate_selectors, [])

            # Verify no duplicate was added
            with open(kb_path) as f:
                kb_data = json.load(f)

            assert len(kb_data["page_objects"][0]["selectors"]) == 1


class TestIntegration:
    """Integration tests for the complete indexing process."""

    @patch("subprocess.run")
    def test_run_complete_process(self, mock_run: Any) -> None:
        """Test the complete run() method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_dir = Path(tmpdir) / "clone"
            kb_path = Path(tmpdir) / "kb.json"

            # Create actual test directory and files so exists() works naturally
            test_dir = clone_dir / "src" / "tests"
            test_dir.mkdir(parents=True)

            test_file = test_dir / "test_login.py"
            test_file.write_text(
                """
def test_login():
    page.goto("https://example.com")
    page.fill("#username", "testuser")
    page.fill("#password", "secret")
    page.click("#submit")
    page.wait_for_selector("#welcome")
            """
            )

            indexer = GitHubIndexer(
                repo_url="https://github.com/test/repo.git",
                clone_dir=str(clone_dir),
                kb_path=str(kb_path),
            )

            # Run the indexer - clone_dir already exists from setup above
            indexer.run()

            # Verify knowledge base was created and populated
            assert kb_path.exists()
            with open(kb_path) as f:
                kb_data = json.load(f)

            # Should have extracted selectors and flows
            assert len(kb_data["page_objects"]) > 0
            assert len(kb_data["page_objects"][0]["selectors"]) > 0
            assert len(kb_data["test_flows"]) > 0

            # Verify specific extractions
            selectors = kb_data["page_objects"][0]["selectors"]
            selector_values = [s["selector"] for s in selectors]
            assert "#username" in selector_values
            assert "#password" in selector_values
            assert "#submit" in selector_values
            assert "#welcome" in selector_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
