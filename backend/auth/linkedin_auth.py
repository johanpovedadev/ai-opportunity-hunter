"""Autenticador para LinkedIn."""

from playwright.async_api import Page
from backend.auth.authenticator import BaseAuthenticator


class LinkedInAuthenticator(BaseAuthenticator):
    @property
    def platform(self) -> str:
        return "linkedin"

    @property
    def login_url(self) -> str:
        return "https://www.linkedin.com/login"

    async def _on_page_ready(self, page: Page) -> None:
        """Espera a que el formulario de login esté listo."""
        await page.wait_for_selector("#username", timeout=15000)

    async def _validate_session(self, page: Page) -> None:
        """Verifica que redirigió al feed principal."""
        current = page.url
        if "feed" in current or "checkpoint" in current:
            print(f"  [OK] Sesion detectada en: {current[:60]}")
        else:
            print(f"  [!] Posiblemente no autenticado. URL actual: {current[:60]}")
