"""Tests para LinkedInProfileUpdater (version simplificada)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.profile_updater.linkedin_updater import LinkedInProfileUpdater
from backend.profile_updater.updater import ProfileData


class TestLinkedInProfileUpdater:
    @pytest.mark.asyncio
    async def test_login_success(self):
        """login() siempre retorna True."""
        updater = LinkedInProfileUpdater()
        ok = await updater.login()
        assert ok

    @pytest.mark.asyncio
    async def test_read_current_profile_returns_empty(self):
        """read_current_profile() retorna ProfileData vacio."""
        updater = LinkedInProfileUpdater()
        data = await updater.read_current_profile()
        assert isinstance(data, ProfileData)
        assert data.headline is None
        assert data.about is None

    @pytest.mark.asyncio
    async def test_update_profile_returns_false(self):
        """update_profile() retorna False (LinkedIn bloqueado)."""
        updater = LinkedInProfileUpdater()
        data = ProfileData(headline="Test")
        ok = await updater.update_profile(data)
        assert not ok
