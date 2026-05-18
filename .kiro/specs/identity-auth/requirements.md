# Requirements Document

## Introduction

The Identity & Auth module provides the sole authentication mechanism for Vroom HR through Google OAuth2. HR users log in with their Google account, and the system simultaneously requests Gmail and Google Calendar access to serve the Inbox, Recruitment, and Interview modules. Access is controlled via an email whitelist (config file). The system issues JWT-based sessions (access token 15min + refresh token 7d) and stores encrypted Google OAuth2 tokens for downstream API calls.

## Glossary

- **System**: The Vroom HR Identity & Auth backend module
- **HR**: The human resources user who logs into the system
- **Whitelist**: A plain text configuration file containing authorized email addresses (one per line), supporting hot-reload
- **OAuth_Grant**: The stored Google OAuth2 credentials (encrypted access + refresh tokens) for a user
- **Refresh_Token**: A system-issued JWT refresh token (7-day expiry) stored as a hashed value in the database
- **Access_Token**: A system-issued JWT access token (15-minute expiry) delivered as an httpOnly cookie
- **Auth_Middleware**: The middleware component that validates JWT access tokens on protected API endpoints
- **Token_Service**: The service responsible for issuing, refreshing, and revoking JWT tokens
- **OAuth_Service**: The service responsible for Google OAuth2 flow, token exchange, and token refresh
- **Grant_Status**: A boolean indicator (gmail_grant_valid, calendar_grant_valid) reflecting whether the user granted the required Google API scopes

## Requirements

### Requirement 1: Google OAuth2 Login Initiation

**User Story:** As an HR user, I want to click "Login with Google" so that I am redirected to Google's consent screen to authenticate.

#### Acceptance Criteria

1. WHEN HR clicks "Login with Google", THE System SHALL redirect to Google OAuth2 consent screen with scopes: openid, email, profile, gmail.readonly, gmail.modify, gmail.send, calendar.events
2. WHEN generating the OAuth2 redirect URL, THE System SHALL include a signed CSRF state token with a 10-minute expiry
3. WHEN generating the OAuth2 redirect URL, THE System SHALL include PKCE code_verifier and code_challenge parameters

### Requirement 2: OAuth2 Callback and Token Exchange

**User Story:** As an HR user, I want the system to securely exchange the authorization code for tokens so that my identity is verified.

#### Acceptance Criteria

1. WHEN Google returns an authorization code, THE System SHALL validate the CSRF state token before proceeding
2. IF the CSRF state token is invalid or expired, THEN THE System SHALL return HTTP 400 with error code AUTH_INVALID_STATE
3. WHEN the state token is valid, THE System SHALL exchange the authorization code for Google tokens using PKCE code_verifier
4. IF the Google token exchange fails, THEN THE System SHALL return HTTP 502 with error code AUTH_GOOGLE_ERROR

### Requirement 3: Email Whitelist Access Control

**User Story:** As a system administrator, I want only authorized emails to access the system so that access is restricted to approved HR personnel.

#### Acceptance Criteria

1. WHEN Google returns user profile data, THE System SHALL validate the email against the whitelist using case-insensitive exact matching
2. IF the email is NOT in the whitelist, THEN THE System SHALL return HTTP 403 with error code AUTH_ACCESS_DENIED and message "Access denied. Contact administrator."
3. WHEN the whitelist file is modified, THE System SHALL detect changes and reload the whitelist without requiring a restart

### Requirement 4: User Auto-Provisioning

**User Story:** As an HR user logging in for the first time, I want the system to automatically create my account so that I don't need a separate registration step.

#### Acceptance Criteria

1. WHEN the email IS in the whitelist AND the user does NOT exist in the database, THE System SHALL create a User record with Google profile data (email, name, avatar_url, google_sub)
2. WHEN the email IS in the whitelist AND the user already exists, THE System SHALL update last_login timestamp and refresh the stored OAuth tokens
3. WHEN creating or updating a user, THE System SHALL NOT create duplicate User records for the same email

### Requirement 5: JWT Session Management

**User Story:** As an HR user, I want the system to issue secure session tokens so that I remain authenticated across requests.

#### Acceptance Criteria

1. WHEN login succeeds, THE Token_Service SHALL issue a JWT access token with 15-minute expiry containing user_id and email claims
2. WHEN login succeeds, THE Token_Service SHALL issue a refresh token with 7-day expiry and store its SHA-256 hash in the database
3. WHEN login succeeds, THE System SHALL deliver both tokens as httpOnly, Secure, SameSite=Lax cookies
4. WHEN a new login occurs for an existing user, THE Token_Service SHALL revoke all previously active refresh tokens for that user

### Requirement 6: Token Refresh

**User Story:** As an HR user, I want my session to be seamlessly extended so that I don't have to re-login every 15 minutes.

#### Acceptance Criteria

1. WHEN the access token expires AND a valid (non-expired, non-revoked) refresh token exists, THE Token_Service SHALL issue a new access token upon request to /api/auth/refresh
2. IF the refresh token is expired, THEN THE System SHALL return HTTP 401 Unauthorized
3. IF the refresh token has been revoked, THEN THE System SHALL return HTTP 401 Unauthorized

### Requirement 7: Logout

**User Story:** As an HR user, I want to securely log out so that my session is terminated and cannot be reused.

#### Acceptance Criteria

1. WHEN HR requests logout via POST /api/auth/logout, THE System SHALL revoke the active refresh token by setting revoked_at timestamp
2. WHEN HR requests logout, THE System SHALL clear both access_token and refresh_token cookies

### Requirement 8: API Authentication Middleware

**User Story:** As a system architect, I want all API endpoints to be protected so that unauthenticated requests are rejected.

#### Acceptance Criteria

1. WHEN any protected API endpoint receives a request without a valid JWT access token, THE Auth_Middleware SHALL return HTTP 401 Unauthorized
2. WHEN the JWT access token has an invalid signature, THE Auth_Middleware SHALL return HTTP 401 Unauthorized
3. WHEN the JWT access token is expired, THE Auth_Middleware SHALL return HTTP 401 Unauthorized

### Requirement 9: Google OAuth Token Storage and Encryption

**User Story:** As a system architect, I want Google OAuth tokens stored securely so that they cannot be read if the database is compromised.

#### Acceptance Criteria

1. WHEN storing Google OAuth2 tokens (access_token, refresh_token), THE OAuth_Service SHALL encrypt them using AES-256-GCM before writing to the database
2. WHEN retrieving Google OAuth2 tokens for API calls, THE OAuth_Service SHALL decrypt them using the encryption key from environment configuration
3. THE System SHALL store the encryption key exclusively in environment variables, never in the database or source code

### Requirement 10: Google API Token Auto-Refresh

**User Story:** As an HR user, I want the system to automatically refresh Google API tokens so that Gmail and Calendar integrations work without manual intervention.

#### Acceptance Criteria

1. WHEN the system needs to call Gmail or Calendar API AND the stored Google access token is expired, THE OAuth_Service SHALL use the Google refresh token to obtain a new access token
2. WHEN the Google token refresh succeeds, THE OAuth_Service SHALL update the stored encrypted access token and token_expires_at
3. IF the Google token refresh fails (token revoked by user), THEN THE OAuth_Service SHALL mark the OAuth_Grant as invalid (is_valid=false)
4. WHEN an OAuth_Grant is marked invalid, THE System SHALL prompt the user to re-authorize via the Grant Warning modal

### Requirement 11: Grant Status Reporting

**User Story:** As an HR user, I want to know if my Gmail/Calendar permissions are active so that I understand why certain features may be unavailable.

#### Acceptance Criteria

1. WHEN the user did not grant Gmail scopes during OAuth consent, THE System SHALL set gmail_grant_valid to false
2. WHEN the user did not grant Calendar scopes during OAuth consent, THE System SHALL set calendar_grant_valid to false
3. WHEN the user requests GET /api/auth/grant-status, THE System SHALL return the current validity of Gmail and Calendar grants

### Requirement 12: Rate Limiting

**User Story:** As a system architect, I want login attempts rate-limited so that the system is protected against brute-force attacks on the OAuth callback.

#### Acceptance Criteria

1. WHEN login attempts from a single IP exceed 5 per minute, THE System SHALL return HTTP 429 Too Many Requests
2. THE System SHALL use Redis-based rate limiting with per-IP tracking
