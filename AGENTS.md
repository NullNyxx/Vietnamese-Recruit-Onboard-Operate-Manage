# Agent Instructions

## Project: Vroom HR

Nền tảng quản lý nhân sự cho doanh nghiệp Việt Nam (Recruit-Onboard-Operate-Manage).

### Trước khi làm việc

1. Đọc `docs/product/overview.md` — tổng quan project, modules, tech stack
2. Đọc `docs/product/tech-stack.md` — commands, conventions, patterns
3. Đọc `docs/FEATURE_INTAKE.md` — phân loại task trước khi code
4. Tuân thủ module architecture: `api/ → application/ → domain/ → infrastructure/`

### Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLModel, PostgreSQL 15, Redis 7
- **Frontend:** Next.js 14 (App Router), TypeScript, pnpm, Tailwind, shadcn/ui
- **Auth:** Cookie-based JWT (KHÔNG dùng Bearer headers)
- **Storage:** MinIO (documents, CVs, payslips)
- **Linting:** Ruff (line-length=100), MyPy strict
- **Testing:** pytest + Hypothesis (backend), Vitest + fast-check (frontend)

---

## ⛔ QUY TẮC BẮT BUỘC — ĐỌC TRƯỚC KHI LÀM BẤT CỨ GÌ

### 1. KHÔNG tạo docs tùy tiện

Thư mục `docs/` có cấu trúc cố định. KHÔNG tạo thư mục hoặc file ngoài cấu trúc sau:

```
docs/
├── product/          ← Product docs (overview, guides, feature specs)
├── stories/          ← Story packets (work items theo template)
├── decisions/        ← Architecture Decision Records (ADRs)
├── templates/        ← Templates (KHÔNG SỬA)
├── HARNESS.md        ← Operating model (KHÔNG SỬA)
├── FEATURE_INTAKE.md ← Intake rules (KHÔNG SỬA)
├── ARCHITECTURE.md   ← Architecture rules (KHÔNG SỬA)
├── TEST_MATRIX.md    ← Validation matrix
└── HARNESS_BACKLOG.md← Backlog
```

**Ví dụ SAI:**

- ❌ `docs/cham-cong-nghi-phep/` — thư mục tùy tiện
- ❌ `docs/my-feature-notes.md` — notes không theo format
- ❌ `docs/tien-do-xxx.md` — tiến độ viết bằng markdown

**Ví dụ ĐÚNG:**

- ✅ `docs/product/payroll-guide.md` — hướng dẫn sử dụng
- ✅ `docs/stories/US-042-attendance-checkin.md` — story packet
- ✅ `docs/decisions/0006-payroll-tax-formula.md` — ADR

### 2. KHÔNG viết tiến độ/task list vào markdown

Dùng Harness DB thay vì tạo file checklist:

```bash
# Thêm story
scripts/harness story add --id "US-042" --title "Attendance check-in" --lane normal

# Cập nhật status
scripts/harness story update --id "US-042" --status in_progress
scripts/harness story update --id "US-042" --status implemented --unit 1
```

### 3. PHẢI tuân thủ module architecture

Mọi code mới trong backend PHẢI theo cấu trúc:

```
backend/src/modules/<module_name>/
├── api/
│   ├── router.py          # FastAPI endpoints
│   ├── schemas.py         # Pydantic request/response
│   └── error_handler.py   # Exception → HTTP mapping
├── application/
│   └── <name>_service.py  # Business logic
├── domain/
│   ├── entities.py        # SQLModel tables
│   ├── enums.py           # Enumerations
│   └── exceptions.py      # Domain exceptions
├── infrastructure/
│   ├── config.py          # Pydantic Settings
│   └── <name>_repository.py
└── container.py           # DI wiring (FastAPI Depends)
```

### 4. PHẢI phân loại task trước khi code

Đọc `docs/FEATURE_INTAKE.md` và xác định:

- **Tiny** (0-1 risk flags): patch trực tiếp
- **Normal** (2-3 flags): cần story file
- **High-risk** (4+ flags hoặc hard gate): cần story folder + human confirm

Hard gates (luôn high-risk): auth, authorization, data loss, audit/security, external provider.

### 5. Git Branch & Commit Convention

**Branch format:** `<type>/<short-description-in-english>`

```
feature/payroll-tax-calculator       ← tính năng mới
fix/overtime-hours-query             ← sửa bug
chore/update-ruff-config             ← config, CI, deps
refactor/extract-tax-service         ← refactor
docs/add-payroll-guide               ← chỉ docs
hotfix/login-cookie-expired          ← fix khẩn cấp
```

- ✅ Tiếng Anh, lowercase, dấu `-` ngăn cách
- ❌ KHÔNG dùng tên người (`nguyen`), tiếng Việt (`feat/Ting_luong`), underscore

**Commit format:** `<type>(<scope>): <description in English>`

```
feat(payroll): add tax calculation for dependents
fix(attendance): correct overtime hours query
docs(product): add payroll user guide
refactor(identity): extract token validation logic
test(payroll): add regression tests for tax formula
chore(infra): update docker compose for redis 7
```

Scopes: `identity`, `employee`, `gmail`, `recruitment`, `attendance`, `payroll`,
`self-service`, `frontend`, `ui`, `infra`, `migrations`

- ✅ Tiếng Anh, imperative mood ("add" not "added"), dưới 72 ký tự
- ❌ KHÔNG viết tiếng Việt, KHÔNG trộn type (`feat/ fix ...`)

### 6. GitHub Workflow

```bash
# 1. LUÔN pull main mới nhất trước khi bắt đầu
git checkout main
git pull origin main

# 2. Tạo branch từ main
git checkout -b feature/my-feature-name

# 3. Code & commit atomic (mỗi commit = 1 thay đổi logic)
git add <files>
git commit -m "feat(module): description"

# 4. Trước khi push, rebase lại main (tránh conflict)
git fetch origin main
git rebase origin/main

# 5. Push branch
git push -u origin feature/my-feature-name

# 6. Tạo Pull Request
gh pr create --title "feat(module): description" --body "What/Why/How"
# Hoặc tạo PR trên GitHub UI

# 7. Sau khi merge, cleanup
git checkout main
git pull origin main
git branch -d feature/my-feature-name
```

**PR Rules:**

- Title theo commit format: `feat(payroll): implement salary calculation`
- Description: mô tả what/why/how
- Cần ít nhất 1 approval + pass CI
- Merge strategy: **Squash merge**
- KHÔNG push trực tiếp vào `main`

---

## Workflow cho mỗi task

```
1. Classify    → docs/FEATURE_INTAKE.md
2. Record      → scripts/harness intake --type <type> --summary "<text>" --lane <lane>
3. Story       → scripts/harness story add (nếu normal/high-risk)
4. Implement   → Code theo architecture rules
5. Validate    → Run tests, lint, typecheck
6. Trace       → scripts/harness trace --summary "<text>" --outcome <outcome>
7. Friction    → scripts/harness backlog add (nếu gặp vấn đề)
```

---

## Harness CLI

```bash
scripts/harness query stats          # Tổng quan DB
scripts/harness query matrix         # Story validation status
scripts/harness intake --type "change_request" --summary "..." --lane "normal"
scripts/harness story add --id "US-XXX" --title "..." --lane "normal"
scripts/harness story update --id "US-XXX" --status "implemented"
scripts/harness trace --summary "..." --outcome "completed"
scripts/harness backlog add --title "..." --pain "..."
```

---

## Key Conventions

- Tất cả API routes bắt đầu bằng `/api/`
- Auth dùng httpOnly secure cookies (access_token, refresh_token)
- Soft delete cho employees (`is_active` flag)
- Mọi admin action phải có audit log
- OAuth tokens encrypted AES-256-GCM
- Vietnamese tax: personal deduction 11M VND/month, dependent 4.4M/person
- Insurance: employee 10.5% (BHXH 8% + BHYT 1.5% + BHTN 1%)
- Work days per month: 26 (for salary calculation)

<!-- HARNESS:BEGIN -->

## Harness

This repo uses Harness. Before work, read:

- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md`
- `scripts/harness query matrix`

<!-- HARNESS:END -->
