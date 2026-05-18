# SPEC-PROJECT — Vroom HR

> **Phiên bản:** 1.0.0
> **Ngày tạo:** 2026-05-18
> **Tác giả:** NullNyx + Kiro
> **Trạng thái:** `Accepted`

---

## 1. Tổng quan dự án

### Mô tả

**Vroom HR** — **V**ietnamese **R**ecruit-**O**nboard-**O**perate-**M**anage — là một nền tảng web
hỗ trợ HR quản lý công việc hàng ngày, lấy **Email Inbox** làm trung tâm. AI Agent phân loại email theo intent
(CV ứng viên, đối tác, sự kiện, nhân sự nội bộ...), tự động hoá pipeline
tuyển dụng (OCR → parse CV → candidate pool → interview scheduling), và
giúp HR giảm tải khối lượng công việc lặp đi lặp lại.

Sản phẩm được giao dưới dạng self-hosted single-tenant — mỗi công ty khách
hàng có instance riêng, deploy qua Docker Compose trên 1 server.

### Mục tiêu chính

1. Giảm 70% thời gian HR xử lý email CV thủ công
2. Tự động hoá pipeline: nhận CV → parse → candidate pool → lên lịch phỏng vấn
3. Cung cấp inbox thông minh phân loại email theo intent
4. Quản lý nhân sự tập trung (profile, hồ sơ, document vault)
5. AI Agent gợi ý hành động, HR ra quyết định cuối cùng

### Đối tượng sử dụng

| Role | Mô tả |
|------|--------|
| HR | Actor duy nhất login hệ thống. Quản lý inbox, tuyển dụng, nhân sự |

**Subjects (không login):** Candidate, Employee, Tech Lead/Interviewer,
Partner/Client, Event Speaker — tương tác qua email.

---

## 2. Phạm vi tổng thể

### Trong scope (MVP-1)

| Module | Mô tả |
|--------|--------|
| Inbox | Email workspace, AI intent classifier, thread view, filter by intent |
| Recruitment | CV pipeline (OCR → parse → candidate pool), 6 actions, email templates |
| Interview | Scheduling (Google Calendar + Meet), interviewer assignment |
| Employee | Profile management, Excel import, document vault, candidate → employee |
| AI Agent | LangGraph workflows: classify, parse CV, parse hồ sơ, draft email |
| Identity | HR authentication (email/password + JWT + optional Google SSO) |

### Không trong scope (MVP-1)

| Item | Lý do |
|------|--------|
| Leave & Attendance | Phase 2 — cần Employee login, chưa có trong MVP |
| Payroll | Phase 3 — phụ thuộc Leave & Attendance |
| Multi-HR (nhiều HR cùng dùng) | Phase 2 — MVP chỉ 1 HR account |
| Mobile app | Phase 3 — MVP web-only |
| Candidate self-service portal | Phase 2 — MVP candidate chỉ qua email |
| Email draft/reply assist (non-CV) | Phase 2 — MVP chỉ classify, chưa draft |
| Microsoft 365 integration | Phase 2 — MVP Google Workspace only |
| RAG knowledge base (HR policies) | Phase 2 — MVP chưa cần |

---

## 3. Tech Stack

> **Đây là quyết định cứng — agent không thay đổi trừ khi human cho phép.**

### Core Stack

| Thành phần | Công nghệ | Version | Ghi chú |
|------------|-----------|---------|---------|
| Backend framework | FastAPI | 0.115+ | Async-first, Pydantic v2 native |
| Language | Python | 3.11+ | Type hints, async/await |
| ORM | SQLAlchemy 2.0 + SQLModel | latest | Type-safe, async session |
| Validation | Pydantic v2 | 2.x | Contract giữa các layer |
| Frontend framework | Next.js (App Router) | 14+ | SSR + client interactive |
| Frontend language | TypeScript | 5.x | Strict mode |
| UI library | shadcn/ui + Tailwind CSS | latest | Accessible components |
| Database | PostgreSQL + pgvector | 15+ | Relational + vector embeddings |
| Cache / Queue broker | Redis | 7+ | ARQ job queue + caching |
| Object storage | MinIO | latest | S3-compatible, self-host |
| Container | Docker + docker-compose | latest | Single-node deployment |

### AI & ML Stack

| Thành phần | Công nghệ | Ghi chú |
|------------|-----------|---------|
| LLM gateway | litellm | Multi-provider abstraction (OpenAI/Anthropic/Gemini/Azure/Bedrock) |
| Agent framework | LangGraph | Stateful graph, human-in-the-loop interrupt, checkpoint-postgres |
| OCR | PaddleOCR | Self-host Docker service, tiếng Việt tốt |
| LLM for parsing | Text-only LLM qua litellm | Parse OCR output → structured JSON |

### Auth & Security

| Thành phần | Công nghệ | Ghi chú |
|------------|-----------|---------|
| JWT | python-jose | Access + Refresh token |
| Password hash | passlib[bcrypt] | bcrypt rounds=12 |
| OAuth2 client | Authlib | Google SSO + Gmail/Calendar grant |

### Background Jobs

| Thành phần | Công nghệ | Ghi chú |
|------------|-----------|---------|
| Job queue | ARQ | Async-native, Redis-backed |
| Scheduled tasks | ARQ cron | Gmail poll mỗi 5 phút (configurable) |

### External Services / Providers

| Service | Provider | Ghi chú |
|---------|----------|---------|
| Email (read/send) | Gmail API (OAuth2) | Scope: gmail.readonly, gmail.modify, gmail.send |
| Calendar | Google Calendar API | Create event, check free/busy (Phase 2) |
| Meeting | Google Meet | Auto-generated từ Calendar event |
| LLM | Multi-provider (khách tự chọn) | Config qua env: LITELLM_MODEL, API keys |

---

## 4. Kiến trúc tổng thể

### Sơ đồ kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                           │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────┐  │
│  │  Inbox   │ │  Candidate   │ │ Interview │ │   Employee   │  │
│  │  View    │ │    Pool      │ │  Calendar │ │  Management  │  │
│  └──────────┘ └──────────────┘ └───────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ REST API (JSON)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              API Layer (routers, middleware, auth)        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Application Layer (use cases, services)        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Domain Layer (entities, value objects, events)  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Infrastructure (repos, adapters, clients)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐
│  PostgreSQL  │ │   Redis   │ │   MinIO   │ │  PaddleOCR   │
│  + pgvector  │ │           │ │           │ │  (Docker)    │
└──────────────┘ └───────────┘ └───────────┘ └──────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│              External Services                                │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Gmail API│ │Google Calendar│ │Google Meet│ │ LLM Provider│ │
│  └──────────┘ └──────────────┘ └──────────┘ └────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Thành phần chính

| Thành phần | Vai trò |
|------------|---------|
| Frontend (Next.js) | Dashboard cho HR: inbox, candidate pool, interview, employee |
| API Layer | REST endpoints, JWT auth, request validation, rate limiting |
| Application Layer | Use case orchestration, business rules, AI agent invocation |
| Domain Layer | Core entities, value objects, domain events (framework-agnostic) |
| Infrastructure | Database repos, external service adapters, file storage |
| AI Agent (LangGraph) | Stateful workflows: classify intent, parse CV, draft email |
| Background Worker (ARQ) | Gmail poll, scheduled reminders, async CV processing |

### Architecture Pattern

**Modular Monolith + Light Clean Architecture**

- 1 codebase, 1 deploy unit (Docker Compose)
- Chia thành module packages với ranh giới rõ ràng
- Domain layer không phụ thuộc framework (FastAPI, SQLAlchemy)
- Cross-module communication qua application service hoặc domain event
- **Không import ngang** giữa modules — chỉ qua shared kernel hoặc event bus

---

## 5. Domain Map

### Domains

| Domain | Mô tả | Core Entities |
|--------|--------|---------------|
| inbox | Email workspace, intent classification | EmailMessage, EmailThread, Intent, Label |
| recruitment | CV pipeline, candidate lifecycle | Candidate, CvDocument, ParsedCv, Evaluation |
| interview | Scheduling, calendar integration | Interview, TimeSlot, Interviewer, MeetingLink |
| employee | HR management, document vault | Employee, Department, Role, PersonalDocument |
| ai_agent | LangGraph workflows, prompt management | AgentWorkflow, AgentAction, PromptTemplate |
| identity | Authentication, session | User, Session, OAuthGrant |

### Dependency Map

```
identity ← (mọi module đều phụ thuộc auth)
    │
    ▼
inbox ──────────► recruitment ──────────► interview
    │                   │
    │                   ▼
    │              employee (candidate → employee promotion)
    │                   ▲
    └───────────────────┘ (inbox parse hồ sơ → employee vault)

ai_agent ← (được gọi bởi inbox, recruitment, interview, employee)
```

### Suggested Implementation Order

1. **identity** — auth cơ bản, HR login
2. **employee** — employee CRUD, Excel import (foundation data)
3. **inbox** — Gmail OAuth2, email fetch, intent classifier
4. **recruitment** — CV pipeline, candidate pool, 6 actions
5. **interview** — scheduling, calendar, meet link
6. **ai_agent** — LangGraph workflows (chạy song song với 3-4-5, refine dần)

---

## 6. Conventions & Rules

### Code Style

| Rule | Giá trị |
|------|---------|
| Naming (Python) | snake_case cho functions/variables, PascalCase cho classes |
| Naming (TypeScript) | camelCase cho functions/variables, PascalCase cho components/types |
| Max function length | 30 lines (khuyến nghị), 50 lines (hard limit) |
| Import style (Python) | Absolute imports, grouped: stdlib → third-party → local |
| Import style (TS) | Path aliases (@/modules/...), auto-sorted |
| Error handling | Custom exception hierarchy, never bare `except:` |
| Docstrings | Google style cho public functions |
| Type hints | Bắt buộc cho mọi function signature (Python + TypeScript strict) |

### Architecture Rules

| Rule | Mô tả |
|------|--------|
| Module boundary | Modules KHÔNG import lẫn nhau trực tiếp |
| Cross-module call | Qua application service interface hoặc domain event |
| Domain purity | Domain layer không import FastAPI, SQLAlchemy, Redis |
| Adapter pattern | External services (Gmail, Calendar, LLM, OCR) đều qua port/adapter |
| Config | Tất cả config qua environment variables (.env), validate bằng Pydantic Settings |
| Secrets | Không hardcode. Dùng .env file (self-host) hoặc Docker secrets |

### Security Baseline

| Rule | Mô tả |
|------|--------|
| Auth | JWT (access 15min + refresh 7d), bcrypt password |
| HTTPS | TLS 1.3 bắt buộc (reverse proxy: Caddy hoặc Traefik) |
| CORS | Whitelist frontend origin only |
| Rate limiting | API: 100 req/min/user. LLM endpoints: 20 req/min |
| Input validation | Pydantic model cho mọi request body |
| SQL injection | SQLAlchemy parameterized queries only |
| File upload | Validate MIME type + file size (max 10MB/file) |
| PII redaction | Mask CCCD/CMND, MST, số tài khoản, lương trước khi gửi LLM |
| Audit log | Log mọi LLM call + mọi action thay đổi state (create/update/delete) |

### Testing Strategy

| Scope | Tool | Coverage Target |
|-------|------|-----------------|
| Unit test (domain + service) | pytest + pytest-asyncio | 70% |
| Integration test (API + DB) | pytest + httpx + testcontainers | Happy paths + edge cases |
| E2E test | Playwright (frontend) | Critical user journeys |
| LLM mock | pytest-recording / VCR cassette | Mọi LLM call phải mock trong test |
| OCR mock | Fixture trả pre-recorded output | Không gọi PaddleOCR thật trong CI |
| Linting | ruff (Python), eslint + prettier (TS) | Zero warnings in CI |
| Type check | mypy (Python), tsc --noEmit (TS) | Strict mode |

---

## 7. Project Structure

```text
vroom-hr/
├── docker-compose.yml          # Orchestrate all services
├── .env.example                # Template environment variables
├── backend/
│   ├── pyproject.toml          # Python project config (uv/poetry)
│   ├── alembic/                # Database migrations
│   ├── src/
│   │   ├── main.py             # FastAPI app entrypoint
│   │   ├── config.py           # Pydantic Settings
│   │   ├── modules/
│   │   │   ├── identity/
│   │   │   │   ├── domain/     # User, Session entities
│   │   │   │   ├── application/# Auth service, OAuth flow
│   │   │   │   ├── infrastructure/ # User repo, JWT utils
│   │   │   │   └── api/        # Auth routers
│   │   │   ├── inbox/
│   │   │   │   ├── domain/     # EmailMessage, Intent, Label
│   │   │   │   ├── application/# ClassifyIntent, FetchEmails
│   │   │   │   ├── infrastructure/ # Gmail adapter, email repo
│   │   │   │   └── api/        # Inbox routers
│   │   │   ├── recruitment/
│   │   │   │   ├── domain/     # Candidate, CvDocument, ParsedCv
│   │   │   │   ├── application/# ParseCv, EvaluateCandidate
│   │   │   │   ├── infrastructure/ # Candidate repo, OCR adapter
│   │   │   │   └── api/        # Recruitment routers
│   │   │   ├── interview/
│   │   │   │   ├── domain/     # Interview, TimeSlot, Interviewer
│   │   │   │   ├── application/# ScheduleInterview
│   │   │   │   ├── infrastructure/ # Calendar adapter, Meet adapter
│   │   │   │   └── api/        # Interview routers
│   │   │   ├── employee/
│   │   │   │   ├── domain/     # Employee, Department, PersonalDoc
│   │   │   │   ├── application/# ImportExcel, PromoteCandidate
│   │   │   │   ├── infrastructure/ # Employee repo, Excel parser
│   │   │   │   └── api/        # Employee routers
│   │   │   └── ai_agent/
│   │   │       ├── workflows/  # LangGraph graph definitions
│   │   │       ├── tools/      # Tool functions for agent
│   │   │       ├── prompts/    # Prompt templates (Jinja2)
│   │   │       └── checkpoints/# LangGraph checkpoint config
│   │   ├── integrations/
│   │   │   ├── gmail/          # Gmail OAuth2 + API client
│   │   │   ├── calendar/       # Google Calendar client
│   │   │   ├── meeting/        # Google Meet (via Calendar)
│   │   │   ├── ocr/            # PaddleOCR client (HTTP)
│   │   │   └── llm/            # litellm wrapper + PII redactor
│   │   └── shared/
│   │       ├── domain/         # Value objects: EmailAddress, DateRange
│   │       ├── infrastructure/ # DB session, Redis, MinIO client
│   │       ├── events/         # Domain event bus (in-process)
│   │       └── api/            # Middleware, error handlers, deps
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/           # VCR cassettes, sample CVs, mock data
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # Shared UI components (shadcn/ui)
│   │   ├── lib/                # API client, utils, hooks
│   │   └── types/              # TypeScript type definitions
│   └── tests/
│       └── e2e/                # Playwright tests
├── services/
│   └── paddleocr/
│       └── Dockerfile          # PaddleOCR HTTP service
└── docs/                       # Harness docs (from harness-experimental)
```

---

## 8. Yêu cầu phi chức năng

| Yêu cầu | Mô tả | Target |
|----------|--------|--------|
| Performance (API) | Response time p95 | < 2s (trừ LLM endpoints) |
| Performance (CV parse) | End-to-end: OCR + LLM parse | < 60s per CV |
| Performance (Email fetch) | Batch poll Gmail | 100 emails / 5 phút |
| Availability | Uptime target | 99% (best-effort, single-node) |
| Scalability | Concurrent users | 1-5 HR users (SME) |
| Scalability | Data volume | < 500 CV/tháng, < 200 employees |
| Security | Transport | TLS 1.3 (Caddy/Traefik reverse proxy) |
| Security | Data at rest | Postgres: disk encryption. MinIO: server-side encryption |
| Security | Secrets | .env file, không commit vào git |
| Security | PII | Redact trước khi gửi LLM. Audit log mọi LLM call |
| Compliance | Vietnam PDPL (NĐ 13/2023) | PII store tại VN (on-prem), consent tracking |
| Compliance | Right-to-erasure | Hard-delete candidate data sau N tháng (configurable) |
| Compliance | Audit trail | Mọi action thay đổi state được log (who, what, when) |
| Logging | Application logs | Structured JSON, stdout → Docker log driver |
| Logging | Audit log | Separate table, retention 1 năm |
| Monitoring | Health check | /health endpoint cho Docker healthcheck |
| Backup | Database | pg_dump daily (cron), retain 7 days |
| Backup | Object storage | MinIO versioning hoặc rsync daily |

---

## 9. Assumptions & Constraints

### Giả định

1. Khách hàng đã có Google Workspace (Gmail + Calendar + Meet)
2. Server khách hàng có tối thiểu 4GB RAM, 2 vCPU, 50GB disk
3. Khách hàng có internet ổn định để gọi LLM API + Gmail API
4. HR có kiến thức cơ bản sử dụng web app
5. CV ứng viên chủ yếu dạng PDF, một số DOCX hoặc image (JPG/PNG)
6. Mỗi instance chỉ phục vụ 1 công ty (single-tenant)
7. Khách hàng tự cung cấp API key cho LLM provider đã chọn

### Ràng buộc kỹ thuật

1. Single-node deployment — không thiết kế cho horizontal scaling
2. PaddleOCR cần ~1GB RAM riêng — tổng system cần ≥ 4GB
3. Gmail API rate limit: 250 quota units/user/second — batch 100 email/lần
4. LLM latency phụ thuộc provider (2-30s) — UI phải có loading state
5. Google Calendar API không hỗ trợ real-time push cho free tier — dùng polling
6. MinIO không có CDN — file serve qua pre-signed URL, latency local

### Ask First — Agent KHÔNG được tự ý quyết định

1. Đổi LLM provider strategy (multi-provider) sang lock-in 1 provider
2. Đổi từ self-host single-tenant sang multi-tenant
3. Đổi architecture pattern (Modular Monolith → microservices)
4. Mở rộng MVP scope sang module khác trước khi recruitment hoàn thiện
5. Bỏ hoặc giảm PII redaction trước LLM call
6. Đổi tech stack chính (Python/FastAPI, Next.js, Postgres, Redis, ARQ, LangGraph)
7. Thêm external service mới (payment, SMS, third-party HR system)
8. Thay đổi OCR provider (PaddleOCR → Tesseract hoặc cloud OCR)
9. Bỏ audit log hoặc giảm retention
10. Thay đổi authentication flow (bỏ JWT, đổi sang session-based)

---

## 10. Candidate Epics & Roadmap

### MVP-1 (Phase 1) — Inbox + Recruitment + Interview + Employee

| Epic | Mô tả | Priority | Risk |
|------|--------|----------|------|
| E01: Identity & Auth | HR login, JWT, Google OAuth2 grant | P0 | Low |
| E02: Employee Management | CRUD, Excel import, department/role | P0 | Low |
| E03: Gmail Integration | OAuth2 connect, email fetch, label management | P0 | Medium (OAuth2 flow) |
| E04: Inbox & Classifier | Email list view, AI intent classifier (CV/Partner/Event/Internal/Other) | P0 | Medium (AI accuracy) |
| E05: CV Pipeline | PaddleOCR → LLM parse → Candidate record | P0 | High (OCR quality) |
| E06: Candidate Pool | List/detail view, search, filter, 6 actions | P0 | Low |
| E07: Interview Scheduling | Time slot picker, add interviewer, Calendar event + Meet link | P1 | Medium (Calendar API) |
| E08: Email Pipelines | Auto-send templates (congrats, reject, interview invite, onboarding) | P1 | Low |
| E09: Onboarding Email | Gửi nội quy + yêu cầu hồ sơ, parse reply attachments → employee vault | P1 | Medium (parse hồ sơ) |
| E10: Dashboard & Analytics | KPIs: CV count, pass rate, avg processing time, pipeline funnel | P2 | Low |

### Phase 2 — Leave & Attendance + Multi-HR + Email Assist

| Epic | Mô tả | Priority | Risk |
|------|--------|----------|------|
| E11: Leave Management | Email-driven leave request, balance tracking, manager approval | P1 | Medium |
| E12: Attendance | Timesheet import, working hours calculation | P2 | Low |
| E13: Multi-HR | Multiple HR accounts, task assignment, shared inbox | P1 | Medium |
| E14: Email Draft Assist | AI draft reply cho mọi intent (không chỉ CV) | P2 | Medium |
| E15: Candidate Portal | Magic-link portal cho candidate tự upload hồ sơ | P2 | Low |
| E16: Microsoft 365 | Outlook + Teams + Calendar adapter | P2 | High |

### Phase 3 — Payroll + Mobile + Advanced AI

| Epic | Mô tả | Priority | Risk |
|------|--------|----------|------|
| E17: Payroll Integration | Tính lương cuối tháng, export cho kế toán | P2 | High |
| E18: Mobile App | React Native hoặc PWA cho Employee self-service | P3 | Medium |
| E19: RAG Knowledge Base | HR policy docs → vector search → AI answer | P3 | Medium |
| E20: Advanced Analytics | Hiring funnel, time-to-hire, source effectiveness | P3 | Low |

---

## 11. Open Questions

| # | Câu hỏi | Impact | Khi nào cần trả lời |
|---|---------|--------|---------------------|
| Q1 | Gmail label "recruitment" do HR tự gắn hay hệ thống auto-detect dựa vào subject/sender? | Inbox module design | Trước khi implement E03 |
| Q2 | Khi OCR/LLM parse CV sai (confidence thấp), flow xử lý thế nào? Chỉ flag cho HR hay auto-retry? | Recruitment UX | Trước khi implement E05 |
| Q3 | Email template cho mỗi action (reject, congrats, interview invite) — HR tự soạn hay có sẵn default? | Email pipeline | Trước khi implement E08 |
| Q4 | Candidate data retention: sau bao lâu kể từ reject thì hard-delete? (30/60/90/180 ngày?) | Compliance | Trước khi implement E06 |
| Q5 | Khi promote candidate → employee, những field nào bắt buộc phải có trước khi chuyển? | Employee domain | Trước khi implement E09 |
| Q6 | Interview feedback/scorecard từ tech lead — có cần lưu trong hệ thống hay chỉ qua email? | Interview module scope | Trước khi implement E07 |
| Q7 | Multi-language support (UI tiếng Việt + tiếng Anh) có cần cho MVP? | Frontend i18n | Trước khi implement frontend |
| Q8 | Backup strategy: khách tự backup hay hệ thống có built-in backup script? | DevOps / installer | Trước khi viết docker-compose |
| Q9 | Leave & Attendance (Phase 2): employee gửi đơn nghỉ qua email hay cần portal riêng? | Phase 2 architecture | Trước Phase 2 |
| Q10 | Cost monitoring cho LLM usage — cần dashboard riêng hay chỉ log? | AI Agent module | Trước khi implement E05 |

---

## Appendix: Key Workflows

### A. CV Processing Pipeline

```
Gmail Inbox (label: recruitment)
    │ [ARQ cron: mỗi 5 phút]
    ▼
Fetch new emails with PDF/DOCX/image attachments
    │
    ▼
Save attachment → MinIO (storage/cv/{message_id}.{ext})
    │
    ▼
PaddleOCR service → extract text (tiếng Việt + dấu)
    │
    ▼
LLM parse (litellm) → structured JSON:
  { name, email, phone, skills[], experience[], education[], summary }
    │
    ▼
Validate required fields (name + email minimum)
    │
    ▼
Create Candidate record in Postgres
    │
    ▼
Mark Gmail message with label "processed"
    │
    ▼
Candidate appears in Candidate Pool (dashboard)
```

### B. Interview Scheduling Flow

```
HR selects candidate → Action: "Interview"
    │
    ▼
HR picks: date/time, duration, interviewer(s) from employee list
    │
    ▼
System creates Google Calendar event:
  - Title: "Interview - {candidate_name} - {position}"
  - Attendees: interviewer(s) email
  - Auto-generate Google Meet link
    │
    ▼
System sends email to candidate:
  - Template: interview_invite
  - Contains: date, time, Meet link, interviewer name(s)
    │
    ▼
System sends email to interviewer(s):
  - Template: interviewer_notify
  - Contains: candidate info, CV link, date, time, Meet link
    │
    ▼
Interview record saved in DB (status: scheduled)
```

### C. Candidate → Employee Promotion Flow

```
HR marks candidate as "Passed Interview"
    │
    ▼
System sends onboarding email to candidate:
  - Template: onboarding_welcome
  - Attachments: nội quy công ty, thông báo nhận việc
  - Request: gửi lại CCCD, MST, bằng cấp, ảnh 3x4
    │
    ▼
Candidate replies with attachments
    │
    ▼
Gmail poll picks up reply (same thread)
    │
    ▼
PaddleOCR + LLM parse each document:
  - CCCD: số, họ tên, ngày sinh, nơi cấp, ngày cấp
  - MST: mã số thuế (10-13 digits)
  - Bằng cấp: trường, chuyên ngành, năm tốt nghiệp
    │
    ▼
Create Employee record (promote from Candidate)
Store documents in Employee vault (MinIO + metadata in Postgres)
    │
    ▼
HR reviews & confirms employee profile complete
```

---

*End of spec.*
