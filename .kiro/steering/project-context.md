---
inclusion: always
---

# Vroom HR — Project Context

Đây là nền tảng quản lý nhân sự (HRM) cho doanh nghiệp Việt Nam.
Tên project: **Vroom HR** (Vietnamese Recruit-Onboard-Operate-Manage).

## Quick Reference

- **Backend:** FastAPI + SQLModel + PostgreSQL 15 + Redis 7 (Python 3.11+)
- **Frontend:** Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Auth:** Google OAuth2 + PKCE, JWT cookies, email whitelist
- **Storage:** MinIO (documents, CVs, payslips)
- **AI:** OpenAI (CV parsing)
- **Infra:** Docker Compose

## Project Structure

```
backend/src/modules/
├── identity/       # Auth, OAuth, JWT, roles, whitelist, audit
├── employee/       # Employee CRUD, departments, positions, documents
├── gmail/          # Gmail API integration
├── recruitment/    # Candidate pipeline, CV processing (AI)
├── attendance/     # Check-in/out, schedules, leave, overtime
├── payroll/        # Salary, payslips, Vietnamese tax calculation
└── self_service/   # Employee self-service (ESS)

frontend/src/
├── app/(dashboard)/  # Admin views
├── app/(employee)/   # Employee self-service views
├── components/       # Shared UI components
├── hooks/            # Custom React hooks
└── lib/              # API clients, utils
```

## Module Architecture (mỗi module)

```
api/           → Routers, schemas, error handlers
application/   → Services (business logic)
domain/        → Entities, enums, exceptions
infrastructure/→ Repositories, configs, external clients
container.py   → Dependency injection
```

## Key Commands

```bash
# Backend (from backend/)
uvicorn src.main:app --reload --port 8000
alembic upgrade head
ruff check src/ && ruff format src/
pytest tests/

# Frontend (from frontend/)
pnpm dev
pnpm build
pnpm lint
pnpm test

# Docker
docker compose up -d postgres redis  # local dev
docker compose up -d                 # full stack
```

## Harness Usage

Project sử dụng Harness framework. Trước khi làm việc:

1. Đọc `docs/HARNESS.md` để hiểu quy trình
2. Phân loại task theo `docs/FEATURE_INTAKE.md`
3. Dùng CLI để ghi nhận:

```bash
# WSL required (bash script + sqlite3)
wsl -- /bin/bash -c "cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage && /bin/bash scripts/harness <command>"

# Common commands:
scripts/harness intake --type <type> --summary "<text>" --lane <lane>
scripts/harness story add --id <id> --title "<text>" --lane <lane>
scripts/harness story update --id <id> --status <status>
scripts/harness trace --summary "<text>" --outcome <outcome>
scripts/harness query matrix
scripts/harness query stats
scripts/harness backlog add --title "<name>" --pain "<what was hard>"
```

## Important Conventions

- Tất cả API routes bắt đầu bằng `/api/`
- Auth dùng cookies (không phải Bearer token headers)
- Soft delete cho employees (`is_active` flag)
- Mọi admin action phải có audit log
- OAuth tokens encrypted AES-256-GCM
- Vietnamese tax: personal deduction 11M VND/month
- Line length: 100 chars (Ruff)
- Strict MyPy typing

## Docs Reference

- #[[file:docs/product/overview.md]] — Full product overview
- #[[file:docs/product/tech-stack.md]] — Tech stack & commands
- #[[file:docs/HARNESS.md]] — Harness operating model
- #[[file:docs/FEATURE_INTAKE.md]] — Feature intake & risk lanes
- #[[file:docs/ARCHITECTURE.md]] — Architecture rules
