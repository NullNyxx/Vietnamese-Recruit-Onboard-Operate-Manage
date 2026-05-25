# Payroll — Feature Spec

## 1. Tổng quan

Module Payroll quản lý toàn bộ quy trình tính lương theo luật lao động Việt Nam: cấu hình lương, phụ cấp, người phụ thuộc (giảm trừ thuế), tính thuế TNCN lũy tiến 7 bậc, tạo payslip PDF, và gửi email bảng lương. Hỗ trợ position-based salary bands (grade A/B/C/D) và tính OT từ approved overtime requests.

## 2. Actors

| Actor        | Mô tả                                                |
| ------------ | ---------------------------------------------------- |
| **HR Admin** | Cấu hình lương, chạy payroll, confirm, send payslips |
| **System**   | Tính toán tự động: thuế, bảo hiểm, OT, net salary    |
| **Employee** | Xem payslip cá nhân qua ESS (read-only)              |

## 3. Luồng hoạt động (User Flows)

### 3.1 Payroll Calculation Flow

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── POST /api/payroll/       │                          │
 │   periods                  │                          │
 │   {month, year} ──────────►│── Create period ─────────►│
 │                            │   (status: draft)         │
 │◄─ 201 {period} ───────────│                          │
 │                            │                          │
 │── POST /api/payroll/       │                          │
 │   periods/{id}/calculate ─►│                          │
 │                            │── Status → calculating    │
 │                            │── For each active employee:│
 │                            │   ├─ Get salary_config ──►│
 │                            │   ├─ Get allowances ─────►│
 │                            │   ├─ Get dependents ─────►│
 │                            │   ├─ Get attendance ─────►│
 │                            │   │  (count work days)    │
 │                            │   ├─ Get approved OT ────►│
 │                            │   ├─ Calculate:           │
 │                            │   │  actual_gross         │
 │                            │   │  insurance            │
 │                            │   │  deductions           │
 │                            │   │  taxable_income       │
 │                            │   │  income_tax           │
 │                            │   │  net_salary           │
 │                            │   └─ Create payslip ─────►│
 │                            │── Status → draft          │
 │◄─ 200 {period, payslips} ─│                          │
 │                            │                          │
 │── POST /api/payroll/       │                          │
 │   periods/{id}/confirm ───►│── Status → confirmed ────►│
 │◄─ 200 OK ─────────────────│                          │
 │                            │                          │
 │── POST /api/payroll/       │                          │
 │   periods/{id}/mark-paid ─►│── Status → paid ─────────►│
 │                            │── Generate PDF payslips   │
 │                            │── Upload to MinIO         │
 │◄─ 200 OK ─────────────────│                          │
 │                            │                          │
 │── POST /api/payroll/       │                          │
 │   periods/{id}/send ──────►│── Batch email payslips ──►│ Gmail
 │◄─ 200 {sent: N, failed: M}│                          │
```

### 3.2 Tax Calculation Formula

```
┌─────────────────────────────────────────────────────────────────┐
│                    CÔNG THỨC TÍNH LƯƠNG NET                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. actual_gross = (gross_salary / 26) × actual_work_days        │
│                                                                  │
│  2. insurance_premium = insurance_salary × 10.5%                 │
│     (BHXH 8% + BHYT 1.5% + BHTN 1%)                            │
│                                                                  │
│  3. taxable_income = actual_gross + taxable_allowances           │
│                      + ot_amount                                  │
│                      - insurance_premium                          │
│                      - personal_deduction (11,000,000 VND)        │
│                      - dependent_deduction (4,400,000 × N)        │
│                                                                  │
│  4. income_tax = progressive_tax(taxable_income)                 │
│     ┌──────────────────────────────────────────┐                │
│     │ Bậc │ Thu nhập chịu thuế    │ Thuế suất │                │
│     │  1  │ 0 - 5,000,000         │    5%     │                │
│     │  2  │ 5,000,001 - 10,000,000│   10%     │                │
│     │  3  │ 10,000,001 - 18,000,000│  15%     │                │
│     │  4  │ 18,000,001 - 32,000,000│  20%     │                │
│     │  5  │ 32,000,001 - 52,000,000│  25%     │                │
│     │  6  │ 52,000,001 - 80,000,000│  30%     │                │
│     │  7  │ > 80,000,000          │   35%     │                │
│     └──────────────────────────────────────────┘                │
│                                                                  │
│  5. net_salary = actual_gross + all_allowances + ot_amount       │
│                  - insurance_premium - income_tax                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Work Days Counting

```
Attendance Status        → Work Day Count
─────────────────────────────────────────
present                  → 1.0
late                     → 1.0
early_leave              → 1.0
on_leave (approved)      → 1.0
absent                   → 0.0
holiday                  → 0.0 (không tính vào actual_work_days)
```

### 3.4 OT Calculation

```
Source: ONLY approved overtime_requests (NOT attendance_records.overtime_hours)

For each approved OT request in the period:
  hourly_rate = gross_salary / 26 / 8

  IF is_holiday:  ot_amount += hourly_rate × hours × 3.0
  ELIF is_weekend: ot_amount += hourly_rate × hours × 2.0
  ELSE:           ot_amount += hourly_rate × hours × 1.5
```

## 4. Business Rules

### Salary Configuration

1. **BR-01**: Mỗi employee có 1 salary_config active (gross_salary, insurance_salary, contract_type).
2. **BR-02**: Insurance salary có thể khác gross salary (thường ≤ gross, dùng để tính BHXH).
3. **BR-03**: Position salary bands: grade A/B/C/D, mỗi grade có min/mid/max salary.

### Allowances

4. **BR-04**: Loại phụ cấp: telephone, transport, meal, housing, responsibility, other.
5. **BR-05**: Phụ cấp có flag `is_taxable`: true → tính vào thu nhập chịu thuế, false → không.
6. **BR-06**: Non-taxable allowances vẫn cộng vào gross_income nhưng KHÔNG vào taxable_income.

### Tax & Insurance

7. **BR-07**: Personal deduction: 11,000,000 VND/tháng (cố định).
8. **BR-08**: Dependent deduction: 4,400,000 VND/người/tháng.
9. **BR-09**: Employee insurance rate: 10.5% (BHXH 8% + BHYT 1.5% + BHTN 1%).
10. **BR-10**: Employer insurance rate: 21.5% (informational, không trừ vào lương NV).
11. **BR-11**: Thuế TNCN lũy tiến 7 bậc (5% → 35%).
12. **BR-12**: Nếu taxable_income ≤ 0 → income_tax = 0.

### Payroll Period

13. **BR-13**: Daily rate = gross_salary / 26 (26 ngày công/tháng).
14. **BR-14**: actual_gross = daily_rate × actual_work_days.
15. **BR-15**: Mỗi tháng chỉ có 1 payroll period.
16. **BR-16**: Period phải ở status `draft` mới được calculate lại.
17. **BR-17**: Period phải ở status `confirmed` mới được mark as paid.

### OT

18. **BR-18**: OT source: CHỈ từ approved `overtime_requests`, KHÔNG từ `attendance_records.overtime_hours`.
19. **BR-19**: OT rates: weekday 1.5x, weekend 2.0x, holiday 3.0x.
20. **BR-20**: Hourly rate = gross_salary / 26 / 8.

### Payslip

21. **BR-21**: PDF payslip generated bằng ReportLab, lưu trên MinIO.
22. **BR-22**: Email payslips gửi batch qua Gmail API.
23. **BR-23**: Payslip chứa breakdown đầy đủ: gross, allowances, OT, deductions, tax, net.

## 5. Data Model

### SalaryConfig

| Field            | Type                                                  | Constraints                         | Mô tả              |
| ---------------- | ----------------------------------------------------- | ----------------------------------- | ------------------ |
| id               | UUID                                                  | PK                                  | ID duy nhất        |
| employee_id      | UUID                                                  | FK → employees.id, UNIQUE, NOT NULL | Nhân viên          |
| gross_salary     | Decimal(15,2)                                         | NOT NULL                            | Lương gross        |
| insurance_salary | Decimal(15,2)                                         | NOT NULL                            | Lương đóng BHXH    |
| contract_type    | Enum('permanent','fixed_term','probation','seasonal') | NOT NULL                            | Loại HĐ            |
| effective_date   | Date                                                  | NOT NULL                            | Ngày hiệu lực      |
| is_active        | Boolean                                               | NOT NULL, DEFAULT true              | Đang áp dụng       |
| created_at       | DateTime                                              | NOT NULL                            | Thời điểm tạo      |
| updated_at       | DateTime                                              | NOT NULL                            | Thời điểm cập nhật |

### Allowance

| Field       | Type                                                                    | Constraints                 | Mô tả         |
| ----------- | ----------------------------------------------------------------------- | --------------------------- | ------------- |
| id          | UUID                                                                    | PK                          | ID duy nhất   |
| employee_id | UUID                                                                    | FK → employees.id, NOT NULL | Nhân viên     |
| type        | Enum('telephone','transport','meal','housing','responsibility','other') | NOT NULL                    | Loại phụ cấp  |
| amount      | Decimal(15,2)                                                           | NOT NULL                    | Số tiền/tháng |
| is_taxable  | Boolean                                                                 | NOT NULL, DEFAULT true      | Chịu thuế     |
| description | String(255)                                                             | NULLABLE                    | Mô tả         |
| is_active   | Boolean                                                                 | NOT NULL, DEFAULT true      | Đang áp dụng  |
| created_at  | DateTime                                                                | NOT NULL                    | Thời điểm tạo |

### Dependent

| Field          | Type        | Constraints                 | Mô tả                              |
| -------------- | ----------- | --------------------------- | ---------------------------------- |
| id             | UUID        | PK                          | ID duy nhất                        |
| employee_id    | UUID        | FK → employees.id, NOT NULL | Nhân viên                          |
| full_name      | String(255) | NOT NULL                    | Họ tên người phụ thuộc             |
| relationship   | String(100) | NOT NULL                    | Quan hệ (con, vợ/chồng, cha/mẹ)    |
| date_of_birth  | Date        | NULLABLE                    | Ngày sinh                          |
| id_number      | String(20)  | NULLABLE                    | Số CCCD                            |
| tax_code       | String(20)  | NULLABLE                    | MST người phụ thuộc                |
| effective_from | Date        | NOT NULL                    | Ngày bắt đầu giảm trừ              |
| effective_to   | Date        | NULLABLE                    | Ngày kết thúc (NULL = vô thời hạn) |
| is_active      | Boolean     | NOT NULL, DEFAULT true      | Đang giảm trừ                      |
| created_at     | DateTime    | NOT NULL                    | Thời điểm tạo                      |

### PositionSalary

| Field       | Type                  | Constraints                 | Mô tả            |
| ----------- | --------------------- | --------------------------- | ---------------- |
| id          | UUID                  | PK                          | ID duy nhất      |
| position_id | UUID                  | FK → positions.id, NOT NULL | Chức vụ          |
| grade       | Enum('A','B','C','D') | NOT NULL                    | Bậc lương        |
| min_salary  | Decimal(15,2)         | NOT NULL                    | Lương tối thiểu  |
| mid_salary  | Decimal(15,2)         | NOT NULL                    | Lương trung bình |
| max_salary  | Decimal(15,2)         | NOT NULL                    | Lương tối đa     |
| is_active   | Boolean               | NOT NULL, DEFAULT true      | Đang áp dụng     |
| created_at  | DateTime              | NOT NULL                    | Thời điểm tạo    |

**Unique constraint:** `(position_id, grade)`

### PayrollPeriod

| Field           | Type                                           | Constraints               | Mô tả                   |
| --------------- | ---------------------------------------------- | ------------------------- | ----------------------- |
| id              | UUID                                           | PK                        | ID duy nhất             |
| month           | Integer                                        | NOT NULL, 1-12            | Tháng                   |
| year            | Integer                                        | NOT NULL                  | Năm                     |
| status          | Enum('draft','calculating','confirmed','paid') | NOT NULL, DEFAULT 'draft' | Trạng thái              |
| total_gross     | Decimal(18,2)                                  | NULLABLE                  | Tổng gross toàn công ty |
| total_net       | Decimal(18,2)                                  | NULLABLE                  | Tổng net toàn công ty   |
| total_tax       | Decimal(18,2)                                  | NULLABLE                  | Tổng thuế               |
| total_insurance | Decimal(18,2)                                  | NULLABLE                  | Tổng BHXH (employee)    |
| employee_count  | Integer                                        | NULLABLE                  | Số nhân viên            |
| calculated_at   | DateTime                                       | NULLABLE                  | Thời điểm tính          |
| confirmed_at    | DateTime                                       | NULLABLE                  | Thời điểm confirm       |
| paid_at         | DateTime                                       | NULLABLE                  | Thời điểm trả lương     |
| created_by      | UUID                                           | FK → users.id             | Người tạo               |
| created_at      | DateTime                                       | NOT NULL                  | Thời điểm tạo           |

**Unique constraint:** `(month, year)`

### Payslip

| Field                  | Type          | Constraints                       | Mô tả                   |
| ---------------------- | ------------- | --------------------------------- | ----------------------- |
| id                     | UUID          | PK                                | ID duy nhất             |
| period_id              | UUID          | FK → payroll_periods.id, NOT NULL | Kỳ lương                |
| employee_id            | UUID          | FK → employees.id, NOT NULL       | Nhân viên               |
| gross_salary           | Decimal(15,2) | NOT NULL                          | Lương gross config      |
| actual_work_days       | Integer       | NOT NULL                          | Số ngày công thực tế    |
| actual_gross           | Decimal(15,2) | NOT NULL                          | Gross thực nhận         |
| total_allowances       | Decimal(15,2) | NOT NULL, DEFAULT 0               | Tổng phụ cấp chịu thuế  |
| non_taxable_allowances | Decimal(15,2) | NOT NULL, DEFAULT 0               | Phụ cấp không chịu thuế |
| total_ot_hours         | Float         | NOT NULL, DEFAULT 0               | Tổng giờ OT             |
| total_ot_amount        | Decimal(15,2) | NOT NULL, DEFAULT 0               | Tổng tiền OT            |
| insurance_salary       | Decimal(15,2) | NOT NULL                          | Lương đóng BHXH         |
| insurance_premium      | Decimal(15,2) | NOT NULL                          | Tiền BHXH (employee)    |
| personal_deduction     | Decimal(15,2) | NOT NULL                          | Giảm trừ bản thân       |
| dependent_count        | Integer       | NOT NULL, DEFAULT 0               | Số người phụ thuộc      |
| dependent_deduction    | Decimal(15,2) | NOT NULL, DEFAULT 0               | Giảm trừ NPT            |
| taxable_income         | Decimal(15,2) | NOT NULL                          | Thu nhập chịu thuế      |
| income_tax             | Decimal(15,2) | NOT NULL                          | Thuế TNCN               |
| net_salary             | Decimal(15,2) | NOT NULL                          | Lương net               |
| pdf_object_key         | String(500)   | NULLABLE                          | MinIO key cho PDF       |
| email_sent_at          | DateTime      | NULLABLE                          | Thời điểm gửi email     |
| created_at             | DateTime      | NOT NULL                          | Thời điểm tạo           |

**Unique constraint:** `(period_id, employee_id)`

## 6. State Machine

### Payroll Period Status

```
┌───────┐     calculate      ┌─────────────┐     (auto back)    ┌───────┐
│ draft │ ──────────────────► │ calculating │ ──────────────────► │ draft │
└───┬───┘                    └─────────────┘                    └───┬───┘
    │                                                               │
    │  (re-calculate allowed when draft)                            │
    │                                                               │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    │ confirm
                                    ▼
                            ┌─────────────┐
                            │  confirmed  │
                            └──────┬──────┘
                                   │ mark paid
                                   ▼
                            ┌─────────────┐
                            │    paid     │
                            └─────────────┘
```

**Rules:**

- `draft` → `calculating`: khi bắt đầu tính lương
- `calculating` → `draft`: khi tính xong (có thể tính lại)
- `draft` → `confirmed`: admin xác nhận bảng lương đúng
- `confirmed` → `paid`: đã chuyển lương cho nhân viên
- `paid` là terminal state — KHÔNG thể rollback

**Forbidden:**

- `confirmed` → `draft` (không thể un-confirm)
- `paid` → bất kỳ status nào

## 7. API Endpoints

### Payroll Periods

| Method | Path                                      | Mô tả                        | Auth  |
| ------ | ----------------------------------------- | ---------------------------- | ----- |
| GET    | `/api/payroll/periods`                    | Danh sách kỳ lương           | Admin |
| POST   | `/api/payroll/periods`                    | Tạo kỳ lương mới             | Admin |
| GET    | `/api/payroll/periods/{id}`               | Chi tiết kỳ lương + payslips | Admin |
| POST   | `/api/payroll/periods/{id}/calculate`     | Tính lương cho tất cả NV     | Admin |
| POST   | `/api/payroll/periods/{id}/confirm`       | Xác nhận bảng lương          | Admin |
| POST   | `/api/payroll/periods/{id}/mark-paid`     | Đánh dấu đã trả lương        | Admin |
| POST   | `/api/payroll/periods/{id}/send-payslips` | Gửi email payslips           | Admin |

### Payslips

| Method | Path                             | Mô tả                | Auth  |
| ------ | -------------------------------- | -------------------- | ----- |
| GET    | `/api/payroll/payslips/{id}`     | Chi tiết payslip     | Admin |
| GET    | `/api/payroll/payslips/{id}/pdf` | Download PDF payslip | Admin |

### Salary Configuration

| Method | Path                                           | Mô tả                      | Auth  |
| ------ | ---------------------------------------------- | -------------------------- | ----- |
| GET    | `/api/payroll/salary/configs`                  | Danh sách salary configs   | Admin |
| GET    | `/api/payroll/salary/configs/{employee_id}`    | Config của nhân viên       | Admin |
| POST   | `/api/payroll/salary/configs`                  | Tạo/cập nhật salary config | Admin |
| GET    | `/api/payroll/salary/allowances/{employee_id}` | Phụ cấp của nhân viên      | Admin |
| POST   | `/api/payroll/salary/allowances`               | Thêm phụ cấp               | Admin |
| PUT    | `/api/payroll/salary/allowances/{id}`          | Cập nhật phụ cấp           | Admin |
| DELETE | `/api/payroll/salary/allowances/{id}`          | Xóa phụ cấp                | Admin |
| GET    | `/api/payroll/salary/dependents/{employee_id}` | Người phụ thuộc            | Admin |
| POST   | `/api/payroll/salary/dependents`               | Thêm người phụ thuộc       | Admin |
| PUT    | `/api/payroll/salary/dependents/{id}`          | Cập nhật NPT               | Admin |
| DELETE | `/api/payroll/salary/dependents/{id}`          | Xóa NPT                    | Admin |
| GET    | `/api/payroll/salary/position-salaries`        | Bảng lương theo chức vụ    | Admin |
| POST   | `/api/payroll/salary/position-salaries`        | Tạo salary band            | Admin |
| PUT    | `/api/payroll/salary/position-salaries/{id}`   | Cập nhật salary band       | Admin |

## 8. Edge Cases & Error Handling

| Scenario                             | Xử lý                                                  |
| ------------------------------------ | ------------------------------------------------------ |
| Employee không có salary_config      | Skip employee, ghi warning trong period                |
| Period đã tồn tại (month/year)       | 409 `PERIOD_ALREADY_EXISTS`                            |
| Calculate khi status ≠ draft         | 409 `PERIOD_NOT_IN_DRAFT`                              |
| Confirm khi chưa calculate           | 400 `PERIOD_NOT_CALCULATED`                            |
| Mark paid khi chưa confirm           | 400 `PERIOD_NOT_CONFIRMED`                             |
| Taxable income âm                    | Set taxable_income = 0, income_tax = 0                 |
| Employee không có attendance records | actual_work_days = 0, actual_gross = 0                 |
| Dependent effective_to đã qua        | Không tính vào deduction                               |
| Allowance is_active = false          | Không tính vào payslip                                 |
| PDF generation fail                  | Log error, payslip vẫn tạo nhưng pdf_object_key = NULL |
| Email send fail (partial)            | Trả về `{sent: N, failed: M, errors: [...]}`           |
| Gross salary = 0                     | Tạo payslip với tất cả = 0                             |
| Insurance salary > gross             | Cho phép (edge case hợp lệ theo luật)                  |

## 9. Integration Points

| Module              | Cách tích hợp                                      |
| ------------------- | -------------------------------------------------- |
| **Attendance**      | Query attendance_records để đếm actual_work_days   |
| **Attendance (OT)** | Query approved overtime_requests để tính OT amount |
| **Employee**        | Lấy employee info, hire_date, department, position |
| **Gmail**           | Gửi batch email payslips qua Gmail API             |
| **MinIO**           | Lưu PDF payslips                                   |
| **Self-Service**    | Employee xem payslip qua ESS                       |
| **Identity**        | Admin auth, audit logging                          |

## 10. Configuration

| Env Variable                      | Default    | Mô tả                       |
| --------------------------------- | ---------- | --------------------------- |
| `PAYROLL_PERSONAL_DEDUCTION`      | `11000000` | Giảm trừ bản thân (VND)     |
| `PAYROLL_DEPENDENT_DEDUCTION`     | `4400000`  | Giảm trừ NPT (VND/người)    |
| `PAYROLL_EMPLOYEE_INSURANCE_RATE` | `0.105`    | Tỷ lệ BHXH employee (10.5%) |
| `PAYROLL_EMPLOYER_INSURANCE_RATE` | `0.215`    | Tỷ lệ BHXH employer (21.5%) |
| `PAYROLL_WORK_DAYS_PER_MONTH`     | `26`       | Số ngày công/tháng          |
| `PAYROLL_WORK_HOURS_PER_DAY`      | `8`        | Số giờ/ngày                 |
| `PAYROLL_OT_RATE_WEEKDAY`         | `1.5`      | Hệ số OT ngày thường        |
| `PAYROLL_OT_RATE_WEEKEND`         | `2.0`      | Hệ số OT cuối tuần          |
| `PAYROLL_OT_RATE_HOLIDAY`         | `3.0`      | Hệ số OT ngày lễ            |
| `PAYROLL_PDF_TEMPLATE`            | `default`  | Template PDF payslip        |
| `PAYROLL_MINIO_BUCKET`            | `payslips` | MinIO bucket cho PDF        |
