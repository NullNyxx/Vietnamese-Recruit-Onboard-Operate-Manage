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

## Conventions

- **Git**: Branch per feature (`feat/`, `fix/`, `refactor/`), conventional commits, PR to main
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
