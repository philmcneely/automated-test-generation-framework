# Product CI Integration Guide

This guide shows how to integrate the automated test generation framework into your product's CI pipeline with Jira result reporting.

## 🚨 Framework Assumptions & Requirements

### Language & Runtime Requirements
- **Primary Language**: Python 3.10+ (framework is Python-based)
- **Test Framework**: pytest (required for test execution)
- **Browser Automation**: Playwright (Python version)
- **Generated Tests**: Python/pytest format only

### Test Framework Assumptions
This framework is **specifically designed for the playwright-ai-framework** and makes several assumptions:

#### ✅ Compatible Frameworks
- **playwright-ai-framework** (primary target - full compatibility)
- **Standard Playwright + pytest** (basic compatibility)
- **Python-based Page Object Model** frameworks

#### ❌ Currently NOT Compatible With
- **JavaScript/TypeScript** test frameworks (Cypress, WebdriverIO, etc.)
- **Java** test frameworks (Selenium, TestNG, etc.)
- **C#** test frameworks (SpecFlow, NUnit, etc.)
- **Non-pytest** Python frameworks (unittest, nose, etc.)
- **Non-Page Object Model** architectures

### Generated Test Structure
The framework generates tests in this specific format:
```python
# Generated test structure (Python only)
import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
@pytest.mark.generated
async def test_login_happy_path(page, app):
    await app.home_page.navigate()           # Page Object Model
    await app.home_page.click_login()        # Assumes POM methods
    await app.home_page.enter_username('user')
    await expect(page.locator('text=Welcome')).to_be_visible()
```

### Knowledge Base Requirements
- **Source Repository**: Must contain Python Playwright test files
- **Selector Patterns**: Framework extracts from `page.click()`, `page.fill()`, etc.
- **File Extensions**: Looks for `.py` files in test directories
- **Page Object Pattern**: Expects `app.page_name.method_name()` structure

## 🔧 Adapting to Other Frameworks

If you're using a different test framework, you have several options:

### Option 1: Adapt Your Framework
Modify your existing framework to match the expected patterns:
- Use Page Object Model architecture
- Use pytest as test runner
- Structure methods as `app.page.action()` format

### Option 2: Custom Template Modification (Advanced)
Modify the code generation templates in `src/agent/agent_runner_pom.py`:
- Change import statements for your framework
- Modify action templates (click, fill, etc.)
- Update assertion patterns
- Adjust test structure format

### Option 3: Translation Layer
Create a translation layer that converts generated Python tests to your target language:
- Generate Python tests as intermediate format
- Parse and convert to JavaScript/TypeScript/Java/etc.
- Maintain action mappings between frameworks

### Option 4: LLM Integration (Future)
The framework includes sophisticated LLM integration capabilities that could:
- Generate tests in any language/framework
- Adapt to different coding patterns
- Handle more complex scenarios

## 🎯 Integration Examples

Below are examples assuming you're using **Python + Playwright + pytest**. For other frameworks, apply the adaptation strategies above.

## Example: Product CI Integration with Test Result Reporting

## 1. GitHub Actions Workflow for Product CI

```yaml
# .github/workflows/product-ci.yml
name: Product CI with Automated Test Generation

on:
  push:
    branches: [ main, develop ]
  pull_request:

jobs:
  automated-acceptance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Set up the test generation framework
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install test framework
        run: |
          pip install -r requirements.txt
          python -m playwright install --with-deps

      # Generate fresh knowledge base from your test repository
      - name: Generate Knowledge Base
        env:
          GITHUB_REPO_URL: https://github.com/your-org/your-test-repository.git
          GITHUB_BRANCH: main
        run: |
          python -m src.indexer.github_indexer

      # Generate test from Jira ticket (you'd have this in your repo)
      - name: Generate Acceptance Test
        run: |
          python -m src.agent.agent_runner_pom \
            --ticket acceptance_criteria/ABC-123.json \
            --kb knowledge_base_schema.json \
            --output tests/generated/test_acceptance_ABC_123.py

      # Run the generated test against your application
      - name: Run Generated Test
        id: test_execution
        env:
          APP_BASE_URL: ${{ secrets.APP_BASE_URL }}
        run: |
          pytest tests/generated/test_acceptance_ABC_123.py \
            --json-report --json-report-file=test_results.json \
            --continue-on-collection-errors

      # Report results back to Jira (on success or failure)
      - name: Report to Jira
        if: always()
        env:
          JIRA_BASE: ${{ secrets.JIRA_BASE }}
          JIRA_USER: ${{ secrets.JIRA_USER }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
        run: |
          python -m src.integrations.jira_reporter \
            ABC-123 \
            ${{ steps.test_execution.outcome }} \
            "See GitHub Actions run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

      # Optional: Update Jira ticket status based on test result
      - name: Update Jira Status
        if: steps.test_execution.outcome == 'success'
        env:
          JIRA_BASE: ${{ secrets.JIRA_BASE }}
          JIRA_USER: ${{ secrets.JIRA_USER }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
        run: |
          python -c "
          from src.integrations.jira_reporter import JiraReporter
          reporter = JiraReporter()
          reporter.update_ticket_status('ABC-123', 'Ready for Review')
          "
```

## 2. Jira Ticket JSON Format

```json
// acceptance_criteria/ABC-123.json
{
  "id": "ABC-123",
  "title": "User can login with valid credentials",
  "description": "As a user, I want to login with my credentials so that I can access my account",
  "acceptance_criteria": [
    {
      "action": "goto",
      "target": "login_page"
    },
    {
      "action": "fill",
      "target": "username_field",
      "value": "testuser@example.com"
    },
    {
      "action": "fill",
      "target": "password_field",
      "value": "SecurePass123"
    },
    {
      "action": "click",
      "target": "login_button"
    },
    {
      "action": "assert_text",
      "value": "Welcome to Dashboard"
    }
  ]
}
```

## 3. Example Jira Comments Generated

### ✅ Successful Test
```
✅ **Automated Test Result**

**Test:** Generated Acceptance Test (1 tests)
**Status:** PASSED
**Duration:** 2,450ms
**Timestamp:** 2023-12-01T10:30:45.123Z
**Test File:** `tests/generated/test_acceptance_ABC_123.py`

_This comment was automatically generated by the test automation framework._
```

### ❌ Failed Test
```
❌ **Automated Test Result**

**Test:** Generated Acceptance Test (1 tests)
**Status:** FAILED
**Duration:** 1,200ms
**Timestamp:** 2023-12-01T10:30:45.123Z
**Test File:** `tests/generated/test_acceptance_ABC_123.py`

**Error Details:**
```
TimeoutError: Locator.click: Timeout 30000ms exceeded.
=========================== Locator.click ===========================
Target: button#login-submit
  - waiting for locator to be visible
  - locator resolved to <button id="login-submit" disabled="">Login</button>
  - attempting click action
  - waiting for element to be enabled
```

See GitHub Actions run: https://github.com/your-org/your-app/actions/runs/123456789

_This comment was automatically generated by the test automation framework._
```

## 4. Benefits

✅ **Immediate Feedback**: Developers see test results directly in Jira tickets
✅ **Traceability**: Links from Jira to CI logs for debugging
✅ **Automation**: No manual testing needed for basic acceptance criteria
✅ **Status Updates**: Tickets automatically move through workflow states
✅ **History**: Complete audit trail of all test executions
✅ **Fresh Data**: Knowledge base generated fresh each run (~2 seconds)

## 5. Local Development Usage

```bash
# Generate knowledge base locally
export GITHUB_REPO_URL=https://github.com/your-org/your-test-repo.git
python -m src.indexer.github_indexer

# Generate test from ticket
python -m src.agent.agent_runner_pom \
  --ticket acceptance_criteria/ABC-123.json \
  --kb knowledge_base_schema.json

# Run the test
export APP_BASE_URL=http://localhost:3000
pytest tests/generated/test_acceptance_ABC_123.py -v

# Report results (dry run)
python -c "
from src.integrations.jira_reporter import JiraReporter, TestResult
reporter = JiraReporter(dry_run=True)
result = TestResult('ABC-123', 'Local Test', 'passed', 1500)
reporter.report_test_result(result)
"
```

This approach gives you:
- **Deterministic test generation** (same input = same test)
- **Fresh knowledge base** (always up-to-date selectors)
- **Immediate Jira feedback** (results posted automatically)
- **No submodule dependencies** (framework CI tests framework, product CI tests product)
