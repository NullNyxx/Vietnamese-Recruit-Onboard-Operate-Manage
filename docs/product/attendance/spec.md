# Attendance & Leave — Feature Spec

## 1. Tổng quan

Module Attendance & Leave quản lý chấm công, nghỉ phép, tăng ca, lịch làm việc, và ngày lễ. Hỗ trợ check-in/out với tự động xác định trạng thái (đúng giờ/trễ/về sớm), quản lý số ngày phép theo thâm niên (luật lao động Việt Nam), xử lý đơn tăng ca với giới hạn theo ngày/tuần, và báo cáo hàng tháng với export Excel + gửi email tự động.

## 2. Actors

| Actor             | Mô tả                                                               |
| ----------------- | ------------------------------------------------------------------- |
| **HR Admin**      | Quản lý schedules, holidays, approve/reject leave & OT, xem reports |
| **Employee**      | Check-in/out, submit leave/OT requests (qua ESS module)             |
| **System (Cron)** | Auto mark absent (23:00 daily), gửi monthly report (1st of month)   |

## 3. Luồng hoạt động (User Flows)

### 3.1 Check-in/Check-out

```
Employee                    Backend                    Database
 │                            │                          │
 │── POST /api/attendance/    │                          │
 │   check-in ───────────────►│                          │
 │                            │── Get employee schedule   │
 │                            │── Get current time        │
 │                            │── Determine status:       │
 │                            │   IF time ≤ start_time    │
 │                            │     + late_threshold      │
 │                            │     → "present"           │
 │                            │   ELSE                    │
 │                            │     → "late"              │
 │                            │── Create/update record ──►│
 │◄─ 200 {record} ───────────│                          │
 │                            │                          │
 │── POST /api/attendance/    │                          │
 │   check-out ──────────────►│                          │
 │                            │── Get today's record      │
 │                            │── Determine status:       │
 │                            │   IF time ≥ end_time      │
 │                            │     - early_threshold     │
 │                            │     → keep current status │
 │                            │   ELSE                    │
 │                            │     → "early_leave"       │
 │                            │── Update record ─────────►│
 │◄─ 200 {record} ───────────│                          │
```

### 3.2 Leave Request Flow

```
Employee                    Backend                    Database        Admin
 │                            │                          │               │
 │── POST /api/attendance/    │                          │               │
 │   leave/requests           │                          │               │
 │   {type, start, end,       │── Validate dates         │               │
 │    reason} ───────────────►│── Check balance ─────────►│               │
 │                            │── Check no overlap ──────►│               │
 │                            │── Create request ────────►│               │
 │                            │   (status: pending)       │               │
 │◄─ 201 {request} ──────────│                          │               │
 │                            │                          │               │
 │                            │                          │               │
 │                            │◄─ GET /leave/requests ───────────────────│
 │                            │── Return pending list ───────────────────►│
 │                            │                          │               │
 │                            │◄─ PUT /leave/requests/{id}/approve ──────│
 │                            │── Update status → approved│               │
 │                            │── Deduct balance ────────►│               │
 │◄─ (notification) ─────────│                          │               │
```

### 3.3 Overtime Request Flow

```
Employee                    Backend                    Database        Admin
 │                            │                          │               │
 │── POST /api/attendance/    │                          │               │
 │   overtime/requests        │                          │               │
 │   {date, hours, reason} ──►│── Validate:              │               │
 │                            │   hours ≤ 4 (daily max)  │               │
 │                            │   week_total ≤ 20 ───────►│               │
 │                            │── Create request ────────►│               │
 │                            │   (status: pending)       │               │
 │◄─ 201 {request} ──────────│                          │               │
 │                            │                          │               │
 │                            │◄─ PUT /overtime/{id}/approve ───────────│
 │                            │── Update status → approved│               │
 │◄─ (notification) ─────────│                          │               │
```

### 3.4 Auto Mark Absent (Cron 23:00)

```
System (Cron)               Backend                    Database
 │                            │                          │
 │── Trigger 23:00 daily ────►│                          │
 │                            │── Get today's date        │
 │                            │── Check if holiday ──────►│
 │                            │   IF holiday → skip       │
 │                            │── Get all active employees│
 │                            │── For each employee:      │
 │                            │   ├─ Has attendance? skip │
 │                            │   ├─ Has approved leave?  │
 │                            │   │  skip                 │
 │                            │   └─ ELSE: mark absent ──►│
 │◄─ Done (N marked) ────────│                          │
```

### 3.5 Monthly Report (Cron 1st of month)

```
System (Cron)               Backend                    Database        Email
 │                            │                          │               │
 │── Trigger 1st of month ───►│                          │               │
 │                            │── Get previous month      │               │
 │                            │── Query all records ─────►│               │
 │                            │── Calculate summaries:    │               │
 │                            │   - Total work days       │               │
 │                            │   - Present/late/absent   │               │
 │                            │   - Leave days used       │               │
 │                            │   - OT hours              │               │
 │                            │── Generate Excel report   │               │
 │                            │── Send to HR admins ─────────────────────►│
 │◄─ Done ────────────────────│                          │               │
```

## 4. Business Rules

### Attendance

1. **BR-01**: Status determination dựa trên work schedule:
   - `present`: check-in ≤ start_time + late_threshold (default 15 min)
   - `late`: check-in > start_time + late_threshold
   - `early_leave`: check-out < end_time - early_leave_threshold (default 15 min)
   - `absent`: không có record (marked by cron)
2. **BR-02**: Mỗi nhân viên chỉ có 1 attendance record per ngày.
3. **BR-03**: Không thể check-in 2 lần trong 1 ngày (update existing record).
4. **BR-04**: Auto mark absent chạy lúc 23:00, skip ngày lễ và nhân viên có approved leave.

### Leave

5. **BR-05**: Số ngày phép năm = 12 (base) + 1 ngày cho mỗi 5 năm thâm niên (luật lao động VN).
6. **BR-06**: Leave types: `annual`, `sick`, `unpaid`, `maternity`, `wedding`, `funeral`, `personal`.
7. **BR-07**: Không thể submit leave request cho ngày trong quá khứ.
8. **BR-08**: Leave request không được overlap với request đã approved.
9. **BR-09**: Balance check: remaining_days ≥ requested_days (trừ `unpaid` và `sick`).
10. **BR-10**: Balance bị trừ khi request được approve, hoàn lại khi reject/cancel.
11. **BR-11**: Max carry-over: 5 ngày phép năm chuyển sang năm sau.

### Overtime

12. **BR-12**: Giới hạn OT per ngày: tối đa 4 giờ.
13. **BR-13**: Giới hạn OT per tuần: tối đa 20 giờ.
14. **BR-14**: OT rates: weekday 1.5x, weekend 2.0x, holiday 3.0x (dùng cho payroll).
15. **BR-15**: Chỉ approved overtime_requests mới được tính vào payroll (KHÔNG dùng attendance_records.overtime_hours).

### Schedule & Holidays

16. **BR-16**: Work schedule mặc định: 08:00 - 17:00, break 60 phút.
17. **BR-17**: Holidays có 2 loại: recurring (hàng năm, e.g., 1/1, 30/4) và one-time.
18. **BR-18**: Ngày lễ không tính là ngày absent.

## 5. Data Model

### WorkSchedule

| Field                         | Type        | Constraints             | Mô tả                            |
| ----------------------------- | ----------- | ----------------------- | -------------------------------- |
| id                            | UUID        | PK                      | ID duy nhất                      |
| name                          | String(255) | NOT NULL                | Tên lịch (e.g., "Ca hành chính") |
| start_time                    | Time        | NOT NULL                | Giờ bắt đầu                      |
| end_time                      | Time        | NOT NULL                | Giờ kết thúc                     |
| break_minutes                 | Integer     | NOT NULL, DEFAULT 60    | Thời gian nghỉ trưa (phút)       |
| late_threshold_minutes        | Integer     | NOT NULL, DEFAULT 15    | Ngưỡng tính trễ (phút)           |
| early_leave_threshold_minutes | Integer     | NOT NULL, DEFAULT 15    | Ngưỡng tính về sớm (phút)        |
| is_default                    | Boolean     | NOT NULL, DEFAULT false | Lịch mặc định                    |
| is_active                     | Boolean     | NOT NULL, DEFAULT true  | Còn sử dụng                      |
| created_at                    | DateTime    | NOT NULL                | Thời điểm tạo                    |

### AttendanceRecord

| Field          | Type                                                     | Constraints                 | Mô tả                       |
| -------------- | -------------------------------------------------------- | --------------------------- | --------------------------- |
| id             | UUID                                                     | PK                          | ID duy nhất                 |
| employee_id    | UUID                                                     | FK → employees.id, NOT NULL | Nhân viên                   |
| date           | Date                                                     | NOT NULL                    | Ngày chấm công              |
| check_in_time  | DateTime                                                 | NULLABLE                    | Giờ check-in                |
| check_out_time | DateTime                                                 | NULLABLE                    | Giờ check-out               |
| status         | Enum('present','late','early_leave','absent','on_leave') | NOT NULL                    | Trạng thái                  |
| overtime_hours | Float                                                    | DEFAULT 0                   | Giờ OT (informational only) |
| notes          | Text                                                     | NULLABLE                    | Ghi chú                     |
| schedule_id    | UUID                                                     | FK → work_schedules.id      | Lịch áp dụng                |
| created_at     | DateTime                                                 | NOT NULL                    | Thời điểm tạo               |
| updated_at     | DateTime                                                 | NOT NULL                    | Thời điểm cập nhật          |

**Unique constraint:** `(employee_id, date)`

### LeaveType

| Field             | Type        | Constraints            | Mô tả                        |
| ----------------- | ----------- | ---------------------- | ---------------------------- |
| id                | UUID        | PK                     | ID duy nhất                  |
| name              | String(100) | UNIQUE, NOT NULL       | Tên loại phép                |
| code              | String(20)  | UNIQUE, NOT NULL       | Mã (annual, sick, unpaid...) |
| max_days_per_year | Integer     | NULLABLE               | Số ngày tối đa/năm           |
| is_paid           | Boolean     | NOT NULL, DEFAULT true | Có lương hay không           |
| requires_balance  | Boolean     | NOT NULL, DEFAULT true | Cần kiểm tra balance         |
| is_active         | Boolean     | NOT NULL, DEFAULT true | Còn sử dụng                  |

### LeaveBalance

| Field          | Type    | Constraints                   | Mô tả                       |
| -------------- | ------- | ----------------------------- | --------------------------- |
| id             | UUID    | PK                            | ID duy nhất                 |
| employee_id    | UUID    | FK → employees.id, NOT NULL   | Nhân viên                   |
| leave_type_id  | UUID    | FK → leave_types.id, NOT NULL | Loại phép                   |
| year           | Integer | NOT NULL                      | Năm áp dụng                 |
| total_days     | Float   | NOT NULL                      | Tổng số ngày được phép      |
| used_days      | Float   | NOT NULL, DEFAULT 0           | Số ngày đã dùng             |
| remaining_days | Float   | NOT NULL                      | Số ngày còn lại             |
| carried_over   | Float   | DEFAULT 0                     | Số ngày chuyển từ năm trước |

**Unique constraint:** `(employee_id, leave_type_id, year)`

### LeaveRequest

| Field            | Type                                              | Constraints                   | Mô tả              |
| ---------------- | ------------------------------------------------- | ----------------------------- | ------------------ |
| id               | UUID                                              | PK                            | ID duy nhất        |
| employee_id      | UUID                                              | FK → employees.id, NOT NULL   | Nhân viên          |
| leave_type_id    | UUID                                              | FK → leave_types.id, NOT NULL | Loại phép          |
| start_date       | Date                                              | NOT NULL                      | Ngày bắt đầu       |
| end_date         | Date                                              | NOT NULL                      | Ngày kết thúc      |
| total_days       | Float                                             | NOT NULL                      | Tổng số ngày nghỉ  |
| reason           | Text                                              | NULLABLE                      | Lý do              |
| status           | Enum('pending','approved','rejected','cancelled') | NOT NULL, DEFAULT 'pending'   | Trạng thái         |
| approved_by      | UUID                                              | FK → users.id, NULLABLE       | Người duyệt        |
| approved_at      | DateTime                                          | NULLABLE                      | Thời điểm duyệt    |
| rejection_reason | Text                                              | NULLABLE                      | Lý do từ chối      |
| created_at       | DateTime                                          | NOT NULL                      | Thời điểm tạo      |
| updated_at       | DateTime                                          | NOT NULL                      | Thời điểm cập nhật |

### OvertimeRequest

| Field       | Type                                  | Constraints                 | Mô tả              |
| ----------- | ------------------------------------- | --------------------------- | ------------------ |
| id          | UUID                                  | PK                          | ID duy nhất        |
| employee_id | UUID                                  | FK → employees.id, NOT NULL | Nhân viên          |
| date        | Date                                  | NOT NULL                    | Ngày tăng ca       |
| hours       | Float                                 | NOT NULL, CHECK > 0 AND ≤ 4 | Số giờ OT          |
| reason      | Text                                  | NULLABLE                    | Lý do              |
| status      | Enum('pending','approved','rejected') | NOT NULL, DEFAULT 'pending' | Trạng thái         |
| approved_by | UUID                                  | FK → users.id, NULLABLE     | Người duyệt        |
| approved_at | DateTime                              | NULLABLE                    | Thời điểm duyệt    |
| is_weekend  | Boolean                               | NOT NULL, DEFAULT false     | Ngày cuối tuần     |
| is_holiday  | Boolean                               | NOT NULL, DEFAULT false     | Ngày lễ            |
| created_at  | DateTime                              | NOT NULL                    | Thời điểm tạo      |
| updated_at  | DateTime                              | NOT NULL                    | Thời điểm cập nhật |

### Holiday

| Field        | Type        | Constraints             | Mô tả            |
| ------------ | ----------- | ----------------------- | ---------------- |
| id           | UUID        | PK                      | ID duy nhất      |
| name         | String(255) | NOT NULL                | Tên ngày lễ      |
| date         | Date        | NOT NULL                | Ngày lễ          |
| is_recurring | Boolean     | NOT NULL, DEFAULT false | Lặp lại hàng năm |
| description  | Text        | NULLABLE                | Mô tả            |
| created_at   | DateTime    | NOT NULL                | Thời điểm tạo    |

## 6. State Machine

### Leave Request Status

```
┌─────────┐
│ pending │
└────┬────┘
     │
     ├──── approve ────► ┌──────────┐
     │                   │ approved │
     │                   └──────────┘
     │
     ├──── reject ─────► ┌──────────┐
     │                   │ rejected │
     │                   └──────────┘
     │
     └──── cancel ─────► ┌───────────┐
           (by employee)  │ cancelled │
                         └───────────┘
```

**Rules:**

- Chỉ `pending` mới có thể approve/reject/cancel
- Employee chỉ cancel được request của mình
- Admin approve/reject bất kỳ pending request

### Overtime Request Status

```
┌─────────┐
│ pending │
└────┬────┘
     │
     ├──── approve ────► ┌──────────┐
     │                   │ approved │
     │                   └──────────┘
     │
     └──── reject ─────► ┌──────────┐
                         │ rejected │
                         └──────────┘
```

## 7. API Endpoints

### Attendance

| Method | Path                                    | Mô tả                                     | Auth           |
| ------ | --------------------------------------- | ----------------------------------------- | -------------- |
| POST   | `/api/attendance/check-in`              | Check-in cho employee                     | Admin/Employee |
| POST   | `/api/attendance/check-out`             | Check-out cho employee                    | Admin/Employee |
| GET    | `/api/attendance/records`               | Danh sách records (paginated, filterable) | Admin          |
| GET    | `/api/attendance/records/{employee_id}` | Records của 1 nhân viên                   | Admin          |
| POST   | `/api/attendance/records`               | Tạo manual record                         | Admin          |
| PUT    | `/api/attendance/records/{id}`          | Sửa record                                | Admin          |
| GET    | `/api/attendance/reports/monthly`       | Báo cáo tháng                             | Admin          |
| GET    | `/api/attendance/reports/export`        | Export Excel                              | Admin          |

### Leave

| Method | Path                                           | Mô tả                           | Auth             |
| ------ | ---------------------------------------------- | ------------------------------- | ---------------- |
| GET    | `/api/attendance/leave/types`                  | Danh sách loại phép             | Admin/Employee   |
| GET    | `/api/attendance/leave/balances/{employee_id}` | Balance của nhân viên           | Admin/Employee   |
| GET    | `/api/attendance/leave/requests`               | Danh sách requests (filterable) | Admin            |
| POST   | `/api/attendance/leave/requests`               | Tạo leave request               | Admin/Employee   |
| PUT    | `/api/attendance/leave/requests/{id}/approve`  | Approve request                 | Admin            |
| PUT    | `/api/attendance/leave/requests/{id}/reject`   | Reject request                  | Admin            |
| PUT    | `/api/attendance/leave/requests/{id}/cancel`   | Cancel request                  | Employee (owner) |

### Overtime

| Method | Path                                             | Mô tả                 | Auth           |
| ------ | ------------------------------------------------ | --------------------- | -------------- |
| GET    | `/api/attendance/overtime/requests`              | Danh sách OT requests | Admin          |
| POST   | `/api/attendance/overtime/requests`              | Tạo OT request        | Admin/Employee |
| PUT    | `/api/attendance/overtime/requests/{id}/approve` | Approve OT            | Admin          |
| PUT    | `/api/attendance/overtime/requests/{id}/reject`  | Reject OT             | Admin          |

### Schedules & Holidays

| Method | Path                             | Mô tả                    | Auth           |
| ------ | -------------------------------- | ------------------------ | -------------- |
| GET    | `/api/attendance/schedules`      | Danh sách work schedules | Admin          |
| POST   | `/api/attendance/schedules`      | Tạo schedule             | Admin          |
| PUT    | `/api/attendance/schedules/{id}` | Cập nhật schedule        | Admin          |
| GET    | `/api/attendance/holidays`       | Danh sách holidays       | Admin/Employee |
| POST   | `/api/attendance/holidays`       | Tạo holiday              | Admin          |
| PUT    | `/api/attendance/holidays/{id}`  | Cập nhật holiday         | Admin          |
| DELETE | `/api/attendance/holidays/{id}`  | Xóa holiday              | Admin          |

## 8. Edge Cases & Error Handling

| Scenario                    | Xử lý                                 |
| --------------------------- | ------------------------------------- |
| Check-in 2 lần trong ngày   | Update existing record, không tạo mới |
| Check-out mà chưa check-in  | 400 `NO_CHECK_IN_RECORD`              |
| Leave request overlap       | 409 `LEAVE_OVERLAP_EXISTS`            |
| Leave balance không đủ      | 400 `INSUFFICIENT_LEAVE_BALANCE`      |
| Leave request ngày quá khứ  | 400 `CANNOT_REQUEST_PAST_DATE`        |
| OT > 4h/ngày                | 400 `EXCEEDS_DAILY_OT_LIMIT`          |
| OT > 20h/tuần               | 400 `EXCEEDS_WEEKLY_OT_LIMIT`         |
| Approve request đã approved | 409 `REQUEST_ALREADY_PROCESSED`       |
| Cancel request đã approved  | 409 `CANNOT_CANCEL_APPROVED_REQUEST`  |
| Xóa schedule đang được dùng | 409 `SCHEDULE_IN_USE`                 |
| Holiday trùng ngày          | 409 `HOLIDAY_DATE_EXISTS`             |
| Cron fail (DB unavailable)  | Retry next cycle, log error           |
| Employee không có schedule  | Dùng default schedule                 |

## 9. Integration Points

| Module           | Cách tích hợp                                                         |
| ---------------- | --------------------------------------------------------------------- |
| **Employee**     | `employee_id` FK, lấy hire_date để tính thâm niên                     |
| **Payroll**      | Attendance records → tính actual_work_days; approved OT → tính OT pay |
| **Self-Service** | Employee check-in/out, view records, submit leave/OT qua ESS          |
| **Gmail**        | Gửi monthly report email cho HR admins                                |
| **Identity**     | Auth middleware, admin role check                                     |

## 10. Configuration

| Env Variable                               | Default | Mô tả                    |
| ------------------------------------------ | ------- | ------------------------ |
| `ATTENDANCE_MAX_CARRY_OVER_DAYS`           | `5`     | Max ngày phép carry-over |
| `ATTENDANCE_ANNUAL_LEAVE_BASE_DAYS`        | `12`    | Số ngày phép cơ bản      |
| `ATTENDANCE_SENIORITY_BONUS_YEARS`         | `5`     | Mỗi N năm +1 ngày phép   |
| `ATTENDANCE_DEFAULT_START_TIME`            | `08:00` | Giờ bắt đầu mặc định     |
| `ATTENDANCE_DEFAULT_END_TIME`              | `17:00` | Giờ kết thúc mặc định    |
| `ATTENDANCE_DEFAULT_BREAK_MINUTES`         | `60`    | Thời gian nghỉ trưa      |
| `ATTENDANCE_LATE_THRESHOLD_MINUTES`        | `15`    | Ngưỡng tính trễ          |
| `ATTENDANCE_EARLY_LEAVE_THRESHOLD_MINUTES` | `15`    | Ngưỡng tính về sớm       |
| `ATTENDANCE_MAX_OT_PER_DAY_HOURS`          | `4.0`   | Max OT per ngày          |
| `ATTENDANCE_MAX_OT_PER_WEEK_HOURS`         | `20.0`  | Max OT per tuần          |
| `ATTENDANCE_OT_RATE_WEEKDAY`               | `1.5`   | Hệ số OT ngày thường     |
| `ATTENDANCE_OT_RATE_WEEKEND`               | `2.0`   | Hệ số OT cuối tuần       |
| `ATTENDANCE_OT_RATE_HOLIDAY`               | `3.0`   | Hệ số OT ngày lễ         |
