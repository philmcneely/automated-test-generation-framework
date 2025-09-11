import json
import os
import re
import subprocess
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
        subprocess.run(
            ["git", "-C", str(CLONE_DIR), "fetch", "--depth=1", "origin", BRANCH],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(CLONE_DIR), "reset", "--hard", "FETCH_HEAD"], check=True
        )
    else:
        subprocess.run(
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
