# Vroom HR — Product Overview

Vroom HR (Vietnamese Recruit-Onboard-Operate-Manage) là nền tảng quản lý nhân
sự cho doanh nghiệp Việt Nam, tập trung hiện tại vào tuyển dụng, onboarding,
vận hành hồ sơ nhân sự, Gmail integration, và quản trị danh tính.

## Tech Stack

| Layer          | Technology                                                   |
| -------------- | ------------------------------------------------------------ |
| Backend        | FastAPI (Python 3.11+), SQLModel, asyncpg                    |
| Database       | PostgreSQL 15                                                |
| Cache          | Redis 7                                                      |
| Frontend       | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Object Storage | MinIO (via aioboto3)                                         |
| AI             | OpenAI API (CV parsing)                                      |
| Auth           | Google OAuth2 + PKCE, JWT (cookie-based)                     |
| Infra          | Docker Compose                                               |
| Migrations     | Alembic (27 schema revisions; 027 retires attendance/payroll)|
| Testing        | pytest, Hypothesis, Vitest, fast-check                       |

## Modules

### 1. Identity & Auth (`backend/src/modules/identity/`)

- Google OAuth2 login with PKCE
- JWT access/refresh tokens (httpOnly cookies)
- Email whitelist (file + DB)
- Role-based access: admin / user
- Rate limiting (Redis)
- Admin audit logging
- OAuth config management

### 2. Employee Management (`backend/src/modules/employee/`)

- Employee CRUD with pagination, search, filters
- Departments & Positions management
- Excel import
- Document vault (MinIO storage)
- Candidate-to-employee promotion

### 3. Gmail Integration (`backend/src/modules/gmail/`)

- Gmail API connection
- Email sending
- Message tracking

### 4. Recruitment (`backend/src/modules/recruitment/`)

- Candidate pipeline: new → reviewing → interview_scheduled → accepted/rejected → archived
- CV document storage with presigned URLs
- AI-powered CV parsing (OpenAI)
- Recruitment metrics & audit logs

## Retired Modules

Migration `027_drop_attendance_payroll_tables.py` removed attendance, leave,
payroll, and related tables from active application state. Product specs remain
under `docs/product/attendance/`, `docs/product/payroll/`, and
`docs/product/self-service/` as archived/reference material until those modules
are reintroduced by a new story.

### Attendance (`backend/src/modules/attendance/`)

- Check-in/out
- Manual records
- Monthly reports & Excel export
- Work schedules & holidays
- Overtime requests
- Email report distribution

### Leave Management (within attendance module)

- Leave types, balances, requests

### Payroll (`backend/src/modules/payroll/`)

- Salary configs & allowances
- Dependents (tax deduction)
- Payroll periods & payslip calculation
- Vietnamese tax model (personal deduction 11M VND)
- PDF payslip generation
- Email distribution
- Position-based salaries

### Self-Service / ESS (`backend/src/modules/self_service/`)

- Employee self-service portal
- Audit middleware

## Architecture Pattern

Mỗi module tuân theo Clean/Hexagonal Architecture:

```
module/
├── api/           # FastAPI routers, schemas, error handlers
├── application/   # Service layer (business logic)
├── domain/        # Entities, enums, exceptions
├── infrastructure/# Repositories, external clients, config
└── container.py   # Dependency injection wiring
```

## Active Database Tables (18 tables)

users, oauth_grants, refresh_tokens, departments, positions, employees,
employee_documents, email_messages, candidates, cv_documents,
recruitment_audit_logs, whitelist_entries, oauth_configs, audit_logs,
sync_cursors, gmail_label_mappings, email_attachments, gmail_audit_logs

Retired by migration 027: leave_types, leave_balances, leave_requests,
work_schedules, attendance_records, overtime_requests, holidays,
salary_configs, allowances, dependents, payroll_periods, payslips,
position_salaries.

## API Prefixes

- `/api/auth/` — Authentication
- `/api/auth/admin/` — Admin management
- `/api/employees/` — Employee CRUD
- `/api/departments/` — Departments
- `/api/positions/` — Positions
- `/api/documents/` — Document vault
- `/api/gmail/` — Gmail integration
- `/api/recruitment/candidates/` — Recruitment
- `/api/recruitment/cv-review/` — AI CV review
- `/api/recruitment/metrics/` — Analytics
- `/health` — Health check
