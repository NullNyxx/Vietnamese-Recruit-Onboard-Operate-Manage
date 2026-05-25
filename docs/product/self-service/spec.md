# Employee Self-Service (ESS) — Feature Spec

## 1. Tổng quan

Module Employee Self-Service (ESS) cung cấp cổng thông tin cho nhân viên tự phục vụ: xem/cập nhật thông tin cá nhân (giới hạn), chấm công, xem lịch sử chấm công, quản lý nghỉ phép và tăng ca, xem tài liệu cá nhân, và dashboard tổng hợp. Tất cả thao tác được audit logging và rate limiting per endpoint.

## 2. Actors

| Actor                   | Mô tả                                                              |
| ----------------------- | ------------------------------------------------------------------ |
| **Employee**            | Nhân viên đã đăng nhập, có `employee_id` liên kết với User account |
| **System (Middleware)** | Audit middleware ghi log mọi ESS access                            |

## 3. Luồng hoạt động (User Flows)

### 3.1 Authentication & Employee Linking

```
Employee                    Backend                    Database
 │                            │                          │
 │── ANY /api/v1/ess/* ──────►│                          │
 │   (cookie: access_token)   │── Extract user_id from JWT│
 │                            │── Find employee by ──────►│
 │                            │   user.email = employee.email│
 │                            │                          │
 │                            │── IF no employee found:   │
 │◄─ 403 NO_EMPLOYEE_LINK ───│                          │
 │                            │                          │
 │                            │── ELSE: inject employee_id│
 │                            │   into request context    │
 │                            │── Continue to handler     │
```

### 3.2 Profile View (Masked Fields)

```
Employee                    Backend                    Database
 │                            │                          │
 │── GET /api/v1/ess/profile ►│                          │
 │                            │── Get employee ──────────►│
 │                            │── Mask sensitive fields:  │
 │                            │   id_number: "****1234"   │
 │                            │   tax_code: "****5678"    │
 │                            │── Return masked profile   │
 │◄─ 200 {profile} ──────────│                          │
```

### 3.3 Profile Update (Limited Fields)

```
Employee                    Backend                    Database
 │                            │                          │
 │── PUT /api/v1/ess/profile  │                          │
 │   {phone: "0901234567",    │                          │
 │    address: "123 ABC"} ───►│── Validate allowed fields│
 │                            │   (phone, address,        │
 │                            │    emergency_contact ONLY)│
 │                            │── IF other fields present:│
 │◄─ 403 FIELD_NOT_ALLOWED ──│                          │
 │                            │                          │
 │                            │── ELSE: update ──────────►│
 │◄─ 200 {updated_profile} ──│                          │
```

### 3.4 Self Check-in/Check-out

```
Employee                    Backend                    Database
 │                            │                          │
 │── POST /api/v1/ess/        │                          │
 │   attendance/check-in ────►│── Get employee's schedule │
 │                            │── Get current time        │
 │                            │── Determine status:       │
 │                            │   present / late          │
 │                            │── Create/update record ──►│
 │◄─ 200 {record} ───────────│                          │
 │                            │                          │
 │── POST /api/v1/ess/        │                          │
 │   attendance/check-out ───►│── Get today's record      │
 │                            │── Determine status:       │
 │                            │   keep / early_leave      │
 │                            │── Update record ─────────►│
 │◄─ 200 {record} ───────────│                          │
```

### 3.5 Leave Request Flow

```
Employee                    Backend                    Database
 │                            │                          │
 │── GET /api/v1/ess/         │                          │
 │   leave/balances ─────────►│── Get balances for ──────►│
 │                            │   current year            │
 │◄─ 200 [{type, total,      │                          │
 │    used, remaining}] ──────│                          │
 │                            │                          │
 │── POST /api/v1/ess/        │                          │
 │   leave/requests           │                          │
 │   {type_id, start_date,    │── Validate:              │
 │    end_date, reason} ─────►│   - start ≥ today        │
 │                            │   - balance sufficient    │
 │                            │   - no overlap            │
 │                            │── Create request ────────►│
 │                            │   (status: pending)       │
 │◄─ 201 {request} ──────────│                          │
 │                            │                          │
 │── PUT /api/v1/ess/         │                          │
 │   leave/requests/{id}/     │                          │
 │   cancel ─────────────────►│── Validate:              │
 │                            │   - request belongs to me │
 │                            │   - status = pending      │
 │                            │── Update → cancelled ────►│
 │◄─ 200 OK ─────────────────│                          │
```

### 3.6 Dashboard

```
Employee                    Backend                    Database
 │                            │                          │
 │── GET /api/v1/ess/         │                          │
 │   dashboard ──────────────►│── Query multiple sources:│
 │                            │   ├─ Today's attendance ─►│
 │                            │   ├─ Pending leave count ►│
 │                            │   ├─ Pending OT count ──►│
 │                            │   ├─ Monthly summary ───►│
 │                            │   └─ Annual leave left ─►│
 │◄─ 200 {                   │                          │
 │    today_status,           │                          │
 │    pending_leave_count,    │                          │
 │    pending_ot_count,       │                          │
 │    monthly_summary: {      │                          │
 │      work_days, late,      │                          │
 │      absent, ot_hours      │                          │
 │    },                      │                          │
 │    annual_leave_remaining  │                          │
 │   } ──────────────────────│                          │
```

## 4. Business Rules

### Authentication & Authorization

1. **BR-01**: Employee identity xác định bằng: JWT → user_id → user.email → employee.email match.
2. **BR-02**: Nếu user không có employee record liên kết → 403 `NO_EMPLOYEE_LINK`.
3. **BR-03**: Employee chỉ truy cập được data của chính mình (employee_id from JWT context).
4. **BR-04**: Rate limiting per endpoint per employee (tránh abuse).

### Profile

5. **BR-05**: Sensitive fields masked khi hiển thị:
   - `id_number`: hiển thị 4 ký tự cuối, phần còn lại thay bằng `*` (e.g., `****1234`)
   - `tax_code`: hiển thị 4 ký tự cuối (e.g., `****5678`)
6. **BR-06**: Chỉ cho phép update 3 fields: `phone`, `address`, `emergency_contact`.
7. **BR-07**: Cố gắng update field khác (name, email, id_number, etc.) → 403 `FIELD_NOT_ALLOWED`.

### Attendance

8. **BR-08**: Self check-in/out logic giống admin check-in/out (cùng status determination).
9. **BR-09**: Employee chỉ xem attendance history của mình.
10. **BR-10**: Monthly attendance summary: tổng ngày công, trễ, vắng, OT hours.

### Leave

11. **BR-11**: Không thể submit leave request cho ngày trong quá khứ (start_date ≥ today).
12. **BR-12**: Balance check: remaining_days ≥ requested_days (trừ unpaid/sick).
13. **BR-13**: Chỉ cancel được request có status `pending` và thuộc về mình.
14. **BR-14**: Xem tất cả leave requests của mình (mọi status).

### Overtime

15. **BR-15**: Submit OT request: validate daily limit (4h) và weekly limit (20h).
16. **BR-16**: Xem history OT requests của mình.
17. **BR-17**: Không thể cancel/edit OT request đã approved/rejected.

### Documents

18. **BR-18**: Employee chỉ xem (read-only) tài liệu của mình.
19. **BR-19**: Không thể upload/delete documents qua ESS (chỉ admin).

### Schedule

20. **BR-20**: Xem work schedule hiện tại và danh sách holidays sắp tới.

### Audit

21. **BR-21**: Audit middleware log mọi ESS request: method, path, employee_id, response status, duration (ms).
22. **BR-22**: Audit logs không expose cho employee (chỉ admin xem).

## 5. Data Model

Module ESS không có entities riêng — sử dụng entities từ các module khác:

| Entity (from module)          | Cách sử dụng trong ESS      |
| ----------------------------- | --------------------------- |
| Employee (employee)           | Profile view/update         |
| AttendanceRecord (attendance) | Check-in/out, history       |
| LeaveBalance (attendance)     | View balances               |
| LeaveRequest (attendance)     | Submit/cancel/view requests |
| OvertimeRequest (attendance)  | Submit/view OT requests     |
| EmployeeDocument (employee)   | View documents (read-only)  |
| WorkSchedule (attendance)     | View schedule               |
| Holiday (attendance)          | View upcoming holidays      |

### Audit Middleware Data (logged per request)

| Field       | Type     | Mô tả                            |
| ----------- | -------- | -------------------------------- |
| method      | String   | HTTP method (GET, POST, PUT)     |
| path        | String   | Request path                     |
| employee_id | UUID     | Employee making the request      |
| user_id     | UUID     | User ID from JWT                 |
| status_code | Integer  | Response HTTP status             |
| duration_ms | Float    | Request duration in milliseconds |
| ip_address  | String   | Client IP                        |
| timestamp   | DateTime | Request timestamp                |

## 6. State Machine

ESS không có state machine riêng — sử dụng state machines từ:

- **Leave Request**: pending → approved/rejected/cancelled (xem Attendance spec)
- **Overtime Request**: pending → approved/rejected (xem Attendance spec)

### ESS-specific constraints:

- Employee chỉ có thể trigger: `pending → cancelled` (cancel own request)
- Employee KHÔNG thể: approve, reject, hoặc modify approved/rejected requests

## 7. API Endpoints

### Profile

| Method | Path                  | Mô tả                                    | Auth     |
| ------ | --------------------- | ---------------------------------------- | -------- |
| GET    | `/api/v1/ess/profile` | Xem profile (masked sensitive fields)    | Employee |
| PUT    | `/api/v1/ess/profile` | Cập nhật phone/address/emergency_contact | Employee |

### Attendance

| Method | Path                               | Mô tả                      | Auth     |
| ------ | ---------------------------------- | -------------------------- | -------- |
| POST   | `/api/v1/ess/attendance/check-in`  | Self check-in              | Employee |
| POST   | `/api/v1/ess/attendance/check-out` | Self check-out             | Employee |
| GET    | `/api/v1/ess/attendance/history`   | Monthly attendance history | Employee |
| GET    | `/api/v1/ess/attendance/today`     | Today's attendance status  | Employee |

### Leave

| Method | Path                                     | Mô tả                             | Auth     |
| ------ | ---------------------------------------- | --------------------------------- | -------- |
| GET    | `/api/v1/ess/leave/balances`             | Xem leave balances (current year) | Employee |
| GET    | `/api/v1/ess/leave/requests`             | Danh sách leave requests của mình | Employee |
| POST   | `/api/v1/ess/leave/requests`             | Submit leave request              | Employee |
| PUT    | `/api/v1/ess/leave/requests/{id}/cancel` | Cancel pending request            | Employee |

### Overtime

| Method | Path                            | Mô tả                          | Auth     |
| ------ | ------------------------------- | ------------------------------ | -------- |
| GET    | `/api/v1/ess/overtime/requests` | Danh sách OT requests của mình | Employee |
| POST   | `/api/v1/ess/overtime/requests` | Submit OT request              | Employee |

### Documents

| Method | Path                                  | Mô tả                       | Auth     |
| ------ | ------------------------------------- | --------------------------- | -------- |
| GET    | `/api/v1/ess/documents`               | Danh sách tài liệu của mình | Employee |
| GET    | `/api/v1/ess/documents/{id}/download` | Download tài liệu           | Employee |

### Schedule

| Method | Path                   | Mô tả                      | Auth     |
| ------ | ---------------------- | -------------------------- | -------- |
| GET    | `/api/v1/ess/schedule` | Work schedule hiện tại     | Employee |
| GET    | `/api/v1/ess/holidays` | Danh sách holidays sắp tới | Employee |

### Dashboard

| Method | Path                    | Mô tả              | Auth     |
| ------ | ----------------------- | ------------------ | -------- |
| GET    | `/api/v1/ess/dashboard` | Dashboard tổng hợp | Employee |

## 8. Edge Cases & Error Handling

| Scenario                               | Xử lý                                                        |
| -------------------------------------- | ------------------------------------------------------------ |
| User không có employee record          | 403 `NO_EMPLOYEE_LINK` — mọi ESS endpoint                    |
| Update field không cho phép            | 403 `FIELD_NOT_ALLOWED` — list allowed fields trong response |
| Check-in 2 lần trong ngày              | Update existing record (idempotent)                          |
| Check-out mà chưa check-in             | 400 `NO_CHECK_IN_TODAY`                                      |
| Leave request ngày quá khứ             | 400 `CANNOT_REQUEST_PAST_DATE`                               |
| Leave balance không đủ                 | 400 `INSUFFICIENT_LEAVE_BALANCE`                             |
| Cancel request đã approved             | 409 `CANNOT_CANCEL_PROCESSED_REQUEST`                        |
| Cancel request không phải của mình     | 403 `NOT_YOUR_REQUEST`                                       |
| OT > 4h/ngày                           | 400 `EXCEEDS_DAILY_OT_LIMIT`                                 |
| OT > 20h/tuần                          | 400 `EXCEEDS_WEEKLY_OT_LIMIT`                                |
| Download document không phải của mình  | 403 `NOT_YOUR_DOCUMENT`                                      |
| Rate limit exceeded                    | 429 `RATE_LIMIT_EXCEEDED`                                    |
| Employee bị deactivate                 | 403 `EMPLOYEE_INACTIVE`                                      |
| Attendance history tháng không có data | 200 với empty array                                          |

## 9. Integration Points

| Module         | Cách tích hợp                                                          |
| -------------- | ---------------------------------------------------------------------- |
| **Identity**   | JWT authentication, user → employee linking by email                   |
| **Employee**   | Read employee profile, documents                                       |
| **Attendance** | Check-in/out, attendance history, leave balances/requests, OT requests |
| **Payroll**    | (Future) View payslips                                                 |

## 10. Configuration

| Env Variable                     | Default                           | Mô tả                                    |
| -------------------------------- | --------------------------------- | ---------------------------------------- |
| `ESS_RATE_LIMIT_PER_MINUTE`      | `60`                              | Max requests per minute per employee     |
| `ESS_RATE_LIMIT_CHECK_IN`        | `5`                               | Max check-in attempts per hour           |
| `ESS_AUDIT_ENABLED`              | `true`                            | Enable/disable audit middleware          |
| `ESS_MASKED_FIELD_VISIBLE_CHARS` | `4`                               | Số ký tự cuối hiển thị cho masked fields |
| `ESS_ALLOWED_UPDATE_FIELDS`      | `phone,address,emergency_contact` | Fields employee được update              |
| `ESS_HOLIDAYS_LOOKAHEAD_DAYS`    | `90`                              | Số ngày hiển thị holidays sắp tới        |
