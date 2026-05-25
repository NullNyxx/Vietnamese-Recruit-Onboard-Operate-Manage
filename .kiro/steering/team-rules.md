---
inclusion: always
---

# Team Rules — Quy Tắc Cho AI Agent

## ⛔ KHÔNG được làm

1. **KHÔNG tạo file docs tùy tiện** trong `docs/`. Thư mục `docs/` có cấu trúc cố định:
   - `docs/product/` — Product contract (overview, tech-stack)
   - `docs/stories/` — Story packets (theo template)
   - `docs/decisions/` — Architecture Decision Records
   - `docs/templates/` — Templates (không sửa)
   - `docs/HARNESS.md`, `docs/FEATURE_INTAKE.md`, `docs/ARCHITECTURE.md` — Harness policy docs

2. **KHÔNG tạo thư mục mới** trong `docs/` mà không có story hoặc decision đi kèm.
   - ❌ `docs/cham-cong-nghi-phep/` — SAI (không theo format)
   - ❌ `docs/my-feature-notes/` — SAI
   - ✅ `docs/stories/US-042-attendance-checkin.md` — ĐÚNG
   - ✅ `docs/decisions/0006-payroll-tax-formula.md` — ĐÚNG

3. **KHÔNG viết tiến độ/task list** vào markdown files. Dùng harness DB:
   - ❌ Tạo file `tien-do-xxx.md` với checklist
   - ✅ `scripts/harness story add --id "US-042" --title "..." --lane normal`
   - ✅ `scripts/harness story update --id "US-042" --status in_progress`

4. **KHÔNG viết hướng dẫn sử dụng** vào `docs/`. Đó là product docs:
   - ❌ `docs/cham-cong-nghi-phep/huong-dan-payroll.md`
   - ✅ `docs/product/payroll-guide.md` (nếu cần user guide)

5. **KHÔNG bỏ qua harness workflow**. Mọi task phải:
   - Classify (intake)
   - Record (story nếu normal/high-risk)
   - Trace (khi xong)

## ✅ PHẢI làm

1. **Trước khi code**, phân loại task:
   - Tiny: patch trực tiếp, không cần story
   - Normal: tạo story file theo `docs/templates/story.md`
   - High-risk: tạo story folder theo `docs/templates/high-risk-story/`

2. **Khi tạo docs mới**, đặt đúng chỗ:
   - Feature spec/guide → `docs/product/<feature-name>.md`
   - Story → `docs/stories/<story-id>.md`
   - Decision → `docs/decisions/<NNNN>-<slug>.md`
   - Progress tracking → Harness DB (không phải markdown)

3. **Khi hoàn thành task**, ghi trace:

   ```bash
   wsl -- /bin/bash -c "cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage && /bin/bash scripts/harness trace --summary '<mô tả>' --outcome completed"
   ```

4. **Tuân thủ module architecture** khi tạo code mới:

   ```
   backend/src/modules/<module>/
   ├── api/        (routers, schemas, error_handler)
   ├── application/(services)
   ├── domain/     (entities, enums, exceptions)
   ├── infrastructure/ (repos, configs, clients)
   └── container.py
   ```

5. **Commit message** phải rõ ràng:
   - `feat(payroll): add tax calculation for dependents`
   - `fix(attendance): correct overtime hours query`
   - `docs(product): add payroll user guide`

## 📁 Cấu trúc docs/ hợp lệ

```
docs/
├── product/          ← Product docs (overview, guides, specs)
├── stories/          ← Story packets (work items)
├── decisions/        ← ADRs (architecture decisions)
├── templates/        ← Templates (KHÔNG SỬA)
├── HARNESS.md        ← Harness operating model
├── FEATURE_INTAKE.md ← Intake classification
├── ARCHITECTURE.md   ← Architecture rules
├── TEST_MATRIX.md    ← Validation matrix
└── HARNESS_BACKLOG.md← Backlog
```

Bất kỳ thư mục/file nào ngoài cấu trúc trên đều là **trash** và cần được di chuyển hoặc xóa.

## 🔧 Xử lý docs cũ không đúng format

Thư mục `docs/cham-cong-nghi-phep/` là ví dụ về docs sai format. Nội dung hữu ích
trong đó cần được:

- Roadmap/tiến độ → Import vào harness DB bằng `scripts/harness story add`
- Hướng dẫn sử dụng → Di chuyển sang `docs/product/`
- Feature specs → Di chuyển sang `docs/product/`

## 🌐 WSL cho Harness

Trên Windows, mọi harness command chạy qua WSL:

```bash
wsl -- /bin/bash -c "cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage && /bin/bash scripts/harness <command>"
```
