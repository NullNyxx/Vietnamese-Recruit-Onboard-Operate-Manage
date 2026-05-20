---
inclusion: auto
---

# Project Context — Vroom HR

## Tổng quan

**Vroom HR** (Vietnamese Recruit-Onboard-Operate-Manage) là nền tảng web hỗ trợ HR quản lý công việc hàng ngày, lấy Email Inbox làm trung tâm. AI Agent phân loại email theo intent, tự động hoá pipeline tuyển dụng (OCR → parse CV → candidate pool → interview scheduling).

- **Deployment**: Self-hosted, single-tenant, Docker Compose
- **Users**: 1 HR user per instance (MVP)
- **Language**: Vietnamese-first (UI + data), code in English

## Tech Stack (LOCKED — không thay đổi)

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 + SQLModel, Pydantic v2 |
| Frontend | Next.js 14+ (App Router), TypeScript, shadcn/ui + Tailwind |
| Database | PostgreSQL 15+ (+ pgvector) |
| Cache/Queue | Redis 7+ (ARQ job queue) |
| Object Storage | MinIO (S3-compatible) |
| AI | LangGraph + litellm (multi-provider LLM) + PaddleOCR |
| Auth | Google OAuth2 + JWT (python-jose) + AES-256-GCM token encryption |
| Package Managers | uv (Python), pnpm (Node.js) |

## Architecture

**Modular Monolith + Light Clean Architecture**

```
backend/src/modules/{module_name}/
├── domain/          # Entities, value objects, exceptions (no framework imports)
├── application/     # Services, use cases, orchestrators
├── infrastructure/  # Repositories, adapters, external clients
└── api/             # FastAPI routers, schemas, dependencies
```

**Rules:**
- Modules KHÔNG import lẫn nhau trực tiếp
- Cross-module qua application service interface hoặc domain event
- Domain layer không import FastAPI, SQLAlchemy, Redis
- Config qua environment variables, validate bằng Pydantic Settings
- All datetime columns use `sa_column=Column(DateTime(timezone=True))`

## Modules & Status

| Module | Status | Spec |
|--------|--------|------|
| identity | ✅ Done (auth working E2E) | `.kiro/specs/identity-auth/` |
| employee | 🔄 Spec agreed, ready to implement | `.kiro/specs/employee-management/` |
| inbox | ⏳ Not started | — |
| recruitment | ⏳ Not started | — |
| interview | ⏳ Not started | — |
| ai_agent | ⏳ Not started | — |

## Implementation Order

1. ✅ identity — Google OAuth2, JWT sessions, whitelist
2. 🔄 employee — CRUD, Excel import, document vault (MinIO)
3. ⏳ inbox — Gmail fetch, AI intent classifier
4. ⏳ recruitment — CV pipeline, candidate pool
5. ⏳ interview — Calendar + Meet scheduling
6. ⏳ ai_agent — LangGraph workflows

## Key Files

| Purpose | Path |
|---------|------|
| Project spec | `harness-experimental/specs/project/vroom-hr.md` |
| Feature specs | `harness-experimental/specs/features/*.md` |
| Kiro specs (tasks) | `.kiro/specs/{feature}/tasks.md` |
| Backend entry | `backend/src/main.py` |
| Identity module | `backend/src/modules/identity/` |
| Employee module | `backend/src/modules/employee/` (to be created) |
| Docker infra | `docker-compose.infra.yml` (Postgres + Redis) |
| Docs | `docs/` (GIT_WORKFLOW, TECH_STACK, GETTING_STARTED) |
| Harness docs | `harness-experimental/docs/` |

## Package Managers

### Backend — uv

- **LUÔN dùng `uv`** thay vì `pip`, `pip install`, `pip freeze`
- Thêm dependency: `uv add <package>`
- Thêm dev dependency: `uv add --dev <package>`
- Chạy script: `uv run python ...` hoặc `uv run pytest ...`
- Sync dependencies: `uv sync`
- Lock file: `uv.lock` (commit vào repo)
- Config: `pyproject.toml` (section `[project]` + `[tool.uv]`)
- **KHÔNG dùng**: `pip install`, `pip freeze`, `requirements.txt`, `poetry`

### Frontend — pnpm

- **LUÔN dùng `pnpm`** thay vì `npm`, `yarn`
- Thêm dependency: `pnpm add <package>`
- Thêm dev dependency: `pnpm add -D <package>`
- Chạy script: `pnpm run <script>` hoặc `pnpm <script>`
- Install dependencies: `pnpm install`
- Lock file: `pnpm-lock.yaml` (commit vào repo)
- **KHÔNG dùng**: `npm install`, `npm run`, `yarn add`, `yarn`

### Khởi chạy dự án — Docker Compose

- **LUÔN dùng Docker Compose** để khởi chạy và test dự án
- Start toàn bộ: `docker compose up --build`
- Start riêng service: `docker compose up --build backend`
- Rebuild sau khi đổi code: `docker compose up --build`
- Xem logs: `docker compose logs -f <service>`
- Chạy migration: `docker compose exec backend uv run alembic upgrade head`
- File config: `docker-compose.yml` (root)
- **KHÔNG chạy trực tiếp** `uv run uvicorn ...` hay `pnpm dev` trên host — luôn qua Docker

## Git Workflow

### Khi user yêu cầu push code & tạo PR:

1. Stage các file liên quan: `git add <files>`
2. Commit với conventional commit message: `git commit -m "feat(module): mô tả ngắn"`
3. Push lên nhánh feature: `git push -u origin <branch-name>`
4. Tạo Pull Request bằng GitHub CLI: `gh pr create --title "..." --body "..."`
   - Title ngắn gọn < 70 ký tự
   - Body gồm: tóm tắt thay đổi, những gì đã test, ghi chú nếu có
5. Thông báo cho user link PR để review

### Khi user review done (merge xong):

1. Chuyển về nhánh main: `git checkout main`
2. Pull code mới nhất: `git pull origin main`
3. Xoá nhánh feature local (nếu đã merge): `git branch -d <branch-name>`
4. Thông báo cho user đã sẵn sàng cho task tiếp theo

### Quy tắc:

- **KHÔNG push trực tiếp lên main** — luôn qua PR
- Branch naming: `feat/`, `fix/`, `refactor/`, `docs/` + tên ngắn gọn (ví dụ: `feat/gmail-integration`)
- Commit message: conventional commits (feat, fix, refactor, docs, chore)
- Mỗi PR chỉ chứa 1 feature/fix, không gộp nhiều thay đổi không liên quan

## Conventions

- **Git**: Branch per feature, conventional commits, PR to main (xem chi tiết ở section Git Workflow)
- **Python**: snake_case, Google docstrings, type hints mandatory, ruff + mypy
- **TypeScript**: camelCase, strict mode, eslint
- **Testing**: pytest + pytest-asyncio, testcontainers for integration
- **Secrets**: Never commit .env, use .env.example for templates

## Constraints (Ask Human First)

- Không đổi tech stack
- Không đổi architecture (modular monolith)
- Không mở rộng scope ngoài current epic
- Không bỏ PII redaction hoặc audit log
- Không thêm external service mới
