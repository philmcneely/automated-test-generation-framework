.PHONY: setup test run-agent docker-build docker-test index-github

VENV?=.venv
PY?=python

setup:
	$(PY) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install -U pip && pip install -r requirements.txt

test:
	pytest -q

run-agent:
	$(PY) src/agent/agent_runner.py --ticket sample_ticket.json --kb knowledge_base_schema.json

docker-build:
	docker build -t atg:latest .

docker-test:
	docker run --rm -e APP_BASE_URL=$$APP_BASE_URL atg:latest

index-github:
	$(PY) src/indexer/github_indexer.py
