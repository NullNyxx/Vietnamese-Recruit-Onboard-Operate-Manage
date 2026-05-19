# Tech Stack & Package Managers

## Package Managers

| Layer | Tool | Version | Mô tả |
|-------|------|---------|--------|
| Backend (Python) | [uv](https://docs.astral.sh/uv/) | latest | Fast Python package manager & project tool |
| Frontend (Node.js) | [pnpm](https://pnpm.io/) | latest | Fast, disk-efficient Node.js package manager |

---

## Backend — Python + uv

### Cài đặt uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Sử dụng

```bash
cd backend

# Tạo virtual environment + cài dependencies từ pyproject.toml
uv sync

# Cài thêm dependency
uv add <package>

# Cài dev dependency
uv add --dev <package>

# Chạy command trong venv (không cần activate)
uv run uvicorn src.main:app --reload --port 8000

# Chạy tests
uv run pytest tests/ -v

# Chạy linter
uv run ruff check .

# Chạy type checker
uv run mypy src/
```

### Cấu trúc file

```text
backend/
├── pyproject.toml      ← Dependencies + project config
├── uv.lock             ← Lock file (auto-generated, commit vào git)
├── .python-version     ← Python version constraint
├── .env                ← Environment variables (không commit)
├── config/
│   └── whitelist.txt   ← Email whitelist
└── src/
    └── ...
```

### Quy tắc

- Luôn dùng `uv add` thay vì edit pyproject.toml thủ công
- Commit `uv.lock` vào git để đảm bảo reproducible builds
- Dùng `uv run` để chạy commands — không cần activate venv thủ công
- Python version: >= 3.11

---

## Frontend — Node.js + pnpm

### Cài đặt pnpm

```bash
# Nếu đã có Node.js
npm install -g pnpm

# Hoặc standalone (không cần npm)
# Windows (PowerShell)
iwr https://get.pnpm.io/install.ps1 -useb | iex

# macOS / Linux
curl -fsSL https://get.pnpm.io/install.sh | sh -
```

### Sử dụng

```bash
cd frontend

# Cài dependencies từ package.json
pnpm install

# Chạy dev server
pnpm dev

# Build production
pnpm build

# Chạy linter
pnpm lint

# Thêm dependency
pnpm add <package>

# Thêm dev dependency
pnpm add -D <package>

# Remove dependency
pnpm remove <package>
```

### Cấu trúc file

```text
frontend/
├── package.json        ← Dependencies + scripts
├── pnpm-lock.yaml      ← Lock file (auto-generated, commit vào git)
├── next.config.js      ← Next.js configuration
├── tsconfig.json       ← TypeScript config
├── tailwind.config.ts  ← Tailwind CSS config
└── src/
    ├── app/            ← Next.js App Router pages
    ├── components/     ← Shared components
    └── lib/            ← Utilities
```

### Quy tắc

- Luôn dùng `pnpm` thay vì `npm` hoặc `yarn`
- Commit `pnpm-lock.yaml` vào git
- Không commit `node_modules/`
- Node.js version: >= 18

---

## Khởi động Development

### Prerequisites

1. Python >= 3.11 + uv
2. Node.js >= 18 + pnpm
3. PostgreSQL 15+ (chạy local hoặc Docker)
4. Redis 7+ (chạy local hoặc Docker)

### Backend

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

Backend sẽ chạy tại: http://localhost:8000

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend sẽ chạy tại: http://localhost:3000

### Docker (PostgreSQL + Redis)

```bash
# PostgreSQL
docker run -d --name vroom-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=vroom_hr \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d --name vroom-redis \
  -p 6379:6379 \
  redis:7
```

### Chạy migrations

```bash
cd backend
uv run alembic upgrade head
```

---

## Tại sao chọn uv + pnpm?

| Tiêu chí | uv (Python) | pnpm (Node.js) |
|-----------|-------------|----------------|
| Tốc độ | 10-100x nhanh hơn pip | 2-3x nhanh hơn npm |
| Disk usage | Shared cache | Content-addressable store |
| Lock file | Deterministic | Deterministic |
| Monorepo | Workspace support | Workspace support |
| DX | `uv run` không cần activate | Strict by default |
