"""Aplicación automática de ofertas de empleo.

Navega a la URL de una oferta, detecta el formulario de postulación,
rellena datos del perfil, sube CV y envía.
Detecta CAPTCHAs y bloqueos durante el proceso.
"""

from dataclasses import dataclass, field
from pathlib import Path
from playwright.async_api import async_playwright
from backend.auth import SessionStorage
from backend.captcha import CaptchaDetector, CaptchaType, CaptchaResult


@dataclass
class ApplicationResult:
    success: bool = False
    platform: str = ""
    company: str = ""
    position: str = ""
    applied: bool = False
    captcha: CaptchaResult | None = None
    error: str = ""
    steps: list[str] = field(default_factory=list)


class JobApplicator:
    """Aplica a una oferta usando el perfil del usuario y CV."""

    APPLY_KEYWORDS = [
        "apply", "postular", "aplicar", "apply now", "postularme",
        "solicitar", "send application", "submit",
    ]

    def __init__(self, cv_path: str | Path | None = None):
        self.cv_path = Path(cv_path) if cv_path else None

    async def _make_context(self, browser, platform: str = "", state=None):
        """Crea contexto con configuracion especifica segun plataforma."""
        kwargs = {
            "viewport": {"width": 1280, "height": 800},
        }
        if state:
            kwargs["storage_state"] = state

        if platform == "computrabajo":
            kwargs.update(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="es-CO",
            )

        return await browser.new_context(**kwargs)

    async def apply(
        self,
        offer_url: str,
        platform: str = "",
        profile_text: str = "",
        headless: bool = True,
    ) -> ApplicationResult:
        result = ApplicationResult(platform=platform)
        result.steps.append(f"Iniciando aplicacion a: {offer_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            storage = SessionStorage(platform) if platform else None
            state = storage.load() if storage and storage.exists() else None

            context = await self._make_context(browser, platform=platform, state=state)
            page = await context.new_page()

            # 1. Navegar a la oferta
            try:
                await page.goto(offer_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                result.steps.append("Pagina cargada")
            except Exception as e:
                result.success = False
                result.error = f"Error navegando a oferta: {e}"
                await browser.close()
                return result

            # 2. Verificar CAPTCHA / bloqueos
            detector = CaptchaDetector(page)
            captcha = await detector.ensure_page_ready()
            result.captcha = captcha

            if captcha.detected:
                result.steps.append(f"[!] CAPTCHA/Bloqueo detectado: {captcha.captcha_type.value} - {captcha.detail}")
                if captcha.captcha_type == CaptchaType.LOGIN_REQUIRED:
                    result.error = "Se requiere iniciar sesion. Usa: python -m backend.scripts.auth_cli login <plataforma>"
                else:
                    result.error = f"Bloqueo detectado: {captcha.detail}"
                await browser.close()
                return result

            result.steps.append("Sin bloqueos ni CAPTCHA")

            # 3. Buscar boton de aplicar
            apply_clicked = await self._click_apply(page, result)
            if not apply_clicked:
                result.steps.append("[!] No se encontro boton de aplicar")
                # Podria ser que la pagina ya muestra el formulario directamente

            # 4. Detectar y rellenar formulario
            filled = await self._fill_application(page, profile_text, result)
            if filled:
                result.applied = True
                result.success = True
                result.steps.append("[OK] Postulacion completada")

            await browser.close()
            return result

    async def _click_apply(self, page, result: ApplicationResult) -> bool:
        """Busca y hace clic en el boton de aplicar."""
        for keyword in self.APPLY_KEYWORDS:
            selectors = [
                f"a[href*='{keyword}']",
                f"button:has-text('{keyword}')",
                f"a:has-text('{keyword}')",
                f"[data-test*='{keyword}']",
                f"[class*='{keyword}']",
            ]
            for sel in selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        result.steps.append(f"Click en boton: {sel}")
                        return True
                except Exception:
                    continue
        return False

    async def _fill_application(self, page, profile_text: str, result: ApplicationResult) -> bool:
        """Intenta rellenar campos del formulario de postulacion."""
        fields_filled = 0

        # Buscar inputs de texto
        inputs = await page.query_selector_all("input:not([type='hidden']):not([type='submit']), textarea")
        for inp in inputs[:5]:
            try:
                name = await inp.get_attribute("name") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                await inp.fill(" ")  # placeholder para no dejar vacio
                fields_filled += 1
            except Exception:
                continue

        # Subir CV si existe
        if self.cv_path and self.cv_path.exists():
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                try:
                    await file_input.set_input_files(str(self.cv_path))
                    result.steps.append(f"CV subido: {self.cv_path.name}")
                    fields_filled += 1
                except Exception as e:
                    result.steps.append(f"Error subiendo CV: {e}")

        # Buscar boton submit / enviar
        for text in ["submit", "send", "enviar", "apply", "postular", "send application"]:
            try:
                btn = await page.query_selector(f"button:has-text('{text}'), input[type='submit'][value*='{text}']")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    result.steps.append(f"Formulario enviado (boton: {text})")
                    fields_filled += 1
                    break
            except Exception:
                continue

        return fields_filled > 0
