"""Pydantic models for structured test requirements from Jira tickets."""
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional

# Actions the template generator can execute (after translating navigate -> goto
# and wait -> wait_for_selector). hover/select have no generator equivalent, so
# they are rejected here rather than silently emitted as TODO comments.
StepAction = Literal["click", "fill", "navigate", "assert_text", "assert_visible", "wait"]
ASSERTION_ACTIONS = {"assert_text", "assert_visible"}


class TestStep(BaseModel):
    action: StepAction = Field(description="Playwright action: click, fill, navigate, assert_text, assert_visible, wait")
    target: str = Field(description="CSS selector, URL, or element description")
    value: Optional[str] = Field(default=None, description="Value for fill/select/assert actions")
    assertion: Optional[str] = Field(default=None, description="Expected result after this step")


class TestDataRequirement(BaseModel):
    field: str = Field(description="Field name needing test data")
    type: str = Field(description="Data type: string, email, password, number, date, phone")
    constraints: Optional[str] = Field(default=None, description="Validation constraints: min_length, max_length, required, pattern")


class TestScenario(BaseModel):
    name: str = Field(description="Short test scenario name")
    type: str = Field(default="happy_path", description="Test type: happy_path, negative, boundary, security")
    preconditions: list[str] = Field(default_factory=list, description="What must be true before test runs")
    steps: list[TestStep] = Field(min_length=1, description="Ordered test steps")
    expected_result: str = Field(description="What should be true after test completes")
    test_data: list[TestDataRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_executable_assertion(self) -> "TestScenario":
        # The generator only runs steps, so a scenario with no assert_* step
        # could pass even when the feature is broken.
        if not any(step.action in ASSERTION_ACTIONS for step in self.steps):
            raise ValueError(
                "scenario must contain at least one assert_text or assert_visible step"
            )
        return self


class ConfidenceScores(BaseModel):
    overall: float = Field(ge=0.0, le=1.0, description="Overall parsing confidence")
    steps: float = Field(ge=0.0, le=1.0, description="Confidence in step extraction")
    selectors: float = Field(ge=0.0, le=1.0, description="Confidence in selector identification")
    test_data: float = Field(ge=0.0, le=1.0, description="Confidence in test data requirements")


class TestRequirement(BaseModel):
    ticket_id: str
    title: str
    scenarios: list[TestScenario] = Field(min_length=1)
    edge_cases: list[str] = Field(default_factory=list, description="Identified edge cases")
    confidence: ConfidenceScores
    raw_description: str = Field(default="", description="Original Jira description for reference")
    needs_human_review: bool = Field(default=False, description="True if confidence too low")
