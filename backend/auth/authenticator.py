"""Autenticador base para plataformas de empleo."""

from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Page
from backend.auth.session import SessionStorage


class BaseAuthenticator(ABC):
    """Flujo de autenticación asistida para una plataforma."""

    @property
    @abstractmethod
    def platform(self) -> str: ...

    @property
    @abstractmethod
    def login_url(self) -> str: ...

    @property
    def timeout(self) -> int:
        return 120000

    def __init__(self):
        self.storage = SessionStorage(self.platform)

    async def authenticate(self, headless: bool = False) -> bool:
        """Abre navegador visible, usuario inicia sesión manualmente, guarda sesión."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()

            print(f"\n=== Autenticación: {self.platform} ===")
            print(f"1. Abriendo {self.login_url} ...")
            await page.goto(self.login_url, timeout=self.timeout, wait_until="domcontentloaded")

            await self._on_page_ready(page)

            print("2. Navegador abierto en modo visible.")
            print("   Inicia sesión manualmente en la página.")
            print("   Cuando hayas terminado, presiona Enter aquí para guardar la sesión.")
            input("   [Presiona Enter después de iniciar sesión]...")

            try:
                await self._validate_session(page)
            except Exception as e:
                print(f"  [!] Advertencia al validar sesion: {e}")

            storage = await context.storage_state()
            self.storage.save(storage)
            n_cookies = len(storage.get("cookies", []))
            print(f"3. Sesión guardada ({n_cookies} cookies) en {self.storage.path}")
            await browser.close()
            return True

    async def get_context(self, playwright, **kwargs):
        """Crea un context de navegador con la sesión cargada si existe."""
        storage = self.storage.load()
        kwargs.setdefault("viewport", {"width": 1280, "height": 800})
        if storage:
            kwargs["storage_state"] = storage
        return await playwright.chromium.launch_persistent_context(
            user_data_dir=f"data/sessions/{self.platform}_profile",
            **kwargs,
        )

    async def _on_page_ready(self, page: Page) -> None:
        """Hook para pasos adicionales después de cargar la página de login."""
        pass

    async def _validate_session(self, page: Page) -> None:
        """Verifica que la sesión sea válida después del login."""
        pass

    def session_info(self) -> dict:
        return self.storage.info()
