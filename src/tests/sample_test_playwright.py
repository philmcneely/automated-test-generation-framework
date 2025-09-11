import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("APP_BASE_URL", "https://example.com")


@pytest.mark.e2e  # type: ignore[misc]
def test_login_happy_path() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)
        page.click("#login")
        page.fill("#username", "user1")
        page.fill("#password", "pass123")
        page.click("#submit")
        page.wait_for_selector("text=Welcome")
        browser.close()
