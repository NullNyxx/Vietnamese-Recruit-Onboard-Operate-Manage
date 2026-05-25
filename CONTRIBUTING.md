# Contributing Guide

## Quy trình làm việc

### 1. Nhận task

- Đọc `docs/FEATURE_INTAKE.md` để phân loại (tiny/normal/high-risk)
- Nếu dùng AI Agent: agent sẽ tự classify và record intake

### 2. Tạo branch

Format: `<type>/<short-description-in-english>`

| Type        | Khi nào          | Ví dụ                            |
| ----------- | ---------------- | -------------------------------- |
| `feature/`  | Tính năng mới    | `feature/payroll-tax-calculator` |
| `fix/`      | Sửa bug          | `fix/overtime-hours-query`       |
| `chore/`    | Config, CI, deps | `chore/update-ruff-config`       |
| `refactor/` | Refactor         | `refactor/extract-tax-service`   |
| `docs/`     | Chỉ docs         | `docs/add-payroll-guide`         |
| `hotfix/`   | Fix khẩn cấp     | `hotfix/login-cookie-expired`    |

**Rules:**

- ✅ Tiếng Anh, lowercase, dấu `-` ngăn cách
- ❌ KHÔNG dùng tên người: `nguyen`, `hoang`
- ❌ KHÔNG dùng tiếng Việt: `feat/Ting_luong`
- ❌ KHÔNG dùng underscore: `feat/ting_luong`

```bash
# ⚠️ LUÔN pull main mới nhất trước khi tạo branch
git checkout main
git pull origin main
git checkout -b feature/my-feature-name
```

### 3. Commit

Format: `<type>(<scope>): <description>`

**Types:** `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `perf`, `style`

**Scopes:** `identity`, `employee`, `gmail`, `recruitment`, `attendance`, `payroll`, `self-service`, `frontend`, `ui`, `infra`, `migrations`

```bash
# Ví dụ đúng
git commit -m "feat(payroll): add progressive tax calculation"
git commit -m "fix(attendance): correct overtime hours query"
git commit -m "docs(product): add payroll user guide"

# Ví dụ SAI
git commit -m "feat/thêm tính năng"        # ❌ tiếng Việt
git commit -m "fix bug"                     # ❌ thiếu scope, không rõ ràng
git commit -m "update"                      # ❌ không mô tả gì
```

**Rules:**

- Tiếng Anh, imperative mood ("add" not "added")
- Dưới 72 ký tự
- Mỗi commit = 1 thay đổi logic hoàn chỉnh (atomic)

### 4. Trước khi push — rebase main

Luôn đảm bảo branch up-to-date với main:

```bash
git fetch origin main
git rebase origin/main
# Nếu có conflict: resolve → git rebase --continue
```

### 5. Push & Tạo Pull Request

```bash
# Push branch
git push -u origin feature/my-feature-name

# Tạo PR bằng GitHub CLI
gh pr create --title "feat(payroll): implement salary calculation" --body "## What
- Add payroll calculation service
## Why
- HR needs monthly salary processing"

# Hoặc tạo PR trên GitHub UI
```

**PR Title:** Dùng format commit message

- ✅ `feat(payroll): implement salary calculation module`
- ❌ `Feat/ting luong`

**PR Description template:**

```markdown
## What

- Mô tả thay đổi chính

## Why

- Lý do cần thay đổi

## Testing

- Đã test gì
```

**Merge requirements:**

- Ít nhất 1 approval
- CI pass (lint + tests khi có)
- No merge conflicts
- Branch up-to-date với main (đã rebase)

**Merge strategy:** Squash merge (giữ main history sạch)

### 6. Sau khi merge

```bash
git checkout main
git pull origin main
git branch -d feature/my-feature-name  # xóa branch local
```

---

## Cấu trúc code

### Backend module (bắt buộc)

```
backend/src/modules/<module>/
├── api/           # Routers, schemas, error handlers
├── application/   # Services (business logic)
├── domain/        # Entities, enums, exceptions
├── infrastructure/# Repositories, configs, clients
└── container.py   # Dependency injection
```

### Docs (bắt buộc)

```
docs/
├── product/       # Product docs, guides, specs
├── stories/       # Story packets
├── decisions/     # Architecture Decision Records
└── templates/     # Templates (KHÔNG SỬA)
```

❌ KHÔNG tạo thư mục/file tùy tiện trong `docs/`

---

## Cho AI Agent users

Nếu bạn dùng AI Agent (Codex CLI, Cursor, Claude Code, Kiro...):

1. Agent sẽ đọc `AGENTS.md` tự động
2. Agent PHẢI tuân thủ branch naming + commit convention
3. Agent KHÔNG được tạo docs ngoài cấu trúc cho phép
4. Agent PHẢI push lên branch mới, KHÔNG push vào main
5. Nếu dùng Harness: record intake → story → trace

---

## Quick Reference

```bash
# Backend
cd backend
uvicorn src.main:app --reload --port 8000
ruff check src/ && ruff format src/
pytest tests/

# Frontend
cd frontend
pnpm dev
pnpm lint
pnpm test

# Docker
docker compose up -d postgres redis
```
