# Identity & Auth — Feature Spec

## 1. Tổng quan

Module Identity & Auth quản lý toàn bộ luồng xác thực và phân quyền của hệ thống Vroom HR. Sử dụng Google OAuth2 với PKCE flow để đăng nhập, JWT tokens lưu trong httpOnly cookies để duy trì session, và email whitelist để kiểm soát ai được phép truy cập hệ thống.

Module cũng cung cấp giao diện quản trị cho admin: quản lý whitelist, phân quyền, cấu hình OAuth, và audit logs.

## 2. Actors

| Actor                   | Mô tả                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| **Anonymous User**      | Người chưa đăng nhập, chỉ có thể truy cập `/api/auth/login`       |
| **User (role: user)**   | Nhân viên đã đăng nhập, xem thông tin cá nhân                     |
| **Admin (role: admin)** | Quản trị viên, quản lý whitelist/users/roles/OAuth config         |
| **Super Admin**         | Admin đầu tiên được bootstrap từ env var `AUTH_SUPER_ADMIN_EMAIL` |
| **System (Redis)**      | Quản lý rate limiting và token blacklist                          |

## 3. Luồng hoạt động (User Flows)

### 3.1 Login Flow (Google OAuth2 + PKCE)

```
User                    Frontend              Backend                 Google
 │                        │                      │                      │
 │── Click Login ────────►│                      │                      │
 │                        │── GET /api/auth/login ►│                      │
 │                        │                      │── Generate:           │
 │                        │                      │   - code_verifier     │
 │                        │                      │   - code_challenge    │
 │                        │                      │   - state (CSRF)      │
 │                        │                      │── Store in session ──►│
 │                        │◄─ 302 Redirect ──────│                      │
 │                        │                      │                      │
 │◄─ Redirect to Google ──│                      │                      │
 │── Consent + Login ─────────────────────────────────────────────────►│
 │                        │                      │                      │
 │◄─ Redirect callback ──────────────────────────────────────────────── │
 │                        │                      │                      │
 │── GET /api/auth/callback?code=X&state=Y ─────►│                      │
 │                        │                      │── Verify state (CSRF)│
 │                        │                      │── Exchange code ─────►│
 │                        │                      │◄─ tokens ────────────│
 │                        │                      │── Verify email in     │
 │                        │                      │   whitelist           │
 │                        │                      │── Create/update User  │
 │                        │                      │── Encrypt OAuth token │
 │                        │                      │   (AES-256-GCM)      │
 │                        │                      │── Generate JWT access │
 │                        │                      │   + refresh token     │
 │                        │                      │── Set httpOnly cookies│
 │◄─ 302 Redirect to frontend ──────────────────│                      │
```

### 3.2 Token Refresh Flow

```
Frontend                    Backend                    Redis
 │                            │                          │
 │── GET /api/auth/refresh ──►│                          │
 │   (cookie: refresh_token)  │── Validate refresh token │
 │                            │── Check not revoked ─────►│
 │                            │◄─ OK ───────────────────│
 │                            │── Generate new access    │
 │                            │   token (15min)          │
 │                            │── Set new cookie         │
 │◄─ 200 + new access_token ─│                          │
```

### 3.3 Logout Flow

```
Frontend                    Backend                    Redis
 │                            │                          │
 │── POST /api/auth/logout ──►│                          │
 │   (cookie: refresh_token)  │── Revoke refresh token ─►│
 │                            │── Clear cookies          │
 │◄─ 200 OK ─────────────────│                          │
```

### 3.4 Admin Whitelist Management

```
Admin                       Backend                    Database
 │                            │                          │
 │── POST /api/admin/whitelist ►│                          │
 │   {pattern: "@company.vn"}  │── Validate pattern       │
 │                            │── Check duplicates ──────►│
 │                            │── Insert entry ──────────►│
 │                            │── Write audit log ───────►│
 │◄─ 201 Created ────────────│                          │
```

## 4. Business Rules

1. **BR-01**: Chỉ email có trong whitelist (file `config/whitelist.txt` HOẶC bảng `whitelist_entries`) mới được đăng nhập.
2. **BR-02**: Whitelist hỗ trợ 2 dạng pattern:
   - Exact email: `user@company.vn`
   - Domain pattern: `@company.vn` (cho phép tất cả email thuộc domain)
3. **BR-03**: Access token hết hạn sau 15 phút (`AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15`).
4. **BR-04**: Refresh token hết hạn sau 7 ngày (`AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7`).
5. **BR-05**: Rate limiting: tối đa 5 requests/60 giây per IP cho login endpoint (Redis sliding window).
6. **BR-06**: Super admin được bootstrap tự động khi email khớp `AUTH_SUPER_ADMIN_EMAIL` env var.
7. **BR-07**: Chỉ admin mới có quyền:
   - Quản lý whitelist (CRUD)
   - Thay đổi role user
   - Cấu hình OAuth
   - Xem audit logs
8. **BR-08**: OAuth tokens (Google access/refresh) được mã hóa AES-256-GCM trước khi lưu DB.
9. **BR-09**: PKCE flow bắt buộc — code_verifier + code_challenge (S256) để chống authorization code interception.
10. **BR-10**: State parameter (CSRF token) phải khớp giữa login request và callback.
11. **BR-11**: Mọi admin action phải ghi audit log (actor, action, target, timestamp, IP).
12. **BR-12**: JWT chỉ dùng HMAC algorithms (HS256/HS384/HS512), không dùng RSA.
13. **BR-13**: Cookies phải có flags: `httpOnly`, `secure` (production), `SameSite=Lax`.
14. **BR-14**: User bị xóa khỏi whitelist → refresh token bị revoke → không thể refresh.

## 5. Data Model

### User

| Field         | Type                 | Constraints              | Mô tả                  |
| ------------- | -------------------- | ------------------------ | ---------------------- |
| id            | UUID                 | PK, auto-generated       | ID duy nhất            |
| email         | String(255)          | UNIQUE, NOT NULL         | Email Google           |
| name          | String(255)          | NOT NULL                 | Tên hiển thị từ Google |
| picture_url   | String(500)          | NULLABLE                 | Avatar URL             |
| role          | Enum('admin','user') | NOT NULL, DEFAULT 'user' | Vai trò                |
| is_active     | Boolean              | NOT NULL, DEFAULT true   | Trạng thái hoạt động   |
| created_at    | DateTime             | NOT NULL, auto           | Thời điểm tạo          |
| updated_at    | DateTime             | NOT NULL, auto           | Thời điểm cập nhật     |
| last_login_at | DateTime             | NULLABLE                 | Lần đăng nhập cuối     |

### WhitelistEntry

| Field        | Type                   | Constraints            | Mô tả              |
| ------------ | ---------------------- | ---------------------- | ------------------ |
| id           | UUID                   | PK                     | ID duy nhất        |
| pattern      | String(255)            | UNIQUE, NOT NULL       | Email hoặc @domain |
| pattern_type | Enum('email','domain') | NOT NULL               | Loại pattern       |
| description  | String(500)            | NULLABLE               | Ghi chú            |
| created_by   | UUID                   | FK → users.id          | Admin tạo          |
| created_at   | DateTime               | NOT NULL               | Thời điểm tạo      |
| is_active    | Boolean                | NOT NULL, DEFAULT true | Còn hiệu lực       |

### OAuthGrant

| Field                   | Type       | Constraints                | Mô tả                       |
| ----------------------- | ---------- | -------------------------- | --------------------------- |
| id                      | UUID       | PK                         | ID duy nhất                 |
| user_id                 | UUID       | FK → users.id, NOT NULL    | User sở hữu                 |
| provider                | String(50) | NOT NULL, DEFAULT 'google' | OAuth provider              |
| access_token_encrypted  | Text       | NOT NULL                   | Token đã mã hóa AES-256-GCM |
| refresh_token_encrypted | Text       | NULLABLE                   | Refresh token đã mã hóa     |
| token_expiry            | DateTime   | NULLABLE                   | Thời điểm token hết hạn     |
| scopes                  | Text       | NULLABLE                   | OAuth scopes granted        |
| created_at              | DateTime   | NOT NULL                   | Thời điểm tạo               |
| updated_at              | DateTime   | NOT NULL                   | Thời điểm cập nhật          |

### RefreshToken

| Field      | Type        | Constraints             | Mô tả                  |
| ---------- | ----------- | ----------------------- | ---------------------- |
| id         | UUID        | PK                      | ID duy nhất            |
| user_id    | UUID        | FK → users.id, NOT NULL | User sở hữu            |
| token_hash | String(255) | UNIQUE, NOT NULL        | SHA-256 hash của token |
| expires_at | DateTime    | NOT NULL                | Thời điểm hết hạn      |
| is_revoked | Boolean     | NOT NULL, DEFAULT false | Đã bị thu hồi          |
| created_at | DateTime    | NOT NULL                | Thời điểm tạo          |
| revoked_at | DateTime    | NULLABLE                | Thời điểm thu hồi      |

### OAuthConfig

| Field                   | Type        | Constraints            | Mô tả              |
| ----------------------- | ----------- | ---------------------- | ------------------ |
| id                      | UUID        | PK                     | ID duy nhất        |
| provider                | String(50)  | UNIQUE, NOT NULL       | Provider name      |
| client_id               | String(255) | NOT NULL               | OAuth client ID    |
| client_secret_encrypted | Text        | NOT NULL               | Secret đã mã hóa   |
| redirect_uri            | String(500) | NOT NULL               | Callback URL       |
| scopes                  | Text        | NOT NULL               | Required scopes    |
| is_active               | Boolean     | NOT NULL, DEFAULT true | Đang hoạt động     |
| updated_by              | UUID        | FK → users.id          | Admin cập nhật     |
| updated_at              | DateTime    | NOT NULL               | Thời điểm cập nhật |

### AuditLog

| Field       | Type        | Constraints             | Mô tả                                |
| ----------- | ----------- | ----------------------- | ------------------------------------ |
| id          | UUID        | PK                      | ID duy nhất                          |
| actor_id    | UUID        | FK → users.id, NOT NULL | Người thực hiện                      |
| action      | String(100) | NOT NULL                | Hành động (e.g., 'whitelist.create') |
| target_type | String(100) | NULLABLE                | Loại đối tượng bị tác động           |
| target_id   | String(255) | NULLABLE                | ID đối tượng                         |
| details     | JSON        | NULLABLE                | Chi tiết bổ sung                     |
| ip_address  | String(45)  | NULLABLE                | IP của actor                         |
| created_at  | DateTime    | NOT NULL                | Thời điểm                            |

## 6. State Machine

### User Status

```
                 ┌──────────────┐
                 │   inactive   │
                 └──────┬───────┘
                        │ admin activates
                        ▼
┌─────────┐    login   ┌──────────────┐
│  (new)  │ ─────────► │    active    │
└─────────┘            └──────┬───────┘
                              │ admin deactivates
                              ▼
                       ┌──────────────┐
                       │   inactive   │
                       └──────────────┘
```

### Refresh Token Lifecycle

```
created → active → revoked (logout/admin action)
                 → expired (TTL 7 days)
```

## 7. API Endpoints

### Authentication

| Method | Path                     | Mô tả                                      | Auth                   |
| ------ | ------------------------ | ------------------------------------------ | ---------------------- |
| GET    | `/api/auth/login`        | Khởi tạo OAuth flow, redirect to Google    | None                   |
| GET    | `/api/auth/callback`     | OAuth callback, exchange code, set cookies | None                   |
| GET    | `/api/auth/refresh`      | Refresh access token                       | Cookie (refresh_token) |
| POST   | `/api/auth/logout`       | Revoke refresh token, clear cookies        | Cookie (access_token)  |
| GET    | `/api/auth/me`           | Lấy thông tin user hiện tại                | Cookie (access_token)  |
| GET    | `/api/auth/grant-status` | Kiểm tra OAuth grant còn hiệu lực          | Cookie (access_token)  |

### Admin Management

| Method | Path                           | Mô tả                                        | Auth  |
| ------ | ------------------------------ | -------------------------------------------- | ----- |
| GET    | `/api/admin/whitelist`         | Danh sách whitelist entries                  | Admin |
| POST   | `/api/admin/whitelist`         | Thêm whitelist entry                         | Admin |
| PUT    | `/api/admin/whitelist/{id}`    | Cập nhật whitelist entry                     | Admin |
| DELETE | `/api/admin/whitelist/{id}`    | Xóa whitelist entry                          | Admin |
| GET    | `/api/admin/users`             | Danh sách users (paginated)                  | Admin |
| PUT    | `/api/admin/users/{id}/role`   | Thay đổi role user                           | Admin |
| PUT    | `/api/admin/users/{id}/status` | Activate/deactivate user                     | Admin |
| GET    | `/api/admin/oauth`             | Lấy OAuth config hiện tại                    | Admin |
| PUT    | `/api/admin/oauth`             | Cập nhật OAuth config                        | Admin |
| GET    | `/api/admin/audit-logs`        | Danh sách audit logs (paginated, filterable) | Admin |

## 8. Edge Cases & Error Handling

| Scenario                         | Xử lý                                                            |
| -------------------------------- | ---------------------------------------------------------------- |
| Email không trong whitelist      | 403 `EMAIL_NOT_WHITELISTED` — redirect về frontend với error     |
| State mismatch (CSRF)            | 400 `INVALID_STATE` — reject callback                            |
| Google trả lỗi khi exchange code | 502 `OAUTH_EXCHANGE_FAILED` — log error, redirect với error      |
| Rate limit exceeded              | 429 `RATE_LIMIT_EXCEEDED` — header `Retry-After`                 |
| Refresh token expired            | 401 `TOKEN_EXPIRED` — client phải re-login                       |
| Refresh token revoked            | 401 `TOKEN_REVOKED` — client phải re-login                       |
| Access token invalid/malformed   | 401 `INVALID_TOKEN`                                              |
| Admin tự hạ role mình            | 403 `CANNOT_DEMOTE_SELF`                                         |
| Xóa super admin                  | 403 `CANNOT_MODIFY_SUPER_ADMIN`                                  |
| Whitelist pattern trùng          | 409 `PATTERN_ALREADY_EXISTS`                                     |
| OAuth token decryption fail      | 500 `ENCRYPTION_ERROR` — log, require re-auth                    |
| Redis unavailable                | Fallback: allow request nhưng log warning (graceful degradation) |
| Concurrent refresh token usage   | Revoke tất cả tokens của user (token rotation)                   |

## 9. Integration Points

| Module           | Cách tích hợp                                                              |
| ---------------- | -------------------------------------------------------------------------- |
| **Employee**     | `User.email` liên kết với `Employee.email` để xác định employee_id cho ESS |
| **Gmail**        | Sử dụng `OAuthGrant.access_token` (decrypted) để gọi Gmail API             |
| **Self-Service** | JWT chứa `user_id` + `employee_id`, ESS dùng để xác định nhân viên         |
| **All Modules**  | Middleware extract user từ JWT cookie, inject vào request state            |
| **Audit**        | Mọi module có thể ghi audit log thông qua shared audit service             |

## 10. Configuration

| Env Variable                           | Default                                   | Mô tả                               |
| -------------------------------------- | ----------------------------------------- | ----------------------------------- |
| `AUTH_GOOGLE_CLIENT_ID`                | (required)                                | Google OAuth2 Client ID             |
| `AUTH_GOOGLE_CLIENT_SECRET`            | (required)                                | Google OAuth2 Client Secret         |
| `AUTH_GOOGLE_REDIRECT_URI`             | `http://localhost:8000/api/auth/callback` | OAuth callback URL                  |
| `AUTH_JWT_SECRET_KEY`                  | (required)                                | Secret key cho JWT signing          |
| `AUTH_JWT_ALGORITHM`                   | `HS256`                                   | JWT algorithm (HS256/HS384/HS512)   |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`     | `15`                                      | Thời gian sống access token (phút)  |
| `AUTH_REFRESH_TOKEN_EXPIRE_DAYS`       | `7`                                       | Thời gian sống refresh token (ngày) |
| `AUTH_OAUTH_TOKEN_ENCRYPTION_KEY`      | (required)                                | Base64-encoded 32-byte AES key      |
| `AUTH_WHITELIST_FILE_PATH`             | `config/whitelist.txt`                    | Đường dẫn file whitelist            |
| `AUTH_RATE_LIMIT_LOGIN_MAX`            | `5`                                       | Số request tối đa per window        |
| `AUTH_RATE_LIMIT_LOGIN_WINDOW_SECONDS` | `60`                                      | Sliding window (giây)               |
| `AUTH_SUPER_ADMIN_EMAIL`               | (optional)                                | Email auto-assign admin role        |
| `AUTH_FRONTEND_URL`                    | `http://localhost:3000`                   | Frontend URL cho redirect           |
| `AUTH_DATABASE_URL`                    | `postgresql+asyncpg://...`                | Database connection string          |
| `AUTH_REDIS_URL`                       | `redis://localhost:6379/0`                | Redis connection string             |
