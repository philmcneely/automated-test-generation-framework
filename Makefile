.PHONY: setup test run-agent docker-build docker-test index-github lint format check-quality install-hooks clean coverage

VENV?=.venv
PY?=python

# Setup and installation
setup:
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install -U pip && pip install -r requirements.txt

install-hooks:
	. $(VENV)/bin/activate && pre-commit install
	. $(VENV)/bin/activate && pre-commit install --hook-type commit-msg

# Testing commands
test:
	pytest -q

test-unit:
	pytest tests/ -m "unit" -v

test-integration:
	pytest tests/ -m "integration" -v

test-e2e:
	pytest tests/ -m "e2e" -v

test-all:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/index.html"

# Code quality and linting
lint:
	@echo "Running flake8..."
	. $(VENV)/bin/activate && flake8 src/ tests/ --exclude=playwright-ai-framework
	@echo "Running mypy..."
	. $(VENV)/bin/activate && mypy src/ --exclude="playwright-ai-framework"
	@echo "Running bandit security check..."
	. $(VENV)/bin/activate && bandit -r src/ -f json -o bandit-report.json

format:
	@echo "Running black..."
	. $(VENV)/bin/activate && black src/ tests/ --exclude="playwright-ai-framework"
	@echo "Running isort..."
	. $(VENV)/bin/activate && isort src/ tests/ --skip-glob="playwright-ai-framework/*"

format-check:
	@echo "Checking black formatting..."
	. $(VENV)/bin/activate && black --check src/ tests/ --exclude="playwright-ai-framework"
	@echo "Checking isort..."
	. $(VENV)/bin/activate && isort --check-only src/ tests/ --skip-glob="playwright-ai-framework/*"

type-check:
	. $(VENV)/bin/activate && mypy src/ --exclude="playwright-ai-framework"

security-check:
	@echo "Running bandit security analysis..."
	. $(VENV)/bin/activate && bandit -r src/ -f json -o bandit-report.json
	@echo "Running safety check for dependencies..."
	. $(VENV)/bin/activate && safety check

check-quality: format-check lint type-check security-check
	@echo "All quality checks passed!"

# Pre-commit hooks
pre-commit:
	. $(VENV)/bin/activate && pre-commit run --all-files

pre-commit-update:
	. $(VENV)/bin/activate && pre-commit autoupdate

# Main application commands
run-agent:
	$(PY) src/agent/agent_runner.py --ticket sample_ticket.json --kb knowledge_base_schema.json

run-poller:
	$(PY) src/poller/jira_poller_with_validation.py

# Docker commands
docker-build:
	docker build -t atg:latest .

docker-test:
	docker run --rm -e APP_BASE_URL=$$APP_BASE_URL atg:latest

# Utility commands
index-github:
	$(PY) src/indexer/github_indexer.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f bandit-report.json

help:
	@echo "Available commands:"
	@echo "  setup          - Set up virtual environment and install dependencies"
	@echo "  install-hooks  - Install pre-commit hooks"
	@echo "  test           - Run quick tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-e2e       - Run end-to-end tests only"
	@echo "  test-all       - Run all tests with coverage"
	@echo "  coverage       - Generate coverage report"
	@echo "  lint           - Run all linting tools (flake8, mypy, bandit)"
	@echo "  format         - Format code with black and isort"
	@echo "  format-check   - Check code formatting without making changes"
	@echo "  type-check     - Run mypy type checking"
	@echo "  security-check - Run security analysis (bandit, safety)"
	@echo "  check-quality  - Run all quality checks"
	@echo "  pre-commit     - Run pre-commit hooks on all files"
	@echo "  pre-commit-update - Update pre-commit hooks"
	@echo "  run-agent      - Run the test generation agent"
	@echo "  run-poller     - Run the Jira poller"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-test    - Run tests in Docker container"
	@echo "  index-github   - Index GitHub repositories"
	@echo "  clean          - Clean up generated files and caches"
	@echo "  help           - Show this help message"
