# Giải thích chi tiết: Chức năng Đăng nhập (Authentication)

## Tổng quan

Hệ thống Vroom HR sử dụng **Google OAuth2 + PKCE** để xác thực người dùng, kết hợp với **email whitelist** để kiểm soát quyền truy cập. Chỉ những email HR được phê duyệt trước mới có thể đăng nhập.

**Công nghệ sử dụng:**
- Google OAuth2 với PKCE (Proof Key for Code Exchange)
- JWT (JSON Web Token) cho session management
- AES-256-GCM cho mã hóa token Google
- Redis cho rate limiting
- HttpOnly cookies cho bảo mật token

---

## Sơ đồ luồng đăng nhập

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Browser │     │ Frontend │     │ Backend  │     │  Google  │
│  (User)  │     │ Next.js  │     │ FastAPI  │     │  OAuth2  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                 │                 │
     │ 1. Truy cập /  │                 │                 │
     │────────────────>│                 │                 │
     │                 │                 │                 │
     │ 2. Middleware   │                 │                 │
     │    kiểm tra     │                 │                 │
     │    cookie       │                 │                 │
     │    → không có   │                 │                 │
     │    → redirect   │                 │                 │
     │<────────────────│                 │                 │
     │  /login         │                 │                 │
     │                 │                 │                 │
     │ 3. Nhấn "Login  │                 │                 │
     │    with Google" │                 │                 │
     │────────────────────────────────-->│                 │
     │  GET /api/auth/login              │                 │
     │                 │                 │                 │
     │                 │                 │ 4. Tạo PKCE     │
     │                 │                 │    code_verifier │
     │                 │                 │    + state token │
     │                 │                 │                 │
     │ 5. Redirect 302 │                 │                 │
     │<──────────────────────────────────│                 │
     │  → Google OAuth URL               │                 │
     │  + Set cookie: code_verifier      │                 │
     │                 │                 │                 │
     │ 6. Đăng nhập Google               │                 │
     │────────────────────────────────────────────────────>│
     │                 │                 │                 │
     │ 7. User đồng ý │                 │                 │
     │    cấp quyền   │                 │                 │
     │<────────────────────────────────────────────────────│
     │  Redirect → /api/auth/callback?code=XXX&state=YYY  │
     │                 │                 │                 │
     │ 8. Callback     │                 │                 │
     │────────────────────────────────-->│                 │
     │  GET /api/auth/callback           │                 │
     │                 │                 │                 │
     │                 │                 │ 9. Verify state │
     │                 │                 │    token (CSRF) │
     │                 │                 │                 │
     │                 │                 │ 10. Exchange    │
     │                 │                 │     code →      │
     │                 │                 │────────────────>│
     │                 │                 │     tokens      │
     │                 │                 │<────────────────│
     │                 │                 │                 │
     │                 │                 │ 11. Decode      │
     │                 │                 │     ID token    │
     │                 │                 │     → email     │
     │                 │                 │                 │
     │                 │                 │ 12. Kiểm tra    │
     │                 │                 │     whitelist   │
     │                 │                 │                 │
     │                 │                 │ 13. Upsert user │
     │                 │                 │     vào DB      │
     │                 │                 │                 │
     │                 │                 │ 14. Mã hóa &   │
     │                 │                 │     lưu Google  │
     │                 │                 │     tokens      │
     │                 │                 │                 │
     │                 │                 │ 15. Tạo JWT     │
     │                 │                 │     access +    │
     │                 │                 │     refresh     │
     │                 │                 │     token       │
     │                 │                 │                 │
     │ 16. Redirect 302│                 │                 │
     │<──────────────────────────────────│                 │
     │  → http://localhost:3000          │                 │
     │  + Set cookie: access_token       │                 │
     │  + Set cookie: refresh_token      │                 │
     │                 │                 │                 │
     │ 17. Truy cập /  │                 │                 │
     │────────────────>│                 │                 │
     │                 │ Middleware OK    │                 │
     │ 18. Dashboard   │ (có cookie)     │                 │
     │<────────────────│                 │                 │
     │                 │                 │                 │
```

---

## Chi tiết từng bước

### Bước 1-2: Middleware kiểm tra xác thực

**File:** `frontend/src/middleware.ts`

Khi user truy cập bất kỳ trang nào (trừ `/login`, `/_next/`, `/api/`), middleware Next.js kiểm tra cookie `access_token`:
- **Có cookie** → cho phép truy cập
- **Không có cookie** → redirect về `/login`

```typescript
// middleware.ts
const accessToken = request.cookies.get("access_token");
if (!accessToken) {
  return NextResponse.redirect(new URL("/login", request.url));
}
```

### Bước 3: Trang đăng nhập

**File:** `frontend/src/app/login/page.tsx`

Hiển thị nút "Login with Google". Khi nhấn, redirect trình duyệt đến backend:
```typescript
window.location.href = "/api/auth/login";
```

### Bước 4-5: Backend khởi tạo OAuth flow

**File:** `backend/src/modules/identity/api/router.py` → endpoint `GET /api/auth/login`
**File:** `backend/src/modules/identity/application/auth_service.py` → `initiate_login()`

Backend thực hiện:

1. **Rate limiting** – Kiểm tra IP có vượt quá 5 lần/phút không (Redis sorted set)
2. **Tạo PKCE code_verifier** – Chuỗi random 43 ký tự URL-safe
3. **Tạo code_challenge** – SHA-256 hash của code_verifier, base64url encoded
4. **Tạo state token** – JWT chứa nonce random, hết hạn sau 10 phút (chống CSRF)
5. **Build Google OAuth URL** với các params:
   - `client_id`: Google Client ID
   - `redirect_uri`: `http://localhost:8000/api/auth/callback`
   - `response_type`: `code`
   - `scope`: openid, email, profile, Gmail, Calendar
   - `access_type`: `offline` (để nhận refresh token)
   - `prompt`: `consent` (luôn hỏi lại quyền)
   - `state`: CSRF state token
   - `code_challenge`: PKCE challenge
   - `code_challenge_method`: `S256`

6. **Trả về Redirect 302** đến Google + set cookie `code_verifier` (httpOnly, 10 phút)

### Bước 6-7: User đăng nhập Google

User đăng nhập tài khoản Google và đồng ý cấp quyền:
- Đọc email (Gmail readonly)
- Chỉnh sửa email (Gmail modify)
- Gửi email (Gmail send)
- Quản lý lịch (Calendar events)

Google redirect về: `http://localhost:8000/api/auth/callback?code=XXX&state=YYY`

### Bước 8-15: Backend xử lý callback

**File:** `backend/src/modules/identity/api/router.py` → endpoint `GET /api/auth/callback`
**File:** `backend/src/modules/identity/application/auth_service.py` → `handle_callback()`

#### 9. Verify CSRF state token
```python
self._jwt_utils.verify_state_token(state)
# Kiểm tra JWT hợp lệ, chưa hết hạn, purpose == "state"
```

#### 10. Exchange code → Google tokens
```python
google_tokens = await self._oauth_service.exchange_code(code, code_verifier)
# POST https://oauth2.googleapis.com/token
# Gửi: code, client_id, client_secret, redirect_uri, code_verifier, grant_type
# Nhận: access_token, refresh_token, id_token, expires_in, scope
```

#### 11. Decode ID token → lấy thông tin user
```python
id_token_claims = jose_jwt.get_unverified_claims(google_tokens.id_token)
# Lấy: sub (Google user ID), email, name, picture
```

#### 12. Kiểm tra whitelist
```python
if not self._whitelist_service.is_allowed(user_info.email):
    raise AccessDeniedError()
# So sánh email (case-insensitive) với file config/whitelist.txt
```

**File whitelist:** `backend/config/whitelist.txt`
```
# Mỗi dòng 1 email, dòng # là comment
nthengoc.dev@gmail.com
```

#### 13. Upsert user vào database
- Nếu user chưa tồn tại → tạo mới (auto-provision)
- Nếu đã tồn tại → cập nhật `last_login`, `name`, `avatar_url`

#### 14. Mã hóa & lưu Google tokens
```python
encrypted_access = self._crypto.encrypt(google_tokens.access_token)
encrypted_refresh = self._crypto.encrypt(google_tokens.refresh_token)
# AES-256-GCM: nonce (12 bytes) + ciphertext + tag (16 bytes) → base64
# Lưu vào bảng oauth_grants
```

#### 15. Tạo session tokens
```python
# JWT Access Token (15 phút)
access_token = self._token_service.create_access_token(user.id, user.email)
# Payload: { sub: user_id, email: email, exp: ..., iat: ... }

# Opaque Refresh Token (7 ngày)
raw_refresh_token = secrets.token_urlsafe(32)
token_hash = sha256(raw_refresh_token)  # Chỉ lưu hash vào DB
```

### Bước 16: Redirect về frontend với cookies

```python
response = RedirectResponse(url="http://localhost:3000", status_code=302)
response.set_cookie("access_token", value=jwt_token, max_age=900, httponly=True, secure=True)
response.set_cookie("refresh_token", value=raw_token, max_age=604800, httponly=True, secure=True)
```

---

## Cơ chế bảo mật

### 1. PKCE (Proof Key for Code Exchange)
Ngăn chặn authorization code interception attack:
- Login: tạo `code_verifier` → hash thành `code_challenge` → gửi challenge cho Google
- Callback: gửi `code_verifier` gốc cho Google → Google verify khớp với challenge

### 2. CSRF State Token
Ngăn chặn cross-site request forgery:
- Login: tạo JWT state token có nonce random
- Callback: verify state token hợp lệ và chưa hết hạn

### 3. HttpOnly Cookies
- Tokens lưu trong cookie `httpOnly` → JavaScript không đọc được
- `secure=True` → chỉ gửi qua HTTPS
- `samesite=lax` → chống CSRF cơ bản

### 4. Token Encryption (AES-256-GCM)
- Google tokens được mã hóa trước khi lưu DB
- Key: 32 bytes, base64-encoded trong biến môi trường
- Mỗi lần mã hóa dùng nonce random 12 bytes → cùng plaintext cho ciphertext khác nhau

### 5. Rate Limiting
- Redis sorted set theo IP
- Mặc định: 5 requests / 60 giây
- Sliding window algorithm

### 6. Single Active Session
- Mỗi lần đăng nhập mới → revoke tất cả refresh token cũ
- Chỉ 1 session hoạt động tại 1 thời điểm

---

## Luồng Refresh Token

Khi access token hết hạn (15 phút):

```
Frontend → POST /api/auth/refresh (cookie: refresh_token)
         → Backend hash token, tìm trong DB
         → Kiểm tra: chưa revoke, chưa hết hạn
         → Tạo access token mới
         → Set cookie access_token mới
```

---

## Luồng Logout

```
Frontend → POST /api/auth/logout (cookie: refresh_token)
         → Backend hash token, đánh dấu revoked_at trong DB
         → Xóa cookie access_token
         → Xóa cookie refresh_token
```

---

## Luồng kiểm tra user hiện tại

```
Frontend → GET /api/auth/me (cookie: access_token)
         → Backend decode JWT → lấy user_id
         → Query user từ DB
         → Kiểm tra OAuth grant status (Gmail, Calendar)
         → Trả về: { id, email, name, avatar_url, gmail_grant_valid, calendar_grant_valid }
```

---

## Cấu trúc Database

### Bảng `users`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| id | UUID | Primary key |
| email | VARCHAR(255) | Email Google (unique) |
| name | VARCHAR(255) | Tên hiển thị |
| avatar_url | VARCHAR | URL ảnh đại diện Google |
| google_sub | VARCHAR(255) | Google subject ID (unique) |
| created_at | TIMESTAMP | Thời điểm tạo |
| last_login | TIMESTAMP | Lần đăng nhập cuối |
| is_active | BOOLEAN | Trạng thái hoạt động |

### Bảng `oauth_grants`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| id | UUID | Primary key |
| user_id | UUID | FK → users.id |
| provider | VARCHAR(50) | Luôn là "google" |
| access_token_enc | TEXT | Google access token (mã hóa AES-256-GCM) |
| refresh_token_enc | TEXT | Google refresh token (mã hóa AES-256-GCM) |
| scopes | TEXT[] | Danh sách scope được cấp |
| token_expires_at | TIMESTAMP | Thời điểm access token hết hạn |
| is_valid | BOOLEAN | Token còn hợp lệ không |

### Bảng `refresh_tokens`
| Cột | Kiểu | Mô tả |
|-----|------|--------|
| id | UUID | Primary key |
| user_id | UUID | FK → users.id |
| token_hash | VARCHAR(64) | SHA-256 hash của raw token (unique) |
| expires_at | TIMESTAMP | Hết hạn sau 7 ngày |
| revoked_at | TIMESTAMP | NULL nếu chưa revoke |

---

## Cấu hình cần thiết

### File `backend/.env`
```env
# Google OAuth2
AUTH_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
AUTH_GOOGLE_CLIENT_SECRET=xxx
AUTH_GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT
AUTH_JWT_SECRET_KEY=<random-hex-64-chars>
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption key cho Google tokens
AUTH_OAUTH_TOKEN_ENCRYPTION_KEY=<base64-encoded-32-bytes>

# Whitelist
AUTH_WHITELIST_FILE_PATH=config/whitelist.txt

# Rate limiting
AUTH_RATE_LIMIT_LOGIN_MAX=5
AUTH_RATE_LIMIT_LOGIN_WINDOW_SECONDS=60
```

### File `backend/config/whitelist.txt`
```
# Thêm email HR được phép đăng nhập
admin@company.com
hr@company.com
```

---

## Tóm tắt các file liên quan

| File | Vai trò |
|------|---------|
| `frontend/src/app/login/page.tsx` | Trang đăng nhập (nút Google) |
| `frontend/src/middleware.ts` | Kiểm tra cookie, redirect nếu chưa login |
| `backend/src/modules/identity/api/router.py` | Các endpoint: login, callback, refresh, logout, me |
| `backend/src/modules/identity/application/auth_service.py` | Logic chính: initiate_login, handle_callback, logout |
| `backend/src/modules/identity/application/oauth_service.py` | Giao tiếp Google: exchange code, refresh token |
| `backend/src/modules/identity/application/token_service.py` | Quản lý JWT access + refresh token |
| `backend/src/modules/identity/application/whitelist_service.py` | Kiểm tra email whitelist |
| `backend/src/modules/identity/infrastructure/jwt_utils.py` | Encode/decode JWT, state token |
| `backend/src/modules/identity/infrastructure/crypto_utils.py` | Mã hóa/giải mã AES-256-GCM |
| `backend/src/modules/identity/infrastructure/rate_limiter.py` | Rate limiting bằng Redis |
| `backend/src/modules/identity/infrastructure/user_repository.py` | CRUD user trong PostgreSQL |
| `backend/src/modules/identity/domain/entities.py` | Entity: User, OAuthGrant, RefreshToken |
| `backend/config/whitelist.txt` | Danh sách email được phép đăng nhập |
