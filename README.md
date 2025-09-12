# Automated Test Generation Package (with Samples)

Contents:
- automated_test_generation_spec.md (spec with code)
- src/poller/jira_poller.py (Jira poller)
- src/agent/unified_generator.py (unified test generator)
- examples/sample_test_playwright.py (Playwright+Pytest sample)
- src/indexer/github_indexer.py (shallow clone + index)
- knowledge_base_schema.json (KB schema)
- ci_cd_pipeline.yml (GitHub Actions tests)
- .github/workflows/index_kb.yml (KB indexing workflow)
- Dockerfile, docker-compose.yml
- config/example.config.yaml
- Makefile
- requirements.txt

Quick start:
1) python -m venv .venv && source .venv/bin/activate
2) pip install -r requirements.txt
3) export APP_BASE_URL=https://example.com
4) pytest -q
5) make run-agent (uses sample_ticket.json + knowledge_base_schema.json)
6) export GITHUB_REPO_URL=... && make index-github
