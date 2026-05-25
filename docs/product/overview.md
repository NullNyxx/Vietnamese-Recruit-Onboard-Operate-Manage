# Vroom HR — Product Overview

Vroom HR (Vietnamese Recruit-Onboard-Operate-Manage) là nền tảng quản lý nhân
sự toàn diện cho doanh nghiệp Việt Nam, bao gồm tuyển dụng, onboarding, vận
hành nhân sự, chấm công, nghỉ phép, và tính lương theo luật Việt Nam.

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
| Migrations     | Alembic (26 migrations)                                      |
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

### 5. Attendance (`backend/src/modules/attendance/`)

- Check-in/out
- Manual records
- Monthly reports & Excel export
- Work schedules & holidays
- Overtime requests
- Email report distribution

### 6. Leave Management (within attendance module)

- Leave types, balances, requests

### 7. Payroll (`backend/src/modules/payroll/`)

- Salary configs & allowances
- Dependents (tax deduction)
- Payroll periods & payslip calculation
- Vietnamese tax model (personal deduction 11M VND)
- PDF payslip generation
- Email distribution
- Position-based salaries

### 8. Self-Service / ESS (`backend/src/modules/self_service/`)

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

## Database (26 tables)

users, oauth_grants, refresh_tokens, departments, positions, employees,
employee_documents, email_messages, candidates, cv_documents,
recruitment_audit_logs, whitelist_entries, oauth_configs, audit_logs,
leave_types, leave_balances, leave_requests, work_schedules,
attendance_records, overtime_requests, holidays, salary_configs,
allowances, dependents, payroll_periods, payslips, position_salaries

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
- `/api/attendance/` — Attendance
- `/api/attendance/leave/` — Leave
- `/api/attendance/overtime/` — Overtime
- `/api/attendance/schedules/` — Schedules
- `/api/payroll/` — Payroll
- `/api/payroll/salary/` — Salary config
- `/api/ess/` — Employee self-service
- `/health` — Health check
