# Employee Management — Feature Spec

## 1. Tổng quan

Module Employee Management quản lý toàn bộ thông tin nhân viên, phòng ban, chức vụ, và tài liệu nhân sự. Hỗ trợ CRUD đầy đủ với phân trang, tìm kiếm, lọc, import từ Excel, và lưu trữ tài liệu trên MinIO. Module cũng xử lý luồng chuyển đổi ứng viên (candidate) thành nhân viên chính thức.

## 2. Actors

| Actor        | Mô tả                                                             |
| ------------ | ----------------------------------------------------------------- |
| **HR Admin** | Quản lý toàn bộ: CRUD nhân viên, phòng ban, chức vụ, tài liệu     |
| **System**   | Tự động sinh mã nhân viên, tạo phòng ban/chức vụ khi import Excel |
| **Employee** | Xem thông tin cá nhân qua ESS module (read-only)                  |

## 3. Luồng hoạt động (User Flows)

### 3.1 Tạo nhân viên mới

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── POST /api/employees ────►│                          │
 │   {full_name, email,       │── Validate input         │
 │    department_id,          │── Check email unique ────►│
 │    position_id, ...}       │── Generate code (NV-XXX)─►│
 │                            │── Insert employee ───────►│
 │◄─ 201 {employee} ─────────│                          │
```

### 3.2 Import từ Excel

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── POST /api/employees/     │                          │
 │   import (file.xlsx) ─────►│                          │
 │                            │── Parse Excel rows        │
 │                            │── For each row:           │
 │                            │   ├─ Find/create dept ───►│
 │                            │   ├─ Find/create pos ────►│
 │                            │   ├─ Validate fields      │
 │                            │   └─ Insert employee ────►│
 │                            │── Collect results         │
 │◄─ 200 {created: N,        │                          │
 │    errors: [...]} ─────────│                          │
```

### 3.3 Upload tài liệu

```
HR Admin                    Backend                    MinIO
 │                            │                          │
 │── POST /api/documents      │                          │
 │   {employee_id, file,      │── Validate MIME type      │
 │    document_type} ─────────│── Validate size ≤ 10MB    │
 │                            │── Upload to MinIO ───────►│
 │                            │◄─ object_key ────────────│
 │                            │── Save metadata to DB     │
 │◄─ 201 {document} ─────────│                          │
```

### 3.4 Candidate → Employee Promotion

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── POST /api/employees/     │                          │
 │   promote/{candidate_id} ─►│                          │
 │                            │── Fetch candidate ───────►│
 │                            │── Validate status =       │
 │                            │   'accepted'              │
 │                            │── Create employee from    │
 │                            │   candidate data          │
 │                            │── Generate code (NV-XXX)  │
 │                            │── Update candidate status │
 │                            │   → 'promoted'            │
 │◄─ 201 {employee} ─────────│                          │
```

## 4. Business Rules

1. **BR-01**: Mã nhân viên tự động sinh theo format `NV-XXX` (3 chữ số, zero-padded, tăng dần).
2. **BR-02**: Email nhân viên phải unique trong hệ thống.
3. **BR-03**: Không thể xóa phòng ban/chức vụ nếu còn nhân viên active thuộc về (cascade protection).
4. **BR-04**: Soft delete: nhân viên bị "xóa" chỉ set `is_active = false`, không xóa record.
5. **BR-05**: Import Excel tự động tạo phòng ban/chức vụ nếu chưa tồn tại (match by name).
6. **BR-06**: Tài liệu upload tối đa 10MB per file.
7. **BR-07**: MIME types cho phép: `application/pdf`, `image/jpeg`, `image/png`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
8. **BR-08**: Chỉ candidate có status `accepted` mới được promote thành employee.
9. **BR-09**: Khi promote, dữ liệu từ candidate (name, email, phone) được copy sang employee.
10. **BR-10**: Phòng ban và chức vụ có thể deactivate (soft delete) nhưng không xóa cứng.
11. **BR-11**: Tìm kiếm nhân viên hỗ trợ: full_name, email, employee_code, department, position.
12. **BR-12**: Pagination mặc định: page=1, page_size=20, max page_size=100.

## 5. Data Model

### Employee

| Field             | Type                                                  | Constraints                   | Mô tả                     |
| ----------------- | ----------------------------------------------------- | ----------------------------- | ------------------------- |
| id                | UUID                                                  | PK                            | ID duy nhất               |
| employee_code     | String(20)                                            | UNIQUE, NOT NULL              | Mã NV (NV-001, NV-002...) |
| full_name         | String(255)                                           | NOT NULL                      | Họ tên đầy đủ             |
| email             | String(255)                                           | UNIQUE, NOT NULL              | Email công ty             |
| phone             | String(20)                                            | NULLABLE                      | Số điện thoại             |
| date_of_birth     | Date                                                  | NULLABLE                      | Ngày sinh                 |
| gender            | Enum('male','female','other')                         | NULLABLE                      | Giới tính                 |
| id_number         | String(20)                                            | NULLABLE                      | Số CCCD/CMND              |
| tax_code          | String(20)                                            | NULLABLE                      | Mã số thuế cá nhân        |
| address           | Text                                                  | NULLABLE                      | Địa chỉ thường trú        |
| emergency_contact | String(255)                                           | NULLABLE                      | Liên hệ khẩn cấp          |
| department_id     | UUID                                                  | FK → departments.id, NULLABLE | Phòng ban                 |
| position_id       | UUID                                                  | FK → positions.id, NULLABLE   | Chức vụ                   |
| hire_date         | Date                                                  | NOT NULL                      | Ngày vào làm              |
| contract_type     | Enum('permanent','fixed_term','probation','seasonal') | NULLABLE                      | Loại hợp đồng             |
| is_active         | Boolean                                               | NOT NULL, DEFAULT true        | Còn làm việc              |
| created_at        | DateTime                                              | NOT NULL                      | Thời điểm tạo             |
| updated_at        | DateTime                                              | NOT NULL                      | Thời điểm cập nhật        |

### Department

| Field       | Type        | Constraints                 | Mô tả              |
| ----------- | ----------- | --------------------------- | ------------------ |
| id          | UUID        | PK                          | ID duy nhất        |
| name        | String(255) | UNIQUE, NOT NULL            | Tên phòng ban      |
| description | Text        | NULLABLE                    | Mô tả              |
| manager_id  | UUID        | FK → employees.id, NULLABLE | Trưởng phòng       |
| is_active   | Boolean     | NOT NULL, DEFAULT true      | Còn hoạt động      |
| created_at  | DateTime    | NOT NULL                    | Thời điểm tạo      |
| updated_at  | DateTime    | NOT NULL                    | Thời điểm cập nhật |

### Position

| Field         | Type        | Constraints                   | Mô tả              |
| ------------- | ----------- | ----------------------------- | ------------------ |
| id            | UUID        | PK                            | ID duy nhất        |
| name          | String(255) | UNIQUE, NOT NULL              | Tên chức vụ        |
| description   | Text        | NULLABLE                      | Mô tả              |
| department_id | UUID        | FK → departments.id, NULLABLE | Thuộc phòng ban    |
| is_active     | Boolean     | NOT NULL, DEFAULT true        | Còn hoạt động      |
| created_at    | DateTime    | NOT NULL                      | Thời điểm tạo      |
| updated_at    | DateTime    | NOT NULL                      | Thời điểm cập nhật |

### EmployeeDocument

| Field         | Type        | Constraints                 | Mô tả                                         |
| ------------- | ----------- | --------------------------- | --------------------------------------------- |
| id            | UUID        | PK                          | ID duy nhất                                   |
| employee_id   | UUID        | FK → employees.id, NOT NULL | Nhân viên sở hữu                              |
| document_type | String(100) | NOT NULL                    | Loại tài liệu (contract, id_card, diploma...) |
| file_name     | String(255) | NOT NULL                    | Tên file gốc                                  |
| file_size     | Integer     | NOT NULL                    | Kích thước (bytes)                            |
| mime_type     | String(100) | NOT NULL                    | MIME type                                     |
| object_key    | String(500) | NOT NULL                    | MinIO object key                              |
| uploaded_by   | UUID        | FK → users.id, NOT NULL     | Người upload                                  |
| created_at    | DateTime    | NOT NULL                    | Thời điểm upload                              |

## 6. State Machine

### Employee Lifecycle

```
┌──────────┐   promote    ┌──────────┐
│ Candidate│ ────────────► │  Active  │
└──────────┘              └────┬─────┘
                               │ deactivate (soft delete)
                               ▼
                          ┌──────────┐
                          │ Inactive │
                          └────┬─────┘
                               │ reactivate
                               ▼
                          ┌──────────┐
                          │  Active  │
                          └──────────┘
```

Lưu ý: Không có trạng thái "deleted" — chỉ có active/inactive (soft delete).

## 7. API Endpoints

### Employees

| Method | Path                                    | Mô tả                                       | Auth  |
| ------ | --------------------------------------- | ------------------------------------------- | ----- |
| GET    | `/api/employees`                        | Danh sách nhân viên (paginated, searchable) | Admin |
| POST   | `/api/employees`                        | Tạo nhân viên mới                           | Admin |
| GET    | `/api/employees/{id}`                   | Chi tiết nhân viên                          | Admin |
| PUT    | `/api/employees/{id}`                   | Cập nhật nhân viên                          | Admin |
| DELETE | `/api/employees/{id}`                   | Soft delete nhân viên                       | Admin |
| POST   | `/api/employees/import`                 | Import từ Excel                             | Admin |
| POST   | `/api/employees/promote/{candidate_id}` | Promote candidate → employee                | Admin |

### Departments

| Method | Path                    | Mô tả                         | Auth  |
| ------ | ----------------------- | ----------------------------- | ----- |
| GET    | `/api/departments`      | Danh sách phòng ban           | Admin |
| POST   | `/api/departments`      | Tạo phòng ban                 | Admin |
| GET    | `/api/departments/{id}` | Chi tiết phòng ban            | Admin |
| PUT    | `/api/departments/{id}` | Cập nhật phòng ban            | Admin |
| DELETE | `/api/departments/{id}` | Xóa phòng ban (cascade check) | Admin |

### Positions

| Method | Path                  | Mô tả                       | Auth  |
| ------ | --------------------- | --------------------------- | ----- |
| GET    | `/api/positions`      | Danh sách chức vụ           | Admin |
| POST   | `/api/positions`      | Tạo chức vụ                 | Admin |
| GET    | `/api/positions/{id}` | Chi tiết chức vụ            | Admin |
| PUT    | `/api/positions/{id}` | Cập nhật chức vụ            | Admin |
| DELETE | `/api/positions/{id}` | Xóa chức vụ (cascade check) | Admin |

### Documents

| Method | Path                           | Mô tả                             | Auth  |
| ------ | ------------------------------ | --------------------------------- | ----- |
| GET    | `/api/documents/{employee_id}` | Danh sách tài liệu của nhân viên  | Admin |
| POST   | `/api/documents`               | Upload tài liệu                   | Admin |
| GET    | `/api/documents/{id}/download` | Download tài liệu (presigned URL) | Admin |
| DELETE | `/api/documents/{id}`          | Xóa tài liệu                      | Admin |

## 8. Edge Cases & Error Handling

| Scenario                                  | Xử lý                                             |
| ----------------------------------------- | ------------------------------------------------- |
| Email trùng khi tạo employee              | 409 `EMAIL_ALREADY_EXISTS`                        |
| Employee code collision (race condition)  | Retry với code tiếp theo, DB unique constraint    |
| Xóa department có employees               | 409 `DEPARTMENT_HAS_ACTIVE_EMPLOYEES`             |
| Xóa position có employees                 | 409 `POSITION_HAS_ACTIVE_EMPLOYEES`               |
| Upload file > 10MB                        | 413 `FILE_TOO_LARGE`                              |
| Upload MIME type không hợp lệ             | 415 `UNSUPPORTED_MEDIA_TYPE`                      |
| Import Excel file lỗi format              | 422 `INVALID_EXCEL_FORMAT` — trả về row errors    |
| Import Excel partial failure              | 200 với `{created: N, skipped: M, errors: [...]}` |
| Promote candidate không ở status accepted | 409 `CANDIDATE_NOT_ACCEPTED`                      |
| MinIO unavailable khi upload              | 503 `STORAGE_UNAVAILABLE`                         |
| Download document đã bị xóa trên MinIO    | 404 `DOCUMENT_NOT_FOUND`                          |
| Employee không tồn tại                    | 404 `EMPLOYEE_NOT_FOUND`                          |

## 9. Integration Points

| Module           | Cách tích hợp                                                                    |
| ---------------- | -------------------------------------------------------------------------------- |
| **Identity**     | Admin auth required cho tất cả endpoints; `User.email` link với `Employee.email` |
| **Recruitment**  | Candidate promote flow: lấy data từ `candidates` table                           |
| **Attendance**   | `employee_id` dùng trong attendance_records, leave_requests                      |
| **Payroll**      | `employee_id` dùng trong salary_configs, payslips                                |
| **Self-Service** | Employee xem thông tin cá nhân qua ESS                                           |
| **Gmail**        | Gửi email thông báo khi tạo/promote employee                                     |

## 10. Configuration

| Env Variable                     | Default              | Mô tả                          |
| -------------------------------- | -------------------- | ------------------------------ |
| `MINIO_ENDPOINT`                 | `localhost:9000`     | MinIO server endpoint          |
| `MINIO_ACCESS_KEY`               | `minioadmin`         | MinIO access key               |
| `MINIO_SECRET_KEY`               | `minioadmin`         | MinIO secret key               |
| `MINIO_BUCKET_NAME`              | `employee-documents` | Bucket cho tài liệu nhân viên  |
| `MINIO_PRESIGNED_URL_EXPIRY`     | `900`                | Presigned URL expiry (seconds) |
| `EMPLOYEE_MAX_UPLOAD_SIZE_BYTES` | `10485760`           | Max file size (10MB)           |
| `EMPLOYEE_ALLOWED_MIME_TYPES`    | `pdf,docx,jpeg,png`  | MIME types cho phép            |
| `EMPLOYEE_CODE_PREFIX`           | `NV`                 | Prefix cho mã nhân viên        |
| `EMPLOYEE_DEFAULT_PAGE_SIZE`     | `20`                 | Số records per page mặc định   |
| `EMPLOYEE_MAX_PAGE_SIZE`         | `100`                | Số records per page tối đa     |
