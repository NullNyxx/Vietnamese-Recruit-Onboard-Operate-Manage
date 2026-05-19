# Getting Started

Hướng dẫn khởi chạy dự án Vroom HR trên máy local.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (cho PostgreSQL + Redis)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)
- Python >= 3.11
- Node.js >= 18

---

## 1. Khởi động Infrastructure (PostgreSQL + Redis)

```bash
docker compose -f docker-compose.infra.yml up -d
```

Kiểm tra containers đang chạy:

```bash
docker ps
```

Kết quả mong đợi:
- `vroom-postgres` — PostgreSQL 15 trên port 5432
- `vroom-redis` — Redis 7 trên port 6379

---

## 2. Cấu hình Backend

### 2.1 File .env

Copy file `.env` mẫu (đã có sẵn tại `backend/.env`). Các biến cần cấu hình:

```env
# Database (match với docker-compose.infra.yml)
AUTH_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vroom_hr

# Redis (match với docker-compose.infra.yml)
AUTH_REDIS_URL=redis://localhost:6379/0

# Google OAuth2 — Lấy từ Google Cloud Console
AUTH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
AUTH_GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
AUTH_GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT — Tạo random key (giữ nguyên giá trị mẫu cho dev)
AUTH_JWT_SECRET_KEY=MTwHcUnedXDrRrvh4Ox58OF3i11kOyP4AZ4wmw9XVHw
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth token encryption — Base64-encoded 32-byte key
AUTH_OAUTH_TOKEN_ENCRYPTION_KEY=YZ3/AIRA0yfcqIWX7CdDonMUwu6UyftrG+LlJTker/4=

# Whitelist
AUTH_WHITELIST_FILE_PATH=config/whitelist.txt

# Rate limiting
AUTH_RATE_LIMIT_LOGIN_MAX=5
AUTH_RATE_LIMIT_LOGIN_WINDOW_SECONDS=60

# Frontend URL
AUTH_FRONTEND_URL=http://localhost:3000
```

### 2.2 Google OAuth2 Credentials

1. Vào [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project hoặc chọn project có sẵn
3. Vào **APIs & Services > Credentials**
4. Tạo **OAuth 2.0 Client ID** (Web application)
5. Thêm Authorized redirect URI: `http://localhost:8000/api/auth/callback`
6. Copy Client ID và Client Secret vào `.env`

### 2.3 Email Whitelist

Thêm email được phép login vào `backend/config/whitelist.txt`:

```text
# Email whitelist for Vroom HR
# One email per line. Lines starting with # are comments.

your-email@gmail.com
colleague@company.com
```

File này hỗ trợ hot-reload — sửa và save là có hiệu lực ngay, không cần restart server.

---

## 3. Chạy Backend

```bash
cd backend

# Cài dependencies
uv sync

# Chạy database migrations
uv run alembic upgrade head

# Start server (auto-reload khi sửa code)
uv run uvicorn src.main:app --reload --port 8000
```

Backend chạy tại: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## 4. Chạy Frontend

```bash
cd frontend

# Cài dependencies
pnpm install

# Start dev server
pnpm dev
```

Frontend chạy tại: http://localhost:3000

---

## 5. Test Login Flow

1. Mở http://localhost:3000
2. Sẽ redirect tới `/login`
3. Click **"Login with Google"**
4. Chọn Google account (email phải có trong whitelist)
5. Grant permissions (Gmail + Calendar)
6. Redirect về dashboard

---

## Chạy toàn bộ bằng Docker (full stack)

Nếu muốn chạy cả BE + FE trong Docker:

```bash
docker compose up --build
```

Lưu ý: Lần đầu build sẽ mất vài phút do pull images và install dependencies.

---

## Troubleshooting

### Redis connection refused

```
redis.exceptions.ConnectionError: Error connecting to localhost:6379
```

→ Chạy `docker compose -f docker-compose.infra.yml up -d` để start Redis.

### Google token exchange failed (400)

→ Kiểm tra `AUTH_GOOGLE_REDIRECT_URI` trong `.env` phải match chính xác với URI đã đăng ký trong Google Cloud Console.

### Access denied (403)

→ Email chưa có trong `backend/config/whitelist.txt`. Thêm email và save file.

### Database migration error

```bash
# Reset database (xóa data)
docker compose -f docker-compose.infra.yml down -v
docker compose -f docker-compose.infra.yml up -d

# Chạy lại migrations
cd backend
uv run alembic upgrade head
```

### Port đã bị chiếm

```bash
# Kiểm tra process đang dùng port
netstat -ano | findstr :8000
netstat -ano | findstr :3000
```

---

## Dừng dự án

```bash
# Dừng infrastructure
docker compose -f docker-compose.infra.yml down

# Dừng và xóa data
docker compose -f docker-compose.infra.yml down -v
```
