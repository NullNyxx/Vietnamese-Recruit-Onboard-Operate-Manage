# Giải Thích Code Module Chấm Công & Nghỉ Phép

> Tài liệu mô tả chi tiết tất cả hàm/class trong module Attendance & Leave.
> Cập nhật lần cuối: 2026-05-01

---

## Sơ Đồ Luồng Dữ Liệu

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ leave.ts │  │attendance.ts │  │ Pages    │  │ Components    │  │
│  └────┬─────┘  └──────┬───────┘  └────┬─────┘  └───────────────┘  │
└───────┼────────────────┼───────────────┼───────────────────────────┘
        │ HTTP           │ HTTP          │
        ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI Routers)                     │
│  ┌────────────┐ ┌──────────────────┐ ┌────────────────┐            │
│  │leave_router│ │attendance_router │ │overtime_router │            │
│  └─────┬──────┘ └────────┬─────────┘ └───────┬────────┘            │
│        │                  │                    │                     │
│  ┌─────┴──────┐          │              ┌─────┴──────┐             │
│  │schedule_   │          │              │error_      │             │
│  │router      │          │              │handler     │             │
│  └────────────┘          │              └────────────┘             │
└───────┼──────────────────┼─────────────────────┼───────────────────┘
        │                  │                     │
        ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER (Services)                       │
│  ┌──────────────┐ ┌──────────────────┐ ┌────────────────┐          │
│  │leave_service │ │attendance_service│ │overtime_service│          │
│  └──────┬───────┘ └────────┬─────────┘ └───────┬────────┘          │
│         │                  │                    │                    │
│  ┌──────┴───────┐  ┌──────┴─────────┐                              │
│  │balance_      │  │export_service  │                              │
│  │service       │  └────────────────┘                              │
│  └──────────────┘                                                   │
└───────┼──────────────────┼─────────────────────┼───────────────────┘
        │                  │                     │
        ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER (Repositories)                 │
│  ┌──────────────────┐ ┌────────────────────┐ ┌──────────────────┐  │
│  │leave_repository  │ │attendance_repository│ │overtime_repository│ │
│  └──────────────────┘ └────────────────────┘ └──────────────────┘  │
│  ┌──────────────────────────────────────┐  ┌─────────────────────┐ │
│  │schedule_repository (Schedule+Holiday)│  │config.py (Settings) │ │
│  └──────────────────────────────────────┘  └─────────────────────┘ │
└───────┼──────────────────┼─────────────────────┼───────────────────┘
        │                  │                     │
        ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER (Entities)                        │
│  entities.py │ enums.py │ exceptions.py                             │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                           │
│  leave_types │ leave_balances │ leave_requests │ attendance_records │
│  work_schedules │ overtime_requests │ holidays                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. DOMAIN LAYER

### 1.1 `src/modules/attendance/domain/entities.py`

Định nghĩa các entity (bảng database) dùng SQLModel.

| Entity | Mô tả | Các trường chính |
|--------|--------|-----------------|
| `LeaveType` | Loại nghỉ phép (phép năm, ốm, không lương...) | `id`, `name`, `display_name`, `default_days_per_year`, `is_paid`, `requires_approval`, `requires_document`, `created_at` |
| `LeaveBalance` | Số ngày phép còn lại của NV theo loại/năm | `id`, `employee_id`, `leave_type_id`, `year`, `total_days`, `used_days`, `remaining_days`, `created_at`, `updated_at` |
| `LeaveRequest` | Đơn xin nghỉ phép | `id`, `employee_id`, `leave_type_id`, `start_date`, `end_date`, `total_days`, `reason`, `status`, `approved_by`, `approved_at`, `rejection_reason`, `created_at`, `updated_at` |
| `WorkSchedule` | Ca làm việc (giờ vào/ra, ngưỡng muộn) | `id`, `name`, `start_time`, `end_time`, `break_minutes`, `late_threshold_minutes`, `early_leave_threshold_minutes`, `is_default`, `created_at` |
| `AttendanceRecord` | Bản ghi chấm công hàng ngày | `id`, `employee_id`, `work_date`, `schedule_id`, `check_in`, `check_out`, `work_hours`, `overtime_hours`, `status`, `note`, `created_at`, `updated_at` |
| `OvertimeRequest` | Đơn đăng ký tăng ca | `id`, `employee_id`, `work_date`, `planned_hours`, `actual_hours`, `reason`, `status`, `approved_by`, `created_at` |
| `Holiday` | Ngày lễ/nghỉ công ty | `id`, `holiday_date`, `name`, `is_recurring`, `created_at` |

**Ràng buộc đặc biệt:**
- `LeaveBalance`: UNIQUE(`employee_id`, `leave_type_id`, `year`)
- `AttendanceRecord`: UNIQUE(`employee_id`, `work_date`)

---

### 1.2 `src/modules/attendance/domain/enums.py`

| Enum | Giá trị | Mô tả |
|------|---------|--------|
| `LeaveStatus` | `pending`, `approved`, `rejected`, `cancelled` | Trạng thái đơn nghỉ phép |
| `LeaveTypeCode` | `annual`, `sick`, `unpaid`, `maternity`, `wedding`, `funeral`, `personal` | Mã loại nghỉ phép theo luật VN |
| `AttendanceStatus` | `present`, `late`, `early_leave`, `absent`, `on_leave`, `holiday` | Trạng thái chấm công |
| `OvertimeStatus` | `pending`, `approved`, `rejected` | Trạng thái đơn OT |

---

### 1.3 `src/modules/attendance/domain/exceptions.py`

| Exception | Error Code | Mô tả |
|-----------|-----------|--------|
| `AttendanceModuleError` | `ATTENDANCE_ERROR` | Lớp cha cho tất cả exception trong module |
| `LeaveTypeNotFoundError` | `LEAVE_TYPE_NOT_FOUND` | Không tìm thấy loại nghỉ phép |
| `LeaveRequestNotFoundError` | `LEAVE_REQUEST_NOT_FOUND` | Không tìm thấy đơn nghỉ phép |
| `InsufficientBalanceError` | `INSUFFICIENT_LEAVE_BALANCE` | Không đủ ngày phép còn lại |
| `LeaveOverlapError` | `LEAVE_OVERLAP` | Đơn nghỉ trùng ngày với đơn đã có |
| `InvalidLeaveStatusTransitionError` | `INVALID_LEAVE_STATUS_TRANSITION` | Chuyển trạng thái không hợp lệ |
| `LeaveDateInPastError` | `LEAVE_DATE_IN_PAST` | Hủy đơn nghỉ đã bắt đầu |
| `AlreadyCheckedInError` | `ALREADY_CHECKED_IN` | Đã check-in hôm nay rồi |
| `NotCheckedInError` | `NOT_CHECKED_IN` | Chưa check-in mà muốn check-out |
| `AlreadyCheckedOutError` | `ALREADY_CHECKED_OUT` | Đã check-out hôm nay rồi |
| `AttendanceRecordNotFoundError` | `ATTENDANCE_RECORD_NOT_FOUND` | Không tìm thấy bản ghi chấm công |
| `OvertimeRequestNotFoundError` | `OVERTIME_REQUEST_NOT_FOUND` | Không tìm thấy đơn OT |
| `OvertimeLimitExceededError` | `OVERTIME_LIMIT_EXCEEDED` | Vượt giới hạn OT tuần |
| `ScheduleNotFoundError` | `SCHEDULE_NOT_FOUND` | Không tìm thấy ca làm việc |
| `EmployeeNotFoundError` | `EMPLOYEE_NOT_FOUND` | Không tìm thấy nhân viên |

---

## 2. INFRASTRUCTURE LAYER

### 2.1 `src/modules/attendance/infrastructure/config.py`

**Class: `AttendanceSettings`** (kế thừa `BaseSettings` từ pydantic-settings)

Cấu hình module chấm công, đọc từ biến môi trường prefix `ATTENDANCE_`.

| Thuộc tính | Kiểu | Mặc định | Mô tả |
|------------|------|----------|--------|
| `max_carry_over_days` | `int` | 5 | Số ngày phép năm tối đa chuyển sang năm sau |
| `annual_leave_base_days` | `int` | 12 | Số ngày phép năm cơ bản (Luật LĐ VN) |
| `seniority_bonus_years` | `int` | 5 | Mỗi N năm thâm niên → +1 ngày phép |
| `default_start_time` | `str` | `"08:00"` | Giờ bắt đầu mặc định |
| `default_end_time` | `str` | `"17:00"` | Giờ kết thúc mặc định |
| `default_break_minutes` | `int` | 60 | Thời gian nghỉ trưa (phút) |
| `late_threshold_minutes` | `int` | 15 | Ngưỡng tính muộn (phút) |
| `early_leave_threshold_minutes` | `int` | 15 | Ngưỡng tính về sớm (phút) |
| `max_ot_per_day_hours` | `float` | 4.0 | Giới hạn OT/ngày |
| `max_ot_per_week_hours` | `float` | 20.0 | Giới hạn OT/tuần |
| `ot_rate_weekday` | `float` | 1.5 | Hệ số OT ngày thường |
| `ot_rate_weekend` | `float` | 2.0 | Hệ số OT cuối tuần |
| `ot_rate_holiday` | `float` | 3.0 | Hệ số OT ngày lễ |

---

### 2.2 `src/modules/attendance/infrastructure/leave_repository.py`

#### Class: `LeaveTypeRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo với DB session | Router |
| `list_all` | — | `list[LeaveType]` | Lấy tất cả loại nghỉ phép, sắp xếp theo tên | `BalanceService.initialize_employee_balance`, `leave_router.list_leave_types` |
| `get_by_id` | `leave_type_id: UUID` | `LeaveType \| None` | Tìm loại nghỉ theo ID | `LeaveService.submit_request` |
| `get_by_name` | `name: str` | `LeaveType \| None` | Tìm loại nghỉ theo mã tên | — |

#### Class: `LeaveBalanceRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | Router |
| `get_by_employee_year` | `employee_id: UUID, year: int` | `list[LeaveBalance]` | Lấy tất cả balance của NV trong năm | `BalanceService.get_employee_balances` |
| `get_balance` | `employee_id: UUID, leave_type_id: UUID, year: int` | `LeaveBalance \| None` | Lấy balance cụ thể (NV + loại + năm) | `BalanceService.check_sufficient_balance`, `BalanceService.initialize_employee_balance` |
| `create` | `balance: LeaveBalance` | `LeaveBalance` | Tạo balance mới | `BalanceService.initialize_employee_balance` |
| `deduct` | `balance_id: UUID, days: Decimal` | `LeaveBalance \| None` | Trừ ngày phép (khi duyệt đơn) | `BalanceService.deduct_balance` |
| `restore` | `balance_id: UUID, days: Decimal` | `LeaveBalance \| None` | Hoàn ngày phép (khi hủy đơn đã duyệt) | `BalanceService.restore_balance` |

#### Class: `LeaveRequestRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | Router |
| `create` | `request: LeaveRequest` | `LeaveRequest` | Tạo đơn nghỉ mới | `LeaveService.submit_request` |
| `get_by_id` | `request_id: UUID` | `LeaveRequest \| None` | Tìm đơn theo ID | `LeaveService.approve/reject/cancel_request` |
| `list_by_employee` | `employee_id: UUID, status?: str, page: int, page_size: int` | `tuple[list[LeaveRequest], int]` | Danh sách đơn của NV (có phân trang) | `LeaveService.list_requests` |
| `list_pending` | `page: int, page_size: int` | `tuple[list[LeaveRequest], int]` | Danh sách đơn chờ duyệt (cho HR) | `LeaveService.list_requests` |
| `check_overlap` | `employee_id: UUID, start_date: date, end_date: date, exclude_id?: UUID` | `bool` | Kiểm tra trùng ngày với đơn đã có | `LeaveService.submit_request` |
| `update` | `request: LeaveRequest` | `LeaveRequest` | Cập nhật đơn nghỉ | `LeaveService.approve/reject/cancel_request` |

---

### 2.3 `src/modules/attendance/infrastructure/attendance_repository.py`

#### Class: `AttendanceRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | `attendance_router` |
| `get_by_employee_date` | `employee_id: UUID, work_date: date` | `AttendanceRecord \| None` | Lấy bản ghi chấm công của NV theo ngày | `AttendanceService.check_in/check_out/get_today/manual_record` |
| `create` | `record: AttendanceRecord` | `AttendanceRecord` | Tạo bản ghi chấm công mới | `AttendanceService.check_in/manual_record` |
| `update` | `record: AttendanceRecord` | `AttendanceRecord` | Cập nhật bản ghi chấm công | `AttendanceService.check_out/manual_record` |
| `get_monthly_report` | `employee_id: UUID, year: int, month: int` | `list[AttendanceRecord]` | Lấy tất cả bản ghi trong tháng của NV | `AttendanceService.get_monthly_report` |
| `get_team_by_date` | `work_date: date, department_id?: UUID` | `list[AttendanceRecord]` | Lấy chấm công toàn bộ NV theo ngày | `AttendanceService.get_team_today` |
| `get_employees_with_records_on_date` | `work_date: date` | `set[UUID]` | Lấy danh sách ID nhân viên đã có bản ghi | Worker (cron job) |
| `bulk_create` | `records: list[AttendanceRecord]` | `None` | Tạo nhiều bản ghi cùng lúc | Worker (cron job) |

---

### 2.4 `src/modules/attendance/infrastructure/overtime_repository.py`

#### Class: `OvertimeRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | `overtime_router` |
| `create` | `request: OvertimeRequest` | `OvertimeRequest` | Tạo đơn OT mới | `OvertimeService.submit_request` |
| `get_by_id` | `request_id: UUID` | `OvertimeRequest \| None` | Tìm đơn OT theo ID | `OvertimeService.approve/reject` |
| `update` | `request: OvertimeRequest` | `OvertimeRequest` | Cập nhật đơn OT | `OvertimeService.approve/reject` |
| `get_weekly_hours` | `employee_id: UUID, reference_date: date` | `Decimal` | Tính tổng giờ OT đã duyệt trong tuần | `OvertimeService.submit_request` |
| `list_by_status` | `status?: str, page: int, page_size: int` | `tuple[list[OvertimeRequest], int]` | Danh sách đơn OT (lọc theo status, phân trang) | `OvertimeService.list_requests` |
| `get_approved_monthly` | `employee_id: UUID, year: int, month: int` | `list[OvertimeRequest]` | Lấy đơn OT đã duyệt trong tháng | — (dự phòng cho tính lương) |

---

### 2.5 `src/modules/attendance/infrastructure/schedule_repository.py`

#### Class: `ScheduleRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | `attendance_router`, `schedule_router` |
| `get_default` | — | `WorkSchedule \| None` | Lấy ca làm việc mặc định (is_default=True) | `AttendanceService.check_in/check_out/manual_record` |
| `get_by_id` | `schedule_id: UUID` | `WorkSchedule \| None` | Tìm ca theo ID | — |
| `list_all` | — | `list[WorkSchedule]` | Danh sách tất cả ca làm việc | `schedule_router.list_schedules` |
| `create` | `schedule: WorkSchedule` | `WorkSchedule` | Tạo ca mới | `schedule_router.create_schedule` |
| `update` | `schedule: WorkSchedule` | `WorkSchedule` | Cập nhật ca | — |

#### Class: `HolidayRepository`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `__init__` | `session: AsyncSession` | — | Khởi tạo | `attendance_router`, `schedule_router` |
| `list_by_year` | `year: int` | `list[Holiday]` | Danh sách ngày lễ trong năm | `schedule_router.list_holidays` |
| `is_holiday` | `check_date: date` | `bool` | Kiểm tra ngày có phải ngày lễ không | `AttendanceService.check_in` |
| `create` | `holiday: Holiday` | `Holiday` | Tạo ngày lễ mới | `schedule_router.create_holiday` |
| `delete` | `holiday_id: UUID` | `None` | Xóa ngày lễ | `schedule_router.delete_holiday` |

---

## 3. APPLICATION LAYER (Services)

### 3.1 `src/modules/attendance/application/balance_service.py`

#### Class: `BalanceService`

**Constructor:** `__init__(balance_repo, type_repo, settings)`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `get_employee_balances` | `employee_id: UUID, year: int` | `list[LeaveBalance]` | Lấy tất cả balance của NV trong năm | `leave_router.get_employee_balance` |
| `check_sufficient_balance` | `employee_id: UUID, leave_type_id: UUID, year: int, requested_days: Decimal` | `LeaveBalance` | Kiểm tra đủ ngày phép. Raise `InsufficientBalanceError` nếu thiếu | `LeaveService.submit_request`, `LeaveService.approve_request` |
| `deduct_balance` | `balance_id: UUID, days: Decimal` | `None` | Trừ ngày phép (khi duyệt đơn) | `LeaveService.approve_request` |
| `restore_balance` | `balance_id: UUID, days: Decimal` | `None` | Hoàn ngày phép (khi hủy đơn đã duyệt) | `LeaveService.cancel_request` |
| `initialize_employee_balance` | `employee_id: UUID, year: int, start_date?: date` | `list[LeaveBalance]` | Khởi tạo balance cho NV đầu năm. Tính phép năm theo thâm niên | `leave_router.initialize_balance` |
| `_calculate_annual_days` | `start_date: date, year: int` | `Decimal` | Tính ngày phép năm: 12 + (thâm niên ÷ 5) | `initialize_employee_balance` (nội bộ) |

**Logic tính phép năm:**
```
Ngày phép = 12 (cơ bản) + floor(số_năm_làm_việc / 5)
```

---

### 3.2 `src/modules/attendance/application/leave_service.py`

#### Class: `LeaveService`

**Constructor:** `__init__(request_repo, type_repo, balance_service, session)`

| Phương thức | Tham số | Trả về | Mô tả | Exceptions |
|-------------|---------|--------|--------|------------|
| `submit_request` | `employee_id: UUID, leave_type_id: UUID, start_date: date, end_date: date, reason?: str` | `LeaveRequest` | Tạo đơn nghỉ mới. Validate loại nghỉ, trùng ngày, đủ balance | `LeaveTypeNotFoundError`, `LeaveOverlapError`, `InsufficientBalanceError` |
| `approve_request` | `request_id: UUID, approved_by: UUID` | `LeaveRequest` | Duyệt đơn nghỉ → trừ balance | `LeaveRequestNotFoundError`, `InvalidLeaveStatusTransitionError`, `InsufficientBalanceError` |
| `reject_request` | `request_id: UUID, rejection_reason?: str` | `LeaveRequest` | Từ chối đơn nghỉ | `LeaveRequestNotFoundError`, `InvalidLeaveStatusTransitionError` |
| `cancel_request` | `request_id: UUID` | `LeaveRequest` | Hủy đơn. Nếu đã duyệt → hoàn balance. Chỉ hủy được nếu chưa bắt đầu | `LeaveRequestNotFoundError`, `InvalidLeaveStatusTransitionError`, `LeaveDateInPastError` |
| `list_requests` | `employee_id?: UUID, status?: str, page: int, page_size: int` | `tuple[list[LeaveRequest], int]` | Danh sách đơn nghỉ (lọc theo NV/status) | — |
| `_calculate_working_days` | `start_date: date, end_date: date` | `Decimal` | Tính số ngày làm việc (bỏ T7, CN) | Nội bộ |

**Luồng duyệt đơn:**
```
submit_request → status="pending"
approve_request → status="approved" + deduct_balance
reject_request → status="rejected"
cancel_request → status="cancelled" + restore_balance (nếu đã duyệt)
```

---

### 3.3 `src/modules/attendance/application/attendance_service.py`

#### Class: `AttendanceService`

**Constructor:** `__init__(attendance_repo, schedule_repo, holiday_repo, session)`

| Phương thức | Tham số | Trả về | Mô tả | Exceptions |
|-------------|---------|--------|--------|------------|
| `check_in` | `employee_id: UUID, check_in_time?: datetime` | `AttendanceRecord` | Ghi nhận check-in. Xác định status (present/late/holiday) | `AlreadyCheckedInError`, `ScheduleNotFoundError` |
| `check_out` | `employee_id: UUID, check_out_time?: datetime` | `AttendanceRecord` | Ghi nhận check-out. Tính work_hours, overtime | `NotCheckedInError`, `AlreadyCheckedOutError`, `ScheduleNotFoundError` |
| `get_today` | `employee_id: UUID` | `AttendanceRecord \| None` | Lấy bản ghi hôm nay của NV | — |
| `get_monthly_report` | `employee_id: UUID, year: int, month: int` | `dict` | Báo cáo tháng: summary + records | — |
| `get_team_today` | `work_date?: date` | `list[AttendanceRecord]` | Chấm công toàn team theo ngày | — |
| `manual_record` | `employee_id: UUID, work_date: date, check_in?: datetime, check_out?: datetime, status: str, note?: str` | `AttendanceRecord` | HR nhập thủ công (tạo mới hoặc cập nhật) | — |
| `_determine_checkin_status` | `checkin_time: time, schedule: WorkSchedule` | `str` | Xác định present/late dựa trên giờ check-in vs ngưỡng | Nội bộ |
| `_is_early_leave` | `checkout_time: time, schedule: WorkSchedule` | `bool` | Kiểm tra có về sớm không | Nội bộ |
| `_calculate_work_hours` | `check_in: datetime, check_out: datetime, break_minutes: int` | `Decimal` | Tính giờ làm = (checkout - checkin) - break | Nội bộ |
| `_calculate_overtime` | `checkout_time: time, schedule: WorkSchedule` | `Decimal` | Tính giờ OT = thời gian sau giờ kết thúc ca | Nội bộ |

**Logic xác định trạng thái:**
```
check_in_time > (start_time + late_threshold) → LATE
check_out_time < (end_time - early_leave_threshold) → EARLY_LEAVE
Ngày lễ → HOLIDAY
```

---

### 3.4 `src/modules/attendance/application/overtime_service.py`

#### Class: `OvertimeService`

**Constructor:** `__init__(ot_repo, settings, session)`

| Phương thức | Tham số | Trả về | Mô tả | Exceptions |
|-------------|---------|--------|--------|------------|
| `submit_request` | `employee_id: UUID, work_date: date, planned_hours: float, reason: str` | `OvertimeRequest` | Tạo đơn OT. Validate giới hạn ngày (4h) và tuần (20h) | `OvertimeLimitExceededError` |
| `approve` | `request_id: UUID, approved_by: UUID` | `OvertimeRequest` | Duyệt đơn OT | `OvertimeRequestNotFoundError` |
| `reject` | `request_id: UUID` | `OvertimeRequest` | Từ chối đơn OT | `OvertimeRequestNotFoundError` |
| `list_requests` | `status?: str, page: int, page_size: int` | `tuple[list[OvertimeRequest], int]` | Danh sách đơn OT (lọc, phân trang) | — |

**Validation OT:**
```
planned_hours > 4.0 → OvertimeLimitExceededError (giới hạn ngày)
weekly_approved + planned_hours > 20.0 → OvertimeLimitExceededError (giới hạn tuần)
```

---

### 3.5 `src/modules/attendance/application/export_service.py`

#### Class: `ExportService`

| Phương thức | Tham số | Trả về | Mô tả | Gọi bởi |
|-------------|---------|--------|--------|----------|
| `generate_monthly_excel` | `records: list[AttendanceRecord], employee_name: str, year: int, month: int` | `io.BytesIO` | Tạo file Excel (.xlsx) báo cáo chấm công tháng | `attendance_router.export_attendance` |

**Nội dung file Excel:**
- Tiêu đề: "BẢNG CHẤM CÔNG THÁNG X/YYYY"
- Thông tin NV + tháng
- Tổng kết: ngày có mặt, muộn, vắng, nghỉ phép, tổng giờ làm, tổng OT
- Bảng chi tiết: Ngày | Thứ | Check-in | Check-out | Giờ làm | OT | Trạng thái
- Màu sắc theo trạng thái (xanh=có mặt, vàng=muộn, đỏ=vắng, xanh dương=nghỉ phép)

**Hằng số:**
- `STATUS_LABELS`: Map status → tên tiếng Việt
- `STATUS_COLORS`: Map status → mã màu hex

---

## 4. API LAYER (Routers)

### 4.1 `src/modules/attendance/api/router.py` — Leave Endpoints

**Router prefix:** `/api/leave`

| Endpoint | Method | Hàm | Mô tả | Gọi Service |
|----------|--------|-----|--------|-------------|
| `/types` | GET | `list_leave_types` | Danh sách loại nghỉ phép | `LeaveTypeRepository.list_all` |
| `/balance/{employee_id}` | GET | `get_employee_balance` | Lấy balance NV theo năm (query: `year`) | `BalanceService.get_employee_balances` |
| `/balance/initialize` | POST | `initialize_balance` | Khởi tạo balance cho NV | `BalanceService.initialize_employee_balance` |
| `/requests` | GET | `list_leave_requests` | Danh sách đơn nghỉ (query: `employee_id`, `status`, `page`, `page_size`) | `LeaveService.list_requests` |
| `/requests` | POST | `create_leave_request` | Tạo đơn nghỉ mới | `LeaveService.submit_request` |
| `/requests/{request_id}/approve` | PUT | `approve_leave_request` | Duyệt đơn nghỉ | `LeaveService.approve_request` |
| `/requests/{request_id}/reject` | PUT | `reject_leave_request` | Từ chối đơn nghỉ | `LeaveService.reject_request` |
| `/requests/{request_id}/cancel` | PUT | `cancel_leave_request` | Hủy đơn nghỉ | `LeaveService.cancel_request` |

**Dependencies:**
- `_get_leave_service(session)` → tạo `LeaveService` với đầy đủ repos
- `_get_balance_service(session)` → tạo `BalanceService`

---

### 4.2 `src/modules/attendance/api/attendance_router.py` — Attendance Endpoints

**Router prefix:** `/api/attendance`

| Endpoint | Method | Hàm | Mô tả | Gọi Service |
|----------|--------|-----|--------|-------------|
| `/check-in` | POST | `check_in` | Ghi nhận check-in (body: `employee_id`, `check_in_time?`) | `AttendanceService.check_in` |
| `/check-out` | POST | `check_out` | Ghi nhận check-out (body: `employee_id`, `check_out_time?`) | `AttendanceService.check_out` |
| `/today/{employee_id}` | GET | `get_today` | Lấy bản ghi hôm nay | `AttendanceService.get_today` |
| `/report/{employee_id}` | GET | `get_monthly_report` | Báo cáo tháng (query: `year`, `month`) | `AttendanceService.get_monthly_report` |
| `/team` | GET | `get_team_today` | Chấm công toàn team (query: `work_date?`) | `AttendanceService.get_team_today` |
| `/manual` | POST | `manual_record` | HR nhập thủ công | `AttendanceService.manual_record` |
| `/export` | GET | `export_attendance` | Xuất Excel (query: `employee_id`, `year`, `month`) | `AttendanceService.get_monthly_report` → `ExportService.generate_monthly_excel` |

**Schemas:**
- `CheckInRequest`: `employee_id: UUID`, `check_in_time?: datetime`
- `CheckOutRequest`: `employee_id: UUID`, `check_out_time?: datetime`
- `ManualRecordRequest`: `employee_id: UUID`, `work_date: date`, `check_in?: datetime`, `check_out?: datetime`, `status: str`, `note?: str`
- `AttendanceRecordResponse`: Response model đầy đủ
- `MonthlyReportResponse`: `employee_id`, `year`, `month`, `summary: dict`, `records: list`

---

### 4.3 `src/modules/attendance/api/overtime_router.py` — OT Endpoints

**Router prefix:** `/api/overtime`

| Endpoint | Method | Hàm | Mô tả | Gọi Service |
|----------|--------|-----|--------|-------------|
| `/requests` | POST | `create_overtime_request` | Tạo đơn OT (body: `employee_id`, `work_date`, `planned_hours`, `reason`) | `OvertimeService.submit_request` |
| `/requests` | GET | `list_overtime_requests` | Danh sách đơn OT (query: `status?`, `page`, `page_size`) | `OvertimeService.list_requests` |
| `/requests/{request_id}/approve` | PUT | `approve_overtime` | Duyệt đơn OT | `OvertimeService.approve` |
| `/requests/{request_id}/reject` | PUT | `reject_overtime` | Từ chối đơn OT | `OvertimeService.reject` |

**Schemas:**
- `OvertimeRequestCreate`: `employee_id: UUID`, `work_date: date`, `planned_hours: float (0-4)`, `reason: str`
- `OvertimeRequestResponse`: Response model
- `OvertimeListResponse`: `items`, `total`, `page`, `page_size`

---

### 4.4 `src/modules/attendance/api/schedule_router.py` — Schedule & Holiday Endpoints

**Router prefix:** `/api`

| Endpoint | Method | Hàm | Mô tả | Gọi Repository |
|----------|--------|-----|--------|----------------|
| `/schedules` | GET | `list_schedules` | Danh sách ca làm việc | `ScheduleRepository.list_all` |
| `/schedules` | POST | `create_schedule` | Tạo ca mới | `ScheduleRepository.create` |
| `/holidays` | GET | `list_holidays` | Danh sách ngày lễ (query: `year`) | `HolidayRepository.list_by_year` |
| `/holidays` | POST | `create_holiday` | Tạo ngày lễ mới | `HolidayRepository.create` |
| `/holidays/{holiday_id}` | DELETE | `delete_holiday` | Xóa ngày lễ | `HolidayRepository.delete` |

**Schemas:**
- `WorkScheduleCreate`: `name`, `start_time`, `end_time`, `break_minutes`, `late_threshold_minutes`, `early_leave_threshold_minutes`, `is_default`
- `HolidayCreate`: `holiday_date`, `name`, `is_recurring`

---

### 4.5 `src/modules/attendance/api/error_handler.py`

#### Hàm: `register_attendance_error_handlers(app: FastAPI) → None`

Đăng ký exception handler cho toàn bộ module. Map domain exception → HTTP status code.

| Exception | HTTP Status | Ý nghĩa |
|-----------|-------------|----------|
| `LeaveTypeNotFoundError` | 404 | Không tìm thấy |
| `LeaveRequestNotFoundError` | 404 | Không tìm thấy |
| `AttendanceRecordNotFoundError` | 404 | Không tìm thấy |
| `OvertimeRequestNotFoundError` | 404 | Không tìm thấy |
| `ScheduleNotFoundError` | 404 | Không tìm thấy |
| `EmployeeNotFoundError` | 404 | Không tìm thấy |
| `InsufficientBalanceError` | 422 | Không đủ ngày phép |
| `LeaveOverlapError` | 422 | Trùng ngày |
| `InvalidLeaveStatusTransitionError` | 422 | Chuyển trạng thái sai |
| `LeaveDateInPastError` | 422 | Ngày đã qua |
| `OvertimeLimitExceededError` | 422 | Vượt giới hạn OT |
| `AlreadyCheckedInError` | 409 | Đã check-in |
| `AlreadyCheckedOutError` | 409 | Đã check-out |
| `NotCheckedInError` | 400 | Chưa check-in |

**Response format:**
```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Mô tả lỗi"
  }
}
```

---

## 5. WORKER (Cron Job)

### 5.1 `src/modules/attendance/worker.py`

**Mục đích:** ARQ worker chạy cron job hàng ngày lúc 23:00 để đánh dấu NV vắng mặt.

| Hàm | Tham số | Mô tả |
|-----|---------|--------|
| `startup(ctx: dict)` | ARQ context | Khởi tạo DB engine + session maker khi worker start |
| `shutdown(ctx: dict)` | ARQ context | Cleanup khi worker dừng |
| `auto_mark_absent(ctx: dict)` | ARQ context | **Cron job chính** — đánh dấu NV vắng/nghỉ phép |

**Logic `auto_mark_absent`:**
1. Kiểm tra hôm nay có phải ngày lễ → bỏ qua
2. Lấy danh sách tất cả NV active
3. Lấy danh sách NV đã có bản ghi chấm công hôm nay
4. Lấy danh sách NV có đơn nghỉ phép đã duyệt bao gồm hôm nay
5. NV vắng = active - đã chấm công - đang nghỉ phép → INSERT status='absent'
6. NV nghỉ phép chưa có record → INSERT status='on_leave', note='Nghỉ phép (tự động)'
7. Dùng `ON CONFLICT DO NOTHING` để tránh duplicate

**Class: `WorkerSettings`**
- `on_startup`: `startup`
- `on_shutdown`: `shutdown`
- `cron_jobs`: chạy `auto_mark_absent` lúc 23:00:00 mỗi ngày
- `redis_settings`: kết nối Redis từ `AuthSettings.redis_url`

**Chạy worker:**
```bash
arq src.modules.attendance.worker.WorkerSettings
```

---

## 6. SCRIPTS (Seed Data)

### 6.1 `scripts/seed_leave.py`

**Mục đích:** Tạo dữ liệu mẫu cho leave balances và leave requests.

| Hàm | Mô tả |
|-----|--------|
| `seed_leave()` | Hàm chính — tạo balance cho tất cả NV + 15 đơn nghỉ mẫu |

**Logic:**
1. Lấy danh sách leave_types từ DB
2. Lấy danh sách NV active
3. Xóa dữ liệu cũ (balances + requests) cho năm 2026
4. Tạo leave_balances cho mỗi NV × mỗi loại nghỉ (dùng `LEAVE_TYPE_DEFAULTS`)
5. Tạo 15 leave_requests ngẫu nhiên với phân bố: 4 pending, 7 approved, 2 rejected, 2 cancelled

**Hằng số:**
- `YEAR = 2026`
- `LEAVE_TYPE_DEFAULTS`: annual=12, sick=30, unpaid=365, maternity=180, wedding=3, funeral=3, personal=5
- `REASONS`: 15 lý do nghỉ phép mẫu bằng tiếng Việt

**Chạy:**
```bash
cd backend
python -m scripts.seed_leave
```

---

### 6.2 `scripts/seed_attendance.py`

**Mục đích:** Tạo 1 tháng dữ liệu chấm công ngẫu nhiên cho tất cả NV.

| Hàm | Tham số | Mô tả |
|-----|---------|--------|
| `random_checkin_time(status, work_date)` | `str, date` | Tạo giờ check-in ngẫu nhiên theo status |
| `random_checkout_time(status, work_date)` | `str, date` | Tạo giờ check-out ngẫu nhiên theo status |
| `calculate_work_hours(check_in, check_out)` | `datetime, datetime` | Tính giờ làm (trừ 60 phút nghỉ) |
| `seed_attendance()` | — | Hàm chính — tạo dữ liệu chấm công |

**Logic `seed_attendance`:**
1. Lấy NV active + ngày lễ trong tháng
2. Xóa dữ liệu chấm công cũ tháng 5/2026
3. Với mỗi NV × mỗi ngày làm việc (bỏ T7/CN/lễ):
   - Random status: 70% present, 20% late, 5% absent, 5% early_leave
   - Nếu absent → chỉ INSERT status, không có check-in/out
   - Nếu khác → tạo check-in/out ngẫu nhiên, tính work_hours + overtime

**Phân bố giờ check-in:**
- Present: ±10 phút so với 08:00
- Late: +16 đến +60 phút
- Early leave: ±5 phút (check-in bình thường)

**Phân bố giờ check-out:**
- Present: 0 đến +30 phút sau 17:00
- Late: 0 đến +15 phút
- Early leave: -90 đến -30 phút (về sớm)

**Chạy:**
```bash
cd backend
python -m scripts.seed_attendance
```

---

## 7. FRONTEND

### 7.1 `frontend/src/lib/api/leave.ts` — API Client Nghỉ Phép

| Hàm | Tham số | Trả về | Mô tả | Gọi API |
|-----|---------|--------|--------|---------|
| `handleResponse<T>(res)` | `Response` | `Promise<T>` | Xử lý response, throw Error nếu !ok | Nội bộ |
| `listLeaveTypes()` | — | `Promise<LeaveType[]>` | Lấy danh sách loại nghỉ | `GET /api/leave/types` |
| `getBalance(employeeId, year?)` | `string, number?` | `Promise<LeaveBalance[]>` | Lấy balance NV | `GET /api/leave/balance/{id}` |
| `initializeBalance(data)` | `{employee_id, year, start_date?}` | `Promise<LeaveBalance[]>` | Khởi tạo balance | `POST /api/leave/balance/initialize` |
| `listRequests(params?)` | `{employee_id?, status?, page?, page_size?}` | `Promise<LeaveRequestListResponse>` | Danh sách đơn nghỉ | `GET /api/leave/requests` |
| `createRequest(data)` | `{employee_id, leave_type_id, start_date, end_date, reason?}` | `Promise<LeaveRequest>` | Tạo đơn nghỉ | `POST /api/leave/requests` |
| `approveRequest(requestId)` | `string` | `Promise<LeaveRequest>` | Duyệt đơn | `PUT /api/leave/requests/{id}/approve` |
| `rejectRequest(requestId, reason?)` | `string, string?` | `Promise<LeaveRequest>` | Từ chối đơn | `PUT /api/leave/requests/{id}/reject` |
| `cancelRequest(requestId)` | `string` | `Promise<LeaveRequest>` | Hủy đơn | `PUT /api/leave/requests/{id}/cancel` |

**Interfaces:**
- `LeaveType`: id, name, display_name, default_days_per_year, is_paid, requires_approval, requires_document
- `LeaveBalance`: id, employee_id, leave_type_id, year, total_days, used_days, remaining_days
- `LeaveRequest`: id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status, approved_by, approved_at, rejection_reason, created_at, updated_at
- `LeaveRequestListResponse`: items, total, page, page_size

---

### 7.2 `frontend/src/lib/api/attendance.ts` — API Client Chấm Công & OT

| Hàm | Tham số | Trả về | Mô tả | Gọi API |
|-----|---------|--------|--------|---------|
| `handleResponse<T>(res)` | `Response` | `Promise<T>` | Xử lý response | Nội bộ |
| `checkIn(employeeId, checkInTime?)` | `string, string?` | `Promise<AttendanceRecord>` | Check-in | `POST /api/attendance/check-in` |
| `checkOut(employeeId, checkOutTime?)` | `string, string?` | `Promise<AttendanceRecord>` | Check-out | `POST /api/attendance/check-out` |
| `getToday(employeeId)` | `string` | `Promise<AttendanceRecord \| null>` | Lấy bản ghi hôm nay | `GET /api/attendance/today/{id}` |
| `getMonthlyReport(employeeId, year, month)` | `string, number, number` | `Promise<MonthlyReport>` | Báo cáo tháng | `GET /api/attendance/report/{id}` |
| `getTeamToday(workDate?)` | `string?` | `Promise<AttendanceRecord[]>` | Chấm công team | `GET /api/attendance/team` |
| `manualRecord(data)` | `{employee_id, work_date, check_in?, check_out?, status, note?}` | `Promise<AttendanceRecord>` | Nhập thủ công | `POST /api/attendance/manual` |
| `createOvertimeRequest(data)` | `{employee_id, work_date, planned_hours, reason}` | `Promise<OvertimeRequest>` | Tạo đơn OT | `POST /api/overtime/requests` |
| `listOvertimeRequests(params?)` | `{status?, page?, page_size?}` | `Promise<OvertimeListResponse>` | Danh sách OT | `GET /api/overtime/requests` |
| `approveOvertime(requestId)` | `string` | `Promise<OvertimeRequest>` | Duyệt OT | `PUT /api/overtime/requests/{id}/approve` |
| `rejectOvertime(requestId)` | `string` | `Promise<OvertimeRequest>` | Từ chối OT | `PUT /api/overtime/requests/{id}/reject` |
| `listSchedules()` | — | `Promise<WorkSchedule[]>` | Danh sách ca | `GET /api/schedules` |
| `listHolidays(year?)` | `number?` | `Promise<Holiday[]>` | Danh sách ngày lễ | `GET /api/holidays` |
| `createHoliday(data)` | `{holiday_date, name, is_recurring?}` | `Promise<Holiday>` | Tạo ngày lễ | `POST /api/holidays` |
| `deleteHoliday(holidayId)` | `string` | `Promise<void>` | Xóa ngày lễ | `DELETE /api/holidays/{id}` |

**Interfaces:**
- `AttendanceRecord`: id, employee_id, work_date, check_in, check_out, work_hours, overtime_hours, status, note, created_at, updated_at
- `MonthlyReport`: employee_id, year, month, summary (present_days, late_days, absent_days, leave_days, total_work_hours, total_overtime_hours), records
- `OvertimeRequest`: id, employee_id, work_date, planned_hours, actual_hours, reason, status, approved_by, created_at
- `OvertimeListResponse`: items, total, page, page_size
- `WorkSchedule`: id, name, start_time, end_time, break_minutes, late_threshold_minutes, early_leave_threshold_minutes, is_default
- `Holiday`: id, holiday_date, name, is_recurring

---

### 7.3 `frontend/src/app/(dashboard)/leave/page.tsx` — Trang Quản Lý Nghỉ Phép

**Component:** `LeavePage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchData()` | Load danh sách đơn nghỉ + danh sách NV (để map tên) |
| `fetchRequests()` | Reload chỉ danh sách đơn nghỉ |
| `handleApprove(id)` | Gọi `leaveApi.approveRequest` → reload |
| `handleReject(id)` | Prompt lý do → gọi `leaveApi.rejectRequest` → reload |

**Hiển thị:**
- Cards tổng kết: Chờ duyệt, Tổng đơn
- Bảng danh sách: Nhân viên, Từ ngày, Đến ngày, Số ngày, Lý do, Trạng thái, Hành động (Duyệt/Từ chối)
- Nút "Tạo đơn nghỉ" → link đến `/leave/request`

---

### 7.4 `frontend/src/app/(dashboard)/leave/request/page.tsx` — Form Tạo Đơn Nghỉ

**Component:** `LeaveRequestPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `loadData()` | Load leave types + employees khi mount |
| `handleSubmit(e)` | Validate form → gọi `leaveApi.createRequest` → redirect `/leave` |

**Form fields:**
- Nhân viên (Select từ danh sách)
- Loại nghỉ (Select từ leave types)
- Từ ngày / Đến ngày (date input)
- Lý do (textarea, tùy chọn)

---

### 7.5 `frontend/src/app/(dashboard)/leave/calendar/page.tsx` — Lịch Nghỉ Phép

**Component:** `LeaveCalendarPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchLeaveRequests()` | Load đơn nghỉ → lọc approved/pending trong tháng hiện tại |
| `getRequestsForDay(day)` | Lấy đơn nghỉ overlap với ngày cụ thể |
| `prevMonth()` / `nextMonth()` | Chuyển tháng |
| `getDaysInMonth(year, month)` | Tính số ngày trong tháng |
| `getFirstDayOfMonth(year, month)` | Tính thứ đầu tiên (Monday-based) |

**Hiển thị:**
- Lịch dạng grid 7 cột (T2→CN)
- Mỗi ô hiển thị badge NV đang nghỉ (tối đa 3, "+N người" nếu nhiều hơn)
- Màu: xanh = đã duyệt, vàng = chờ duyệt
- Nút prev/next để chuyển tháng

---

### 7.6 `frontend/src/app/(dashboard)/attendance/page.tsx` — Dashboard Chấm Công

**Component:** `AttendancePage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchData()` | Load chấm công team hôm nay + danh sách NV (map tên) |
| `formatTime(isoString)` | Format ISO datetime → "HH:mm" |

**Hiển thị:**
- 4 Cards: Có mặt hôm nay, Đi muộn, Vắng mặt, Tổng records
- Bảng: Nhân viên, Check-in, Check-out, Giờ làm, OT, Trạng thái
- Nút link: "Bảng chấm công" (→ /attendance/team), "Overtime" (→ /attendance/overtime)

---

### 7.7 `frontend/src/app/(dashboard)/attendance/team/page.tsx` — Nhập Chấm Công Thủ Công

**Component:** `AttendanceTeamPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `loadEmployees()` | Load danh sách NV khi mount |
| `handleSubmit(e)` | Validate → format datetime → gọi `attendanceApi.manualRecord` |

**Form fields:**
- Nhân viên (Select)
- Ngày + Trạng thái (present/late/early_leave/absent/on_leave)
- Giờ vào / Giờ ra (time input)
- Ghi chú (text input)

**Đặc biệt:** Format giờ thành ISO datetime với timezone +07:00 trước khi gửi API.

---

### 7.8 `frontend/src/app/(dashboard)/attendance/overtime/page.tsx` — Quản Lý OT

**Component:** `OvertimePage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `loadData()` | Load danh sách OT + NV |
| `handleCreate(e)` | Validate → gọi `attendanceApi.createOvertimeRequest` → reload |
| `handleApprove(id)` | Gọi `attendanceApi.approveOvertime` → reload |
| `handleReject(id)` | Gọi `attendanceApi.rejectOvertime` → reload |

**Hiển thị:**
- Form đăng ký OT: Nhân viên, Ngày, Số giờ (0.5-4, step 0.5), Lý do
- Bảng danh sách OT: Nhân viên, Ngày, Số giờ, Lý do, Trạng thái, Hành động

---

### 7.9 `frontend/src/app/(dashboard)/attendance/report/page.tsx` — Báo Cáo Tháng

**Component:** `AttendanceReportPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchReport()` | Validate employee ID → gọi `attendanceApi.getMonthlyReport` |
| `handleExport()` | Mở tab mới với URL `/api/attendance/export?...` để tải Excel |
| `formatTime(isoStr)` | Format ISO → "HH:mm" |

**Hiển thị:**
- Form lọc: Employee ID (UUID), Năm, Tháng, nút "Xem báo cáo"
- 6 Cards tổng kết: Ngày có mặt, Muộn, Vắng, Nghỉ phép, Tổng giờ làm, Tổng OT
- Bảng chi tiết: Ngày, Check-in, Check-out, Giờ làm, OT, Trạng thái, Ghi chú
- Nút "Xuất Excel" → download file .xlsx

---

### 7.10 `frontend/src/app/(dashboard)/settings/holidays/page.tsx` — Quản Lý Ngày Lễ

**Component:** `HolidaysPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchHolidays()` | Load ngày lễ theo năm đã chọn |
| `handleCreate()` | Validate → gọi `attendanceApi.createHoliday` → reload |
| `handleDelete(id)` | Confirm → gọi `attendanceApi.deleteHoliday` → reload |

**Hiển thị:**
- Dropdown chọn năm (2025/2026/2027)
- Form thêm: Tên ngày lễ, Ngày, Checkbox "Lặp hàng năm"
- Bảng: Ngày, Tên, Lặp hàng năm (Có/Không), Nút Xóa

---

### 7.11 `frontend/src/app/(dashboard)/settings/schedules/page.tsx` — Quản Lý Ca Làm Việc

**Component:** `SchedulesPage` (Client Component)

| Hàm/Logic | Mô tả |
|-----------|--------|
| `fetchSchedules()` | Load danh sách ca làm việc |
| `handleCreate()` | Validate → POST `/api/schedules` → reload |

**Hiển thị:**
- Nút "Thêm ca mới" → toggle form
- Form: Tên ca, Giờ bắt đầu, Giờ kết thúc, Nghỉ trưa (phút), Ngưỡng muộn, Ngưỡng về sớm, Checkbox mặc định
- Bảng: Tên ca, Giờ BĐ, Giờ KT, Nghỉ trưa, Ngưỡng muộn, Ngưỡng về sớm, Mặc định

---

## 8. CHUỖI PHỤ THUỘC (Dependency Chain)

### 8.1 Luồng Check-in

```
Frontend: attendanceApi.checkIn()
  → POST /api/attendance/check-in
    → attendance_router.check_in()
      → AttendanceService.check_in()
        → AttendanceRepository.get_by_employee_date()  // kiểm tra đã check-in chưa
        → ScheduleRepository.get_default()              // lấy ca mặc định
        → AttendanceService._determine_checkin_status() // xác định present/late
        → HolidayRepository.is_holiday()                // kiểm tra ngày lễ
        → AttendanceRepository.create()                 // tạo record
        → session.commit()
```

### 8.2 Luồng Tạo Đơn Nghỉ Phép

```
Frontend: leaveApi.createRequest()
  → POST /api/leave/requests
    → leave_router.create_leave_request()
      → LeaveService.submit_request()
        → LeaveTypeRepository.get_by_id()              // validate loại nghỉ
        → LeaveService._calculate_working_days()       // tính ngày làm việc
        → LeaveRequestRepository.check_overlap()       // kiểm tra trùng
        → BalanceService.check_sufficient_balance()    // kiểm tra đủ ngày
          → LeaveBalanceRepository.get_balance()
        → LeaveRequestRepository.create()              // tạo đơn
        → session.commit()
```

### 8.3 Luồng Duyệt Đơn Nghỉ

```
Frontend: leaveApi.approveRequest()
  → PUT /api/leave/requests/{id}/approve
    → leave_router.approve_leave_request()
      → LeaveService.approve_request()
        → LeaveRequestRepository.get_by_id()           // tìm đơn
        → BalanceService.check_sufficient_balance()    // kiểm tra lại balance
        → BalanceService.deduct_balance()              // trừ ngày phép
          → LeaveBalanceRepository.deduct()
        → LeaveRequestRepository.update()              // cập nhật status
        → session.commit()
```

### 8.4 Luồng Xuất Excel

```
Frontend: window.open("/api/attendance/export?...")
  → GET /api/attendance/export
    → attendance_router.export_attendance()
      → AttendanceService.get_monthly_report()
        → AttendanceRepository.get_monthly_report()
      → ExportService.generate_monthly_excel()         // tạo file .xlsx
      → StreamingResponse (download file)
```

### 8.5 Luồng Cron Job (23:00 hàng ngày)

```
ARQ Worker → auto_mark_absent()
  → Kiểm tra ngày lễ (SQL trực tiếp)
  → Lấy NV active (SQL)
  → Lấy NV đã chấm công (SQL)
  → Lấy NV đang nghỉ phép (SQL)
  → INSERT absent records (SQL, ON CONFLICT DO NOTHING)
  → INSERT on_leave records (SQL, ON CONFLICT DO NOTHING)
  → session.commit()
```

---

## 9. GHI CHÚ QUAN TRỌNG

1. **Tất cả thao tác đều do HR thực hiện** — không có self-service cho nhân viên
2. **Timezone:** Sử dụng UTC trong backend, frontend hiển thị theo locale vi-VN
3. **Phân trang:** Offset-based (page/page_size), mặc định page=1, page_size=20
4. **Authentication:** Tất cả endpoint yêu cầu `get_current_user` (JWT Bearer token)
5. **Transaction:** Mỗi service method tự commit sau khi hoàn thành
6. **Luật lao động VN:** 12 ngày phép năm cơ bản + 1 ngày/5 năm thâm niên
7. **OT giới hạn:** Tối đa 4h/ngày, 20h/tuần (theo Luật LĐ VN)
8. **Ngày làm việc:** Thứ 2 → Thứ 6 (bỏ T7, CN khi tính ngày phép)
