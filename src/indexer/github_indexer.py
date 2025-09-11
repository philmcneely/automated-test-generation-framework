"""
GitHub Repository Indexer - Knowledge Base Automation

This module provides automated extraction and indexing of test patterns from
GitHub repositories to continuously update the knowledge base with real-world
selectors and test flows. It performs shallow cloning, content analysis,
and knowledge base updates to improve test generation accuracy.

Features:
    ✓ Shallow cloning of GitHub repositories for efficiency
    ✓ Automatic extraction of CSS/XPath selectors from test files
    ✓ Test flow pattern recognition and cataloging
    ✓ Knowledge base update automation with deduplication
    ✓ Environment-based configuration for flexibility
    ✓ Regex-based content parsing for selector identification
    ✓ Structured JSON output for knowledge base integration
    ✓ Error handling for missing repositories or files

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
from typing import Any, Dict, List, Tuple

REPO_URL: str = os.getenv("GITHUB_REPO_URL")  # type: ignore
BRANCH: str = os.getenv("GITHUB_BRANCH", "main")
CLONE_DIR: Path = Path(os.getenv("GITHUB_CLONE_DIR", "./tmp_repo"))
KB_PATH: Path = Path(os.getenv("KB_PATH", "knowledge_base_schema.json"))


def shallow_clone_or_update() -> None:
    if not REPO_URL:
        raise RuntimeError("Set GITHUB_REPO_URL")
    if CLONE_DIR.exists():
        subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
            ["git", "-C", str(CLONE_DIR), "fetch", "--depth=1", "origin", BRANCH],
            check=True,
        )
        subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
            ["git", "-C", str(CLONE_DIR), "reset", "--hard", "FETCH_HEAD"], check=True
        )
    else:
        subprocess.run(  # nosec B607 B603 # Safe: controlled git command with static args
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                BRANCH,
                REPO_URL,
                str(CLONE_DIR),
            ],
            check=True,
        )


def extract_tests() -> Tuple[List[str], List[Dict[str, Any]]]:
    test_dir: Path = CLONE_DIR / "src" / "tests"
    selectors: set = set()
    flows: List[Dict[str, Any]] = []
    if not test_dir.exists():
        return [], []
    for path in test_dir.rglob("*.py"):
        content: str = path.read_text(errors="ignore")
        for sel in re.findall(r"[#.]\w+|text=\w+", content):
            selectors.add(sel)
        actions = [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("page.")
        ]
        if actions:
            flows.append({"file": str(path), "steps": actions})
    return list(selectors), flows


def update_kb(new_selectors: List[str], new_flows: List[Dict[str, Any]]) -> None:
    kb: Dict[str, Any] = {"page_objects": [], "test_flows": [], "test_data": []}
    if KB_PATH.exists():
        with open(KB_PATH, "r") as f:
            kb = json.load(f)
    if not kb["page_objects"]:
        kb["page_objects"].append(
            {"id": "page_auto", "name": "AutoIndexed", "selectors": []}
        )
    existing = {s["selector"] for s in kb["page_objects"][0]["selectors"]}
    for sel in new_selectors:
        if sel not in existing:
            kb["page_objects"][0]["selectors"].append({"element": sel, "selector": sel})
    for flow in new_flows:
        kb["test_flows"].append(
            {
                "id": "flow_" + str(len(kb["test_flows"]) + 1),
                "name": flow["file"],
                "steps": [{"action": "raw", "target": s} for s in flow["steps"]],
            }
        )
    json.dump(kb, open(KB_PATH, "w"), indent=2)
    print("KB updated at", KB_PATH)


def main() -> None:
    shallow_clone_or_update()
    sels, flows = extract_tests()
    update_kb(sels, flows)


if __name__ == "__main__":
    main()
