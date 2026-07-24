from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from playwright.async_api import Page
from backend.captcha.detector import CaptchaDetector


@dataclass
class ProfileData:
    headline: Optional[str] = None
    about: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[list[str]] = None
    education: Optional[list[dict]] = None
    experience: Optional[list[dict]] = None
    certifications: Optional[list[str]] = None
    profile_picture_path: Optional[str] = None
    custom_url: Optional[str] = None
    open_to_work: Optional[bool] = None

    def has_any(self) -> bool:
        return any([
            self.headline, self.about, self.location, self.skills,
            self.education, self.experience, self.certifications,
            self.profile_picture_path, self.custom_url,
            self.open_to_work is not None,
        ])


class BaseProfileUpdater(ABC):
    NAME = "base"

    def __init__(self):
        self.captcha_detector_cls = CaptchaDetector

    @abstractmethod
    async def login(self) -> bool:
        ...

    @abstractmethod
    async def update_profile(self, data: ProfileData) -> bool:
        ...

    async def read_current_profile(self) -> ProfileData:
        return ProfileData()

    async def _handle_captcha(self, page: Page) -> bool:
        """Detecta solo CAPTCHAS reales (iframes), no texto suelto."""
        from backend.captcha.detector import CaptchaType, CaptchaResult
        detector = self.captcha_detector_cls(page)

        for ctype, selectors in detector.SIGNS.items():
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        print(f"[{self.NAME}] CAPTCHA detectado: {ctype.value}")
                        from backend.captcha.handler import CaptchaHandler
                        handler = CaptchaHandler(page)
                        return await handler.handle(
                            CaptchaResult(
                                detected=True, captcha_type=ctype,
                                confidence=0.9, detail=f"Selector: {sel}",
                                selector=sel,
                            )
                        )
                except Exception:
                    continue

        return True

    async def _wait_and_fill(self, page: Page, selector: str, value: str, *, timeout: int = 5000) -> bool:
        try:
            el = await page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.click()
                await el.fill("")
                await page.wait_for_timeout(300)
                await el.fill(value)
                return True
        except Exception:
            pass
        return False

    async def _click_safe(self, page: Page, selector: str, *, timeout: int = 5000) -> bool:
        try:
            el = await page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.click()
                return True
        except Exception:
            pass
        return False

    def _setup_browser(self):
        from playwright.async_api import async_playwright
        raise NotImplementedError
