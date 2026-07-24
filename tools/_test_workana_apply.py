import asyncio, sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
from playwright.async_api import async_playwright
from pathlib import Path

async def test():
    session_path = Path("data/sessions/workana_session.json")
    storage = json.loads(session_path.read_text(encoding="utf-8"))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=storage, viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Visit bot whatsapp project
        await page.goto("https://www.workana.com/job/bot-whatsapp", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Check if we're actually logged in
        is_logged_in = await page.evaluate("""() => {
            const body = document.body;
            // Check for login indicators
            const hasFreelancerLink = !!document.querySelector('a[href*=\"freelancer/dashboard\"]');
            const hasLoginLink = !!document.querySelector('a[href*=\"/login\"]');
            const hasSignupLink = !!document.querySelector('a[href*=\"/signup\"]');
            const hasAvatar = !!document.querySelector('[class*=\"avatar\"], img[class*=\"user\"]');
            return { hasFreelancerLink, hasLoginLink, hasSignupLink, hasAvatar };
        }""")
        print(f"Login indicators: {is_logged_in}")

        # Get all links on the page to understand structure
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                text: (a.textContent || '').trim().slice(0, 50),
                href: a.getAttribute('href') || '',
                class: (a.className || '').slice(0, 40),
            })).filter(l => l.text);
        }""")
        print(f"\nPage links ({len(links)}):")
        for link in links:
            if any(kw in (link['text'] + link['href']).lower() for kw in ['propuesta', 'postular', 'apply', 'login', 'signup', 'freelancer']):
                print(f"  [{link['class']}] '{link['text']}' -> {link['href'][:80]}")

        # Also check if there's a "send proposal" or similar
        buttons = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(b => ({
                text: (b.textContent || '').trim().slice(0, 50),
                class: (b.className || '').slice(0, 40),
                id: b.id,
            })).filter(b => b.text);
        }""")
        print(f"\nButtons:")
        for btn in buttons:
            print(f"  [{btn['class']}] '{btn['text']}'")

        # Check project description and budget
        desc = await page.evaluate("""() => {
            const descEl = document.querySelector('.description, [class*=\"description\"], .project-description, .job-description');
            if (descEl) return descEl.textContent.trim().slice(0, 500);
            // Try getting the main content
            const main = document.querySelector('main, .container, .content');
            return main ? main.textContent.trim().slice(0, 500) : 'no content found';
        }""")
        print(f"\nDescription: {desc[:500]}")

        await browser.close()

asyncio.run(test())
