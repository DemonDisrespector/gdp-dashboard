"""
Browser automation destination connector (Playwright).

Used when the destination EHR/portal only offers a web UI.
Requires: pip install playwright && playwright install chromium

Config keys
-----------
login_url      : str  – URL of the destination login page
username       : str
password       : str
form_selectors : dict – CSS selectors for each field to fill
submit_selector: str  – CSS selector for the submit button
headless       : bool – (default True)
timeout        : int  – milliseconds per action (default 10000)
screenshot_on_error : bool – capture screenshot on failure (default True)
"""
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.connectors.base import BaseConnector, ConnectorResult

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class BrowserConnector(BaseConnector):
    """Fill web forms using Playwright for portal-only destinations."""

    def validate_config(self):
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        required = {"login_url", "username", "password", "form_selectors", "submit_selector"}
        missing = required - self.config.keys()
        if missing:
            raise ValueError(f"BrowserConnector missing config keys: {missing}")

    async def send(self, payload: List[Dict[str, Any]]) -> ConnectorResult:
        if not _PLAYWRIGHT_AVAILABLE:
            return ConnectorResult(success=False, error_message="Playwright not available")

        headless: bool = self.config.get("headless", True)
        timeout: int = int(self.config.get("timeout", 10_000))
        screenshot_on_error: bool = self.config.get("screenshot_on_error", True)

        records_sent = 0
        records_failed = 0

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(timeout)

            try:
                # Login
                await page.goto(self.config["login_url"])
                if "login_username_selector" in self.config:
                    await page.fill(self.config["login_username_selector"], self.config["username"])
                    await page.fill(self.config["login_password_selector"], self.config["password"])
                    await page.click(self.config["login_submit_selector"])
                    await page.wait_for_load_state("networkidle")

                for record in payload:
                    try:
                        await self._fill_form(page, record, timeout)
                        records_sent += 1
                        logger.info("BrowserConnector submitted record %d/%d", records_sent, len(payload))
                    except PWTimeout as exc:
                        records_failed += 1
                        logger.error("BrowserConnector timeout on record: %s", exc)
                        if screenshot_on_error:
                            path = Path(f"/tmp/conduit_browser_error_{records_failed}.png")
                            await page.screenshot(path=str(path))
                            logger.info("Screenshot saved to %s", path)

            finally:
                await browser.close()

        return ConnectorResult(
            success=records_failed == 0,
            records_sent=records_sent,
            records_failed=records_failed,
            error_message=f"{records_failed} records failed" if records_failed else None,
        )

    async def _fill_form(self, page, record: Dict[str, Any], timeout: int):
        """Fill and submit a single form for one record."""
        form_url: str = self.config.get("form_url", "")
        if form_url:
            await page.goto(form_url)
            await page.wait_for_load_state("networkidle")

        selectors: dict = self.config["form_selectors"]
        for field_name, selector in selectors.items():
            value = record.get(field_name)
            if value is not None:
                await page.fill(selector, str(value))

        await page.click(self.config["submit_selector"])
        await page.wait_for_load_state("networkidle")
