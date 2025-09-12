"""
Configuration for Test Generation Agent

This module provides configuration management for both template-based and LLM-based
test generation. Users can choose their preferred generation method and configure
LLM providers as needed.

Features:
    ✓ Unified configuration for all generation modes
    ✓ Environment variable support for sensitive data
    ✓ Multiple LLM provider configurations
    ✓ Validation and default value handling
    ✓ Type-safe configuration with dataclasses
    ✓ Support for various frameworks and models

Configuration Sources:
    - Environment variables (highest priority)
    - Configuration files (YAML/JSON)
    - Command-line arguments
    - Default values (lowest priority)

Usage Examples:
    # Load from environment
    config = load_config()

    # Manual configuration
    config = AgentConfig(
        generation_mode=GenerationMode.HYBRID,
        llm_provider=LLMProvider.OPENAI
    )

Author: PMAC
Date: 2025-09-11
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class GenerationMode(Enum):
    """Test generation modes."""

    TEMPLATE = "template"
    LLM = "llm"
    HYBRID = "hybrid"  # Try LLM first, fallback to template


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    AZURE = "azure"


@dataclass
class AgentConfig:
    """Complete configuration for test generation."""

    # Generation mode
    generation_mode: GenerationMode = GenerationMode.TEMPLATE

    # LLM Configuration (only used if generation_mode is LLM or HYBRID)
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: Optional[str] = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4000
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_timeout: int = 60
    llm_max_cost_usd: float = 1.0

    # Framework configuration
    target_framework: str = "playwright-python"

    # Template configuration (only used if generation_mode is TEMPLATE or HYBRID fallback)
    template_version: str = "pom"  # Page Object Model

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Create configuration from environment variables."""

        # Parse generation mode
        mode_str = os.getenv("AGENT_GENERATION_MODE", "template").lower()
        generation_mode = GenerationMode.TEMPLATE
        for mode in GenerationMode:
            if mode.value == mode_str:
                generation_mode = mode
                break

        # Parse LLM provider
        provider_str = os.getenv("AGENT_LLM_PROVIDER", "openai").lower()
        llm_provider = LLMProvider.OPENAI
        for provider in LLMProvider:
            if provider.value == provider_str:
                llm_provider = provider
                break

        # Default models by provider
        default_models = {
            LLMProvider.OPENAI: "gpt-4-turbo-preview",
            LLMProvider.CLAUDE: "claude-3-5-sonnet-20241022",
            LLMProvider.OLLAMA: "llama3.1:8b",
            LLMProvider.AZURE: "gpt-4",
        }

        return cls(
            generation_mode=generation_mode,
            llm_provider=llm_provider,
            llm_model=os.getenv("AGENT_LLM_MODEL") or default_models[llm_provider],
            llm_temperature=float(os.getenv("AGENT_LLM_TEMPERATURE", "0.1")),
            llm_max_tokens=int(os.getenv("AGENT_LLM_MAX_TOKENS", "4000")),
            llm_api_key=os.getenv("AGENT_LLM_API_KEY"),
            llm_base_url=os.getenv("AGENT_LLM_BASE_URL"),
            llm_timeout=int(os.getenv("AGENT_LLM_TIMEOUT", "60")),
            llm_max_cost_usd=float(os.getenv("AGENT_LLM_MAX_COST", "1.0")),
            target_framework=os.getenv("AGENT_TARGET_FRAMEWORK", "playwright-python"),
            template_version=os.getenv("AGENT_TEMPLATE_VERSION", "pom"),
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "AgentConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "generation_mode": self.generation_mode.value,
            "llm_provider": self.llm_provider.value,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_api_key": self.llm_api_key,
            "llm_base_url": self.llm_base_url,
            "llm_timeout": self.llm_timeout,
            "llm_max_cost_usd": self.llm_max_cost_usd,
            "target_framework": self.target_framework,
            "template_version": self.template_version,
        }

    def get_env_example(self) -> str:
        """Get example environment variable configuration."""
        return """
# Test Generation Configuration
AGENT_GENERATION_MODE=llm  # template, llm, or hybrid
AGENT_TARGET_FRAMEWORK=playwright-python  # playwright-python, cypress, selenium-java, etc.

# LLM Configuration (only needed if using LLM or HYBRID mode)
AGENT_LLM_PROVIDER=openai  # openai, claude, ollama, azure
AGENT_LLM_MODEL=gpt-4-turbo-preview  # Model name (optional, has defaults)
AGENT_LLM_TEMPERATURE=0.1  # 0.0 to 1.0
AGENT_LLM_MAX_TOKENS=4000
AGENT_LLM_API_KEY=your_api_key_here  # Or use provider-specific env vars
AGENT_LLM_BASE_URL=  # Optional, for custom endpoints
AGENT_LLM_TIMEOUT=60  # Seconds
AGENT_LLM_MAX_COST=1.0  # Maximum cost in USD per generation

# Template Configuration (used for template mode or hybrid fallback)
AGENT_TEMPLATE_VERSION=pom  # Page Object Model version
        """.strip()


def get_default_config() -> AgentConfig:
    """Get default configuration."""
    return AgentConfig()


def load_config() -> AgentConfig:
    """Load configuration from environment variables."""
    return AgentConfig.from_env()
