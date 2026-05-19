# SPEC-FEATURE — Employee Management

> **Phiên bản:** 1.0.0
> **Ngày tạo:** 2026-05-19
> **Tác giả:** NullNyx + Kiro
> **Trạng thái:** `Agreed`
> **Epic:** E02 — Employee Management
> **Parent:** harness-experimental/specs/project/vroom-hr.md

---

## 1. Mô tả feature

Module Employee Management cung cấp khả năng quản lý hồ sơ nhân sự tập trung.
HR có thể tạo, xem, sửa, xóa employee, import hàng loạt từ Excel, quản lý
phòng ban/chức vụ, và lưu trữ tài liệu cá nhân (CCCD, bằng cấp, hợp đồng)
trong document vault.

Module này là foundation data — các module khác (recruitment, interview) phụ
thuộc vào danh sách employee để assign interviewer, promote candidate, v.v.

**Domain:** employee

**User roles:**
- HR — CRUD employee, import Excel, quản lý document vault

---

## 2. Phạm vi feature

### Trong scope

- Employee CRUD (create, read, update, soft-delete)
- Department & Position management (CRUD)
- Excel import (bulk create/update employees)
- Document vault (upload, list, download personal documents)
- Employee search & filter (by name, department, position, status)
- Pagination cho employee list
- Candidate → Employee promotion (nhận data từ recruitment module)

### Không trong scope

- Employee self-service portal (Phase 2 — cần employee login)
- Leave & Attendance tracking (Phase 2)
- Payroll / salary management (Phase 3)
- Org chart visualization (nice-to-have, không MVP)
- Employee performance review
- Contract renewal reminders

---

## 3. Requirements

| ID | Requirement (EARS format) | Validation |
|----|---------------------------|------------|
| FR-01 | WHEN HR navigates to /employees THEN system displays paginated employee list with name, email, department, position, status | E2E: verify list renders |
| FR-02 | WHEN HR clicks "Add Employee" and submits valid form THEN system creates Employee record and shows success | Integration: verify DB record |
| FR-03 | WHEN HR submits employee form with duplicate email THEN system returns 409 Conflict | Unit: test unique constraint |
| FR-04 | WHEN HR clicks edit on an employee and saves changes THEN system updates the record and shows updated data | Integration: verify update |
| FR-05 | WHEN HR deletes an employee THEN system soft-deletes (is_active=false), employee no longer appears in default list | Integration: verify soft-delete |
| FR-06 | WHEN HR uploads an Excel file (.xlsx) THEN system parses and creates/updates employees in bulk, returning a summary report | Integration: test with sample Excel |
| FR-07 | WHEN Excel row has invalid data (missing required field, invalid email) THEN system skips that row and includes it in error report | Unit: test validation per row |
| FR-08 | WHEN HR uploads a document for an employee THEN system stores file in MinIO and creates metadata record | Integration: verify file stored |
| FR-09 | WHEN HR views employee detail THEN system shows profile + list of uploaded documents with download links | E2E: verify document list |
| FR-10 | WHEN HR searches employees by name or email THEN system returns matching results (case-insensitive partial match) | Integration: test search |
| FR-11 | WHEN HR filters by department or position THEN system returns only matching employees | Integration: test filter |
| FR-12 | WHEN recruitment module promotes a candidate THEN system creates Employee from candidate data (name, email, phone) | Integration: test promotion flow |
| FR-13 | WHEN HR creates/updates a department THEN system persists it and it appears in employee form dropdown | Integration: verify CRUD |
| FR-14 | WHEN HR creates/updates a position THEN system persists it and it appears in employee form dropdown | Integration: verify CRUD |

---

## 4. Input / Output Contracts

### API Endpoints

| Method | Path | Mô tả |
|--------|------|--------|
| GET | /api/employees | List employees (paginated, searchable, filterable) |
| POST | /api/employees | Create employee |
| GET | /api/employees/:id | Get employee detail |
| PUT | /api/employees/:id | Update employee |
| DELETE | /api/employees/:id | Soft-delete employee |
| POST | /api/employees/import | Import from Excel |
| GET | /api/employees/:id/documents | List employee documents |
| POST | /api/employees/:id/documents | Upload document |
| GET | /api/employees/:id/documents/:docId/download | Download document |
| DELETE | /api/employees/:id/documents/:docId | Delete document |
| GET | /api/departments | List departments |
| POST | /api/departments | Create department |
| PUT | /api/departments/:id | Update department |
| DELETE | /api/departments/:id | Delete department |
| GET | /api/positions | List positions |
| POST | /api/positions | Create position |
| PUT | /api/positions/:id | Update position |
| DELETE | /api/positions/:id | Delete position |

### GET /api/employees

**Query params:**
- `page` (int, default 1)
- `page_size` (int, default 20, max 100)
- `search` (string, optional — matches name or email)
- `department_id` (UUID, optional)
- `position_id` (UUID, optional)
- `is_active` (bool, default true)

**Success response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "employee_code": "NV-001",
      "full_name": "Nguyễn Văn A",
      "email": "a.nguyen@company.com",
      "phone": "0901234567",
      "department": { "id": "uuid", "name": "Engineering" },
      "position": { "id": "uuid", "name": "Senior Developer" },
      "start_date": "2024-01-15",
      "is_active": true
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

### POST /api/employees

**Request body:**
```json
{
  "full_name": "Nguyễn Văn A",
  "email": "a.nguyen@company.com",
  "phone": "0901234567",
  "date_of_birth": "1995-03-15",
  "gender": "male",
  "address": "123 Nguyễn Huệ, Q1, TP.HCM",
  "department_id": "uuid",
  "position_id": "uuid",
  "start_date": "2024-01-15",
  "id_number": "079095001234",
  "tax_code": "8001234567"
}
```

**Success response (201):**
```json
{
  "id": "uuid",
  "employee_code": "NV-046",
  "full_name": "Nguyễn Văn A",
  "email": "a.nguyen@company.com",
  "created_at": "2026-05-19T10:00:00Z"
}
```

**Error responses:**

| Scenario | Status | Error Code | Message |
|----------|--------|------------|---------|
| Missing required field | 422 | VALIDATION_ERROR | Field-level errors |
| Duplicate email | 409 | EMPLOYEE_DUPLICATE_EMAIL | Employee with this email already exists |
| Department not found | 404 | DEPARTMENT_NOT_FOUND | Department not found |
| Position not found | 404 | POSITION_NOT_FOUND | Position not found |

### POST /api/employees/import

**Request:** multipart/form-data with `.xlsx` file

**Success response (200):**
```json
{
  "total_rows": 50,
  "created": 45,
  "updated": 3,
  "errors": [
    { "row": 12, "field": "email", "message": "Invalid email format" },
    { "row": 27, "field": "full_name", "message": "Required field is empty" }
  ]
}
```

### POST /api/employees/:id/documents

**Request:** multipart/form-data
- `file`: the document file (PDF, JPG, PNG, DOCX)
- `document_type`: enum (cccd, tax_code, degree, contract, photo, other)
- `description`: optional string

**Success response (201):**
```json
{
  "id": "uuid",
  "file_name": "cccd_front.jpg",
  "document_type": "cccd",
  "file_size": 245000,
  "uploaded_at": "2026-05-19T10:00:00Z"
}
```

---

## 5. Business Rules & Logic

### Domain Rules

1. **Employee code**: Auto-generated, format `NV-{sequential_number}` (e.g., NV-001, NV-002). Không thay đổi sau khi tạo.
2. **Email unique**: Mỗi employee có email duy nhất trong hệ thống (case-insensitive).
3. **Soft-delete**: Delete chỉ set `is_active=false`. Employee vẫn tồn tại trong DB, documents vẫn giữ.
4. **Department/Position**: Không xóa được nếu còn employee active thuộc department/position đó.
5. **Excel import**: Match bằng email — nếu email đã tồn tại thì update, nếu chưa thì create.
6. **Document vault**: File lưu MinIO tại path `employees/{employee_id}/{document_type}/{filename}`. Max 10MB/file.
7. **Candidate promotion**: Khi candidate được promote, tạo Employee với data từ candidate (name, email, phone). HR bổ sung thêm department, position, start_date.

### Excel Import Format

| Column | Field | Required | Validation |
|--------|-------|----------|------------|
| A | full_name | Yes | Non-empty string |
| B | email | Yes | Valid email format |
| C | phone | No | Vietnamese phone (10 digits, starts with 0) |
| D | date_of_birth | No | Date format YYYY-MM-DD or DD/MM/YYYY |
| E | gender | No | male / female / other |
| F | department | No | Must match existing department name |
| G | position | No | Must match existing position name |
| H | start_date | No | Date format |
| I | id_number | No | 9 or 12 digits (CMND/CCCD) |
| J | tax_code | No | 10-13 digits |

### Edge Cases

| Case | Xử lý |
|------|--------|
| Import Excel với department chưa tồn tại | Skip row, report error |
| Upload file > 10MB | Return 413 Payload Too Large |
| Upload file type không hỗ trợ | Return 415 Unsupported Media Type |
| Delete department có employee | Return 409 Conflict |
| Promote candidate đã có email trùng employee | Update existing employee, link candidate |

---

## 6. Data Model

### Entity: Employee

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Internal ID |
| employee_code | VARCHAR(20) | UNIQUE, NOT NULL | Auto-generated NV-XXX |
| full_name | VARCHAR(255) | NOT NULL | Họ tên đầy đủ |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Email công ty |
| phone | VARCHAR(20) | NULLABLE | Số điện thoại |
| date_of_birth | DATE | NULLABLE | Ngày sinh |
| gender | VARCHAR(10) | NULLABLE | male/female/other |
| address | TEXT | NULLABLE | Địa chỉ |
| department_id | UUID | FK → Department.id, NULLABLE | Phòng ban |
| position_id | UUID | FK → Position.id, NULLABLE | Chức vụ |
| start_date | DATE | NULLABLE | Ngày bắt đầu làm việc |
| id_number | VARCHAR(20) | NULLABLE | Số CMND/CCCD |
| tax_code | VARCHAR(20) | NULLABLE | Mã số thuế |
| candidate_id | UUID | FK → Candidate.id, NULLABLE | Link nếu promote từ candidate |
| contract_type | VARCHAR(20) | NULLABLE | full_time/part_time/intern/contractor |
| is_active | BOOLEAN | NOT NULL, default TRUE | Soft-delete flag |
| created_at | TIMESTAMPTZ | NOT NULL | Thời điểm tạo |
| updated_at | TIMESTAMPTZ | NOT NULL | Lần cập nhật cuối |

### Entity: Department

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Internal ID |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Tên phòng ban |
| description | TEXT | NULLABLE | Mô tả |
| created_at | TIMESTAMPTZ | NOT NULL | Thời điểm tạo |

### Entity: Position

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Internal ID |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Tên chức vụ |
| department_id | UUID | FK → Department.id, NULLABLE | Thuộc phòng ban (optional) |
| created_at | TIMESTAMPTZ | NOT NULL | Thời điểm tạo |

### Entity: EmployeeDocument

| Field | Type | Constraints | Mô tả |
|-------|------|-------------|--------|
| id | UUID | PK | Internal ID |
| employee_id | UUID | FK → Employee.id, NOT NULL | Thuộc employee |
| document_type | VARCHAR(50) | NOT NULL | cccd/tax_code/degree/contract/photo/other |
| file_name | VARCHAR(255) | NOT NULL | Tên file gốc |
| storage_path | TEXT | NOT NULL | Path trong MinIO |
| file_size | INTEGER | NOT NULL | Kích thước (bytes) |
| mime_type | VARCHAR(100) | NOT NULL | MIME type |
| description | TEXT | NULLABLE | Mô tả tùy chọn |
| uploaded_at | TIMESTAMPTZ | NOT NULL | Thời điểm upload |

### Relationships

```
Department (1) ──── (N) Employee
Department (1) ──── (N) Position
Position (1) ──── (N) Employee
Employee (1) ──── (N) EmployeeDocument
```

---

## 7. UI / UX

### Screens

| Screen | Route | Mô tả |
|--------|-------|--------|
| Employee List | /employees | Bảng danh sách, search, filter, pagination |
| Employee Create | /employees/new | Form tạo mới |
| Employee Detail | /employees/:id | Profile + documents |
| Employee Edit | /employees/:id/edit | Form chỉnh sửa |
| Department List | /settings/departments | CRUD departments |
| Position List | /settings/positions | CRUD positions |
| Import Excel | /employees/import | Upload + preview + confirm |

### Employee List Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Employees                              [Import] [+ Add New]  │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Search by name or email...                               │
│ [Department ▼] [Position ▼] [Status ▼]                      │
├─────────────────────────────────────────────────────────────┤
│ Code  │ Name          │ Email         │ Dept    │ Position  │
│ NV-001│ Nguyễn Văn A  │ a@company.com │ Eng     │ Senior    │
│ NV-002│ Trần Thị B    │ b@company.com │ HR      │ Manager   │
│ ...   │               │               │         │           │
├─────────────────────────────────────────────────────────────┤
│ ◀ 1 2 3 ... 5 ▶                          Showing 1-20 of 45│
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Acceptance Criteria

| # | Criterion | Type |
|---|-----------|------|
| AC-01 | Employee list displays with pagination, search works | E2E |
| AC-02 | Create employee with all fields, verify in DB | Integration |
| AC-03 | Duplicate email returns 409 | Unit |
| AC-04 | Update employee, verify changes persisted | Integration |
| AC-05 | Soft-delete hides from list, data preserved in DB | Integration |
| AC-06 | Excel import creates employees, returns summary | Integration |
| AC-07 | Excel import skips invalid rows, reports errors | Unit |
| AC-08 | Upload document stores in MinIO, metadata in DB | Integration |
| AC-09 | Download document returns correct file | Integration |
| AC-10 | Department/Position CRUD works, cascade protection | Integration |
| AC-11 | Search by name/email returns correct results | Integration |
| AC-12 | Filter by department/position works | Integration |
| AC-13 | All tests pass, lint pass, type check pass | CI |

---

## 9. Risk & Dependencies

### Risk Flags

| Risk | Level | Mitigation |
|------|-------|------------|
| MinIO not yet set up | Low | Add to docker-compose.infra.yml |
| Excel parsing edge cases (merged cells, formulas) | Low | Use openpyxl, document supported format |
| File upload size limits | Low | Validate in middleware, 10MB max |

### Dependencies

| Dependency | Type | Mô tả |
|------------|------|--------|
| Identity module | Internal | JWT auth for all endpoints |
| MinIO | Infrastructure | Document vault storage |
| openpyxl | Library | Excel file parsing |
| PostgreSQL | Infrastructure | Employee data persistence |

---

## 10. Validation Plan

### Unit Tests

- Employee code generation (sequential, unique)
- Email uniqueness validation
- Excel row validation (required fields, format)
- Document type enum validation
- Soft-delete logic

### Integration Tests

- Full CRUD cycle (create → read → update → delete)
- Excel import with valid + invalid rows
- Document upload → download round-trip
- Search and filter queries
- Department/Position cascade protection
- Candidate → Employee promotion

### E2E Tests (Playwright)

- Employee list page loads with data
- Create employee form → success
- Search filters results
- Upload document → appears in detail page

---

## 11. Discussion Log

| Date | Chủ đề | Kết luận |
|------|--------|----------|
| 2026-05-19 | Employee code format | Cố định `NV-XXX`, sequential, single-tenant đủ dùng |
| 2026-05-19 | Excel import unknown dept | Skip row + report error, không auto-create department |
| 2026-05-19 | Document vault versioning | Append-only, giữ tất cả versions (audit trail) |
| 2026-05-19 | Contract type field | Thêm `contract_type` enum: full_time, part_time, intern, contractor |
| 2026-05-19 | Soft-delete documents | Giữ nguyên trên MinIO khi soft-delete employee (compliance) |

---

## 12. Open Questions

| # | Câu hỏi | Impact | Khi nào |
|---|---------|--------|---------|
| Q1 | Employee code format: NV-001 hay tùy chỉnh prefix theo công ty? | Employee domain | Trước implement |
| Q2 | Excel import: nếu department name không match, tự tạo department mới hay skip? | Import logic | Trước implement |
| Q3 | Document vault: cần version history (upload lại CCCD mới) hay chỉ giữ bản mới nhất? | Storage design | Trước implement |
| Q4 | Employee có cần field "contract_type" (full-time/part-time/intern) cho MVP? | Data model | Trước implement |
| Q5 | Khi soft-delete employee, documents có xóa khỏi MinIO không hay giữ? | Storage policy | Trước implement |

---

*End of spec.*
