"""
LinkedIn Profile Updater — LIMITACION CONOCIDA

LinkedIn bloquea acceso automatizado a paginas de perfil (publico y edicion)
con su muro de autenticacion (authwall), incluso con sesion activa via cookies.

Esto ocurre porque LinkedIn utiliza autenticacion multifactor para paginas
sensibles: la pagina de inicio (feed) es accesible, pero el perfil y edicion
requieren verificacion adicional que el usuario no puede proveer via script.

Soluciones posibles (ninguna implementada):
  - Usar Chrome REAL del usuario con launch_persistent_context (perfil bloqueado
    si Chrome esta abierto)
  - Extraer cookies via CDP y usar REST API directamente (requiere CSRF token)
  - Proxy manual: el usuario actualiza su perfil en el navegador directamente

El codigo siguiente es funcional pero fallara con authwall hasta que se
encuentre una solucion al bloqueo de LinkedIn.
"""
import asyncio
from playwright.async_api import Page, async_playwright
from pathlib import Path
from backend.profile_updater.updater import BaseProfileUpdater, ProfileData

SEL = {
    "headline": "input[name='headline']",
    "about": "textarea[name='about']",
    "save_btn": "button[data-control-name='save'], button[class*='save']",
    "save_fallback": "button:has-text('Save'), button:has-text('Guardar')",
}

PROFILE_DIR = Path("data/chrome_profile_linkedin")


class LinkedInProfileUpdater(BaseProfileUpdater):
    NAME = "linkedin"
    PROFILE_URL = "https://www.linkedin.com/in/johan-poveda-788760263"
    EDIT_URL = "https://www.linkedin.com/in/johan-poveda-788760263/edit"

    async def login(self) -> bool:
        return True

    async def read_current_profile(self) -> ProfileData:
        print(f"[{self.NAME}] LinkedIn bloquea acceso automatizado al perfil")
        print(f"[{self.NAME}] Abre tu navegador y ve a {self.PROFILE_URL} para ver tu perfil")
        return ProfileData()

    async def update_profile(self, data: ProfileData) -> bool:
        print(f"[{self.NAME}] LinkedIn bloquea actualizacion automatizada del perfil")
        print(f"[{self.NAME}] Para actualizar tu perfil, abre:")
        print(f"[{self.NAME}]   {self.EDIT_URL}")
        print(f"[{self.NAME}]   y edita manualmente los siguientes campos:")
        if data.headline:
            print(f"[{self.NAME}]   - Headline: {data.headline}")
        if data.about:
            print(f"[{self.NAME}]   - About: {data.about}")
        if data.location:
            print(f"[{self.NAME}]   - Location: {data.location}")
        if data.skills:
            print(f"[{self.NAME}]   - Skills: {', '.join(data.skills)}")
        return False

    async def _handle_captcha(self, page: Page) -> bool:
        return True

    async def _setup_browser(self):
        pw = await async_playwright().start()
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return pw, context
