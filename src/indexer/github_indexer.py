"""
GitHub Repository Indexer - Knowledge Base Automation

This module provides automated extraction and indexing of test patterns from
GitHub repositories to continuously update the knowledge base with real-world
selectors and test flows. It performs shallow cloning, content analysis,
and knowledge base updates to improve test generation accuracy.

    Features:
        - Clone GitHub repositories for test analysis
        - Extract Playwright selectors from test files
        - Scan examples directory for Python test files
        - Parse page actions and element interactions

Environment Variables:
    GITHUB_REPO_URL: Target GitHub repository URL for indexing
    GITHUB_BRANCH: Repository branch to index (default: main)
    GITHUB_CLONE_DIR: Local directory for repository cloning (default: ./tmp_repo)
    KB_PATH: Knowledge base file path (default: knowledge_base_schema.json)

Usage Examples:
    # Index with environment variables
    export GITHUB_REPO_URL="https://github.com/user/repo.git"
    python src/indexer/github_indexer.py

    # Index specific branch
    GITHUB_BRANCH=develop python src/indexer/github_indexer.py

Indexing Process:
    - Shallow clone or update target repository
    - Scan src/tests directory for Python test files
    - Extract selectors using regex patterns (#id, .class, text=value)
    - Identify page.* action patterns as test flows
    - Update knowledge base with new selectors and flows
    - Maintain existing data while adding discoveries

Knowledge Base Integration:
    - Adds new selectors to page_objects array
    - Creates test_flows from discovered action sequences
    - Preserves existing knowledge base structure
    - Provides incremental updates without duplication

Dependencies:
    - json: Knowledge base file operations
    - os: Environment variable access
    - re: Selector pattern matching
    - subprocess: Git operations for repository management
    - pathlib: File system path operations
    - typing: Type annotations for better code clarity

Author: PMAC
Date: 2025-09-11
"""

import json
import os
import re
import subprocess  # nosec B404 # Safe usage: controlled git commands only
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class GitHubIndexer:
    """
    GitHub Repository Indexer for automated knowledge base updates.

    This class provides automated extraction and indexing of test patterns from
    GitHub repositories to continuously update the knowledge base with real-world
    selectors and test flows.
    """

    def __init__(
        self,
        repo_url: Optional[str] = None,
        branch: str = "main",
        clone_dir: Optional[str] = None,
        kb_path: Optional[str] = None,
    ) -> None:
        """
        Initialize the GitHub indexer with configuration.

        Args:
            repo_url: GitHub repository URL (defaults to GITHUB_REPO_URL env var)
            branch: Repository branch to index (defaults to GITHUB_BRANCH env var or "main")
            clone_dir: Local directory for cloning (defaults to GITHUB_CLONE_DIR env var or "./tmp_repo")
            kb_path: Knowledge base file path (defaults to KB_PATH env var or "knowledge_base_schema.json")
        """
        self.repo_url = repo_url or os.getenv("GITHUB_REPO_URL")
        self.branch = (
            branch if branch != "main" else (os.getenv("GITHUB_BRANCH") or "main")
        )

        if not self.repo_url:
            raise ValueError(
                "Repository URL must be provided via repo_url parameter or GITHUB_REPO_URL environment variable"
            )

        clone_dir_path = clone_dir or os.getenv("GITHUB_CLONE_DIR") or "./tmp_repo"
        kb_path_str = kb_path or os.getenv("KB_PATH") or "knowledge_base_schema.json"

        self.clone_dir = Path(clone_dir_path)
        self.kb_path = Path(kb_path_str)

    def shallow_clone_or_update(self) -> None:
        """Clone repository or update existing clone with latest changes."""
        if self.clone_dir.exists():
            subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
                [
                    "git",
                    "-C",
                    str(self.clone_dir),
                    "fetch",
                    "--depth=1",
                    "origin",
                    self.branch,
                ],
                check=True,
            )
            subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
                ["git", "-C", str(self.clone_dir), "reset", "--hard", "FETCH_HEAD"],
                check=True,
            )
        else:
            subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    self.branch,
                    self.repo_url,  # type: ignore # Already validated in __init__
                    str(self.clone_dir),
                ],
                check=True,
            )

    @staticmethod
    def generate_element_name(selector: str) -> str:
        """Generate meaningful element name from selector"""
        # Remove quotes and clean up selector
        clean_selector = selector.strip("'\"")

        if clean_selector.startswith("#"):
            # ID selector: #login -> login_button/login_field based on context
            base_name = clean_selector[1:]
            if any(
                word in base_name.lower()
                for word in ["btn", "button", "submit", "click"]
            ):
                return f"{base_name}_button"
            elif any(
                word in base_name.lower()
                for word in ["input", "field", "text", "email", "password"]
            ):
                return f"{base_name}_field"
            else:
                return f"{base_name}_element"

        elif clean_selector.startswith("."):
            # Class selector: .btn-primary -> btn_primary_button
            base_name = clean_selector[1:].replace("-", "_").replace(" ", "_")
            if "btn" in base_name.lower() or "button" in base_name.lower():
                return f"{base_name}_button"
            else:
                return f"{base_name}_element"

        elif clean_selector.startswith("text="):
            # Text selector: text=Welcome -> welcome_text
            text_content = (
                clean_selector[5:].lower().replace(" ", "_").replace("-", "_")
            )
            return f"{text_content}_text"

        elif "[" in clean_selector:
            # Attribute selector: [data-testid="submit"] -> submit_element
            import re

            match = re.search(r'\[.*?[=~]\s*["\']([^"\']+)["\']', clean_selector)
            if match:
                attr_value = match.group(1).replace("-", "_").replace(" ", "_")
                return f"{attr_value}_element"
            else:
                return "unknown_element"

        else:
            # Tag selector or other: button -> button_element
            return f"{clean_selector.replace('-', '_')}_element"

    @staticmethod
    def extract_selectors(content: str) -> List[Dict[str, str]]:
        """Extract and structure selectors from test content"""
        selectors = []

        # Improved regex patterns for different selector types
        patterns = [
            r'["\']#[\w\-_]+["\']',  # ID selectors: "#login", '#submit'
            r'["\']\.[\w\-_]+["\']',  # Class selectors: ".btn-primary"
            r'["\']text=[\w\s\-_]+["\']',  # Text selectors: "text=Welcome"
            r'["\']button["\']',  # Tag selectors: "button"
            r'["\']input["\']',  # Input tags: "input"
            r'["\']a["\']',  # Link tags: "a"
            r'["\']\[[\w\-_=\s"\']+\]["\']',  # Attribute selectors: "[data-testid='submit']"
        ]

        found_selectors = set()
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                clean_match = match.strip("'\"")
                if clean_match and clean_match not in found_selectors:
                    found_selectors.add(clean_match)
                    element_name = GitHubIndexer.generate_element_name(clean_match)
                    selectors.append({"element": element_name, "selector": clean_match})

        return selectors

    @staticmethod
    def parse_page_action(action_line: str) -> Dict[str, Any]:
        """Parse page.action() calls into structured action objects"""
        action_line = action_line.strip()

        # Extract action type and parameters using regex
        click_match = re.match(r'page\.click\(["\']([^"\']+)["\']\)', action_line)
        if click_match:
            selector = click_match.group(1)
            element_name = GitHubIndexer.generate_element_name(selector)
            return {"action": "click", "target": element_name}

        fill_match = re.match(
            r'page\.fill\(["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']', action_line
        )
        if fill_match:
            selector = fill_match.group(1)
            value = fill_match.group(2)
            element_name = GitHubIndexer.generate_element_name(selector)

            # Parameterize common values - check email first
            if "@" in value:
                param_value = "{email}"
            elif value.lower() in ["user1", "testuser", "admin"]:
                param_value = "{username}"
            elif value.lower() in ["password", "pass123", "secret", "test123"]:
                param_value = "{password}"
            else:
                param_value = f"{{{value.lower()}}}"

            return {"action": "fill", "target": element_name, "value": param_value}

        goto_match = re.match(r'page\.goto\(["\']([^"\']+)["\']', action_line)
        if goto_match:
            url = goto_match.group(1)
            return {
                "action": "goto",
                "target": "page",
                "value": "{base_url}" if url.startswith("http") else url,
            }

        wait_match = re.match(
            r'page\.wait_for_selector\(["\']([^"\']+)["\']', action_line
        )
        if wait_match:
            selector = wait_match.group(1)
            element_name = GitHubIndexer.generate_element_name(selector)
            return {"action": "wait_for_selector", "target": element_name}

        expect_match = re.match(r'page\.expect.*?["\']([^"\']+)["\']', action_line)
        if expect_match:
            selector = expect_match.group(1)
            element_name = GitHubIndexer.generate_element_name(selector)
            return {"action": "assert_visible", "target": element_name}

        # Fallback for unrecognized actions
        return {"action": "raw", "target": action_line}

    def extract_tests(self) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Extract selectors and test flows from cloned repository."""
        test_dir: Path = self.clone_dir / "src" / "tests"
        all_selectors: List[Dict[str, str]] = []
        flows: List[Dict[str, Any]] = []

        if not test_dir.exists():
            return [], []

        for path in test_dir.rglob("*.py"):
            content: str = path.read_text(errors="ignore")

            # Extract selectors using improved parsing
            file_selectors = self.extract_selectors(content)
            all_selectors.extend(file_selectors)

            # Extract and parse page actions
            action_lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("page.")
            ]

            if action_lines:
                parsed_steps = []
                for action_line in action_lines:
                    parsed_action = self.parse_page_action(action_line)
                    parsed_steps.append(parsed_action)

                if parsed_steps:
                    flows.append(
                        {"file": str(path.relative_to(test_dir)), "steps": parsed_steps}
                    )

        return all_selectors, flows

    def update_kb(
        self, new_selectors: List[Dict[str, str]], new_flows: List[Dict[str, Any]]
    ) -> None:
        """Update knowledge base with new selectors and flows."""
        kb: Dict[str, Any] = {"page_objects": [], "test_flows": [], "test_data": []}
        if self.kb_path.exists():
            with open(self.kb_path, "r") as f:
                kb = json.load(f)

        # Ensure we have a page object to add selectors to
        if not kb["page_objects"]:
            kb["page_objects"].append(
                {"id": "page_auto", "name": "AutoIndexed", "selectors": []}
            )

        # Get existing selectors to avoid duplicates
        existing_selectors = {s["selector"] for s in kb["page_objects"][0]["selectors"]}

        # Add new selectors with proper element names
        new_selector_count = 0
        for selector_obj in new_selectors:
            if selector_obj["selector"] not in existing_selectors:
                kb["page_objects"][0]["selectors"].append(selector_obj)
                existing_selectors.add(selector_obj["selector"])
                new_selector_count += 1

        # Add new test flows with structured actions
        new_flow_count = 0
        for flow in new_flows:
            # Generate unique flow ID
            flow_id = f"flow_indexed_{len(kb['test_flows']) + 1}"

            # Create structured flow object
            kb["test_flows"].append(
                {
                    "id": flow_id,
                    "name": f"IndexedFlow_{flow['file'].replace('/', '_').replace('.py', '')}",
                    "steps": flow["steps"],
                }
            )
            new_flow_count += 1

        # Save updated knowledge base
        with open(self.kb_path, "w") as f:
            json.dump(kb, f, indent=2)

        print(f"KB updated at {self.kb_path}")
        print(
            f"Added {new_selector_count} new selectors and {new_flow_count} new flows"
        )

    def run(self) -> None:
        """Run the complete indexing process."""
        self.shallow_clone_or_update()
        selectors, flows = self.extract_tests()
        self.update_kb(selectors, flows)


def main() -> None:
    """Main entry point for command-line usage."""
    indexer = GitHubIndexer()
    indexer.run()


if __name__ == "__main__":
    main()
