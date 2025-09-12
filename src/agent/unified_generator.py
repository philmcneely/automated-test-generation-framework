"""
Unified Test Generator

This module provides a unified interface for both template-based and LLM-based test
generation. It automatically chooses the appropriate generation method based on
configuration and provides seamless fallback capabilities.

Features:
    ✓ Unified interface for all generation modes
    ✓ Automatic method selection based on configuration
    ✓ Seamless fallback from LLM to template generation
    ✓ Cost tracking and usage monitoring for LLM generation
    ✓ Support for multiple frameworks and providers
    ✓ Comprehensive error handling and reporting
    ✓ Backward compatibility with existing template system
    ✓ Statistics tracking and performance monitoring

Generation Modes:
    - Template: Fast, reliable template-based generation
    - LLM: Intelligent AI-powered test generation
    - Hybrid: LLM with template fallback (recommended)

Usage Examples:
    # Auto-detect generation mode from environment
    python src/agent/unified_generator.py --ticket ticket.json --kb kb.json

    # Force template generation
    python src/agent/unified_generator.py --ticket ticket.json --kb kb.json --mode template

    # Force LLM generation with specific provider
    python src/agent/unified_generator.py --ticket ticket.json --kb kb.json --mode llm --provider openai

    # Hybrid mode (LLM with template fallback)
    python src/agent/unified_generator.py --ticket ticket.json --kb kb.json --mode hybrid

    # Use in code
    from src.agent.unified_generator import UnifiedTestGenerator
    from src.agent.config import AgentConfig, GenerationMode

    config = AgentConfig(generation_mode=GenerationMode.HYBRID)
    generator = UnifiedTestGenerator(config)
    result = generator.generate_test(ticket_data, kb_data)

Dependencies:
    - template_generator: Template-based generation
    - llm_generator: LLM-based generation
    - config: Configuration management
    - argparse: Command-line interface
    - json: JSON processing

Author: PMAC
Date: 2025-09-11
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AgentConfig, GenerationMode, LLMProvider, load_config
from .llm_generator import GenerationResult, LLMConfig, LLMTestGenerator
from .template_generator import TemplateTestGenerator


class UnifiedTestGenerator:
    """
    Unified test generator that can use either template or LLM-based generation.

    This class provides a single interface for all test generation methods,
    with automatic fallback and comprehensive error handling.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the unified test generator."""
        self.config = config or load_config()
        self.generation_stats = {
            "total_generated": 0,
            "template_used": 0,
            "llm_used": 0,
            "fallback_used": 0,
            "total_cost": 0.0,
            "total_time": 0.0,
        }

    def _create_llm_config(self) -> LLMConfig:
        """Create LLM configuration from agent configuration."""
        return LLMConfig(
            provider=self.config.llm_provider,
            model=self.config.llm_model or "gpt-4",
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url,
            timeout=self.config.llm_timeout,
            max_cost_usd=self.config.llm_max_cost_usd,
        )

    def _generate_with_template(
        self, ticket: Dict[str, Any], kb: Dict[str, Any]
    ) -> GenerationResult:
        """Generate test using template-based approach."""
        start_time = time.time()

        try:
            template_generator = TemplateTestGenerator()
            test_code = template_generator.generate_test(ticket, kb)

            generation_time = time.time() - start_time

            return GenerationResult(
                test_code=test_code,
                success=True,
                provider_used="template",
                model_used=self.config.template_version,
                tokens_used=0,
                cost_usd=0.0,
                generation_time=generation_time,
            )

        except Exception as e:
            generation_time = time.time() - start_time

            return GenerationResult(
                test_code="",
                success=False,
                provider_used="template",
                model_used=self.config.template_version,
                generation_time=generation_time,
                error_message=str(e),
            )

    def _generate_with_llm(
        self, ticket: Dict[str, Any], kb: Dict[str, Any]
    ) -> GenerationResult:
        """Generate test using LLM approach."""
        try:
            llm_config = self._create_llm_config()
            llm_generator = LLMTestGenerator(llm_config)

            return llm_generator.generate_test(ticket, kb, self.config.target_framework)

        except Exception as e:
            return GenerationResult(
                test_code="",
                success=False,
                provider_used=self.config.llm_provider.value,
                model_used=self.config.llm_model or "unknown",
                error_message=str(e),
            )

    def generate_test(
        self, ticket: Dict[str, Any], kb: Dict[str, Any]
    ) -> GenerationResult:
        """Generate test using the configured method with fallback."""

        self.generation_stats["total_generated"] += 1

        # Template mode - use template generation only
        if self.config.generation_mode == GenerationMode.TEMPLATE:
            result = self._generate_with_template(ticket, kb)
            if result.success:
                self.generation_stats["template_used"] += 1
            self.generation_stats["total_time"] += result.generation_time
            return result

        # LLM mode - use LLM generation only
        elif self.config.generation_mode == GenerationMode.LLM:
            result = self._generate_with_llm(ticket, kb)
            if result.success:
                self.generation_stats["llm_used"] += 1
                self.generation_stats["total_cost"] += result.cost_usd
            self.generation_stats["total_time"] += result.generation_time
            return result

        # Hybrid mode - try LLM first, fallback to template
        elif self.config.generation_mode == GenerationMode.HYBRID:
            # Try LLM first
            llm_result = self._generate_with_llm(ticket, kb)

            if llm_result.success:
                self.generation_stats["llm_used"] += 1
                self.generation_stats["total_cost"] += llm_result.cost_usd
                self.generation_stats["total_time"] += llm_result.generation_time
                return llm_result

            # Fallback to template
            print(
                f"🔄 LLM generation failed ({llm_result.error_message}), falling back to template..."
            )

            template_result = self._generate_with_template(ticket, kb)

            if template_result.success:
                self.generation_stats["fallback_used"] += 1
                template_result.fallback_used = True

            self.generation_stats["total_time"] += (
                llm_result.generation_time + template_result.generation_time
            )
            return template_result

        else:
            raise ValueError(
                f"Unsupported generation mode: {self.config.generation_mode}"
            )

    def generate_from_files(
        self, ticket_file: str, kb_file: str, output_file: Optional[str] = None
    ) -> GenerationResult:
        """Generate test from ticket and knowledge base files."""

        # Load input files
        with open(ticket_file, "r") as f:
            ticket = json.load(f)

        with open(kb_file, "r") as f:
            kb = json.load(f)

        # Generate the test
        result = self.generate_test(ticket, kb)

        # Save output if requested and generation was successful
        if output_file and result.success:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(result.test_code)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self.generation_stats.copy()

    def reset_stats(self) -> None:
        """Reset generation statistics."""
        self.generation_stats = {
            "total_generated": 0,
            "template_used": 0,
            "llm_used": 0,
            "fallback_used": 0,
            "total_cost": 0.0,
            "total_time": 0.0,
        }

    def print_stats(self) -> None:
        """Print generation statistics."""
        stats = self.generation_stats

        print("\n" + "=" * 50)
        print("Test Generation Statistics")
        print("=" * 50)
        print(f"Total tests generated: {stats['total_generated']}")
        print(f"Template generations: {stats['template_used']}")
        print(f"LLM generations: {stats['llm_used']}")
        print(f"Fallback generations: {stats['fallback_used']}")
        print(f"Total cost: ${stats['total_cost']:.4f}")
        print(f"Total time: {stats['total_time']:.2f}s")

        if stats["total_generated"] > 0:
            avg_time = stats["total_time"] / stats["total_generated"]
            print(f"Average time per test: {avg_time:.2f}s")


def _parse_arguments() -> Any:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate tests using unified template/LLM agent."
    )

    # Required arguments
    parser.add_argument("--ticket", required=True, help="Path to ticket JSON file")
    parser.add_argument("--kb", required=True, help="Path to knowledge base JSON file")
    parser.add_argument("--output", help="Output file path (optional)")

    # Generation mode override
    parser.add_argument(
        "--mode",
        choices=["template", "llm", "hybrid"],
        help="Override generation mode (from config/env)",
    )

    # LLM configuration overrides
    parser.add_argument(
        "--provider",
        choices=["openai", "claude", "ollama", "azure"],
        help="Override LLM provider",
    )
    parser.add_argument("--model", help="Override LLM model")
    parser.add_argument("--framework", help="Override target framework")
    parser.add_argument("--temperature", type=float, help="Override LLM temperature")
    parser.add_argument("--max-tokens", type=int, help="Override max tokens")
    parser.add_argument("--max-cost", type=float, help="Override max cost")

    # Utility options
    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration"
    )
    parser.add_argument(
        "--show-env-example",
        action="store_true",
        help="Show environment variable example",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show generation statistics"
    )

    return parser.parse_args()


def _apply_overrides(config: AgentConfig, args: Any) -> None:
    """Apply command-line overrides to configuration."""
    if args.mode:
        config.generation_mode = GenerationMode(args.mode)
    if args.provider:
        config.llm_provider = LLMProvider(args.provider)
    if args.model:
        config.llm_model = args.model
    if args.framework:
        config.target_framework = args.framework
    if args.temperature is not None:
        config.llm_temperature = args.temperature
    if args.max_tokens:
        config.llm_max_tokens = args.max_tokens
    if args.max_cost:
        config.llm_max_cost_usd = args.max_cost


def _print_result(result: Any, args: Any) -> None:
    """Print generation result."""
    if result.success:
        print(f"✅ Test generated successfully using {result.provider_used}")
        if result.model_used:
            print(f"🤖 Model: {result.model_used}")
        if result.tokens_used > 0:
            print(f"📊 Tokens used: {result.tokens_used}")
        if result.cost_usd > 0:
            print(f"💰 Cost: ${result.cost_usd:.4f}")
        print(f"⏱️  Generation time: {result.generation_time:.2f}s")
        if result.fallback_used:
            print("🔄 Used template fallback")

        if args.output:
            print(f"📁 Test saved to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("Generated Test Code:")
            print("=" * 60)
            print(result.test_code)
    else:
        print(f"❌ Test generation failed: {result.error_message}")
        exit(1)


def main() -> None:
    """Main entry point for command-line usage."""
    args = _parse_arguments()

    # Handle utility options
    if args.show_env_example:
        config = AgentConfig()
        print("Environment Variable Configuration Example:")
        print(config.get_env_example())
        return

    try:
        # Load base configuration
        config = load_config()

        # Apply command-line overrides
        _apply_overrides(config, args)

        if args.show_config:
            print("Current Configuration:")
            for key, value in config.to_dict().items():
                if key == "llm_api_key" and value:
                    value = "***" + value[-4:] if len(value) > 4 else "***"
                print(f"  {key}: {value}")
            return

        # Create generator and generate test
        generator = UnifiedTestGenerator(config)
        result = generator.generate_from_files(args.ticket, args.kb, args.output)

        # Handle the result
        _print_result(result, args)

        # Show statistics if requested
        if args.stats:
            generator.print_stats()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
