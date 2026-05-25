"""Unit tests for TokenService token management operations."""

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.modules.identity.api.schemas import TokenPayload
from src.modules.identity.application.token_service import TokenService
from src.modules.identity.domain.exceptions import InvalidTokenError
from src.modules.identity.infrastructure.config import AuthSettings
from src.modules.identity.infrastructure.jwt_utils import JWTUtils


SECRET_KEY = "test-secret-key-for-token-service"
ALGORITHM = "HS256"


def _make_settings(**overrides: object) -> AuthSettings:
    """Create AuthSettings with test defaults."""
    defaults = {
        "google_client_id": "test-client-id",
        "google_client_secret": "test-client-secret",
        "jwt_secret_key": SECRET_KEY,
        "jwt_algorithm": ALGORITHM,
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 7,
        "oauth_token_encryption_key": "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcw==",
    }
    defaults.update(overrides)
    return AuthSettings(**defaults)


@pytest.fixture
def jwt_utils() -> JWTUtils:
    """Create a JWTUtils instance with a test secret key."""
    return JWTUtils(secret_key=SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def settings() -> AuthSettings:
    """Create AuthSettings with test defaults."""
    return _make_settings()


@pytest.fixture
def mock_repo() -> AsyncMock:
    """Create a mock RefreshTokenRepository."""
    repo = AsyncMock()
    repo.find_by_token_hash = AsyncMock(return_value=None)
    repo.revoke_all_for_user = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def token_service(jwt_utils: JWTUtils, settings: AuthSettings, mock_repo: AsyncMock) -> TokenService:
    """Create a TokenService with test dependencies."""
    return TokenService(
        jwt_utils=jwt_utils,
        settings=settings,
        refresh_token_repository=mock_repo,
    )


class TestCreateAccessToken:
    """Tests for access token creation."""

    def test_creates_valid_jwt(self, token_service: TokenService, jwt_utils: JWTUtils) -> None:
        user_id = uuid4()
        email = "hr@example.com"

        token = token_service.create_access_token(user_id, email)
        decoded = jwt_utils.decode(token)

        assert decoded["sub"] == str(user_id)
        assert decoded["email"] == email

    def test_includes_employee_id_when_provided(
        self, token_service: TokenService, jwt_utils: JWTUtils
    ) -> None:
        user_id = uuid4()
        employee_id = uuid4()
        email = "employee@example.com"

        token = token_service.create_access_token(user_id, email, employee_id=employee_id)
        decoded = jwt_utils.decode(token)

        assert decoded["employee_id"] == str(employee_id)

    def test_omits_employee_id_when_none(
        self, token_service: TokenService, jwt_utils: JWTUtils
    ) -> None:
        user_id = uuid4()
        email = "hr@example.com"

        token = token_service.create_access_token(user_id, email, employee_id=None)
        decoded = jwt_utils.decode(token)

        assert "employee_id" not in decoded

    def test_omits_employee_id_when_not_provided(
        self, token_service: TokenService, jwt_utils: JWTUtils
    ) -> None:
        user_id = uuid4()
        email = "hr@example.com"

        token = token_service.create_access_token(user_id, email)
        decoded = jwt_utils.decode(token)

        assert "employee_id" not in decoded

    def test_token_has_15_minute_expiry(self, token_service: TokenService, jwt_utils: JWTUtils) -> None:
        user_id = uuid4()
        email = "hr@example.com"

        token = token_service.create_access_token(user_id, email)
        decoded = jwt_utils.decode(token)

        diff = decoded["exp"] - decoded["iat"]
        assert diff == 900  # 15 minutes in seconds

    def test_custom_expiry_from_settings(self, jwt_utils: JWTUtils, mock_repo: AsyncMock) -> None:
        settings = _make_settings(access_token_expire_minutes=30)
        service = TokenService(jwt_utils=jwt_utils, settings=settings, refresh_token_repository=mock_repo)

        token = service.create_access_token(uuid4(), "test@example.com")
        decoded = jwt_utils.decode(token)

        diff = decoded["exp"] - decoded["iat"]
        assert diff == 1800  # 30 minutes in seconds

    def test_sub_claim_is_string(self, token_service: TokenService, jwt_utils: JWTUtils) -> None:
        user_id = uuid4()
        token = token_service.create_access_token(user_id, "test@example.com")
        decoded = jwt_utils.decode(token)

        assert isinstance(decoded["sub"], str)
        assert decoded["sub"] == str(user_id)


class TestCreateRefreshToken:
    """Tests for refresh token creation."""

    def test_returns_tuple_of_raw_and_hash(self, token_service: TokenService) -> None:
        result = token_service.create_refresh_token(uuid4())

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hash_is_sha256_of_raw(self, token_service: TokenService) -> None:
        raw_token, token_hash = token_service.create_refresh_token(uuid4())

        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert token_hash == expected_hash

    def test_raw_token_is_url_safe(self, token_service: TokenService) -> None:
        raw_token, _ = token_service.create_refresh_token(uuid4())

        # URL-safe base64 characters only
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', raw_token)

    def test_hash_is_64_char_hex(self, token_service: TokenService) -> None:
        _, token_hash = token_service.create_refresh_token(uuid4())

        assert len(token_hash) == 64
        assert all(c in "0123456789abcdef" for c in token_hash)

    def test_generates_unique_tokens(self, token_service: TokenService) -> None:
        user_id = uuid4()
        raw1, hash1 = token_service.create_refresh_token(user_id)
        raw2, hash2 = token_service.create_refresh_token(user_id)

        assert raw1 != raw2
        assert hash1 != hash2


class TestVerifyAccessToken:
    """Tests for access token verification."""

    def test_returns_token_payload(self, token_service: TokenService) -> None:
        user_id = uuid4()
        email = "hr@example.com"
        token = token_service.create_access_token(user_id, email)

        payload = token_service.verify_access_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == user_id
        assert payload.email == email

    def test_returns_employee_id_when_present(self, token_service: TokenService) -> None:
        user_id = uuid4()
        employee_id = uuid4()
        email = "employee@example.com"
        token = token_service.create_access_token(user_id, email, employee_id=employee_id)

        payload = token_service.verify_access_token(token)

        assert payload.employee_id == employee_id

    def test_returns_none_employee_id_when_absent(self, token_service: TokenService) -> None:
        user_id = uuid4()
        email = "hr@example.com"
        token = token_service.create_access_token(user_id, email)

        payload = token_service.verify_access_token(token)

        assert payload.employee_id is None

    def test_expired_token_raises_invalid_token_error(
        self, jwt_utils: JWTUtils, settings: AuthSettings, mock_repo: AsyncMock
    ) -> None:
        service = TokenService(jwt_utils=jwt_utils, settings=settings, refresh_token_repository=mock_repo)
        # Create a token that's already expired
        expired_token = jwt_utils.encode(
            {"sub": str(uuid4()), "email": "test@example.com"},
            timedelta(minutes=-1),
        )

        with pytest.raises(InvalidTokenError):
            service.verify_access_token(expired_token)

    def test_malformed_token_raises_invalid_token_error(self, token_service: TokenService) -> None:
        with pytest.raises(InvalidTokenError):
            token_service.verify_access_token("not.a.valid.token")

    def test_missing_claims_raises_invalid_token_error(
        self, jwt_utils: JWTUtils, settings: AuthSettings, mock_repo: AsyncMock
    ) -> None:
        service = TokenService(jwt_utils=jwt_utils, settings=settings, refresh_token_repository=mock_repo)
        # Token without email claim
        token = jwt_utils.encode({"sub": str(uuid4())}, timedelta(minutes=15))

        with pytest.raises(InvalidTokenError):
            service.verify_access_token(token)

    def test_wrong_secret_raises_invalid_token_error(
        self, settings: AuthSettings, mock_repo: AsyncMock
    ) -> None:
        other_jwt = JWTUtils(secret_key="different-secret", algorithm=ALGORITHM)
        service = TokenService(jwt_utils=other_jwt, settings=settings, refresh_token_repository=mock_repo)

        # Token signed with the test secret
        correct_jwt = JWTUtils(secret_key=SECRET_KEY, algorithm=ALGORITHM)
        token = correct_jwt.encode(
            {"sub": str(uuid4()), "email": "test@example.com"},
            timedelta(minutes=15),
        )

        with pytest.raises(InvalidTokenError):
            service.verify_access_token(token)


class TestRefreshAccessToken:
    """Tests for refresh token validation and access token reissue."""

    @pytest.fixture
    def valid_record(self) -> AsyncMock:
        """Create a mock refresh token record that is valid."""
        record = AsyncMock()
        record.user_id = uuid4()
        record.email = "hr@example.com"
        record.token_hash = "somehash"
        record.expires_at = datetime.now(UTC) + timedelta(days=7)
        record.revoked_at = None
        return record

    async def test_issues_new_access_token(
        self, token_service: TokenService, mock_repo: AsyncMock, valid_record: AsyncMock, jwt_utils: JWTUtils
    ) -> None:
        raw_token = "test-raw-refresh-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        valid_record.token_hash = token_hash
        mock_repo.find_by_token_hash.return_value = valid_record

        new_access_token = await token_service.refresh_access_token(raw_token)

        decoded = jwt_utils.decode(new_access_token)
        assert decoded["sub"] == str(valid_record.user_id)
        assert decoded["email"] == valid_record.email

    async def test_hashes_token_for_lookup(
        self, token_service: TokenService, mock_repo: AsyncMock, valid_record: AsyncMock
    ) -> None:
        raw_token = "my-refresh-token"
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        mock_repo.find_by_token_hash.return_value = valid_record

        await token_service.refresh_access_token(raw_token)

        mock_repo.find_by_token_hash.assert_called_once_with(expected_hash)

    async def test_not_found_raises_invalid_token_error(
        self, token_service: TokenService, mock_repo: AsyncMock
    ) -> None:
        mock_repo.find_by_token_hash.return_value = None

        with pytest.raises(InvalidTokenError):
            await token_service.refresh_access_token("unknown-token")

    async def test_revoked_token_raises_invalid_token_error(
        self, token_service: TokenService, mock_repo: AsyncMock, valid_record: AsyncMock
    ) -> None:
        valid_record.revoked_at = datetime.now(UTC) - timedelta(hours=1)
        mock_repo.find_by_token_hash.return_value = valid_record

        with pytest.raises(InvalidTokenError):
            await token_service.refresh_access_token("some-token")

    async def test_expired_token_raises_invalid_token_error(
        self, token_service: TokenService, mock_repo: AsyncMock, valid_record: AsyncMock
    ) -> None:
        valid_record.expires_at = datetime.now(UTC) - timedelta(hours=1)
        mock_repo.find_by_token_hash.return_value = valid_record

        with pytest.raises(InvalidTokenError):
            await token_service.refresh_access_token("some-token")


class TestRevokeUserTokens:
    """Tests for revoking all user tokens."""

    async def test_delegates_to_repository(
        self, token_service: TokenService, mock_repo: AsyncMock
    ) -> None:
        user_id = uuid4()

        await token_service.revoke_user_tokens(user_id)

        mock_repo.revoke_all_for_user.assert_called_once_with(user_id)

    async def test_does_not_raise_on_no_tokens(
        self, token_service: TokenService, mock_repo: AsyncMock
    ) -> None:
        user_id = uuid4()
        mock_repo.revoke_all_for_user.return_value = None

        # Should not raise
        await token_service.revoke_user_tokens(user_id)
