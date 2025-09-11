# Separated Architecture for Automated Test Generation

## Overview

This document describes the separated architecture that keeps the automated test generation system and the playwright-ai-framework completely independent while maintaining seamless integration.

## Architecture

```
Repository 1: automated-test-generation/
├── src/
│   ├── agent/           # Test generation engine
│   ├── poller/          # Jira integration
│   ├── indexer/         # GitHub repository indexing
│   └── validator/       # Test validation service
├── knowledge_base/      # Shared knowledge base
├── .gitmodules         # Git submodule configuration
└── playwright-ai-framework/  # Git submodule (separate repo)

Repository 2: playwright-ai-framework/
├── tests/
│   └── generated/      # Generated tests (managed by submodule)
├── pages/              # Page Object Models
├── utils/              # Utilities and fixtures
├── conftest.py         # Test configuration
└── All existing framework files...
```

## Key Components

### 1. Git Submodule Integration
- **playwright-ai-framework** is included as a git submodule
- **No code changes** to the existing framework
- **Clean separation** - each repository maintains its own history
- **Version control** - submodule can be pinned to specific commits

### 2. Test Validation Pipeline
- **Generated tests are validated** before being saved to the framework
- **Temporary execution** in isolated environment
- **Failure analysis** with detailed error reporting
- **Only validated tests** are committed to the framework

### 3. Development Workflow

#### Local Development
```bash
# Clone test generation repo with submodule
git clone <automated-test-generation-repo>
cd automated-test-generation/
git submodule update --init --recursive

# Work on test generation
python src/agent/agent_runner_pom.py --ticket ticket.json --kb kb.json

# Test against local playwright copy
python src/validator/test_validator.py --test generated_test.py

# Run the enhanced poller with validation
python src/poller/jira_poller_with_validation.py
```

#### CI/CD Integration
- **Separate GitHub Actions** for each repository
- **Test generation repo** validates tests before publishing
- **Playwright framework repo** can pull validated tests as needed
- **No cross-contamination** of CI pipelines

## Benefits

### 1. Complete Isolation
- **No shared dependencies** - each project has its own requirements
- **Independent versioning** - each repo can evolve separately
- **No code conflicts** - changes in one don't affect the other
- **Separate CI/CD** - each project has its own build pipeline

### 2. Maintained Integration
- **Seamless workflow** - tests are generated, validated, and saved automatically
- **Framework features preserved** - AI healing, visual regression, etc. all work
- **Knowledge base sharing** - both systems can access and update the knowledge base
- **Validation pipeline** - ensures only working tests are saved

### 3. Development Flexibility
- **Work on either system independently**
- **Test changes locally** before committing
- **Easy rollback** - submodule can be reverted if issues arise
- **Parallel development** - teams can work on each repo simultaneously

## Usage Instructions

### Setting Up the Submodule
```bash
# Add playwright framework as submodule
git submodule add https://github.com/philmcneely/playwright-ai-framework.git playwright-ai-framework

# Initialize submodule
git submodule update --init --recursive

# Configure submodule to track main branch
git config -f .gitmodules submodule.playwright-ai-framework.branch main
```

### Running the System
```bash
# Option 1: Original poller (no validation)
python src/poller/jira_poller.py

# Option 2: Enhanced poller with validation
python src/poller/jira_poller_with_validation.py

# Manual test validation
python src/validator/test_validator.py --test path/to/test.py
```

### Testing Integration
```bash
# Generate a test
python src/agent/agent_runner_pom.py --ticket sample_ticket.json \
  --kb knowledge_base_existing_framework.json \
  --output test_output.py

# Validate the test
python src/validator/test_validator.py --test test_output.py

# Run the test manually in playwright framework
cd playwright-ai-framework/
python -m pytest tests/generated/test_output.py -v
```

## Migration Path

### Current State → Separated Architecture
1. **Keep current directory structure** as development environment
2. **Create separate git repositories** for production
3. **Use git submodules** for clean integration
4. **Maintain validation pipeline** for quality assurance
5. **Preserve all existing functionality** while adding separation

## Future Enhancements

### 1. LLM Integration for Test Healing
- **Automatic test fixing** when validation fails
- **Knowledge base updates** from failure analysis
- **Continuous improvement** of generated tests

### 2. Advanced Validation
- **Visual regression testing** for generated tests
- **Performance benchmarking** of test execution
- **Cross-browser compatibility** validation

### 3. CI/CD Automation
- **Automatic submodule updates** when tests are validated
- **Integration testing** across both repositories
- **Deployment pipelines** for each component

This architecture provides the clean separation you requested while maintaining all the integration benefits and validation capabilities.
