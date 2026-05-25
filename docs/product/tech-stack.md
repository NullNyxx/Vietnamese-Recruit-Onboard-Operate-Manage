# Tech Stack & Development Guide

## Backend

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Database:** PostgreSQL 15 (async via asyncpg)
- **Cache:** Redis 7
- **Migrations:** Alembic
- **Package Manager:** uv
- **Linting:** Ruff (line-length=100, select E/F/I/N/W/UP)
- **Type Checking:** MyPy (strict mode)
- **Testing:** pytest + pytest-asyncio, Hypothesis, respx, testcontainers

### Backend Commands

```bash
# From backend/ directory (activate venv first)
cd backend

# Run server
uvicorn src.main:app --reload --port 8000

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/

# Test
pytest tests/
```

## Frontend

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5.6
- **UI:** Radix UI + shadcn/ui
- **Styling:** Tailwind CSS 3.4
- **Forms:** react-hook-form + zod
- **Icons:** lucide-react
- **Testing:** Vitest + fast-check

### Frontend Commands

```bash
# From frontend/ directory
cd frontend

# Dev server
pnpm dev

# Build
pnpm build

# Lint
pnpm lint

# Test
pnpm test
```

## Infrastructure

```bash
# Start all services
docker compose up -d

# Start only DB + Redis (for local dev)
docker compose up -d postgres redis

# View logs
docker compose logs -f backend
```

## Environment Variables

Backend env vars are in `backend/.env` (see `.env.example` for template).

Key prefixes:

- `AUTH_*` — Identity module (Google OAuth, JWT, encryption)
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `MINIO_*` — Object storage

## Module Structure Convention

Every new module MUST follow:

```
backend/src/modules/<module_name>/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── router.py          # FastAPI router
│   ├── schemas.py         # Pydantic request/response models
│   └── error_handler.py   # Exception → HTTP response mapping
├── application/
│   ├── __init__.py
│   └── <name>_service.py  # Business logic
├── domain/
│   ├── __init__.py
│   ├── entities.py        # SQLModel table classes
│   ├── enums.py           # Domain enumerations
│   └── exceptions.py      # Domain-specific exceptions
├── infrastructure/
│   ├── __init__.py
│   ├── config.py          # Pydantic Settings
│   └── <name>_repository.py
└── container.py           # DI wiring (FastAPI Depends)
```

## Key Patterns

1. **Dependency Injection:** FastAPI `Depends()` with container.py per module
2. **Async-first:** All DB operations use AsyncSession
3. **Cookie-based auth:** JWT in httpOnly secure cookies (not Bearer headers)
4. **Soft delete:** Employees use `is_active` flag
5. **Audit trail:** Admin actions logged to audit_logs table
6. **Encryption:** OAuth tokens encrypted with AES-256-GCM before storage
7. **Whitelist:** Login restricted to pre-approved emails/domains
