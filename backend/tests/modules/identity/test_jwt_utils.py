"""Unit tests for JWTUtils JWT token operations."""

from datetime import timedelta
from unittest.mock import patch
from datetime import datetime, UTC

import pytest
from jose import jwt

from src.modules.identity.domain.exceptions import InvalidStateError, InvalidTokenError
from src.modules.identity.infrastructure.jwt_utils import JWTUtils


SECRET_KEY = "test-secret-key-for-jwt-utils"
ALGORITHM = "HS256"


@pytest.fixture
def jwt_utils() -> JWTUtils:
    """Create a JWTUtils instance with a test secret key."""
    return JWTUtils(secret_key=SECRET_KEY, algorithm=ALGORITHM)


class TestEncodeDecodeRoundTrip:
    """Tests for encode/decode round-trip correctness."""

    def test_round_trip_preserves_claims(self, jwt_utils: JWTUtils) -> None:
        payload = {"sub": "user-123", "email": "test@example.com"}
        token = jwt_utils.encode(payload, timedelta(minutes=15))
        decoded = jwt_utils.decode(token)

        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@example.com"

    def test_encode_adds_exp_claim(self, jwt_utils: JWTUtils) -> None:
        payload = {"sub": "user-456"}
        token = jwt_utils.encode(payload, timedelta(minutes=30))
        decoded = jwt_utils.decode(token)

        assert "exp" in decoded

    def test_encode_adds_iat_claim(self, jwt_utils: JWTUtils) -> None:
        payload = {"sub": "user-789"}
        token = jwt_utils.encode(payload, timedelta(minutes=15))
        decoded = jwt_utils.decode(token)

        assert "iat" in decoded

    def test_exp_is_correct_duration(self, jwt_utils: JWTUtils) -> None:
        payload = {"sub": "user-abc"}
        token = jwt_utils.encode(payload, timedelta(minutes=15))
        decoded = jwt_utils.decode(token)

        # exp - iat should be approximately 15 minutes (900 seconds)
        diff = decoded["exp"] - decoded["iat"]
        assert diff == 900

    def test_does_not_mutate_original_payload(self, jwt_utils: JWTUtils) -> None:
        payload = {"sub": "user-xyz"}
        original_keys = set(payload.keys())
        jwt_utils.encode(payload, timedelta(minutes=15))

        assert set(payload.keys()) == original_keys


class TestDecodeExpiredToken:
    """Tests for expired token handling."""

    def test_expired_token_raises_invalid_token_error(self, jwt_utils: JWTUtils) -> None:
        # Create a token that expired 1 minute ago
        payload = {"sub": "user-expired"}
        token = jwt_utils.encode(payload, timedelta(minutes=-1))

        with pytest.raises(InvalidTokenError):
            jwt_utils.decode(token)


class TestDecodeTamperedToken:
    """Tests for tampered token handling."""

    def test_wrong_secret_raises_invalid_token_error(self) -> None:
        utils1 = JWTUtils(secret_key="secret-one", algorithm=ALGORITHM)
        utils2 = JWTUtils(secret_key="secret-two", algorithm=ALGORITHM)

        token = utils1.encode({"sub": "user-tampered"}, timedelta(minutes=15))

        with pytest.raises(InvalidTokenError):
            utils2.decode(token)

    def test_malformed_token_raises_invalid_token_error(self, jwt_utils: JWTUtils) -> None:
        with pytest.raises(InvalidTokenError):
            jwt_utils.decode("not.a.valid.jwt.token")

    def test_empty_string_raises_invalid_token_error(self, jwt_utils: JWTUtils) -> None:
        with pytest.raises(InvalidTokenError):
            jwt_utils.decode("")

    def test_modified_payload_raises_invalid_token_error(self, jwt_utils: JWTUtils) -> None:
        token = jwt_utils.encode({"sub": "user-original"}, timedelta(minutes=15))
        # Tamper with the payload portion (second segment)
        parts = token.split(".")
        # Flip a character in the payload
        tampered_payload = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        with pytest.raises(InvalidTokenError):
            jwt_utils.decode(tampered_token)


class TestCreateStateToken:
    """Tests for CSRF state token creation."""

    def test_state_token_round_trip(self, jwt_utils: JWTUtils) -> None:
        data = {"nonce": "abc123", "redirect": "/dashboard"}
        token = jwt_utils.create_state_token(data)
        decoded = jwt_utils.verify_state_token(token)

        assert decoded["nonce"] == "abc123"
        assert decoded["redirect"] == "/dashboard"

    def test_state_token_includes_purpose_claim(self, jwt_utils: JWTUtils) -> None:
        data = {"nonce": "xyz"}
        token = jwt_utils.create_state_token(data)
        decoded = jwt_utils.verify_state_token(token)

        assert decoded["purpose"] == "state"

    def test_state_token_has_10_minute_expiry(self, jwt_utils: JWTUtils) -> None:
        data = {"nonce": "test"}
        token = jwt_utils.create_state_token(data)
        decoded = jwt_utils.verify_state_token(token)

        # exp - iat should be 600 seconds (10 minutes)
        diff = decoded["exp"] - decoded["iat"]
        assert diff == 600

    def test_state_token_does_not_mutate_input(self, jwt_utils: JWTUtils) -> None:
        data = {"nonce": "original"}
        original_keys = set(data.keys())
        jwt_utils.create_state_token(data)

        assert set(data.keys()) == original_keys


class TestVerifyStateToken:
    """Tests for CSRF state token verification."""

    def test_expired_state_token_raises_invalid_state_error(self, jwt_utils: JWTUtils) -> None:
        # Manually create an expired state token
        now = datetime.now(UTC)
        payload = {
            "nonce": "expired",
            "purpose": "state",
            "exp": now - timedelta(minutes=1),
            "iat": now - timedelta(minutes=11),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(InvalidStateError):
            jwt_utils.verify_state_token(token)

    def test_wrong_secret_raises_invalid_state_error(self) -> None:
        utils1 = JWTUtils(secret_key="key-one", algorithm=ALGORITHM)
        utils2 = JWTUtils(secret_key="key-two", algorithm=ALGORITHM)

        token = utils1.create_state_token({"nonce": "test"})

        with pytest.raises(InvalidStateError):
            utils2.verify_state_token(token)

    def test_access_token_rejected_as_state_token(self, jwt_utils: JWTUtils) -> None:
        # An access token (no purpose claim) should be rejected
        token = jwt_utils.encode({"sub": "user-123"}, timedelta(minutes=15))

        with pytest.raises(InvalidStateError):
            jwt_utils.verify_state_token(token)

    def test_wrong_purpose_raises_invalid_state_error(self, jwt_utils: JWTUtils) -> None:
        # Token with wrong purpose claim
        now = datetime.now(UTC)
        payload = {
            "nonce": "test",
            "purpose": "refresh",
            "exp": now + timedelta(minutes=10),
            "iat": now,
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(InvalidStateError):
            jwt_utils.verify_state_token(token)

    def test_malformed_token_raises_invalid_state_error(self, jwt_utils: JWTUtils) -> None:
        with pytest.raises(InvalidStateError):
            jwt_utils.verify_state_token("garbage.token.here")
