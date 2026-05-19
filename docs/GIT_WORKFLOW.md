# Git Workflow

Tài liệu mô tả quy trình làm việc với Git cho dự án Vroom HR.

## Branch Strategy

### Nhánh chính

| Branch | Mục đích |
|--------|----------|
| `main` | Nhánh production, luôn ở trạng thái stable |

### Nhánh làm việc

Tạo branch mới từ `main` cho mỗi đơn vị công việc. Đặt tên theo convention:

```text
<type>/<short-description>
```

**Các type phổ biến:**

| Type | Khi nào dùng |
|------|-------------|
| `feat/` | Tính năng mới |
| `fix/` | Sửa bug |
| `refactor/` | Tái cấu trúc code, không thay đổi behavior |
| `docs/` | Thay đổi documentation |
| `chore/` | Cập nhật dependencies, config, CI |
| `test/` | Thêm hoặc sửa tests |

**Ví dụ:**

```text
feat/oauth-token-refresh
fix/rate-limiter-race-condition
refactor/move-harness-to-subfolder
docs/add-git-workflow
chore/upgrade-fastapi
test/integration-auth-flow
```

## Workflow

### 1. Tạo branch

```bash
git checkout main
git pull origin main
git checkout -b feat/ten-feature
```

### 2. Commit

Commit thường xuyên với message rõ ràng theo [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Ví dụ:**

```bash
git add <files>
git commit -m "feat(identity): add token refresh endpoint"
git commit -m "fix(auth): handle expired state token gracefully"
git commit -m "docs: add git workflow documentation"
```

**Quy tắc commit:**

- Stage file cụ thể, tránh `git add .` trừ khi chắc chắn
- Mỗi commit là một đơn vị logic hoàn chỉnh
- Không commit file chứa secrets (.env, credentials, tokens)
- Không commit file generated (node_modules, __pycache__, .venv)

### 3. Push

```bash
git push -u origin feat/ten-feature
```

Flag `-u` set upstream tracking cho lần push đầu tiên. Các lần sau chỉ cần `git push`.

### 4. Tạo Pull Request

Dùng GitHub CLI:

```bash
gh pr create --title "feat(identity): add token refresh" --body "## Summary
Mô tả ngắn gọn thay đổi.

## Changes
- Thay đổi 1
- Thay đổi 2

## Testing
- Đã test gì" --base main
```

Hoặc tạo trực tiếp trên GitHub UI.

**Quy tắc PR:**

- Title ngắn gọn, dưới 70 ký tự
- Description có: summary, changes, testing notes
- Mỗi PR giải quyết một vấn đề cụ thể
- Không mix nhiều concerns không liên quan trong một PR

### 5. Review & Merge

- PR cần được review trước khi merge (nếu làm team)
- Merge vào `main` qua GitHub UI (Squash and merge hoặc Merge commit)
- Xóa branch sau khi merge

```bash
# Sau khi PR đã merge, cleanup local
git checkout main
git pull origin main
git branch -d feat/ten-feature
```

## Quy tắc an toàn

### KHÔNG được làm

- ❌ Push trực tiếp vào `main`
- ❌ Force push (`git push --force`) trừ khi có lý do rõ ràng và đã confirm
- ❌ `git reset --hard` trên shared branches
- ❌ Commit secrets, credentials, hoặc API keys
- ❌ Amend commit đã push lên remote

### NÊN làm

- ✅ Luôn tạo branch mới cho mỗi thay đổi
- ✅ Pull latest `main` trước khi tạo branch
- ✅ Commit message rõ ràng, có context
- ✅ Review diff trước khi commit (`git diff --staged`)
- ✅ Giữ PR nhỏ, dễ review

## Xử lý conflict

Khi branch bị outdated so với `main`:

```bash
git checkout feat/ten-feature
git fetch origin
git rebase origin/main
# Resolve conflicts nếu có
git push --force-with-lease
```

Dùng `--force-with-lease` thay vì `--force` để tránh overwrite work của người khác.

## Useful Commands

```bash
# Xem trạng thái
git status

# Xem lịch sử commit gọn
git log --oneline -10

# Xem diff chưa stage
git diff

# Xem diff đã stage
git diff --staged

# Tạo PR và mở trên browser
gh pr create --web

# Xem danh sách PR
gh pr list

# Checkout PR của người khác để review
gh pr checkout <pr-number>
```
