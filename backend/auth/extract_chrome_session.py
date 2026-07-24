"""Extraer sesión LinkedIn via Playwright (funciona con Chrome 131+)."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

SESSIONS_DIR = Path("data/sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA = r"C:\Users\Administrador\AppData\Local\Google\Chrome\User Data\Default"


async def main():
    print("=" * 60)
    print("  EXTRACCION DE SESION LINKEDIN")
    print("=" * 60)
    print()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print("  Navegando a LinkedIn feed...")
        await page.goto(
            "https://www.linkedin.com/feed/",
            timeout=30000,
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(5)

        cookies = await context.cookies()
        has_li_at = any(c.get("name") == "li_at" for c in cookies)
        print(f"  Cookies: {len(cookies)}, li_at: {'[OK]' if has_li_at else '[FAIL]'}")

        if has_li_at:
            storage = await context.storage_state()
            path = SESSIONS_DIR / "linkedin_session.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(storage, f, indent=2, ensure_ascii=False)
            print(f"\n  [OK] {len(storage.get('cookies', []))} cookies guardadas en {path}")
        else:
            print("\n  [FAIL] No hay sesion activa.")
            print("  En la ventana del navegador, inicia sesion en LinkedIn.")
            print("  Esperando hasta 3 minutos...")
            for i in range(180):
                await asyncio.sleep(1)
                cookies = await context.cookies()
                if any(c.get("name") == "li_at" for c in cookies):
                    storage = await context.storage_state()
                    path = SESSIONS_DIR / "linkedin_session.json"
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(storage, f, indent=2, ensure_ascii=False)
                    print(f"\n  [OK] Sesion guardada tras login manual ({len(storage.get('cookies', []))} cookies)")
                    break
                if i % 15 == 0:
                    print(f"  Esperando... ({i}s)")
            else:
                print(f"\n  [FAIL] No se detecto login en 3 minutos.")

        await context.close()


asyncio.run(main())
