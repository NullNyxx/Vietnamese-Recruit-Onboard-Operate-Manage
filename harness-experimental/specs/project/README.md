# SPEC-PROJECT — Template & Hướng dẫn

## Mục đích

Template này dùng để khởi tạo dự án. Human và agent thảo luận ý tưởng dự án,
sau khi thống nhất, agent viết spec project hoàn chỉnh vào thư mục này rồi
chuyển vào luồng harness.

## Workflow

```text
1. Human yêu cầu agent đọc README này
2. Human mô tả ý tưởng dự án (qua chat)
3. Agent đặt câu hỏi, đề xuất stack, architecture, domain map
4. Human + Agent trao đổi cho đến khi thống nhất
5. Agent viết file spec hoàn chỉnh: harness-experimental/specs/project/{ten-du-an}.md
6. Agent chạy Feature Intake → "New spec"
7. Agent decompose → sinh product docs, architecture, decisions
8. Agent khởi tạo project structure
```

## Sau khi hoàn thành

File spec project trở thành snapshot lịch sử. Living truth nằm ở:
- `harness-experimental/docs/product/` — product contracts
- `harness-experimental/docs/ARCHITECTURE.md` — architecture decisions
- `harness-experimental/docs/decisions/` — decision records
- `harness-experimental/docs/stories/backlog.md` — candidate epics

Bước tiếp theo: human tạo SPEC-FEATURE cho feature đầu tiên.

---

## Template

> Agent dùng cấu trúc bên dưới khi viết spec project hoàn chỉnh.
> Không cần copy nguyên template — điền thông tin thực tế đã thống nhất.

---

### Metadata

```markdown
> **Phiên bản:** 1.0.0
> **Ngày tạo:** YYYY-MM-DD
> **Tác giả:** [Tên]
> **Trạng thái:** `Accepted` | `Decomposed`
```

### Sections bắt buộc

#### 1. Tổng quan dự án

- Xây dựng cái gì, cho ai, giải quyết vấn đề gì (2–5 câu)
- Mục tiêu chính (3–5 items)
- Đối tượng sử dụng (roles)

#### 2. Phạm vi tổng thể

- Trong scope: liệt kê domains/modules
- Không trong scope: liệt kê rõ + lý do

#### 3. Tech Stack

- Bảng: thành phần, công nghệ, version, ghi chú
- External services / providers
- Đây là quyết định cứng — agent không thay đổi trừ khi human cho phép

#### 4. Kiến trúc tổng thể

- Sơ đồ kiến trúc (text diagram)
- Thành phần chính (bảng)
- Layering / pattern (Clean Architecture, Hexagonal, MVC...)

#### 5. Domain Map

- Bảng domains: tên, mô tả, core entities
- Dependency map: domain nào phụ thuộc domain nào
- Suggested implementation order

#### 6. Conventions & Rules

- Code style (naming, max function length, import style, error handling)
- Architecture rules (boundary rules, dependency rules)
- Security baseline
- Testing strategy (scope, coverage target, tools)

#### 7. Project Structure

- Cấu trúc thư mục đề xuất (tree diagram)

#### 8. Yêu cầu phi chức năng

- Bảng: performance, availability, security, scalability, logging, compliance

#### 9. Assumptions & Constraints

- Giả định
- Ràng buộc kỹ thuật
- **Ask First** — những quyết định agent KHÔNG được tự ý đưa ra

#### 10. Candidate Epics & Roadmap

- Bảng: epic, mô tả, priority, risk signals
- Đây là gợi ý — chi tiết sẽ nằm trong SPEC-FEATURE

#### 11. Open Questions

- Câu hỏi chưa có đáp án, agent ghi decision records khi giải quyết

---

## Quy ước đặt tên file spec

```text
harness-experimental/specs/project/{ten-du-an}.md
```

Ví dụ:
```text
harness-experimental/specs/project/hr-ai-platform.md
harness-experimental/specs/project/ecommerce-backend.md
harness-experimental/specs/project/task-tracker.md
```

Chỉ có 1 file spec project cho mỗi dự án.
