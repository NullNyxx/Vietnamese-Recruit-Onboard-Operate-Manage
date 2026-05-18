# SPEC-FEATURE — Identity & Auth

> **Phiên bản:** 1.0.0
> **Ngày tạo:** 2026-05-18
> **Tác giả:** NullNyx + Kiro
> **Trạng thái:** `Agreed`
> **Epic:** E01 — Identity & Auth
> **Parent:** specs/project/vroom-hr.md

---

## 1. Mô tả feature

Module Identity & Auth cung cấp cơ chế xác thực duy nhất cho Vroom HR thông
qua Google OAuth2. HR login bằng tài khoản Google, hệ thống đồng thời xin
quyền truy cập Gmail và Google Calendar để phục vụ các module Inbox,
Recruitment, và Interview.

**Domain:** identity

**User roles:**
- HR — login qua Google OAuth2, được auto-provision nếu email nằm trong whitelist

---

## 2. Phạm vi feature

### Trong scope

- Google OAuth2 login flow (authorization code + PKCE)
- Request scopes: openid, email, profile, gmail.readonly, gmail.modify, gmail.send, calendar.events
- JWT session management (access token 15min + refresh token 7d)
- Email whitelist access control (config file)
- Auto-provision User record khi login lần đầu
- Token refresh endpoint
- Logout (revoke refresh token)
- Store encrypted OAuth2 tokens (access + refresh) cho Gmail/Calendar API calls

### Không trong scope

- Email/password login — không cần (Google-only)
- Forgot password — không áp dụng
- Multi-role RBAC — MVP chỉ 1 role (HR)
- User management UI — admin quản lý whitelist qua config file
- Multi-factor authentication — Google đã có 2FA built-in
- Registration page — không có, chỉ whitelist login

---

## 3. Requirements

| ID | Requirement (EARS format) | Validation |
|----|---------------------------|------------|
| FR-01 | WHEN HR clicks "Login with Google" THEN system redirects to Google OAuth2 consent screen with required scopes | E2E: verify redirect URL contains correct scopes |
| FR-02 | WHEN Google returns authorization code THEN system exchanges code for tokens and validates email against whitelist | Integration: mock Google token endpoint, test whitelist check |
| FR-03 | WHEN email is NOT in whitelist THEN system returns 403 with message "Access denied. Contact administrator." | Unit: test whitelist rejection |
| FR-04 | WHEN email IS in whitelist AND user does NOT exist THEN system creates User record with Google profile data | Integration: verify User created in DB |
| FR-05 | WHEN email IS in whitelist AND user already exists THEN system updates last_login and refreshes OAuth tokens | Integration: verify update, not duplicate |
| FR-06 | WHEN login succeeds THEN system issues JWT access token (15min) + refresh token (7d) as httpOnly cookies | Unit: verify token claims and expiry |
| FR-07 | WHEN access token expires AND valid refresh token exists THEN /api/auth/refresh returns new access token | Integration: test refresh flow |
| FR-08 | WHEN refresh token is expired or revoked THEN system returns 401 and frontend redirects to login | Integration: test expired refresh |
| FR-09 | WHEN HR clicks "Logout" THEN system revokes refresh token and clears cookies | Integration: verify token revoked in DB |
| FR-10 | WHEN any API endpoint receives request without valid JWT THEN system returns 401 Unauthorized | Unit: test auth middleware |
| FR-11 | WHEN system needs to call Gmail/Calendar API THEN system uses stored OAuth2 tokens, auto-refreshing if expired | Integration: test token refresh for Google API |
| FR-12 | WHEN Google OAuth2 token refresh fails (revoked by user) THEN system marks grant as invalid and prompts re-auth | Integration: simulate revoked token |

---

## 4. Input / Output Contracts

### API Endpoints

| Method | Path | Mô tả |
|--------|------|--------|
| GET | /api/auth/login | Redirect to Google OAuth2 consent |
| GET | /api/auth/callback | Handle Google OAuth2 callback |
| POST | /api/auth/refresh | Refresh access token |
| POST | /api/auth/logout | Revoke refresh token + clear cookies |
| GET | /api/auth/me | Get current user profile |
| GET | /api/auth/grant-status | Check Gmail/Calendar grant validity |

### GET /api/auth/login

**Response:** 302 Redirect to Google OAuth2 URL

```
Location: https://accounts.google.com/o/oauth2/v2/auth?
  client_id={GOOGLE_CLIENT_ID}&
  redirect_uri={CALLBACK_URL}&
  response_type=code&
  scope=openid email profile
    https://www.googleapis.com/auth/gmail.readonly
    https://www.googleapis.com/auth/gmail.modify
    https://www.googleapis.com/auth/gmail.send
    https://www.googleapis.com/auth/calendar.events&
  access_type=offline&
  prompt=consent&
  state={csrf_token}
```

### GET /api/auth/callback

**Query params:** `code`, `state`

**Success response:** 302 Redirect to frontend dashboard
- Sets httpOnly cookies: `access_token`, `refresh_token`

**Error responses:**

| Scenario | Status | Error Code | Message |
|----------|--------|------------|---------|
| Invalid state (CSRF) | 400 | AUTH_INVALID_STATE | Invalid authentication state |
| Google token exchange fails | 502 | AUTH_GOOGLE_ERROR | Failed to authenticate with Google |
| Email not in whitelist | 403 | AUTH_ACCESS_DENIED | Access denied. Contact administrator. |
| Google scopes not fully granted | 400 | AUTH_INSUFFICIENT_SCOPE | Please grant all requested permissions |

### POST /api/auth/refresh

**Request:** Cookie `refresh_token`

**Success response (200):**
```json
{
  "access_token": "eyJ...",
  "expires_in": 900
}
```
Sets new `access_token` cookie.

**Error:** 401 if refresh token invalid/expired.

### GET /api/auth/me

**Success response (200):**
```json
{
  "id": "uuid",
  "email": "hr@company.com",
  "name": "Nguyễn Văn A",
  "avatar_url": "https://...",
  "gmail_grant_valid": true,
  "calendar_grant_valid": true,
  "created_at": "2026-05-18T10:00:00Z",
  "last_login": "2026-05-18T10:00:00Z"
}
```

---

## 5. Business Rules & Logic

### OAuth2 Login Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │     │ Backend  │     │  Google  │     │ Database │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │ Click Login     │                │                │
     │────────────────►│                │                │
     │                 │ Generate state │                │
     │                 │ + PKCE verifier│                │
     │                 │───────────────►│                │
     │ 302 Redirect    │                │                │
     │◄────────────────│                │                │
     │                 │                │                │
     │ User consents   │                │                │
     │─────────────────────────────────►│                │
     │                 │                │                │
     │ Callback w/code │                │                │
     │────────────────►│                │                │
     │                 │ Exchange code  │                │
     │                 │───────────────►│                │
     │                 │ Tokens         │                │
     │                 │◄───────────────│                │
     │                 │                │                │
     │                 │ Verify email   │                │
     │                 │ in whitelist   │                │
     │                 │                │                │
     │                 │ Upsert User    │                │
     │                 │───────────────────────────────►│
     │                 │                │                │
     │                 │ Store Google   │                │
     │                 │ OAuth tokens   │                │
     │                 │───────────────────────────────►│
     │                 │                │                │
     │                 │ Issue JWT      │                │
     │ Set cookies     │                │                │
     │◄────────────────│                │                │
     │ 302 → Dashboard │                │                │
     │◄────────────────│                │                │
```

### Domain Rules

1. **Whitelist check**: Email phải exact-match trong danh sách whitelist (case-insensitive)
2. **Scope validation**: Nếu user không grant đủ scope (bỏ tick Gmail hoặc Calendar), login vẫn thành công nhưng `gmail_grant_valid` hoặc `calendar_grant_valid` = false. Các module phụ thuộc sẽ hiện warning.
3. **Token encryption**: Google OAuth2 tokens (access + refresh) phải encrypt trước khi lưu DB (AES-256-GCM, key từ env)
4. **Token refresh**: Khi gọi Gmail/Calendar API, nếu Google access token expired → auto refresh bằng Google refresh token. Nếu refresh fail → mark grant invalid.
5. **Session isolation**: Mỗi user chỉ có 1 active refresh token. Login mới revoke token cũ.
6. **CSRF protection**: State parameter trong OAuth2 flow phải match. Dùng signed JWT state token (expire 10min).

### Edge Cases

| Case | Xử lý |
|------|--------|
| User revoke app access trong Google Settings | Khi system gọi Gmail API → 401 → mark grant invalid → prompt re-auth |
| Whitelist thay đổi (admin xóa email) | User hiện tại vẫn dùng được đến khi refresh token hết hạn. Không force-logout. |
| Google OAuth2 downtime | Return 502 AUTH_GOOGLE_ERROR, frontend hiện retry button |
| User có 2 Google accounts | Dùng `login_hint` param nếu có session, hoặc `prompt=select_account` |
| Concurrent login từ 2 tab | Tab sau sẽ revoke refresh token của tab trước (single session) |

---

## 6. Data Model

### Entity: User

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK, auto-generated | Internal user ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Google email |
| name | VARCHAR(255) | NOT NULL | Display name from Google profile |
| avatar_url | TEXT | NULLABLE | Google profile picture URL |
| google_sub | VARCHAR(255) | UNIQUE, NOT NULL | Google subject ID (stable identifier) |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW() | First login time |
| last_login | TIMESTAMPTZ | NOT NULL | Most recent login |
| is_active | BOOLEAN | NOT NULL, default TRUE | Soft-disable without removing |

### Entity: OAuthGrant

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Grant ID |
| user_id | UUID | FK → User.id, NOT NULL | Owner |
| provider | VARCHAR(50) | NOT NULL, default 'google' | OAuth provider |
| access_token_enc | TEXT | NOT NULL | Encrypted Google access token |
| refresh_token_enc | TEXT | NOT NULL | Encrypted Google refresh token |
| scopes | TEXT[] | NOT NULL | Granted scopes array |
| token_expires_at | TIMESTAMPTZ | NOT NULL | Google access token expiry |
| is_valid | BOOLEAN | NOT NULL, default TRUE | False if revoked/expired |
| created_at | TIMESTAMPTZ | NOT NULL | Grant creation time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last token refresh time |

### Entity: RefreshToken

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Token ID |
| user_id | UUID | FK → User.id, NOT NULL | Owner |
| token_hash | VARCHAR(64) | UNIQUE, NOT NULL | SHA-256 hash of refresh token |
| expires_at | TIMESTAMPTZ | NOT NULL | Expiry (7 days from issue) |
| revoked_at | TIMESTAMPTZ | NULLABLE | When revoked (NULL = active) |
| created_at | TIMESTAMPTZ | NOT NULL | Issue time |
| user_agent | TEXT | NULLABLE | Browser/device info |

### Relationships

```
User (1) ──── (1) OAuthGrant     [1 user = 1 Google grant]
User (1) ──── (N) RefreshToken   [history, only 1 active at a time]
```

### Migrations

- `001_create_users_table.py`
- `002_create_oauth_grants_table.py`
- `003_create_refresh_tokens_table.py`

---

## 7. UI / UX

### Screens

| Screen | Route | Mô tả |
|--------|-------|--------|
| Login | /login | Trang login đơn giản: logo + "Login with Google" button |
| Dashboard | / | Redirect target sau login thành công |
| Grant Warning | (modal) | Hiện khi gmail_grant_valid=false hoặc calendar_grant_valid=false |

### Login Page

```
┌─────────────────────────────────────┐
│                                     │
│           [Vroom HR Logo]           │
│                                     │
│     Your HR Co-pilot, fast as       │
│              a hum.                 │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  🔵 Login with Google       │   │
│   └─────────────────────────────┘   │
│                                     │
│   By logging in, you agree to       │
│   grant access to Gmail and         │
│   Google Calendar.                  │
│                                     │
└─────────────────────────────────────┘
```

### User Flow

1. HR mở app → redirect /login (nếu chưa auth)
2. Click "Login with Google" → redirect Google consent
3. Grant permissions → callback → redirect dashboard
4. Nếu email không trong whitelist → hiện error page "Access Denied"
5. Nếu không grant đủ scope → login OK nhưng hiện warning modal

### Grant Warning Modal

```
┌─────────────────────────────────────┐
│  ⚠️ Incomplete Permissions          │
│                                     │
│  You haven't granted access to:     │
│  ☐ Gmail (required for Inbox)       │
│  ☐ Calendar (required for           │
│    Interview scheduling)            │
│                                     │
│  [Re-authorize]  [Skip for now]     │
└─────────────────────────────────────┘
```

---

## 8. Acceptance Criteria

| # | Criterion | Type |
|---|-----------|------|
| AC-01 | HR can login via Google OAuth2 and land on dashboard | E2E |
| AC-02 | Non-whitelisted email gets 403 error with clear message | Integration |
| AC-03 | First-time login creates User record with correct profile data | Integration |
| AC-04 | Subsequent login updates last_login, does not create duplicate | Integration |
| AC-05 | Access token expires after 15min, refresh endpoint issues new one | Integration |
| AC-06 | Expired refresh token returns 401, frontend redirects to /login | Integration |
| AC-07 | Logout revokes refresh token and clears cookies | Integration |
| AC-08 | Google OAuth tokens are stored encrypted (not plaintext in DB) | Unit |
| AC-09 | All API endpoints return 401 without valid JWT | Unit |
| AC-10 | If user doesn't grant Gmail scope, gmail_grant_valid=false | Integration |
| AC-11 | If Google refresh token is revoked externally, system detects and marks grant invalid | Integration |
| AC-12 | CSRF state token prevents replay attacks | Unit |
| AC-13 | All tests pass (pytest), lint pass (ruff), type check pass (mypy) | CI |
| AC-14 | Frontend login page renders correctly, button triggers OAuth flow | E2E |

---

## 9. Risk & Dependencies

### Risk Flags

| Risk | Level | Mitigation |
|------|-------|------------|
| Google OAuth2 consent screen review (production) | Medium | Dùng "Internal" app type cho Google Workspace org. Không cần Google review. |
| Token encryption key management | Low | Key từ env variable. Rotate = re-encrypt all tokens (migration script). |
| Google API rate limits | Low | Auth flow ít request. Gmail/Calendar rate limit xử lý ở module khác. |
| User revoke access ngoài hệ thống | Low | Detect khi gọi API, prompt re-auth. Không block UX. |

### Dependencies

| Dependency | Type | Mô tả |
|------------|------|--------|
| Google Cloud Project | External | Cần tạo OAuth2 credentials (client_id, client_secret) |
| PostgreSQL | Infrastructure | User, OAuthGrant, RefreshToken tables |
| Redis | Infrastructure | Optional: rate limit login attempts |
| Frontend (Next.js) | Internal | Login page, cookie handling, auth redirect |
| Reverse proxy (Caddy/Traefik) | Infrastructure | HTTPS termination cho OAuth2 callback |

---

## 10. Validation Plan

### Unit Tests

- Whitelist check logic (case-insensitive, exact match)
- JWT generation and validation (claims, expiry)
- CSRF state token generation and verification
- Token encryption/decryption (AES-256-GCM)
- Auth middleware (reject invalid/expired/missing token)

### Integration Tests

- Full OAuth2 callback flow (mock Google token endpoint)
- User auto-provision on first login
- User update on subsequent login
- Refresh token flow (issue, use, expire, revoke)
- OAuth grant status check (valid, invalid, missing scope)
- Whitelist rejection (403)

### E2E Tests (Playwright)

- Login page renders, button visible
- Click login → redirect to Google (verify URL params)
- After callback → lands on dashboard with user info
- Logout → redirect to login, cannot access dashboard

### Mock Strategy

- Google OAuth2 endpoints: mock via `respx` (Python) or `msw` (frontend)
- Never call real Google in CI
- Fixture: pre-generated Google ID token with known claims

---

## 11. Discussion Log

| Date | Chủ đề | Kết luận |
|------|--------|----------|
| 2026-05-18 | Auth method | Chỉ Google OAuth2, không email/password. Đơn giản hóa toàn bộ auth. |
| 2026-05-18 | Access control | Whitelist danh sách email cụ thể (config file). Không whitelist domain. |
| 2026-05-18 | User provisioning | Auto-provision khi login lần đầu. Không cần pre-create. |
| 2026-05-18 | Scope strategy | Request tất cả scope (Gmail + Calendar) ngay lần login đầu. Partial grant = warning, không block. |
| 2026-05-18 | Session | Single active session per user. Login mới revoke token cũ. |

---

## 12. Open Questions

| # | Câu hỏi | Impact | Khi nào |
|---|---------|--------|---------|
| Q1 | Whitelist config format: plain text file (1 email/line) hay JSON array? | DevOps experience | Trước implement |
| Q2 | Khi admin thêm email vào whitelist, cần restart app hay hot-reload? | UX cho admin | Trước implement |
| Q3 | Có cần rate limit login attempts (chống brute-force OAuth callback)? | Security | Trước implement |
| Q4 | Token encryption key rotation strategy — manual hay automated? | Security ops | Trước production |

---

*End of spec.*
