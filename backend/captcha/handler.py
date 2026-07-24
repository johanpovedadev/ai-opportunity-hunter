"""Manejo de CAPTCHA: notifica al usuario y permite resolucion manual."""

from playwright.async_api import Page
from backend.captcha.detector import CaptchaResult, CaptchaType


class CaptchaHandler:
    """Estrategias para manejar CAPTCHAs detectados."""

    def __init__(self, page: Page):
        self.page = page

    async def handle(self, captcha: CaptchaResult) -> bool:
        """Retorna True si se pudo resolver o saltar el CAPTCHA."""

        if captcha.captcha_type == CaptchaType.RECAPTCHA_V2:
            return await self._handle_recaptcha_v2(captcha)

        elif captcha.captcha_type == CaptchaType.H_CAPTCHA:
            return await self._handle_hcaptcha(captcha)

        elif captcha.captcha_type == CaptchaType.CLOUDFLARE:
            return await self._handle_cloudflare(captcha)

        elif captcha.captcha_type == CaptchaType.BLOCKED:
            return await self._handle_blocked(captcha)

        elif captcha.captcha_type == CaptchaType.LOGIN_REQUIRED:
            return await self._handle_login_required(captcha)

        return False

    async def _handle_recaptcha_v2(self, captcha: CaptchaResult) -> bool:
        """Intenta hacer clic en el checkbox de reCAPTCHA."""
        try:
            frame = await self._find_recaptcha_frame()
            if frame:
                checkbox = await frame.query_selector(".recaptcha-checkbox")
                if checkbox:
                    await checkbox.click()
                    await self.page.wait_for_timeout(3000)
                    return True

            print("\n  [!] reCAPTCHA detectado -- No se pudo resolver automaticamente.")
            print("  Para resolverlo manualmente:")
            print(f"    1. Abre la URL en un navegador normal")
            print(f"    2. Resuelve el CAPTCHA")
            print(f"    3. Guarda la sesion con: python -m backend.scripts.cli auth login <plataforma>")
            return False
        except Exception:
            return False

    async def _handle_hcaptcha(self, captcha: CaptchaResult) -> bool:
        print("\n  [!] hCaptcha detectado -- No se puede resolver automaticamente.")
        return False

    async def _handle_cloudflare(self, captcha: CaptchaResult) -> bool:
        print("\n  [!] Cloudflare Challenge detectado -- Esperando resolucion...")
        try:
            await self.page.wait_for_url(
                lambda url: "challenge" not in url,
                timeout=60000,
            )
            return True
        except Exception:
            print("  [FAIL] No se pudo superar Cloudflare.")
            return False

    async def _handle_blocked(self, captcha: CaptchaResult) -> bool:
        print(f"\n  [!] Bloqueo detectado: {captcha.detail}")
        print("  Posibles soluciones:")
        print("    - Usar una sesion autenticada (python -m backend.scripts.cli auth login)")
        print("    - Reducir velocidad de scraping")
        print("    - Usar un proxy diferente")
        return False

    async def _handle_login_required(self, captcha: CaptchaResult) -> bool:
        print(f"\n  [!] Se requiere iniciar sesion.")
        print("  Ejecuta: python -m backend.scripts.cli auth login <plataforma>")
        return False

    async def _find_recaptcha_frame(self):
        """Busca el iframe de reCAPTCHA en la pagina."""
        for selector in [
            "iframe[src*='google.com/recaptcha']",
            "iframe[title*='recaptcha']",
            "iframe[src*='recaptcha']",
        ]:
            el = await self.page.query_selector(selector)
            if el:
                try:
                    return await el.content_frame()
                except Exception:
                    continue
        return None
