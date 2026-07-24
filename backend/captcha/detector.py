"""Detector de CAPTCHA y bloqueos en plataformas de empleo.

Identifica si una página tiene:
- CAPTCHA (reCAPTCHA, hCaptcha, Cloudflare Turnstile)
- Bloqueo por automatización detectada
- Página de login requerida
- Rate limiting / demasiados requests
"""

from dataclasses import dataclass
from enum import Enum
from playwright.async_api import Page


class CaptchaType(Enum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    H_CAPTCHA = "h_captcha"
    CLOUDFLARE = "cloudflare"
    BLOCKED = "blocked"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"
    NONE = "none"


@dataclass
class CaptchaResult:
    detected: bool
    captcha_type: CaptchaType = CaptchaType.NONE
    confidence: float = 0.0
    detail: str = ""
    selector: str = ""


class CaptchaDetector:
    """Analiza una página de Playwright en busca de CAPTCHAs o bloqueos."""

    SIGNS = {
        CaptchaType.RECAPTCHA_V2: [
            "iframe[src*='google.com/recaptcha']",
            "iframe[src*='recaptcha']",
            "div.g-recaptcha",
            ".recaptcha",
            "[data-sitekey]",
        ],
        CaptchaType.H_CAPTCHA: [
            "iframe[src*='hcaptcha.com']",
            ".h-captcha",
            "[data-hcaptcha]",
        ],
        CaptchaType.CLOUDFLARE: [
            "iframe[src*='cloudflare.com']",
            "#cf-please-wait",
            ".cf-browser-verification",
            "[id*='challenge-running']",
        ],
    }

    BLOCKED_PATTERNS = [
        r"\bautomated\b", r"\bautomation\b", r"\bbot\b", r"\bunusual traffic\b",
        r"\bplease verify\b", r"\bsecurity check\b", r"\bsorry\b",
        r"\baccess denied\b", r"\btoo many requests\b", r"\brate limit",
        r"\bplease wait\b", r"\bchallenge\b",
    ]

    LOGIN_PATTERNS = [
        r"\bsign in\b", r"\blog in\b", r"\blogin\b",
        r"\bwe couldn't find any jobs\b",
    ]

    def __init__(self, page: Page):
        self.page = page

    async def check_all(self) -> CaptchaResult:
        """Ejecuta todas las verificaciones y retorna el primer problema detectado."""

        result = await self._check_selectors()
        if result.detected:
            return result

        result = await self._check_text()
        if result.detected:
            return result

        return CaptchaResult(detected=False, captcha_type=CaptchaType.NONE)

    async def _check_selectors(self) -> CaptchaResult:
        for ctype, selectors in self.SIGNS.items():
            for sel in selectors:
                try:
                    el = await self.page.query_selector(sel)
                    if el:
                        return CaptchaResult(
                            detected=True,
                            captcha_type=ctype,
                            confidence=0.9,
                            detail=f"Selector encontrado: {sel}",
                            selector=sel,
                        )
                except Exception:
                    continue
        return CaptchaResult(detected=False)

    async def _check_text(self) -> CaptchaResult:
        import re
        try:
            text = (await self.page.text_content("body") or "").lower()
            url = self.page.url.lower()
        except Exception:
            return CaptchaResult(detected=False)

        for pattern in CaptchaDetector.BLOCKED_PATTERNS:
            if re.search(pattern, text):
                return CaptchaResult(
                    detected=True,
                    captcha_type=CaptchaType.BLOCKED,
                    confidence=0.7,
                    detail=f"Texto bloqueo detectado: '{pattern}'",
                )

        for pattern in CaptchaDetector.LOGIN_PATTERNS:
            if re.search(pattern, text[:1000]) or re.search(pattern, url):
                return CaptchaResult(
                    detected=True,
                    captcha_type=CaptchaType.LOGIN_REQUIRED,
                    confidence=0.8,
                    detail=f"Login requerido: '{pattern}' en URL o pagina",
                )

        return CaptchaResult(detected=False)

    async def ensure_page_ready(self, timeout: int = 15000) -> CaptchaResult:
        """Espera a que la página cargue y verifica que no haya bloqueos."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass

        result = await self.check_all()
        return result
