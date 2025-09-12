"""
Automated Test Generation Framework

A comprehensive framework for automated test generation with Jira integration,
GitHub repository indexing, and template-based test creation.

This framework is designed specifically for Python/Playwright/pytest applications
using the Page Object Model pattern.
"""

from .__version__ import __version__, __version_info__

# Core components
from .agent.template_generator import TemplateTestGenerator
from .indexer.github_indexer import GitHubIndexer
from .integrations.jira_reporter import JiraReporter, JiraTestResult
from .poller.jira_poller_with_validation import JiraPollerWithValidation
from .validator.test_validator import ValidatorService

__all__ = [
    "__version__",
    "__version_info__",
    "POMTestGenerator",
    "GitHubIndexer",
    "JiraReporter",
    "JiraTestResult",
    "JiraPollerWithValidation",
    "ValidatorService",
]

# Framework metadata
__title__ = "automated-test-generation-framework"
__description__ = (
    "Automated test generation framework for Python/Playwright/pytest applications"
)
__author__ = "Phil McNeely"
__license__ = "MIT"
