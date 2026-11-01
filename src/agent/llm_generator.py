"""
LLM-Based Test Generator

This module provides LLM-powered test generation as an intelligent alternative to
template-based generation. It supports multiple LLM providers and can generate tests
in various frameworks while maintaining compatibility with the existing framework.

Features:
    ✓ Multiple LLM provider support (OpenAI, Anthropic Claude, Ollama, Azure)
    ✓ Intelligent prompt engineering for test generation
    ✓ Framework adaptation (Playwright, Cypress, Selenium, etc.)
    ✓ Knowledge base integration for context-aware generation
    ✓ Configurable model parameters (temperature, max_tokens, etc.)
    ✓ Cost estimation and token usage tracking
    ✓ Output validation and error handling
    ✓ Advanced code cleaning and formatting

LLM Providers Supported:
    - OpenAI (GPT-3.5, GPT-4, GPT-4-turbo)
    - Anthropic Claude (Claude-3, Claude-3.5-Sonnet)
    - Local models via Ollama (Llama, CodeLlama, etc.)
    - Azure OpenAI (with proper configuration)

Usage Examples:
    # Generate test with OpenAI
    python src/agent/llm_generator.py --ticket ticket.json --kb kb.json --provider openai

    # Generate test with Claude
    python src/agent/llm_generator.py --ticket ticket.json --kb kb.json --provider claude

    # Generate test with local Ollama model
    python src/agent/llm_generator.py --ticket ticket.json --kb kb.json --provider ollama --model llama3.1:8b

    # Use with custom framework
    python src/agent/llm_generator.py --ticket ticket.json --kb kb.json --framework cypress

    # Use in code
    from src.agent.llm_generator import LLMTestGenerator, LLMConfig, LLMProvider
    config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")
    generator = LLMTestGenerator(config)
    result = generator.generate_test(ticket_data, kb_data)

Dependencies:
    - openai: OpenAI API client (optional)
    - anthropic: Claude API client (optional)
    - requests: For local model APIs
    - pydantic: Data validation
    - json: JSON processing
    - argparse: Command-line interface

Author: PMAC
Date: 2025-09-11
"""

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


from .config import LLMProvider


@dataclass
class LLMConfig:
    """Configuration for LLM test generation."""

    provider: LLMProvider
    model: str
    temperature: float = 0.1
    max_tokens: int = 4000
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60

    # Cost tracking
    track_costs: bool = True
    max_cost_usd: float = 1.0


@dataclass
class GenerationResult:
    """Result of LLM test generation."""

    test_code: str
    success: bool
    provider_used: str
    model_used: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    generation_time: float = 0.0
    error_message: Optional[str] = None
    fallback_used: bool = False


class LLMTestGenerator:
    """
    LLM-powered test generator with multi-provider support.

    This class provides intelligent test generation using Large Language Models,
    with fallback to template-based generation when needed.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the LLM test generator."""
        self.config = config
        self.total_cost = 0.0
        self._validate_provider_availability()

    def _validate_provider_availability(self) -> None:
        """Validate that the required provider dependencies are available."""
        if self.config.provider == LLMProvider.OPENAI and not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library not available. Install with: pip install openai"
            )

        if self.config.provider == LLMProvider.CLAUDE and not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic library not available. Install with: pip install anthropic"
            )

    def _build_generation_prompt(
        self,
        ticket: Dict[str, Any],
        kb: Dict[str, Any],
        framework: str = "playwright-python",
    ) -> str:
        """Build a comprehensive prompt for LLM test generation."""

        # Extract ticket information
        title = ticket.get("title", "Unknown Test")
        description = ticket.get("description", "")
        acceptance_criteria = ticket.get("acceptance_criteria", [])

        # Extract knowledge base context
        page_objects = kb.get("page_objects", [])
        test_flows = kb.get("test_flows", [])

        # Build context about available selectors
        selectors_context = ""
        if page_objects:
            selectors_context = "\n".join(
                [
                    f"Page: {po.get('name', 'Unknown')}"
                    + "\n  Selectors: "
                    + ", ".join(
                        [
                            f"{s.get('element')}: {s.get('selector')}"
                            for s in po.get("selectors", [])
                        ]
                    )
                    for po in page_objects[:5]  # Limit to avoid token overflow
                ]
            )

        # Build context about available flows
        flows_context = ""
        if test_flows:
            flows_context = "\n".join(
                [
                    f"Flow: {flow.get('name', 'Unknown')}"
                    + "\n  Steps: "
                    + " -> ".join(
                        [
                            f"{step.get('action')}({step.get('target', '')})"
                            for step in flow.get("steps", [])
                        ]
                    )
                    for flow in test_flows[:3]  # Limit to avoid token overflow
                ]
            )

        # Framework-specific templates and patterns
        framework_templates = {
            "playwright-python": {
                "imports": "import pytest\nfrom playwright.async_api import expect",
                "decorators": "@pytest.mark.asyncio\n@pytest.mark.generated",
                "function_signature": "async def {test_name}(page, app):",
                "patterns": {
                    "click": "await app.{page}.click_{element}()",
                    "fill": "await app.{page}.enter_{element}('{value}')",
                    "navigate": "await app.{page}.navigate()",
                    "assert": "await expect(page.locator('text={text}')).to_be_visible()",
                },
            },
            "cypress": {
                "imports": '/// <reference types="cypress" />',
                "decorators": "",
                "function_signature": "describe('{test_suite}', () => {\n  it('{test_name}', () => {",
                "patterns": {
                    "click": "cy.get('{selector}').click()",
                    "fill": "cy.get('{selector}').type('{value}')",
                    "navigate": "cy.visit('{url}')",
                    "assert": "cy.contains('{text}').should('be.visible')",
                },
            },
            "selenium-java": {
                "imports": "import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;",
                "decorators": "@Test",
                "function_signature": "public void {test_name}() {",
                "patterns": {
                    "click": 'driver.findElement(By.{selector_type}("{selector}")).click()',
                    "fill": 'driver.findElement(By.{selector_type}("{selector}")).sendKeys("{value}")',
                    "navigate": 'driver.get("{url}")',
                    "assert": "assertTrue(driver.findElement(By.xpath(\"//*[contains(text(), '{text}')]\")).isDisplayed())",
                },
            },
        }

        template = framework_templates.get(
            framework, framework_templates["playwright-python"]
        )

        prompt = f"""You are an expert test automation engineer. Generate a comprehensive automated test based on the following requirements.

## Test Requirements
**Title**: {title}
**Description**: {description}

## Acceptance Criteria
{json.dumps(acceptance_criteria, indent=2)}

## Available Page Objects & Selectors
{selectors_context or "No page objects available"}

## Available Test Flows
{flows_context or "No test flows available"}

## Target Framework: {framework}

## Framework Template
**Imports**:
```
{template['imports']}
```

**Decorators**: {template['decorators']}
**Function Signature**: {template['function_signature']}

**Action Patterns**:
{json.dumps(template['patterns'], indent=2)}

## Instructions
1. Generate a complete, executable test that covers all acceptance criteria
2. Use the provided page object selectors and methods when available
3. Follow the framework-specific patterns and syntax
4. Include appropriate waits and assertions
5. Make the test robust and maintainable
6. Add meaningful comments explaining each step
7. Use the exact framework syntax and best practices

## Important Guidelines
- Prefer Page Object Model patterns when selectors are available
- Add explicit waits for dynamic elements
- Include comprehensive assertions
- Handle potential race conditions
- Make tests idempotent and independent
- Use meaningful variable names and comments

## Output Requirements
- Return ONLY the test code, no explanations
- Ensure code is properly formatted and indented
- Include all necessary imports
- Make sure syntax is valid for the target framework

Generate the test code now:
"""

        return prompt

    def _call_openai(self, prompt: str) -> Tuple[str, int, float]:
        """Call OpenAI API for test generation."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available")

        client = openai.OpenAI(
            api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=self.config.base_url,
        )

        response = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert test automation engineer.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
        )

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        # Estimate cost (approximate rates)
        cost = 0.0
        if "gpt-4" in self.config.model.lower():
            cost = tokens * 0.00003  # $0.03 per 1K tokens (approximate)
        elif "gpt-3.5" in self.config.model.lower():
            cost = tokens * 0.000002  # $0.002 per 1K tokens (approximate)

        return content, tokens, cost

    def _call_claude(self, prompt: str) -> Tuple[str, int, float]:
        """Call Anthropic Claude API for test generation."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not available")

        client = anthropic.Anthropic(
            api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        )

        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text if response.content else ""
        tokens = (
            response.usage.input_tokens + response.usage.output_tokens
            if response.usage
            else 0
        )

        # Estimate cost (approximate rates)
        cost = tokens * 0.000008  # $0.008 per 1K tokens (approximate for Claude-3)

        return content, tokens, cost

    def _call_ollama(self, prompt: str) -> Tuple[str, int, float]:
        """Call local Ollama model for test generation."""
        base_url = self.config.base_url or "http://localhost:11434"

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        response = requests.post(
            f"{base_url}/api/generate", json=payload, timeout=self.config.timeout
        )
        response.raise_for_status()

        result = response.json()
        content = result.get("response", "")

        # Ollama doesn't provide token counts, estimate based on character count
        tokens = len(content) // 4  # Rough approximation
        cost = 0.0  # Local models are free

        return content, tokens, cost

    def _clean_generated_code(
        self, raw_content: str, framework: str = "playwright-python"
    ) -> str:
        """Clean and validate generated test code."""
        # Remove markdown code blocks if present
        if "```" in raw_content:
            parts = raw_content.split("```")
            for part in parts:
                if any(
                    keyword in part
                    for keyword in [
                        "python",
                        "javascript",
                        "java",
                        "def ",
                        "async def",
                        "it(",
                        "test_",
                    ]
                ):
                    raw_content = part.strip()
                    break

        # Remove common prefixes/suffixes
        lines = raw_content.strip().split("\n")
        cleaned_lines: list[str] = []

        for line in lines:
            # Skip empty lines at start/end
            if not line.strip():
                if cleaned_lines:  # Only add empty lines if we have content
                    cleaned_lines.append(line)
                continue

            # Skip common markdown artifacts
            if line.strip().startswith(("```", "Here's", "The test", "This test")):
                continue

            cleaned_lines.append(line)

        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    def _call_provider(self, prompt: str) -> Tuple[str, int, float]:
        """Dispatch a prompt to the configured provider."""
        if self.config.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt)
        if self.config.provider == LLMProvider.CLAUDE:
            return self._call_claude(prompt)
        if self.config.provider == LLMProvider.OLLAMA:
            return self._call_ollama(prompt)
        raise ValueError(f"Unsupported provider: {self.config.provider}")

    def complete(self, prompt: str) -> str:
        """Send one prompt to the configured provider and return the raw text."""
        content, _tokens, cost = self._call_provider(prompt)
        self.total_cost += cost
        if self.config.track_costs and cost > self.config.max_cost_usd:
            raise ValueError(
                f"Completion cost ${cost:.4f} exceeds limit ${self.config.max_cost_usd}"
            )
        return content

    def generate_test(
        self,
        ticket: Dict[str, Any],
        kb: Dict[str, Any],
        framework: str = "playwright-python",
    ) -> GenerationResult:
        """Generate test using LLM with fallback options."""
        start_time = time.time()

        try:
            # Build the prompt
            prompt = self._build_generation_prompt(ticket, kb, framework)

            # Call the appropriate LLM provider
            content, tokens, cost = self._call_provider(prompt)

            # Check cost limits
            if self.config.track_costs and cost > self.config.max_cost_usd:
                raise ValueError(
                    f"Generation cost ${cost:.4f} exceeds limit ${self.config.max_cost_usd}"
                )

            # Clean and validate the generated code
            cleaned_code = self._clean_generated_code(content, framework)

            if not cleaned_code.strip():
                raise ValueError("Generated code is empty after cleaning")

            generation_time = time.time() - start_time
            self.total_cost += cost

            return GenerationResult(
                test_code=cleaned_code,
                success=True,
                provider_used=self.config.provider.value,
                model_used=self.config.model,
                tokens_used=tokens,
                cost_usd=cost,
                generation_time=generation_time,
            )

        except Exception as e:
            generation_time = time.time() - start_time

            return GenerationResult(
                test_code="",
                success=False,
                provider_used=self.config.provider.value,
                model_used=self.config.model,
                generation_time=generation_time,
                error_message=str(e),
            )

    def generate_from_files(
        self,
        ticket_file: str,
        kb_file: str,
        framework: str = "playwright-python",
        output_file: Optional[str] = None,
    ) -> GenerationResult:
        """Generate test from ticket and knowledge base files."""
        # Load input files
        with open(ticket_file, "r") as f:
            ticket = json.load(f)

        with open(kb_file, "r") as f:
            kb = json.load(f)

        # Generate the test
        result = self.generate_test(ticket, kb, framework)

        # Save output if requested and generation was successful
        if output_file and result.success:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(result.test_code)

        return result


def create_llm_config_from_args(args: Any) -> LLMConfig:
    """Create LLM configuration from command line arguments."""
    provider = LLMProvider(args.provider)

    # Default models for each provider
    default_models = {
        LLMProvider.OPENAI: "gpt-4-turbo-preview",
        LLMProvider.CLAUDE: "claude-3-5-sonnet-20241022",
        LLMProvider.OLLAMA: "llama3.1:8b",
        LLMProvider.AZURE: "gpt-4",
    }

    model = args.model or default_models[provider]

    return LLMConfig(
        provider=provider,
        model=model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        api_key=args.api_key,
        base_url=args.base_url,
        timeout=args.timeout,
        max_cost_usd=args.max_cost,
    )


def main() -> None:
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Generate tests using LLM from ticket JSON and KB JSON."
    )

    # Required arguments
    parser.add_argument("--ticket", required=True, help="Path to ticket JSON file")
    parser.add_argument("--kb", required=True, help="Path to knowledge base JSON file")

    # LLM configuration
    parser.add_argument(
        "--provider",
        choices=["openai", "claude", "ollama", "azure"],
        default="openai",
        help="LLM provider to use",
    )
    parser.add_argument(
        "--model", help="Specific model to use (defaults vary by provider)"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.1, help="Temperature for generation"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=4000, help="Maximum tokens to generate"
    )
    parser.add_argument("--api-key", help="API key (or use environment variable)")
    parser.add_argument("--base-url", help="Base URL for API (useful for local models)")
    parser.add_argument(
        "--timeout", type=int, default=60, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--max-cost", type=float, default=1.0, help="Maximum cost in USD"
    )

    # Generation options
    parser.add_argument(
        "--framework",
        default="playwright-python",
        help="Target test framework (playwright-python, cypress, selenium-java, etc.)",
    )
    parser.add_argument("--output", help="Output file path (optional)")
    parser.add_argument(
        "--fallback", action="store_true", help="Use template generation if LLM fails"
    )

    args = parser.parse_args()

    try:
        # Create LLM configuration
        config = create_llm_config_from_args(args)

        # Generate the test
        generator = LLMTestGenerator(config)
        result = generator.generate_from_files(
            args.ticket, args.kb, args.framework, args.output
        )

        # Handle the result
        if result.success:
            print(
                f"✅ Test generated successfully using {result.provider_used}/{result.model_used}"
            )
            print(f"📊 Tokens used: {result.tokens_used}")
            print(f"💰 Cost: ${result.cost_usd:.4f}")
            print(f"⏱️  Generation time: {result.generation_time:.2f}s")

            if args.output:
                print(f"📁 Test saved to: {args.output}")
            else:
                print("\n" + "=" * 60)
                print("Generated Test Code:")
                print("=" * 60)
                print(result.test_code)
        else:
            print(f"❌ Test generation failed: {result.error_message}")

            # Try fallback to template generation if requested
            if args.fallback:
                print("🔄 Attempting fallback to template generation...")
                try:
                    from .template_generator import TemplateTestGenerator

                    template_generator = TemplateTestGenerator()
                    template_result = template_generator.generate_from_files(
                        args.ticket, args.kb, args.output
                    )

                    print("✅ Template generation successful")
                    if not args.output:
                        print("\n" + "=" * 60)
                        print("Template Generated Test Code:")
                        print("=" * 60)
                        print(template_result)

                except Exception as e:
                    print(f"❌ Template generation also failed: {e}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
