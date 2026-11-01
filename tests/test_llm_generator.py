"""
Tests for LLM-Based Test Generator

This module contains comprehensive unit tests for the LLMTestGenerator class,
which provides AI-powered test generation using various LLM providers.

Test Coverage:
    ✓ LLM configuration creation and validation
    ✓ Multi-provider support (OpenAI, Claude, Ollama, Azure)
    ✓ Test generation with different models and frameworks
    ✓ Prompt engineering and code cleaning
    ✓ Cost tracking and token usage monitoring
    ✓ Error handling and fallback mechanisms
    ✓ File I/O operations and CLI interface

Test Structure:
    - TestLLMConfig: Configuration validation and creation
    - TestLLMTestGenerator: Core generation functionality
    - TestCommandLineInterface: CLI argument parsing and execution
    - TestGenerationResult: Result data structure validation

Dependencies:
    - unittest.mock: Mocking for API calls and external dependencies
    - tempfile: Temporary file operations for testing
    - pathlib: File path operations
    - json: JSON data handling for test fixtures

Author: PMAC
Date: 2025-09-11
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from src.agent.llm_generator import (
    GenerationResult,
    LLMConfig,
    LLMProvider,
    LLMTestGenerator,
    create_llm_config_from_args,
)


class TestLLMConfig:
    """Test LLM configuration creation and validation."""

    def test_llm_config_creation(self) -> None:
        """Test basic LLM configuration creation."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4-turbo-preview",
            temperature=0.2,
            max_tokens=2000,
        )

        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4-turbo-preview"
        assert config.temperature == 0.2
        assert config.max_tokens == 2000
        assert config.api_key is None
        assert config.timeout == 60  # default

    def test_llm_config_with_all_params(self) -> None:
        """Test LLM configuration with all parameters."""
        config = LLMConfig(
            provider=LLMProvider.CLAUDE,
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=4000,
            api_key="test-key",
            base_url="https://api.anthropic.com",
            timeout=120,
            track_costs=False,
            max_cost_usd=5.0,
        )

        assert config.provider == LLMProvider.CLAUDE
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.anthropic.com"
        assert config.timeout == 120
        assert config.track_costs is False
        assert config.max_cost_usd == 5.0


class TestLLMTestGenerator:
    """Test LLM test generator functionality."""

    def test_generator_initialization_openai(self) -> None:
        """Test LLM generator initialization with OpenAI."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        # Mock the availability check
        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)
            assert generator.config == config
            assert generator.total_cost == 0.0

    def test_generator_initialization_claude(self) -> None:
        """Test LLM generator initialization with Claude."""
        config = LLMConfig(
            provider=LLMProvider.CLAUDE, model="claude-3-5-sonnet-20241022"
        )

        # Mock the availability check
        with patch("src.agent.llm_generator.ANTHROPIC_AVAILABLE", True):
            generator = LLMTestGenerator(config)
            assert generator.config == config
            assert generator.total_cost == 0.0

    def test_generator_initialization_unavailable_provider(self) -> None:
        """Test that missing provider dependencies are caught."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", False):
            with pytest.raises(ImportError, match="OpenAI library not available"):
                LLMTestGenerator(config)

    def test_build_generation_prompt(self) -> None:
        """Test prompt building for generation."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            ticket = {
                "title": "User login test",
                "description": "Test user login functionality",
                "acceptance_criteria": [
                    {"action": "goto", "target": "login_page"},
                    {"action": "fill", "target": "username", "value": "testuser"},
                    {"action": "click", "target": "login_button"},
                ],
            }

            kb = {
                "page_objects": [
                    {
                        "name": "login_page",
                        "selectors": [
                            {"element": "username", "selector": "#username"},
                            {"element": "login_button", "selector": "#login-btn"},
                        ],
                    }
                ],
                "test_flows": [
                    {
                        "name": "login_flow",
                        "steps": [
                            {"action": "goto", "target": "login_page"},
                            {"action": "fill", "target": "username"},
                        ],
                    }
                ],
            }

            prompt = generator._build_generation_prompt(ticket, kb, "playwright-python")

            assert "User login test" in prompt
            assert "Test user login functionality" in prompt
            assert "goto" in prompt
            assert "login_page" in prompt
            assert "playwright-python" in prompt
            assert "import pytest" in prompt

    def test_clean_generated_code(self) -> None:
        """Test code cleaning functionality."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            # Test with markdown code blocks
            raw_code = """```python
import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
async def test_login(page, app):
    await app.login_page.navigate()
    await app.login_page.enter_username("user")
```"""

            cleaned = generator._clean_generated_code(raw_code)

            assert "```" not in cleaned
            assert "import pytest" in cleaned
            assert "async def test_login" in cleaned
            assert "await app.login_page.navigate()" in cleaned

    def test_clean_generated_code_no_markdown(self) -> None:
        """Test code cleaning with plain code (no markdown)."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            raw_code = """import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
async def test_login(page, app):
    await app.login_page.navigate()
    await app.login_page.enter_username("user")"""

            cleaned = generator._clean_generated_code(raw_code)

            assert cleaned == raw_code

    def test_generate_test_openai_success(self) -> None:
        """Test successful test generation with OpenAI."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        # Mock the entire OpenAI interaction
        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            # Mock the _call_openai method directly
            test_code = """import pytest
from playwright.async_api import expect

@pytest.mark.asyncio
async def test_login(page, app):
    await app.login_page.navigate()
    await app.login_page.enter_username("user")
    await app.login_page.click_login_button()
    await expect(page.locator("text=Welcome")).to_be_visible()"""

            with patch.object(
                generator, "_call_openai", return_value=(test_code, 150, 0.005)
            ):
                ticket = {
                    "title": "Login test",
                    "description": "Test login",
                    "acceptance_criteria": [{"action": "goto", "target": "login_page"}],
                }
                kb: Dict[str, Any] = {"page_objects": [], "test_flows": []}

                result = generator.generate_test(ticket, kb)

                assert result.success is True
                assert "async def test_login" in result.test_code
                assert result.provider_used == "openai"
                assert result.model_used == "gpt-4"
                assert result.tokens_used == 150
                assert result.cost_usd == 0.005
                assert result.error_message is None

    def test_generate_test_failure(self) -> None:
        """Test generation failure handling."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            # Mock OpenAI to raise an exception
            with patch.object(
                generator, "_call_openai", side_effect=Exception("API Error")
            ):
                ticket = {"title": "Test", "acceptance_criteria": []}
                kb: Dict[str, Any] = {"page_objects": [], "test_flows": []}

                result = generator.generate_test(ticket, kb)

                assert result.success is False
                assert result.error_message == "API Error"
                assert result.test_code == ""

    def test_generate_from_files(self) -> None:
        """Test generating from ticket and KB files."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")

        with patch("src.agent.llm_generator.OPENAI_AVAILABLE", True):
            generator = LLMTestGenerator(config)

            # Create temporary files
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as ticket_file:
                ticket_data = {
                    "title": "Test login",
                    "description": "Login functionality test",
                    "acceptance_criteria": [{"action": "goto", "target": "login_page"}],
                }
                json.dump(ticket_data, ticket_file)
                ticket_path = ticket_file.name

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as kb_file:
                kb_data: Dict[str, Any] = {"page_objects": [], "test_flows": []}
                json.dump(kb_data, kb_file)
                kb_path = kb_file.name

            try:
                # Mock the generate_test method
                mock_result = GenerationResult(
                    test_code="test code here",
                    success=True,
                    provider_used="openai",
                    model_used="gpt-4",
                )

                with patch.object(generator, "generate_test", return_value=mock_result):
                    result = generator.generate_from_files(ticket_path, kb_path)

                    assert result.success is True
                    assert result.test_code == "test code here"
            finally:
                # Clean up
                Path(ticket_path).unlink()
                Path(kb_path).unlink()


class TestCommandLineInterface:
    """Test command-line interface functionality."""

    def test_create_llm_config_from_args(self) -> None:
        """Test creating LLM config from command line arguments."""

        # Mock argparse arguments
        args = Mock()
        args.provider = "openai"
        args.model = None  # Should use default
        args.temperature = 0.2
        args.max_tokens = 3000
        args.api_key = "test-key"
        args.base_url = None
        args.timeout = 90
        args.max_cost = 2.0

        config = create_llm_config_from_args(args)

        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4-turbo-preview"  # default for OpenAI
        assert config.temperature == 0.2
        assert config.max_tokens == 3000
        assert config.api_key == "test-key"
        assert config.timeout == 90
        assert config.max_cost_usd == 2.0

    def test_create_llm_config_claude(self) -> None:
        """Test creating Claude config from args."""
        args = Mock()
        args.provider = "claude"
        args.model = "claude-3-haiku-20240307"
        args.temperature = 0.1
        args.max_tokens = 4000
        args.api_key = None
        args.base_url = None
        args.timeout = 60
        args.max_cost = 1.0

        config = create_llm_config_from_args(args)

        assert config.provider == LLMProvider.CLAUDE
        assert config.model == "claude-3-haiku-20240307"

    def test_create_llm_config_ollama(self) -> None:
        """Test creating Ollama config from args."""
        args = Mock()
        args.provider = "ollama"
        args.model = None  # Should use default
        args.temperature = 0.1
        args.max_tokens = 4000
        args.api_key = None
        args.base_url = "http://localhost:11434"
        args.timeout = 60
        args.max_cost = 1.0

        config = create_llm_config_from_args(args)

        assert config.provider == LLMProvider.OLLAMA
        assert config.model == "llama3.1:8b"  # default for Ollama
        assert config.base_url == "http://localhost:11434"


class TestGenerationResult:
    """Test the GenerationResult dataclass."""

    def test_generation_result_success(self) -> None:
        """Test successful generation result."""
        result = GenerationResult(
            test_code="test code",
            success=True,
            provider_used="openai",
            model_used="gpt-4",
            tokens_used=100,
            cost_usd=0.002,
            generation_time=1.5,
        )

        assert result.test_code == "test code"
        assert result.success is True
        assert result.provider_used == "openai"
        assert result.model_used == "gpt-4"
        assert result.tokens_used == 100
        assert result.cost_usd == 0.002
        assert result.generation_time == 1.5
        assert result.error_message is None
        assert result.fallback_used is False

    def test_generation_result_failure(self) -> None:
        """Test failed generation result."""
        result = GenerationResult(
            test_code="",
            success=False,
            provider_used="claude",
            model_used="claude-3-sonnet",
            error_message="Rate limit exceeded",
        )

        assert result.test_code == ""
        assert result.success is False
        assert result.error_message == "Rate limit exceeded"


class TestComplete:
    def test_complete_returns_raw_text_from_provider(self) -> None:
        from unittest.mock import patch

        from src.agent.config import LLMProvider
        from src.agent.llm_generator import LLMConfig, LLMTestGenerator

        gen = LLMTestGenerator(LLMConfig(provider=LLMProvider.OLLAMA, model="m"))
        with patch.object(gen, "_call_ollama", return_value=("raw", 5, 0.25)) as call:
            assert gen.complete("hello") == "raw"
        call.assert_called_once_with("hello")
        assert gen.total_cost == 0.25
