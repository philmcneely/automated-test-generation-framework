# Automated Test Generation Ecosystem Specification (with Code Samples)

## Overview
End-to-end system that reads Jira acceptance criteria, generates Playwright tests automatically, runs them in CI/CD, and feeds results back to Jira/PRs while updating a structured knowledge base.

## Architecture
- Jira REST API → Ticket poller/webhook
- Agent Orchestrator (LangChain or custom) → parsing, codegen, KB updates
- Knowledge Base → selectors, flows, data
- Test Runner → Playwright + Pytest (swappable)
- CI/CD → GitHub Actions example
- Feedback → Jira or PR comments

## Key Flows
1. Poll Jira → Parse acceptance criteria → Normalize test cases
2. Generate tests using knowledge base + agent
3. Run tests in CI → Collect artifacts
4. Post results → Update knowledge base (selectors, flows)

## Code Samples

### Jira Poller (Python)
```python
import os
import time
import requests
from typing import List, Dict

JIRA_BASE = os.getenv('JIRA_BASE')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
JQL = os.getenv('JIRA_JQL', 'project = ABC AND status in ("To Do", "In Progress")')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '60'))
headers = {'Accept': 'application/json'}

def fetch_tickets() -> List[Dict]:
    if not JIRA_BASE or not JIRA_USER or not JIRA_TOKEN:
        raise RuntimeError('Missing Jira configuration env vars')
    url = f"{JIRA_BASE}/rest/api/3/search"
    r = requests.get(url, headers=headers, params={'jql': JQL, 'maxResults': 50}, auth=(JIRA_USER, JIRA_TOKEN), timeout=30)
    r.raise_for_status()
    return r.json().get('issues', [])

if __name__ == '__main__':
    while True:
        issues = fetch_tickets()
        print(f"Fetched {len(issues)} issues")
        time.sleep(POLL_INTERVAL)
```

### Playwright Test (Pytest)
```python
import os
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv('APP_BASE_URL', 'https://example.com')

@pytest.mark.e2e
def test_login_happy_path():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)
        page.click('#login')
        page.fill('#username', 'user1')
        page.fill('#password', 'pass123')
        page.click('#submit')
        page.wait_for_selector('text=Welcome')
        browser.close()
```

### Knowledge Base Schema (excerpt)
```json
{
  "page_objects": [{"id":"page_home","name":"HomePage","selectors":[
    {"element":"login_button","selector":"#login"},
    {"element":"username_field","selector":"#username"},
    {"element":"password_field","selector":"#password"},
    {"element":"submit_button","selector":"#submit"}
  ]}],
  "test_flows": [{"id":"flow_login","name":"LoginFlow","steps":[
    {"action":"click","target":"login_button"},
    {"action":"fill","target":"username_field","value":"{username}"},
    {"action":"fill","target":"password_field","value":"{password}"},
    {"action":"click","target":"submit_button"}
  ]}]
}
```

### GitHub Actions (tests)
```yaml
name: Automated Tests
on:
  push:
    branches: [ main ]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install deps
        run: |
          pip install -r requirements.txt
          python -m playwright install --with-deps
      - name: Run tests
        run: pytest -q
```

### Docker
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.45.0-focal
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["pytest","-q"]
```

### docker-compose
```yaml
version: '3.8'
services:
  agent:
    build: .
    environment:
      - JIRA_BASE=${JIRA_BASE}
      - JIRA_USER=${JIRA_USER}
      - JIRA_TOKEN=${JIRA_TOKEN}
      - APP_BASE_URL=${APP_BASE_URL}
    command: python src/poller/jira_poller.py
```
