# Linting and Testing Guide

This document provides comprehensive guidance on the linting, testing, and code quality tools available in this project.

## Overview

This project uses a comprehensive set of code quality tools to ensure professional-grade code standards:

- **Linting**: flake8 for style and error checking
- **Formatting**: black for code formatting, isort for import sorting
- **Type Checking**: mypy for static type analysis
- **Security**: bandit for security vulnerability scanning, safety for dependency checking
- **Testing**: pytest with coverage reporting
- **Pre-commit Hooks**: Automated quality checks before commits

## Quick Start

```bash
# Set up the project with all tools
make setup
make install-hooks

# Run all quality checks
make check-quality

# Run tests with coverage
make test-all
```

## Available Make Commands

### Setup and Installation
- `make setup` - Set up virtual environment and install dependencies
- `make install-hooks` - Install pre-commit hooks

### Testing
- `make test` - Run quick tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make test-e2e` - Run end-to-end tests only
- `make test-all` - Run all tests with coverage
- `make coverage` - Generate coverage report

### Code Quality
- `make lint` - Run all linting tools (flake8, mypy, bandit)
- `make format` - Format code with black and isort
- `make format-check` - Check code formatting without making changes
- `make type-check` - Run mypy type checking
- `make security-check` - Run security analysis (bandit, safety)
- `make check-quality` - Run all quality checks
- `make pre-commit` - Run pre-commit hooks on all files

### Utility
- `make clean` - Clean up generated files and caches
- `make help` - Show all available commands

## Configuration Files

### setup.cfg
Contains configuration for all quality tools:
- **flake8**: Line length, ignored errors, excluded directories
- **black**: Line length, target Python versions
- **isort**: Import sorting rules compatible with black
- **mypy**: Type checking strictness and exclusions
- **pytest**: Test discovery and coverage settings
- **coverage**: Coverage reporting configuration

### .pre-commit-config.yaml
Defines pre-commit hooks that run automatically before commits:
- Basic file checks (trailing whitespace, YAML validation)
- Code formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Dependency vulnerability checking (safety)
- Unit test execution

## Tool-Specific Details

### flake8
- **Max line length**: 88 characters (compatible with black)
- **Ignored errors**: E203 (whitespace before ':'), W503 (line break before binary operator)
- **Excluded directories**: .git, __pycache__, .venv, playwright-ai-framework, etc.
- **Max complexity**: 10

### black
- **Line length**: 88 characters
- **Target versions**: Python 3.9, 3.10, 3.11
- **Excluded**: playwright-ai-framework and build directories

### isort
- **Profile**: black-compatible
- **Line length**: 88 characters
- **Multi-line output**: 3 (vertical hanging indent)

### mypy
- **Python version**: 3.9
- **Strict settings**: Enabled for comprehensive type checking
- **Excluded**: playwright-ai-framework and virtual environments

### pytest
- **Test discovery**: tests/ directory
- **Coverage target**: 80% minimum
- **Markers**: unit, integration, e2e, slow
- **Reports**: terminal, HTML, XML

## Testing Strategy

### Test Categories
1. **Unit Tests** (`@pytest.mark.unit`)
   - Test individual functions and classes
   - Fast execution, no external dependencies
   - Located in `tests/` directory

2. **Integration Tests** (`@pytest.mark.integration`)
   - Test component interactions
   - May use external services (mocked)
   - Medium execution time

3. **End-to-End Tests** (`@pytest.mark.e2e`)
   - Test complete workflows
   - Use real external services
   - Slow execution, run sparingly

### Test Structure
```
tests/
├── __init__.py
├── test_agent_runner.py      # Unit tests for agent runner
├── test_validator.py         # Unit tests for validator
└── integration/              # Integration tests (if needed)
    └── test_workflows.py
```

### Running Tests
```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_agent_runner.py

# Run with verbose output
pytest -v
```

## Code Quality Workflow

### Before Committing
1. **Format code**: `make format`
2. **Run quality checks**: `make check-quality`
3. **Run tests**: `make test-unit`
4. **Commit**: Pre-commit hooks will run automatically

### Continuous Integration
The CI pipeline runs:
1. All linting tools (flake8, mypy)
2. All test categories
3. Security scanning
4. Coverage reporting

### Pre-commit Hooks
Automatically run on commit:
```bash
# Install hooks
make install-hooks

# Run manually on all files
make pre-commit

# Update hooks to latest versions
make pre-commit-update
```

## Exclusions

The `playwright-ai-framework` directory is excluded from all quality checks since it's a git submodule maintained separately. This ensures we don't modify or lint external code.

## Troubleshooting

### Common Issues

1. **Import sorting conflicts**
   - Run `make format` to fix automatically
   - Check isort configuration in setup.cfg

2. **Type checking errors**
   - Add type hints to functions
   - Use `# type: ignore` for specific lines if needed
   - Check mypy configuration for exclusions

3. **Line length errors**
   - Black will auto-format most issues
   - For strings, consider using implicit concatenation
   - Break complex expressions into variables

4. **Pre-commit hook failures**
   - Fix the reported issues
   - Run `make pre-commit` to verify fixes
   - Commit again

### Getting Help
```bash
# Show all available commands
make help

# Check specific tool version
. .venv/bin/activate && flake8 --version

# Run tool with verbose output
. .venv/bin/activate && flake8 src/ -v
```

## Best Practices

1. **Write tests first** when adding new features
2. **Run quality checks** before committing
3. **Keep functions small** and focused
4. **Add type hints** to all function signatures
5. **Document complex logic** with docstrings
6. **Use meaningful variable names**
7. **Handle edge cases** explicitly
8. **Mock external dependencies** in unit tests

## Coverage Goals

- **Minimum coverage**: 80%
- **Target coverage**: 90%
- **Focus areas**: Core business logic, error handling
- **Exclude**: Simple getters/setters, external integrations

The coverage report is generated in `htmlcov/index.html` after running `make coverage`.
