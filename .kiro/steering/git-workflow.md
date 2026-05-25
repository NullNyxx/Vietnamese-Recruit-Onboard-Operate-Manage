---
inclusion: always
---

# Git Workflow & Branch Naming

## Branch Naming Convention

Format: `<type>/<short-description-in-english>`

### Types

| Type        | Khi nào dùng                 | Ví dụ                          |
| ----------- | ---------------------------- | ------------------------------ |
| `feature/`  | Tính năng mới                | `feature/payroll-calculation`  |
| `fix/`      | Sửa bug                      | `fix/overtime-hours-query`     |
| `chore/`    | Config, CI, deps, cleanup    | `chore/update-ruff-config`     |
| `refactor/` | Refactor không đổi behavior  | `refactor/extract-tax-service` |
| `docs/`     | Chỉ thay đổi docs            | `docs/add-payroll-guide`       |
| `hotfix/`   | Fix khẩn cấp trên production | `hotfix/login-cookie-expired`  |

### Rules

- ✅ Viết bằng **tiếng Anh**, lowercase, dùng dấu `-` ngăn cách
- ✅ Mô tả ngắn gọn nhưng rõ ràng (2-4 từ)
- ❌ KHÔNG dùng tên người: `nguyen`, `hoang-branch`
- ❌ KHÔNG dùng tiếng Việt: `feat/Ting_luong`, `feat/them-mo-ta`
- ❌ KHÔNG dùng underscore hoặc viết hoa: `feat/Ting_luong`
- ❌ KHÔNG dùng branch quá chung: `feat/onboarding` (thiếu context)

### Ví dụ đúng

```
feature/attendance-check-in-out
feature/payroll-tax-calculator
feature/recruitment-cv-parsing
fix/alembic-migration-multiple-heads
fix/dark-mode-employee-detail
chore/setup-harness-v1
chore/add-codeowners
refactor/move-harness-to-subfolder
docs/add-product-overview
```

---

## Commit Message Convention

Format: `<type>(<scope>): <description in English>`

### Types

| Type       | Khi nào                              |
| ---------- | ------------------------------------ |
| `feat`     | Thêm tính năng mới                   |
| `fix`      | Sửa bug                              |
| `docs`     | Chỉ thay đổi documentation           |
| `refactor` | Refactor code (không đổi behavior)   |
| `chore`    | Build, CI, deps, config              |
| `test`     | Thêm/sửa tests                       |
| `perf`     | Cải thiện performance                |
| `style`    | Format, whitespace (không đổi logic) |

### Scope (module name)

`identity`, `employee`, `gmail`, `recruitment`, `attendance`, `payroll`,
`self-service`, `frontend`, `ui`, `infra`, `migrations`

### Rules

- ✅ Viết bằng **tiếng Anh**
- ✅ Lowercase cho description (không viết hoa chữ đầu)
- ✅ Ngắn gọn, dưới 72 ký tự
- ✅ Dùng imperative mood: "add", "fix", "update" (không phải "added", "fixing")
- ❌ KHÔNG viết tiếng Việt: `feat/thêm file hướng dẫn`
- ❌ KHÔNG trộn type: `feat/ fix chwucs năng`
- ❌ KHÔNG thiếu scope khi thay đổi module cụ thể

### Ví dụ đúng

```
feat(payroll): add progressive tax calculation
feat(attendance): implement check-in/out endpoints
feat(frontend): add leave management UI pages
fix(identity): resolve token refresh race condition
fix(ui): fix dark mode colors on employee detail
docs(product): add payroll user guide
chore(infra): update docker compose for redis 7
refactor(recruitment): extract cv parsing to service
test(payroll): add regression tests for tax formula
```

### Ví dụ SAI (đã xảy ra trong repo)

```
❌ feat/them mô tả                    → ✅ feat(recruitment): add candidate description field
❌ feat/ fix chwucs năng tính lương    → ✅ fix(payroll): correct salary calculation logic
❌ chingr lại giao diện               → ✅ fix(ui): update payroll page layout
❌ Feat/ting luong (#18)              → ✅ feat(payroll): implement salary calculation module
❌ feat/hoàn thiện tính năng tính lương → ✅ feat(payroll): complete payroll calculation feature
```

---

## GitHub Workflow

### 1. LUÔN pull main mới nhất trước khi bắt đầu

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature-name
```

⚠️ **KHÔNG BAO GIỜ** tạo branch từ branch cũ hoặc từ main chưa pull.

### 2. Commit thường xuyên (atomic commits)

Mỗi commit nên là 1 thay đổi logic hoàn chỉnh:

- ❌ 1 commit khổng lồ chứa toàn bộ feature
- ✅ Nhiều commits nhỏ, mỗi cái có ý nghĩa riêng

```bash
git add backend/src/modules/payroll/domain/entities.py
git commit -m "feat(payroll): add payroll domain entities"

git add backend/src/modules/payroll/application/
git commit -m "feat(payroll): implement payroll calculation service"
```

### 3. Trước khi push — rebase main

```bash
git fetch origin main
git rebase origin/main
# Nếu conflict: resolve → git add → git rebase --continue
```

### 4. Push và tạo Pull Request

```bash
# Push branch
git push -u origin feature/my-feature-name

# Tạo PR bằng GitHub CLI
gh pr create --title "feat(payroll): implement salary calculation" --body "## What
- Add payroll calculation service
## Why
- HR needs monthly salary processing"
```

### 5. Pull Request rules

- **Title:** Dùng format commit message: `feat(payroll): implement salary calculation`
- **Description:** Mô tả what/why/how + testing
- **Review:** Cần ít nhất 1 approval trước khi merge
- **CI:** Phải pass lint + tests (khi có)
- **Up-to-date:** Branch phải rebase main trước khi merge
- **Merge strategy:** Squash merge (giữ main history sạch)

### 6. Sau khi merge

```bash
git checkout main
git pull origin main
git branch -d feature/my-feature-name
```

---

## Quy trình cho AI Agent

Khi AI Agent tạo branch hoặc commit:

1. **Branch:** Luôn tạo từ `main`, đặt tên theo convention trên
2. **Commits:** Dùng conventional commits format
3. **PR:** Push lên branch mới, KHÔNG push trực tiếp vào main
4. **Không force push** trừ khi được yêu cầu rõ ràng
