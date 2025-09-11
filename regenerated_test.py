# ===== Generated Playwright Test =====
import pytest
from utils.decorators.screenshot_decorator import screenshot_on_failure

@screenshot_on_failure
@pytest.mark.login
@pytest.mark.asyncio
async def test_login_happy_path(app):
    """Generated test using playwright-ai-framework patterns."""
    await app.login_page.page.click('button[type=')
    await app.login_page.page.fill('#username', 'user1')
    await app.login_page.page.fill('#password', 'pass123')
    await app.login_page.page.click('submit_button')
    await app.login_page.page.wait_for_selector('text=Welcome')
