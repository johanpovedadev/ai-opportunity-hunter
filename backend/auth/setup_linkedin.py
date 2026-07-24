"""Login helper: abre navegador, espera login manual, guarda cookies."""
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

SESSIONS_DIR = Path("data/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    print("=" * 60)
    print("  CONFIGURACION DE SESION LINKEDIN")
    print("=" * 60)
    print()
    print("Se abrira una ventana del navegador.")
    print("1. Inicia sesion en LinkedIn MANUALMENTE en esa ventana.")
    print("2. Cuando veas tu feed de LinkedIn, la sesion se guardara")
    print("   automaticamente en unos segundos.")
    print()
    print("  Tiempo maximo de espera: 10 minutos")
    print("  Para cancelar: cierra la ventana del navegador")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/login", timeout=60000, wait_until="domcontentloaded")
        print("  Navegador abierto. Esperando login...")
        sys.stdout.flush()

        # Intentar usar sesion existente de Chrome primero
        await page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        logged_in = False
        for i in range(200):  # 200 * 3s = 10 min
            url = page.url
            cookies = await context.cookies()
            has_li_at = any(c.get("name") == "li_at" for c in cookies)
            has_jsession = any("JSESSIONID" in c.get("name", "").upper() for c in cookies)

            if has_li_at and has_jsession:
                logged_in = True
                break
            if "feed" in url and has_li_at:
                logged_in = True
                break
            if "/in/" in url and has_li_at:
                logged_in = True
                break

            if i % 10 == 0:
                print(f"  Esperando... ({i*3}s) URL actual: {url[:60]}")
                sys.stdout.flush()

            await asyncio.sleep(3)

        if logged_in:
            storage = await context.storage_state()
            path = SESSIONS_DIR / "linkedin_session.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(storage, f, indent=2, ensure_ascii=False)
            n = len(storage.get("cookies", []))
            print(f"\n  [OK] Sesion guardada: {n} cookies en {path}")
        else:
            print("\n  [FAIL] No se detecto login en 10 minutos.")
            print("  Guardando cookies disponibles igualmente...")
            storage = await context.storage_state()
            path = SESSIONS_DIR / "linkedin_session.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(storage, f, indent=2, ensure_ascii=False)
            print(f"  Estado guardado en {path}")

        await browser.close()


asyncio.run(main())
