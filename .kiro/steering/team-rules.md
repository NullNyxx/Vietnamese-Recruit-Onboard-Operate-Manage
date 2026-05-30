---
inclusion: always
---

# Team Rules — Quy Tắc Cho AI Agent

## ⛔ KHÔNG được làm

1. **KHÔNG tạo file docs tùy tiện** trong `docs/`. Thư mục `docs/` có cấu trúc cố định:
   - `docs/product/` — Product contract (overview, tech-stack, guides, module specs)
   - `docs/technical/` — Cross-cutting technical references (migrations, seed data, error codes)
   - `docs/decisions/` — Architecture Decision Records (ADRs)
   - `docs/templates/` — Templates (không sửa)
   - `docs/ARCHITECTURE.md` — Architecture rules

2. **KHÔNG tạo thư mục mới** trong `docs/` mà không có lý do rõ ràng.
   - ❌ `docs/cham-cong-nghi-phep/` — SAI (không theo format)
   - ❌ `docs/my-feature-notes/` — SAI
   - ✅ `docs/product/attendance-checkin.md` — ĐÚNG
   - ✅ `docs/decisions/0006-payroll-tax-formula.md` — ĐÚNG

3. **KHÔNG viết tiến độ/task list** lan man vào markdown files trong `docs/`.
   - ❌ Tạo file `tien-do-xxx.md` với checklist
   - ✅ Theo dõi công việc bằng issue tracker / PR

4. **KHÔNG viết hướng dẫn sử dụng** lung tung. Đó là product docs:
   - ❌ `docs/cham-cong-nghi-phep/huong-dan-payroll.md`
   - ✅ `docs/product/payroll-guide.md` (nếu cần user guide)

## ✅ PHẢI làm

1. **Khi tạo docs mới**, đặt đúng chỗ:
   - Feature spec/guide → `docs/product/<feature-name>.md`
   - Technical reference → `docs/technical/<topic>.md`
   - Decision → `docs/decisions/<NNNN>-<slug>.md` (dùng `docs/templates/decision.md`)

2. **Tuân thủ module architecture** khi tạo code mới:

   ```
   backend/src/modules/<module>/
   ├── api/        (routers, schemas, error_handler)
   ├── application/(services)
   ├── domain/     (entities, enums, exceptions)
   ├── infrastructure/ (repos, configs, clients)
   └── container.py
   ```

3. **Commit message** phải rõ ràng:
   - `feat(payroll): add tax calculation for dependents`
   - `fix(attendance): correct overtime hours query`
   - `docs(product): add payroll user guide`

## 📁 Cấu trúc docs/ hợp lệ

```
docs/
├── product/          ← Product docs (overview, guides, module specs)
├── technical/        ← Cross-cutting technical references
├── decisions/        ← ADRs (architecture decisions)
├── templates/        ← Templates (KHÔNG SỬA)
├── ARCHITECTURE.md   ← Architecture rules
└── README.md         ← Documentation map
```

Bất kỳ thư mục/file nào ngoài cấu trúc trên đều cần được di chuyển hoặc xóa.

## 🔧 Xử lý docs cũ không đúng format

Nếu gặp thư mục docs sai format (ví dụ `docs/cham-cong-nghi-phep/`), nội dung
hữu ích trong đó cần được:

- Hướng dẫn sử dụng → Di chuyển sang `docs/product/`
- Feature specs → Di chuyển sang `docs/product/`
- Technical notes → Di chuyển sang `docs/technical/`
