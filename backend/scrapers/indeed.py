import re
from backend.scrapers.base import BaseScraper


class IndeedScraper(BaseScraper):
    platform_for_auth = "indeed"

    @property
    def fuente(self) -> str:
        return "indeed"

    async def _make_context(self):
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="es-CO",
        )
        return pw, browser, context

    async def scrape_keyword(self, keyword: str) -> list[dict]:
        results: list[dict] = []
        pw, browser, context = await self._make_context()
        page = await context.new_page()
        page.set_default_timeout(30000)

        try:
            kw = keyword.replace(" ", "+")
            url = f"https://co.indeed.com/ofertas?q={kw}"
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            cards = await page.query_selector_all("div.job_seen_beacon")
            if not cards:
                return results

            for card in cards:
                try:
                    data = await self._extract_job_data(card)
                    if data and data.get("link"):
                        results.append(data)
                except Exception:
                    continue
        finally:
            await browser.close()
            await pw.stop()

        return results

    async def _extract_job_data(self, card) -> dict | None:
        result: dict = {
            "fuente": self.fuente,
            "link": "",
            "empresa": "",
            "cargo": "",
            "ubicacion": "",
            "descripcion": "",
            "salario_min": None,
            "salario_max": None,
            "moneda": None,
        }

        data = await card.evaluate("""(el) => {
            const titleEl = el.querySelector("h3.jobTitle a");
            const link = titleEl ? titleEl.getAttribute("href") || "" : "";
            const fullLink = link.startsWith("/") ? "https://co.indeed.com" + link.split("#")[0] : link.split("#")[0];
            const title = titleEl ? (titleEl.querySelector("span") ? titleEl.querySelector("span").textContent.trim() : titleEl.textContent.trim()) : "";

            const companyEl = el.querySelector("[data-testid='company-name'], span.companyName, .companyName");
            const company = companyEl ? companyEl.textContent.trim() : "";

            const locEl = el.querySelector("[data-testid='text-location'], .companyLocation");
            const location = locEl ? locEl.textContent.trim() : "";

            const salEl = el.querySelector("[data-testid='attribute_snippet_testid'], .metadata.salary, .salary-snippet, .salaryOnly, [class*=salary]");
            const salary = salEl ? salEl.textContent.trim() : "";

            const descEl = el.querySelector(".job-snippet, .summary");
            const desc = descEl ? descEl.textContent.trim() : "";

            return { title, link: fullLink, company, location, salary, description: desc };
        }""")

        if data:
            result["cargo"] = data.get("title", "")
            result["link"] = data.get("link", "")
            result["empresa"] = data.get("company", "")
            result["ubicacion"] = data.get("location", "")
            result["descripcion"] = data.get("description", "")
            salary_text = data.get("salary", "")
            if salary_text:
                result = self._parse_salary(salary_text, result)

        return result

    def _parse_salary(self, text: str, result: dict) -> dict:
        match = re.search(r"\$[\d.,]+", text)
        if match:
            clean = match.group().replace("$", "").replace(".", "").replace(",", "")
            result["salario_min"] = clean
            result["moneda"] = "COP"
        return result
