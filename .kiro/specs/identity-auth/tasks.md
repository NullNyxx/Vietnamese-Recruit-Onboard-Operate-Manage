# Implementation Plan: Identity & Auth

## Overview

This plan implements the Identity & Auth module for Vroom HR using FastAPI, SQLAlchemy/SQLModel, python-jose (JWT), Authlib (OAuth2), and the cryptography library (AES-256-GCM). The implementation follows the modular monolith structure at `backend/src/modules/identity/` with domain, application, infrastructure, and API layers.

## Tasks

- [x] 1. Set up module structure and configuration
  - [x] 1.1 Create the identity module directory structure
    - Create `backend/src/modules/identity/` with subdirectories: `domain/`, `application/`, `infrastructure/`, `api/`
    - Add `__init__.py` files to each package
    - _Requirements: Project structure from design_
  - [x] 1.2 Implement AuthSettings (Pydantic Settings)
    - Create `backend/src/modules/identity/infrastructure/config.py`
    - Define `AuthSettings(BaseSettings)` with all fields: google_client_id, google_client_secret, google_redirect_uri, jwt_secret_key, jwt_algorithm, access_token_expire_minutes, refresh_token_expire_days, oauth_token_encryption_key, whitelist_file_path, rate_limit_login_max, rate_limit_login_window_seconds, frontend_url
    - Use `env_prefix = "AUTH_"` for environment variable mapping
    - _Requirements: Design Configuration section_
  - [x] 1.3 Create domain entities (SQLModel)
    - Create `backend/src/modules/identity/domain/entities.py`
    - Implement `User`, `OAuthGrant`, `RefreshToken` SQLModel table classes as specified in the design data models
    - _Requirements: 4.1, 5.2, 9.1_
  - [x] 1.4 Create domain exceptions
    - Create `backend/src/modules/identity/domain/exceptions.py`
    - Implement exception hierarchy: `AuthError`, `InvalidStateError`, `GoogleAuthError`, `AccessDeniedError`, `InsufficientScopeError`, `InvalidTokenError`, `RateLimitExceededError`
    - Each exception has `status_code`, `error_code`, and `message` attributes
    - _Requirements: 2.2, 2.4, 3.2, 6.2, 6.3, 8.1, 12.1_
  - [x] 1.5 Create Pydantic schemas
    - Create `backend/src/modules/identity/api/schemas.py`
    - Implement: `TokenPayload`, `GoogleTokens`, `GoogleUserInfo`, `GrantStatus`, `UserResponse`, `GrantStatusResponse`, `LoginRedirect`
    - _Requirements: 5.1, 11.3_

- [x] 2. Implement infrastructure layer (crypto, JWT, whitelist)
  - [x] 2.1 Implement CryptoUtils (AES-256-GCM)
    - Create `backend/src/modules/identity/infrastructure/crypto_utils.py`
    - Implement `encrypt(plaintext: str) -> str` — generates random 12-byte nonce, encrypts with AES-256-GCM, returns base64-encoded (nonce + ciphertext + tag)
    - Implement `decrypt(ciphertext: str) -> str` — decodes base64, extracts nonce/ciphertext/tag, decrypts
    - Key loaded from `AuthSettings.oauth_token_encryption_key` (base64-decoded to 32 bytes)
    - _Requirements: 9.1, 9.2_
  - [ ]* 2.2 Write property test for CryptoUtils (encryption round-trip)
    - **Property 1: Encryption Round-Trip**
    - For any arbitrary string, encrypt then decrypt returns the original. Encrypted form differs from plaintext.
    - Use Hypothesis with `st.text()` strategy
    - **Validates: Requirements 9.1, 9.2**
  - [x] 2.3 Implement JWTUtils
    - Create `backend/src/modules/identity/infrastructure/jwt_utils.py`
    - Implement `encode(payload, expires_delta) -> str` using python-jose HS256
    - Implement `decode(token) -> dict` with validation (raises on expired/invalid)
    - Implement `create_state_token(data) -> str` with 10-minute expiry
    - Implement `verify_state_token(token) -> dict` with signature + expiry validation
    - _Requirements: 1.2, 2.2, 5.1_
  - [ ]* 2.4 Write property tests for JWTUtils
    - **Property 2: JWT Access Token Round-Trip**
    - For any UUID user_id and email string, encode then decode preserves claims
    - **Property 3: CSRF State Token Integrity**
    - For any dict payload, create_state_token then verify_state_token returns original payload. Tampered tokens raise error.
    - **Validates: Requirements 5.1, 1.2, 2.2**
  - [x] 2.5 Implement WhitelistLoader and WhitelistService
    - Create `backend/src/modules/identity/infrastructure/whitelist_loader.py`
    - Implement file reading (one email per line), case-insensitive storage (lowercase set)
    - Implement file modification detection (stat mtime check on each call or watchdog)
    - Create `backend/src/modules/identity/application/whitelist_service.py`
    - Implement `is_allowed(email: str) -> bool` — case-insensitive exact match
    - Implement `reload() -> None` — re-read file
    - _Requirements: 3.1, 3.3_
  - [ ]* 2.6 Write property test for WhitelistService
    - **Property 4: Whitelist Case-Insensitive Matching**
    - For any email in the whitelist, any case variation returns True. For any email NOT in whitelist, returns False.
    - Use Hypothesis with `st.emails()` + case mutation strategy
    - **Validates: Requirements 3.1**

- [x] 3. Checkpoint - Ensure infrastructure tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement application layer services
  - [x] 4.1 Implement OAuthService
    - Create `backend/src/modules/identity/application/oauth_service.py`
    - Implement `exchange_code(code, code_verifier) -> GoogleTokens` using Authlib to call Google token endpoint
    - Implement `refresh_google_token(user_id) -> GoogleTokens | None` — decrypt stored refresh token, call Google, re-encrypt new tokens, update DB. Return None if revoked.
    - Implement `get_valid_access_token(user_id) -> str` — check expiry, auto-refresh if needed
    - Implement `determine_grant_status(scopes: list[str]) -> GrantStatus` — check for gmail.readonly, gmail.modify, gmail.send, calendar.events
    - _Requirements: 2.3, 10.1, 10.2, 10.3, 11.1, 11.2_
  - [ ]* 4.2 Write property test for scope determination
    - **Property 5: Scope Determination Correctness**
    - For any list of scopes, gmail_grant_valid is True IFF all Gmail scopes present. calendar_grant_valid is True IFF calendar.events present.
    - Use Hypothesis with `st.lists(st.sampled_from(ALL_POSSIBLE_SCOPES))`
    - **Validates: Requirements 11.1, 11.2**
  - [x] 4.3 Implement TokenService
    - Create `backend/src/modules/identity/application/token_service.py`
    - Implement `create_access_token(user_id, email) -> str` — JWT with 15min expiry, sub=user_id, email claim
    - Implement `create_refresh_token(user_id) -> tuple[str, str]` — generate secure random token, return (raw, sha256_hash)
    - Implement `verify_access_token(token) -> TokenPayload` — decode JWT, return payload
    - Implement `refresh_access_token(refresh_token) -> str` — hash token, lookup in DB, validate not expired/revoked, issue new access token
    - Implement `revoke_user_tokens(user_id) -> None` — set revoked_at on all active tokens for user
    - _Requirements: 5.1, 5.2, 5.4, 6.1, 6.2, 6.3_
  - [x] 4.4 Implement AuthService (orchestrator)
    - Create `backend/src/modules/identity/application/auth_service.py`
    - Implement `initiate_login() -> LoginRedirect` — generate PKCE code_verifier/challenge, create state token, build Google OAuth2 URL with all scopes
    - Implement `handle_callback(code, state) -> AuthResult` — validate state, exchange code, check whitelist, upsert user, store encrypted tokens, revoke old refresh tokens, issue new JWT + refresh token
    - Implement `logout(refresh_token) -> None` — hash token, set revoked_at
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3, 3.1, 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 7.1_

- [x] 5. Implement repositories
  - [x] 5.1 Implement UserRepository
    - Create `backend/src/modules/identity/infrastructure/user_repository.py`
    - Implement `get_by_email(email) -> User | None`
    - Implement `get_by_id(user_id) -> User | None`
    - Implement `upsert(google_user_info) -> User` — create if not exists, update last_login if exists
    - Use async SQLAlchemy session
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 5.2 Write property test for user upsert idempotence
    - **Property 7: User Upsert Idempotence**
    - For any valid Google profile, upserting N times results in exactly 1 User record. last_login reflects most recent upsert.
    - Use Hypothesis with `st.builds(GoogleUserInfo)` and `st.integers(min_value=1, max_value=5)` for repeat count
    - **Validates: Requirements 4.2, 4.3**
  - [x] 5.3 Implement OAuthGrantRepository
    - Create `backend/src/modules/identity/infrastructure/oauth_grant_repository.py`
    - Implement `get_by_user_id(user_id) -> OAuthGrant | None`
    - Implement `upsert(user_id, encrypted_tokens, scopes, expires_at) -> OAuthGrant`
    - Implement `mark_invalid(user_id) -> None`
    - _Requirements: 9.1, 10.2, 10.3_
  - [x] 5.4 Implement RefreshTokenRepository
    - Create `backend/src/modules/identity/infrastructure/refresh_token_repository.py`
    - Implement `create(user_id, token_hash, expires_at, user_agent) -> RefreshToken`
    - Implement `get_by_hash(token_hash) -> RefreshToken | None`
    - Implement `revoke_all_for_user(user_id) -> None` — set revoked_at on all active tokens
    - _Requirements: 5.2, 5.4, 7.1_
  - [ ]* 5.5 Write property test for single active session invariant
    - **Property 8: Single Active Session Invariant**
    - For any user with N existing tokens, after creating a new token (with revoke_all first), exactly 1 non-revoked token exists.
    - Use Hypothesis with `st.integers(min_value=1, max_value=10)` for existing token count
    - **Validates: Requirements 5.4**

- [x] 6. Checkpoint - Ensure application layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement API layer
  - [x] 7.1 Implement rate limiter
    - Create `backend/src/modules/identity/infrastructure/rate_limiter.py`
    - Implement Redis-based sliding window rate limiter
    - `check_rate_limit(ip: str) -> bool` — returns True if under limit (5 req/min), False if exceeded
    - _Requirements: 12.1, 12.2_
  - [x] 7.2 Implement auth dependencies (middleware)
    - Create `backend/src/modules/identity/api/dependencies.py`
    - Implement `get_current_user(request: Request) -> User` FastAPI dependency
    - Extract JWT from `access_token` cookie, decode, lookup user
    - Raise HTTPException(401) if token missing, invalid, or expired
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ]* 7.3 Write property test for auth middleware
    - **Property 6: Auth Middleware Rejects Invalid Tokens**
    - For any malformed/expired/wrong-key JWT, the middleware returns 401.
    - Use Hypothesis with `st.text()` for random strings + token mutation strategies
    - **Validates: Requirements 8.1, 8.2, 8.3**
  - [x] 7.4 Implement auth router
    - Create `backend/src/modules/identity/api/router.py`
    - `GET /api/auth/login` — call AuthService.initiate_login(), return 302 redirect
    - `GET /api/auth/callback` — call AuthService.handle_callback(), set cookies, redirect to frontend
    - `POST /api/auth/refresh` — extract refresh_token cookie, call TokenService.refresh_access_token(), set new access_token cookie
    - `POST /api/auth/logout` — extract refresh_token cookie, call AuthService.logout(), clear cookies
    - `GET /api/auth/me` — require get_current_user, return UserResponse with grant status
    - `GET /api/auth/grant-status` — require get_current_user, return GrantStatusResponse
    - Apply rate limiter to login and callback endpoints
    - _Requirements: 1.1, 2.1, 6.1, 7.1, 7.2, 11.3, 12.1_
  - [x] 7.5 Implement error handler
    - Create or update `backend/src/modules/identity/api/error_handler.py`
    - Register exception handler for `AuthError` base class → return JSON `{"error": {"code": ..., "message": ...}}`
    - _Requirements: 2.2, 2.4, 3.2, 6.2, 6.3, 12.1_

- [x] 8. Implement database migrations
  - [x] 8.1 Create Alembic migrations
    - Create `backend/alembic/versions/001_create_users_table.py` — users table
    - Create `backend/alembic/versions/002_create_oauth_grants_table.py` — oauth_grants table with FK to users
    - Create `backend/alembic/versions/003_create_refresh_tokens_table.py` — refresh_tokens table with FK to users
    - Add indexes: users.email (unique), users.google_sub (unique), refresh_tokens.token_hash (unique), oauth_grants.user_id
    - _Requirements: 4.1, 5.2, 9.1_

- [x] 9. Implement frontend auth pages
  - [x] 9.1 Create login page
    - Create `frontend/src/app/login/page.tsx`
    - Render login page with Vroom HR logo, tagline, and "Login with Google" button
    - Button triggers `GET /api/auth/login` (full page redirect)
    - Include consent notice text about Gmail and Calendar access
    - Style with shadcn/ui Button + Tailwind CSS
    - _Requirements: 1.1_
  - [x] 9.2 Implement frontend auth middleware
    - Create `frontend/src/middleware.ts` (Next.js middleware)
    - Check for `access_token` cookie on protected routes
    - If missing, redirect to `/login`
    - If present, allow request to proceed (server validates on API call)
    - _Requirements: 8.1_
  - [x] 9.3 Create grant warning modal
    - Create `frontend/src/components/grant-warning-modal.tsx`
    - Display when `gmail_grant_valid=false` or `calendar_grant_valid=false`
    - Show which permissions are missing
    - "Re-authorize" button triggers `GET /api/auth/login` (re-consent)
    - "Skip for now" button dismisses modal
    - _Requirements: 10.4, 11.1, 11.2_
  - [x] 9.4 Implement logout functionality
    - Add logout button to dashboard layout
    - On click: `POST /api/auth/logout`, then redirect to `/login`
    - _Requirements: 7.1, 7.2_

- [ ] 10. Integration tests
  - [ ]* 10.1 Write integration tests for OAuth2 login flow
    - Test full callback flow with mocked Google token endpoint (respx)
    - Verify: user created in DB, cookies set, redirect to dashboard
    - Test whitelist rejection → 403
    - Test invalid state → 400
    - Test Google error → 502
    - _Requirements: 1.1, 2.1, 2.2, 2.4, 3.1, 3.2, 4.1_
  - [ ]* 10.2 Write integration tests for token refresh and logout
    - Test: login → refresh → new access token
    - Test: expired refresh token → 401
    - Test: revoked refresh token → 401
    - Test: logout → refresh token revoked, cookies cleared
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2_
  - [ ]* 10.3 Write integration tests for Google token auto-refresh
    - Test: expired Google token → auto-refresh succeeds → grant updated
    - Test: revoked Google token → refresh fails → grant marked invalid
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ]* 10.4 Write integration test for rate limiting
    - Test: 5 requests pass, 6th returns 429
    - _Requirements: 12.1_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

### Task Dependency Graph

```
1.1 Create the identity module directory structure -> 1.2 Implement AuthSettings (Pydantic Settings)
1.2 Implement AuthSettings (Pydantic Settings) -> 1.3 Create domain entities (SQLModel)
1.3 Create domain entities (SQLModel) -> 1.4 Create domain exceptions
1.4 Create domain exceptions -> 1.5 Create Pydantic schemas
1.5 Create Pydantic schemas -> 2.1 Implement CryptoUtils (AES-256-GCM)
2.1 Implement CryptoUtils (AES-256-GCM) -> 2.3 Implement JWTUtils
2.1 Implement CryptoUtils (AES-256-GCM) -> 2.2 Write property test for CryptoUtils (encryption round-trip)
2.3 Implement JWTUtils -> 2.5 Implement WhitelistLoader and WhitelistService
2.3 Implement JWTUtils -> 2.4 Write property tests for JWTUtils
2.5 Implement WhitelistLoader and WhitelistService -> 2.6 Write property test for WhitelistService
2.5 Implement WhitelistLoader and WhitelistService -> 3. Checkpoint - Ensure infrastructure tests pass
3. Checkpoint - Ensure infrastructure tests pass -> 4.1 Implement OAuthService
3. Checkpoint - Ensure infrastructure tests pass -> 5.1 Implement UserRepository
4.1 Implement OAuthService -> 4.2 Write property test for scope determination
4.1 Implement OAuthService -> 4.3 Implement TokenService
4.3 Implement TokenService -> 4.4 Implement AuthService (orchestrator)
5.1 Implement UserRepository -> 5.2 Write property test for user upsert idempotence
5.1 Implement UserRepository -> 5.3 Implement OAuthGrantRepository
5.3 Implement OAuthGrantRepository -> 5.4 Implement RefreshTokenRepository
5.4 Implement RefreshTokenRepository -> 5.5 Write property test for single active session invariant
4.4 Implement AuthService (orchestrator) -> 6. Checkpoint - Ensure application layer tests pass
5.4 Implement RefreshTokenRepository -> 6. Checkpoint - Ensure application layer tests pass
6. Checkpoint - Ensure application layer tests pass -> 7.1 Implement rate limiter
6. Checkpoint - Ensure application layer tests pass -> 8.1 Create Alembic migrations
6. Checkpoint - Ensure application layer tests pass -> 9.1 Create login page
7.1 Implement rate limiter -> 7.2 Implement auth dependencies (middleware)
7.2 Implement auth dependencies (middleware) -> 7.3 Write property test for auth middleware
7.2 Implement auth dependencies (middleware) -> 7.4 Implement auth router
7.4 Implement auth router -> 7.5 Implement error handler
9.1 Create login page -> 9.2 Implement frontend auth middleware
9.2 Implement frontend auth middleware -> 9.3 Create grant warning modal
9.3 Create grant warning modal -> 9.4 Implement logout functionality
7.5 Implement error handler -> 10.1 Write integration tests for OAuth2 login flow
8.1 Create Alembic migrations -> 10.1 Write integration tests for OAuth2 login flow
9.4 Implement logout functionality -> 10.1 Write integration tests for OAuth2 login flow
10.1 Write integration tests for OAuth2 login flow -> 10.2 Write integration tests for token refresh and logout
10.2 Write integration tests for token refresh and logout -> 10.3 Write integration tests for Google token auto-refresh
10.3 Write integration tests for Google token auto-refresh -> 10.4 Write integration test for rate limiting
10.4 Write integration test for rate limiting -> 11. Final checkpoint - Ensure all tests pass
```

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Hypothesis, 100+ iterations)
- Unit tests validate specific examples and edge cases
- Integration tests use testcontainers (PostgreSQL, Redis) and respx (Google API mock)
- Frontend implementation assumes Next.js 14+ App Router with shadcn/ui
