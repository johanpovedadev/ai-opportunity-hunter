import random
import logging
from playwright.async_api import async_playwright
from backend.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    platform_for_auth = "wellfound"

    @property
    def fuente(self) -> str:
        return "wellfound"

    async def with_browser(self):
        """Override para usar configuración anti-detección."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        from backend.auth import SessionStorage
        storage = SessionStorage(self.platform_for_auth or self.fuente)
        state = storage.load()

        if state:
            context = await browser.new_context(
                storage_state=state,
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
        else:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )

        return pw, browser, context

    async def scrape_keyword(self, keyword: str) -> list[dict]:
        results: list[dict] = []
        pw, browser, context = await self.with_browser()
        page = await context.new_page()

        try:
            url = f"https://wellfound.com/role/{keyword.replace(' ', '-')}"
            logger.info(f"Navegando a: {url}")
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_timeout(random.randint(3000, 5000))

            if await self._is_blocked(page):
                logger.warning("Wellfound bloqueado por DataDome. Usa: python -m backend.scripts.cli auth login wellfound")
                return results

            cards = await page.query_selector_all("a[data-test='SearchResultsItem']")
            logger.info(f"Encontradas {len(cards)} tarjetas")
            cards = cards[:15]

            for card in cards:
                try:
                    data = await self._extract_job_data(card)
                    if data:
                        results.append(data)
                except Exception:
                    continue
        finally:
            await browser.close()
            await pw.stop()

        return results

    async def _is_blocked(self, page) -> bool:
        """Detecta si DataDome o similar está bloqueando."""
        html = await page.content()
        checks = [
            "captcha-delivery.com" in html,
            "cf-browser-verification" in html,
            "challenge-platform" in html,
            "just a moment" in html.lower()[:500],
        ]
        return any(checks)

    async def _extract_job_data(self, card) -> dict | None:
        result: dict = {
            "fuente": self.fuente,
            "link": "",
            "empresa": "",
            "cargo": "",
            "ubicacion": "",
            "descripcion": "",
        }

        title_el = await card.query_selector("div[class*='name']")
        result["cargo"] = await title_el.inner_text() if title_el else ""

        company_el = await card.query_selector("div[class*='company-name']")
        result["empresa"] = await company_el.inner_text() if company_el else ""

        meta_el = await card.query_selector("div[class*='meta']")
        result["ubicacion"] = await meta_el.inner_text() if meta_el else ""

        link = await card.get_attribute("href")
        result["link"] = f"https://wellfound.com{link}" if link else ""

        desc_el = await card.query_selector("div[class*='description']")
        result["descripcion"] = await desc_el.inner_text() if desc_el else ""

        return result
