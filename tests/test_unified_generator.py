"""
Tests for Unified Test Generator

This module contains comprehensive unit tests for the UnifiedTestGenerator class,
which provides a unified interface for both template-based and LLM-based test generation.

Test Coverage:
    ✓ Configuration handling for different generation modes
    ✓ Template generation integration and delegation
    ✓ LLM generation integration and delegation
    ✓ Hybrid mode with intelligent fallback logic
    ✓ Statistics tracking and cost monitoring
    ✓ Error handling across generation methods
    ✓ File I/O operations and CLI interface

Test Structure:
    - TestUnifiedTestGenerator: Core unified generation functionality
    - TestCommandLineInterface: CLI argument parsing and execution

Generation Modes Tested:
    - Template: Fast, reliable template-based generation
    - LLM: AI-powered intelligent test generation
    - Hybrid: LLM with template fallback (recommended)

Dependencies:
    - unittest.mock: Mocking for generator dependencies
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

from src.agent.config import AgentConfig, GenerationMode, LLMProvider
from src.agent.llm_generator import GenerationResult
from src.agent.unified_generator import UnifiedTestGenerator


class TestUnifiedTestGenerator:
    """Test cases for UnifiedTestGenerator class."""

    def test_initialization_default_config(self) -> None:
        """Test initialization with default configuration."""
        with patch("src.agent.unified_generator.load_config") as mock_load:
            mock_config = Mock(spec=AgentConfig)
            mock_config.generation_mode = GenerationMode.TEMPLATE
            mock_load.return_value = mock_config

            generator = UnifiedTestGenerator()

            assert generator.config == mock_config
            assert generator.generation_stats["total_generated"] == 0
            assert generator.generation_stats["template_used"] == 0
            assert generator.generation_stats["llm_used"] == 0

    def test_initialization_custom_config(self) -> None:
        """Test initialization with custom configuration."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = GenerationMode.LLM

        generator = UnifiedTestGenerator(config)

        assert generator.config == config

    def test_create_llm_config(self) -> None:
        """Test LLM configuration creation from agent configuration."""
        config = Mock(spec=AgentConfig)
        config.llm_provider = LLMProvider.OPENAI
        config.llm_model = "gpt-4"
        config.llm_temperature = 0.2
        config.llm_max_tokens = 3000
        config.llm_api_key = "test-key"
        config.llm_base_url = "https://api.test.com"
        config.llm_timeout = 30
        config.llm_max_cost_usd = 2.0

        generator = UnifiedTestGenerator(config)
        llm_config = generator._create_llm_config()

        assert llm_config.provider == LLMProvider.OPENAI
        assert llm_config.model == "gpt-4"
        assert llm_config.temperature == 0.2
        assert llm_config.max_tokens == 3000
        assert llm_config.api_key == "test-key"
        assert llm_config.base_url == "https://api.test.com"
        assert llm_config.timeout == 30
        assert llm_config.max_cost_usd == 2.0

    @patch("src.agent.unified_generator.TemplateTestGenerator")
    def test_generate_with_template_success(self, mock_pom_class: Any) -> None:
        """Test successful template generation."""
        # Setup mocks
        mock_pom = Mock()
        mock_pom.generate_test.return_value = "test_code_here"
        mock_pom_class.return_value = mock_pom

        config = Mock(spec=AgentConfig)
        config.template_version = "v1.0"

        generator = UnifiedTestGenerator(config)

        ticket: Dict[str, Any] = {"title": "Test ticket"}
        kb: Dict[str, Any] = {"page_objects": []}

        result = generator._generate_with_template(ticket, kb)

        assert result.success is True
        assert result.test_code == "test_code_here"
        assert result.provider_used == "template"
        assert result.model_used == "v1.0"
        assert result.cost_usd == 0.0
        assert result.generation_time > 0

    @patch("src.agent.unified_generator.TemplateTestGenerator")
    def test_generate_with_template_failure(self, mock_pom_class: Any) -> None:
        """Test template generation failure."""
        # Setup mocks
        mock_pom = Mock()
        mock_pom.generate_test.side_effect = Exception("Template error")
        mock_pom_class.return_value = mock_pom

        config = Mock(spec=AgentConfig)
        config.template_version = "v1.0"

        generator = UnifiedTestGenerator(config)

        ticket: Dict[str, Any] = {"title": "Test ticket"}
        kb: Dict[str, Any] = {"page_objects": []}

        result = generator._generate_with_template(ticket, kb)

        assert result.success is False
        assert result.test_code == ""
        assert result.error_message == "Template error"

    @patch("src.agent.unified_generator.LLMTestGenerator")
    def test_generate_with_llm_success(self, mock_llm_class: Any) -> None:
        """Test successful LLM generation."""
        # Setup mocks
        mock_llm = Mock()
        mock_result = GenerationResult(
            test_code="llm_test_code",
            success=True,
            provider_used="openai",
            model_used="gpt-4",
            tokens_used=500,
            cost_usd=0.02,
            generation_time=2.5,
        )
        mock_llm.generate_test.return_value = mock_result
        mock_llm_class.return_value = mock_llm

        config = Mock(spec=AgentConfig)
        config.llm_provider = LLMProvider.OPENAI
        config.llm_model = "gpt-4"
        config.target_framework = "playwright-python"

        generator = UnifiedTestGenerator(config)

        ticket: Dict[str, Any] = {"title": "Test ticket"}
        kb: Dict[str, Any] = {"page_objects": []}

        result = generator._generate_with_llm(ticket, kb)

        assert result.success is True
        assert result.test_code == "llm_test_code"
        assert result.provider_used == "openai"
        assert result.cost_usd == 0.02

    @patch("src.agent.unified_generator.LLMTestGenerator")
    def test_generate_with_llm_failure(self, mock_llm_class: Any) -> None:
        """Test LLM generation failure."""
        # Setup mocks
        mock_llm_class.side_effect = Exception("LLM error")

        config = Mock(spec=AgentConfig)
        config.llm_provider = LLMProvider.OPENAI
        config.llm_model = "gpt-4"

        generator = UnifiedTestGenerator(config)

        ticket: Dict[str, Any] = {"title": "Test ticket"}
        kb: Dict[str, Any] = {"page_objects": []}

        result = generator._generate_with_llm(ticket, kb)

        assert result.success is False
        assert result.test_code == ""
        assert result.error_message == "LLM error"

    def test_generate_test_template_mode(self) -> None:
        """Test test generation in template mode."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = GenerationMode.TEMPLATE

        generator = UnifiedTestGenerator(config)

        # Mock the template generation method
        mock_result = GenerationResult(
            test_code="template_code",
            success=True,
            provider_used="template",
            model_used="v1.0",
            generation_time=1.0,
        )

        with patch.object(
            generator, "_generate_with_template", return_value=mock_result
        ):
            ticket: Dict[str, Any] = {"title": "Test ticket"}
            kb: Dict[str, Any] = {"page_objects": []}

            result = generator.generate_test(ticket, kb)

            assert result.success is True
            assert generator.generation_stats["total_generated"] == 1
            assert generator.generation_stats["template_used"] == 1
            assert generator.generation_stats["llm_used"] == 0
            assert generator.generation_stats["total_time"] == 1.0

    def test_generate_test_llm_mode(self) -> None:
        """Test test generation in LLM mode."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = GenerationMode.LLM

        generator = UnifiedTestGenerator(config)

        # Mock the LLM generation method
        mock_result = GenerationResult(
            test_code="llm_code",
            success=True,
            provider_used="openai",
            model_used="gpt-4",
            cost_usd=0.05,
            generation_time=2.0,
        )

        with patch.object(generator, "_generate_with_llm", return_value=mock_result):
            ticket: Dict[str, Any] = {"title": "Test ticket"}
            kb: Dict[str, Any] = {"page_objects": []}

            result = generator.generate_test(ticket, kb)

            assert result.success is True
            assert generator.generation_stats["total_generated"] == 1
            assert generator.generation_stats["llm_used"] == 1
            assert generator.generation_stats["template_used"] == 0
            assert generator.generation_stats["total_cost"] == 0.05
            assert generator.generation_stats["total_time"] == 2.0

    def test_generate_test_hybrid_mode_llm_success(self) -> None:
        """Test hybrid mode where LLM succeeds."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = GenerationMode.HYBRID

        generator = UnifiedTestGenerator(config)

        # Mock successful LLM generation
        llm_result = GenerationResult(
            test_code="llm_code",
            success=True,
            provider_used="openai",
            model_used="gpt-4",
            cost_usd=0.03,
            generation_time=1.5,
        )

        with patch.object(generator, "_generate_with_llm", return_value=llm_result):
            ticket: Dict[str, Any] = {"title": "Test ticket"}
            kb: Dict[str, Any] = {"page_objects": []}

            result = generator.generate_test(ticket, kb)

            assert result.success is True
            assert result.test_code == "llm_code"
            assert generator.generation_stats["llm_used"] == 1
            assert generator.generation_stats["fallback_used"] == 0
            assert generator.generation_stats["total_cost"] == 0.03

    def test_generate_test_hybrid_mode_llm_fails_template_succeeds(self) -> None:
        """Test hybrid mode where LLM fails and template succeeds."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = GenerationMode.HYBRID

        generator = UnifiedTestGenerator(config)

        # Mock failed LLM generation
        llm_result = GenerationResult(
            test_code="",
            success=False,
            provider_used="openai",
            model_used="gpt-4",
            error_message="API error",
            generation_time=1.0,
        )

        # Mock successful template generation
        template_result = GenerationResult(
            test_code="template_code",
            success=True,
            provider_used="template",
            model_used="v1.0",
            generation_time=0.5,
        )

        with patch.object(
            generator, "_generate_with_llm", return_value=llm_result
        ), patch.object(
            generator, "_generate_with_template", return_value=template_result
        ):
            ticket: Dict[str, Any] = {"title": "Test ticket"}
            kb: Dict[str, Any] = {"page_objects": []}

            result = generator.generate_test(ticket, kb)

            assert result.success is True
            assert result.test_code == "template_code"
            assert result.fallback_used is True
            assert generator.generation_stats["fallback_used"] == 1
            assert (
                generator.generation_stats["total_time"] == 1.5
            )  # Both generation times

    def test_generate_test_unsupported_mode(self) -> None:
        """Test error handling for unsupported generation mode."""
        config = Mock(spec=AgentConfig)
        config.generation_mode = "unsupported"

        generator = UnifiedTestGenerator(config)

        ticket: Dict[str, Any] = {"title": "Test ticket"}
        kb: Dict[str, Any] = {"page_objects": []}

        with pytest.raises(ValueError, match="Unsupported generation mode"):
            generator.generate_test(ticket, kb)

    def test_generate_from_files_success(self) -> None:
        """Test successful test generation from files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            ticket_file = Path(tmp_dir) / "ticket.json"
            kb_file = Path(tmp_dir) / "kb.json"
            output_file = Path(tmp_dir) / "output.py"

            ticket_data = {"title": "Test ticket", "description": "Test description"}
            kb_data: Dict[str, Any] = {"page_objects": []}

            ticket_file.write_text(json.dumps(ticket_data))
            kb_file.write_text(json.dumps(kb_data))

            config = Mock(spec=AgentConfig)
            generator = UnifiedTestGenerator(config)

            # Mock the generate_test method
            mock_result = GenerationResult(
                test_code="generated_test_code",
                success=True,
                provider_used="template",
                model_used="v1.0",
            )

            with patch.object(generator, "generate_test", return_value=mock_result):
                result = generator.generate_from_files(
                    str(ticket_file), str(kb_file), str(output_file)
                )

                assert result.success is True
                assert output_file.exists()
                assert output_file.read_text() == "generated_test_code"

    def test_generate_from_files_no_output_file(self) -> None:
        """Test test generation from files without output file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            ticket_file = Path(tmp_dir) / "ticket.json"
            kb_file = Path(tmp_dir) / "kb.json"

            ticket_data = {"title": "Test ticket"}
            kb_data: Dict[str, Any] = {"page_objects": []}

            ticket_file.write_text(json.dumps(ticket_data))
            kb_file.write_text(json.dumps(kb_data))

            config = Mock(spec=AgentConfig)
            generator = UnifiedTestGenerator(config)

            # Mock the generate_test method
            mock_result = GenerationResult(
                test_code="generated_test_code",
                success=True,
                provider_used="template",
                model_used="v1.0",
            )

            with patch.object(generator, "generate_test", return_value=mock_result):
                result = generator.generate_from_files(str(ticket_file), str(kb_file))

                assert result.success is True

    def test_generate_from_files_invalid_json(self) -> None:
        """Test error handling for invalid JSON files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create invalid JSON file
            ticket_file = Path(tmp_dir) / "ticket.json"
            kb_file = Path(tmp_dir) / "kb.json"

            ticket_file.write_text("invalid json")
            kb_file.write_text("{}")

            config = Mock(spec=AgentConfig)
            generator = UnifiedTestGenerator(config)

            with pytest.raises(json.JSONDecodeError):
                generator.generate_from_files(str(ticket_file), str(kb_file))

    def test_get_stats(self) -> None:
        """Test statistics retrieval."""
        config = Mock(spec=AgentConfig)
        generator = UnifiedTestGenerator(config)

        # Update some stats
        generator.generation_stats["total_generated"] = 5
        generator.generation_stats["llm_used"] = 3
        generator.generation_stats["template_used"] = 2
        generator.generation_stats["total_cost"] = 0.15

        stats = generator.get_stats()

        assert stats["total_generated"] == 5
        assert stats["llm_used"] == 3
        assert stats["template_used"] == 2
        assert stats["total_cost"] == 0.15

    def test_reset_stats(self) -> None:
        """Test statistics reset."""
        config = Mock(spec=AgentConfig)
        generator = UnifiedTestGenerator(config)

        # Update some stats
        generator.generation_stats["total_generated"] = 5
        generator.generation_stats["total_cost"] = 0.15

        generator.reset_stats()

        assert generator.generation_stats["total_generated"] == 0
        assert generator.generation_stats["total_cost"] == 0.0


class TestCommandLineInterface:
    """Test command-line interface functionality."""

    @patch("src.agent.unified_generator.UnifiedTestGenerator")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_success(
        self, mock_parse_args: Any, mock_generator_class: Any
    ) -> None:
        """Test main function with successful generation."""
        # Setup mocks
        args = Mock()
        args.ticket = "ticket.json"
        args.kb = "kb.json"
        args.output = "output.py"
        args.mode = None  # Use config default
        args.provider = None
        args.framework = None
        args.stats = False
        args.show_env_example = False
        args.show_config = False
        args.show_env_example = False
        mock_parse_args.return_value = args

        mock_generator = Mock()
        mock_result = GenerationResult(
            test_code="test_code",
            success=True,
            provider_used="template",
            model_used="v1.0",
            generation_time=1.0,
        )
        mock_generator.generate_from_files.return_value = mock_result
        mock_generator_class.return_value = mock_generator

        # Mock file operations
        with patch("builtins.open", Mock()), patch("json.load", Mock()), patch(
            "pathlib.Path.mkdir", Mock()
        ), patch("pathlib.Path.write_text", Mock()):
            from src.agent.unified_generator import main

            # Should not raise any exceptions
            main()

            mock_generator.generate_from_files.assert_called_once_with(
                "ticket.json", "kb.json", "output.py"
            )

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_function_with_stats(self, mock_parse_args: Any) -> None:
        """Test main function with stats display."""
        args = Mock()
        args.ticket = "ticket.json"
        args.kb = "kb.json"
        args.output = None
        args.mode = None
        args.provider = None
        args.framework = None
        args.stats = True
        args.show_env_example = False
        args.show_config = False
        mock_parse_args.return_value = args

        with patch(
            "src.agent.unified_generator.UnifiedTestGenerator"
        ) as mock_gen_class:
            mock_generator = Mock()
            mock_generator.get_stats.return_value = {
                "total_generated": 5,
                "llm_used": 3,
                "template_used": 2,
            }
            mock_result = GenerationResult(
                test_code="test_code",
                success=True,
                provider_used="template",
                model_used="v1.0",
                generation_time=1.0,
                tokens_used=0,
                cost_usd=0.0,
            )
            mock_generator.generate_from_files.return_value = mock_result
            mock_gen_class.return_value = mock_generator

            with patch("builtins.print") as mock_print:
                from src.agent.unified_generator import main

                main()

                # Should print stats
                mock_print.assert_called()
