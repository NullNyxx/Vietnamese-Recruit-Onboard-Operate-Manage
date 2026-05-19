# SPEC-FEATURE — Template & Hướng dẫn

## Mục đích

Template này dùng cho mỗi feature/module/workflow mới. Human và agent thảo luận
tính năng, sau khi thống nhất, agent viết spec feature hoàn chỉnh vào thư mục
này rồi chuyển vào luồng harness.

## Workflow

```text
1. Human yêu cầu agent đọc README này
2. Human mô tả feature muốn build (qua chat)
3. Agent đặt câu hỏi, đề xuất approach, contracts, business rules
4. Human + Agent trao đổi cho đến khi thống nhất
5. Agent viết file spec hoàn chỉnh: harness-experimental/specs/features/{domain}-{feature}.md
6. Agent chạy Feature Intake → classify risk, chọn lane
7. Agent tạo story packet(s)
8. Agent implement theo stories
9. Agent update TEST_MATRIX, product docs, decisions
```

## Quan trọng

- Agent KHÔNG được implement trước khi viết spec và human confirm
- Mỗi feature spec phải reference epic từ `harness-experimental/specs/project/`
- Khi feature xong, file giữ nguyên làm tài liệu lịch sử
- Nếu cần thay đổi feature đã xong, tạo spec mới hoặc update version

## Status Flow

```text
Discussing → Agreed → In Progress → Done
     ↑          |
     └── Revision (nếu cần thay đổi khi đang implement)
```

| Status | Ý nghĩa |
|--------|---------|
| `Discussing` | Human + Agent đang thảo luận |
| `Agreed` | Thống nhất, sẵn sàng implement |
| `In Progress` | Agent đang implement |
| `Done` | Feature hoàn thành, tests pass |
| `On Hold` | Tạm dừng vì blocker |

---

## Template

> Agent dùng cấu trúc bên dưới khi viết spec feature hoàn chỉnh.
> Không cần copy nguyên template — điền thông tin thực tế đã thống nhất.

---

### Metadata

```markdown
> **Phiên bản:** 1.0.0
> **Ngày tạo:** YYYY-MM-DD
> **Tác giả:** [Tên]
> **Trạng thái:** `Agreed` | `In Progress` | `Done`
> **Epic:** E0X — [Tên epic]
> **Parent:** specs/project/{ten-du-an}.md
```

### Sections bắt buộc

#### 1. Mô tả feature

- Feature làm gì (2–3 câu)
- Thuộc domain nào
- User roles liên quan + họ làm gì với feature

#### 2. Phạm vi feature

- Trong scope: behaviors cụ thể
- Không trong scope: ranh giới rõ + lý do

#### 3. Requirements

- Viết theo EARS format: `WHEN [điều kiện] THEN [hành vi]`
- Đánh số FR-XX để trace sang stories và test matrix
- Mỗi requirement có VALIDATION (cách kiểm chứng)

#### 4. Input / Output Contracts

- API endpoints (method, path, mô tả)
- Input schema (Zod / TypeScript types)
- Output schema
- Error cases (scenario, status code, error code, message)

#### 5. Business Rules & Logic

- Domain rules chi tiết
- Flow diagram nếu phức tạp
- Edge cases đã thống nhất

#### 6. Data Model (nếu có)

- Entities & fields
- Relationships
- Migrations needed

#### 7. UI / UX (nếu có)

- Screens / components
- User flow

#### 8. Acceptance Criteria

- Tiêu chí cụ thể, testable
- Agent phải pass TẤT CẢ trước khi chuyển Done
- Bao gồm: tests pass, lint pass, type check pass

#### 9. Risk & Dependencies

- Risk flags (bảng từ FEATURE_INTAKE.md)
- Dependencies (features khác, external services)

#### 10. Validation Plan

- Unit / Integration / E2E expectations

#### 11. Discussion Log

- Ghi lại quyết định quan trọng trong quá trình thảo luận
- Format: `[YYYY-MM-DD] Chủ đề → Kết luận`

#### 12. Open Questions

- Câu hỏi cần human trả lời trước khi implement

---

## Quy ước đặt tên file spec

```text
harness-experimental/specs/features/{domain}-{feature-name}.md
```

Ví dụ:
```text
harness-experimental/specs/features/recruitment-cv-parser.md
harness-experimental/specs/features/recruitment-interview-scheduler.md
harness-experimental/specs/features/onboarding-checklist.md
harness-experimental/specs/features/onboarding-document-processor.md
harness-experimental/specs/features/leave-request.md
harness-experimental/specs/features/attendance-processor.md
```
