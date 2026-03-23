"""Tests for LLM-based Jira ticket parser."""
import pytest
from src.models.test_requirement import TestRequirement, TestStep, TestScenario, ConfidenceScores
from src.poller.llm_parser import build_parser_prompt, parse_llm_response


def test_build_parser_prompt():
    prompt = build_parser_prompt("PROJ-123", "Login test", "User logs in with credentials")
    assert "PROJ-123" in prompt
    assert "Login test" in prompt
    assert "User logs in" in prompt


def test_parse_valid_response():
    response = '''{
        "ticket_id": "PROJ-123",
        "title": "Login test",
        "scenarios": [{
            "name": "Happy path login",
            "type": "happy_path",
            "preconditions": ["User exists"],
            "steps": [
                {"action": "navigate", "target": "/login"},
                {"action": "fill", "target": "#username", "value": "testuser"},
                {"action": "fill", "target": "#password", "value": "password123"},
                {"action": "click", "target": "#login-btn"}
            ],
            "expected_result": "User sees dashboard",
            "test_data": [{"field": "username", "type": "string"}]
        }],
        "edge_cases": ["Empty password", "SQL injection in username"],
        "confidence": {"overall": 0.9, "steps": 0.85, "selectors": 0.8, "test_data": 0.9}
    }'''
    result = parse_llm_response(response, "PROJ-123", "Login test", "User logs in")
    assert result is not None
    assert result.ticket_id == "PROJ-123"
    assert len(result.scenarios) == 1
    assert len(result.scenarios[0].steps) == 4
    assert result.confidence.overall == 0.9
    assert not result.needs_human_review


def test_low_confidence_flags_review():
    response = '''{
        "ticket_id": "PROJ-456",
        "title": "Vague ticket",
        "scenarios": [{"name": "test", "steps": [{"action": "click", "target": "button"}], "expected_result": "works"}],
        "edge_cases": [],
        "confidence": {"overall": 0.4, "steps": 0.3, "selectors": 0.2, "test_data": 0.5}
    }'''
    result = parse_llm_response(response, "PROJ-456", "Vague ticket", "Something")
    assert result is not None
    assert result.needs_human_review is True


def test_parse_json_in_code_block():
    response = '''Here is the analysis:
```json
{
    "ticket_id": "X-1",
    "title": "Test",
    "scenarios": [{"name": "t", "steps": [{"action": "click", "target": "#btn"}], "expected_result": "ok"}],
    "edge_cases": [],
    "confidence": {"overall": 0.8, "steps": 0.8, "selectors": 0.7, "test_data": 0.8}
}
```'''
    result = parse_llm_response(response, "X-1", "Test", "desc")
    assert result is not None
    assert result.ticket_id == "X-1"


def test_parse_invalid_json():
    result = parse_llm_response("not json at all", "X-1", "Test", "desc")
    assert result is None


def test_test_requirement_model():
    req = TestRequirement(
        ticket_id="T-1",
        title="Test",
        scenarios=[TestScenario(
            name="login",
            steps=[TestStep(action="click", target="#btn")],
            expected_result="success"
        )],
        confidence=ConfidenceScores(overall=0.9, steps=0.9, selectors=0.8, test_data=0.9)
    )
    assert req.ticket_id == "T-1"
    assert len(req.scenarios) == 1
    d = req.model_dump()
    assert "scenarios" in d
