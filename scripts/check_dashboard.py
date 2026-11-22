"""Verify the student dashboard and linked parent view at supported browser widths."""

import os
import re
import secrets
import sys
from datetime import date, timedelta
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def check_width(browser, base_url, width):
    context = browser.new_context(viewport={"width": width, "height": 900},
                                  has_touch=width < 1000, is_mobile=width < 768)
    page = context.new_page()
    origin = urlsplit(base_url)
    context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url)[:2] == origin[:2] else route.abort())
    try:
        page.goto(base_url)
        email = f"dashboard-{secrets.token_hex(6)}@example.org"
        password = secrets.token_urlsafe(24)
        page.locator("#auth-email").fill(email)
        page.locator("#auth-password").fill(password)
        page.get_by_role("button", name="Register", exact=True).click()
        page.locator("#onboard-course").fill("Physics")
        page.locator("#onboard-age").fill("20")
        page.locator("#onboard-form button").click()
        expect(page.locator("#auth-overlay")).not_to_have_class(re.compile("open"))

        page.locator("#quick-input").fill("Lab notes")
        page.locator("#quick-date").fill((date.today() + timedelta(days=1)).isoformat())
        page.locator("#quick-time").fill("17:45")
        page.locator("#quick-btn").click()
        entry = page.locator("#asgn-list .asgn-item").filter(has_text="Lab notes")
        expect(entry).to_contain_text("17:45")
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        entry.click()
        expect(entry).to_have_class(re.compile("done"))

        page.goto(base_url + "/settings")
        page.locator("#invite-parent").click()
        expect(page.locator("#parent-code")).to_contain_text("Invite code")
        code = page.locator("#parent-code").inner_text().split()[-1]
        context.clear_cookies()
        page.evaluate("localStorage.clear(); sessionStorage.clear()")
        page.goto(base_url + "/parents")
        page.locator("#auth-toggle-link").click()
        page.locator("#auth-email").fill(f"parent-{email}")
        page.locator("#auth-pass").fill(password)
        page.locator("#auth-submit-btn").click()
        page.locator("#empty-state button").click()
        page.locator("#invite-code").fill(code)
        page.locator("#link-btn").click()
        expect(page.locator("#student-dashboard")).to_be_visible()
        expect(page.locator("#stat-focus")).to_contain_text(re.compile(r"\d"))
        assert page.evaluate("document.documentElement.scrollWidth") <= width + 1
        print(f"Dashboard and parent portal passed at {width}px")
    finally:
        context.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("MIMO_CHROME_EXECUTABLE"))
        try:
            for viewport in (320, 393, 820, 1440):
                check_width(browser, sys.argv[1].rstrip("/"), viewport)
        finally:
            browser.close()
