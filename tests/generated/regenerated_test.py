# ===== Generated Playwright Test =====
# NOTE: This test uses playwright-ai-framework patterns but is stored in main project
# because we don't commit to the submodule. In production, generated tests would be
# copied to the playwright-ai-framework/tests/generated/ directory for execution.
# type: ignore

from typing import Any, Callable

import pytest

try:
    # This will only work when executed in the playwright-ai-framework context
    from pages.app import App
    from utils.decorators.screenshot_decorator import screenshot_on_failure

    FRAMEWORK_AVAILABLE = True
    AppType = App
except ImportError:
    # Fallback for when running in main project context
    FRAMEWORK_AVAILABLE = False

    def screenshot_on_failure(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    class AppFallback:
        def __init__(self) -> None:
            self.login_page = self

        def navigate(self) -> Any:
            return None

        @property
        def page(self) -> Any:
            return self

        def click(self, selector: str) -> Any:
            return None

        def fill(self, selector: str, value: str) -> Any:
            return None

        def wait_for_selector(self, selector: str) -> Any:
            return None

    AppType = AppFallback


@pytest.mark.skipif(
    not FRAMEWORK_AVAILABLE, reason="Requires playwright-ai-framework context"
)
@screenshot_on_failure  # type: ignore[misc]
@pytest.mark.login  # type: ignore[misc]
@pytest.mark.asyncio  # type: ignore[misc]
async def test_login_happy_path(app: Any) -> None:
    """Generated test using playwright-ai-framework patterns."""
    await app.login_page.navigate()
    await app.login_page.page.click("button[type=")
    await app.login_page.page.fill("#username", "user1")
    await app.login_page.page.fill("#password", "pass123")
    await app.login_page.page.click("submit_button")
    await app.login_page.page.wait_for_selector("text=Welcome")
