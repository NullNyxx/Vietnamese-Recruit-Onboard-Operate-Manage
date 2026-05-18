"""Unit tests for OAuthService.determine_grant_status."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.identity.api.schemas import GrantStatus
from src.modules.identity.application.oauth_service import OAuthService
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.crypto_utils import CryptoUtils


# Full scope URLs used by Google OAuth2.
GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_MODIFY = "https://www.googleapis.com/auth/gmail.modify"
GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
CALENDAR_EVENTS = "https://www.googleapis.com/auth/calendar.events"

ALL_SCOPES = [GMAIL_READONLY, GMAIL_MODIFY, GMAIL_SEND, CALENDAR_EVENTS]


@pytest.fixture
def oauth_service() -> OAuthService:
    """Create an OAuthService with mocked dependencies for unit testing."""
    settings = MagicMock(spec=AuthSettings)
    crypto = MagicMock(spec=CryptoUtils)
    grant_repo = AsyncMock()
    return OAuthService(settings=settings, crypto=crypto, grant_repository=grant_repo)


class TestDetermineGrantStatus:
    """Tests for OAuthService.determine_grant_status."""

    def test_all_scopes_granted(self, oauth_service: OAuthService) -> None:
        """All Gmail and Calendar scopes present yields both valid."""
        result = oauth_service.determine_grant_status(ALL_SCOPES)
        assert result == GrantStatus(gmail_grant_valid=True, calendar_grant_valid=True)

    def test_no_scopes_granted(self, oauth_service: OAuthService) -> None:
        """Empty scope list yields both invalid."""
        result = oauth_service.determine_grant_status([])
        assert result == GrantStatus(gmail_grant_valid=False, calendar_grant_valid=False)

    def test_only_gmail_scopes(self, oauth_service: OAuthService) -> None:
        """All Gmail scopes without Calendar yields gmail valid only."""
        scopes = [GMAIL_READONLY, GMAIL_MODIFY, GMAIL_SEND]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=True, calendar_grant_valid=False)

    def test_only_calendar_scope(self, oauth_service: OAuthService) -> None:
        """Calendar scope without Gmail yields calendar valid only."""
        scopes = [CALENDAR_EVENTS]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=False, calendar_grant_valid=True)

    def test_partial_gmail_scopes_missing_send(self, oauth_service: OAuthService) -> None:
        """Missing gmail.send means gmail_grant_valid is False."""
        scopes = [GMAIL_READONLY, GMAIL_MODIFY, CALENDAR_EVENTS]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=False, calendar_grant_valid=True)

    def test_partial_gmail_scopes_missing_readonly(self, oauth_service: OAuthService) -> None:
        """Missing gmail.readonly means gmail_grant_valid is False."""
        scopes = [GMAIL_MODIFY, GMAIL_SEND, CALENDAR_EVENTS]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=False, calendar_grant_valid=True)

    def test_partial_gmail_scopes_missing_modify(self, oauth_service: OAuthService) -> None:
        """Missing gmail.modify means gmail_grant_valid is False."""
        scopes = [GMAIL_READONLY, GMAIL_SEND, CALENDAR_EVENTS]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=False, calendar_grant_valid=True)

    def test_unrelated_scopes_ignored(self, oauth_service: OAuthService) -> None:
        """Extra unrelated scopes don't affect the result."""
        scopes = ALL_SCOPES + [
            "https://www.googleapis.com/auth/drive.readonly",
            "openid",
            "email",
            "profile",
        ]
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=True, calendar_grant_valid=True)

    def test_duplicate_scopes_handled(self, oauth_service: OAuthService) -> None:
        """Duplicate scopes in the list don't cause issues."""
        scopes = ALL_SCOPES + ALL_SCOPES
        result = oauth_service.determine_grant_status(scopes)
        assert result == GrantStatus(gmail_grant_valid=True, calendar_grant_valid=True)
