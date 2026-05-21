# Kế Hoạch Chi Tiết: Nhóm 4 (Chấm Công & Nghỉ Phép) + Nhóm 5 (Lương & Phúc Lợi)

## Mục Lục
- [1. Đánh Giá Hiện Trạng Dự Án](#1-đánh-giá-hiện-trạng-dự-án)
- [2. Nhóm 4: Chấm Công & Nghỉ Phép](#2-nhóm-4-chấm-công--nghỉ-phép)
- [3. Nhóm 5: Lương & Phúc Lợi](#3-nhóm-5-lương--phúc-lợi)
- [4. Workflow Triển Khai Từng Bước](#4-workflow-triển-khai-từng-bước)
- [5. Database Schema](#5-database-schema)
- [6. API Endpoints](#6-api-endpoints)
- [7. AI Integration](#7-ai-integration)

---

## 1. Đánh Giá Hiện Trạng Dự Án

### ✅ Đã Có (Sẵn Sàng Sử Dụng)

| Thành phần | Chi tiết |
|------------|----------|
| Backend Framework | FastAPI + SQLAlchemy async + Alembic migrations |
| Database | PostgreSQL (asyncpg) |
| Auth | Google OAuth2 + JWT + Whitelist |
| Background Jobs | ARQ (Redis-based) - đã có worker pattern |
| File Storage | MinIO (S3-compatible) |
| AI/LLM | OpenAI SDK async + LLMAdapter pattern |
| Employee Model | Đầy đủ: id, code, name, email, department, position, start_date, contract_type |
| Department/Position | CRUD hoàn chỉnh |
| Frontend | Next.js 14 App Router + Tailwind + shadcn/ui |
| API Pattern | Clean Architecture (Domain → Application → Infrastructure → API) |

### ⚠️ Cần Bổ Sung

| Thành phần | Lý do |
|------------|-------|
| Bảng `attendance` | Chưa có - cần tạo migration mới |
| Bảng `leave_requests` | Chưa có - cần tạo migration mới |
| Bảng `leave_balances` | Chưa có - cần tạo migration mới |
| Bảng `payroll` | Chưa có - cần tạo migration mới |
| Bảng `salary_configs` | Chưa có - cần tạo migration mới |
| Module `attendance` | Chưa có - cần tạo module mới |
| Module `payroll` | Chưa có - cần tạo module mới |
| Google Calendar API | Chưa tích hợp (đã có grant_status check) |
| Cron job tính lương | Chưa có - mở rộng ARQ worker |

### ✅ Kết Luận: DỰ ÁN ĐỦ NỀN TẢNG ĐỂ LÀM

Lý do:
1. **Architecture pattern** đã chuẩn - chỉ cần copy pattern từ module `employee` hoặc `gmail`
2. **ARQ worker** đã hoạt động - dễ thêm cron job tính lương, nhắc nhở
3. **Employee model** đã có đầy đủ thông tin cần thiết (department, position, start_date)
4. **LLM Adapter** sẵn sàng cho AI features (phát hiện bất thường, đề xuất lương)
5. **Redis** đã có - dùng cho rate limiting, caching, job queue
6. **Frontend pattern** rõ ràng - dễ thêm page mới

---

## 2. Nhóm 4: Chấm Công & Nghỉ Phép

### 4.1 Quản Lý Nghỉ Phép (Leave Management)

#### Chức năng chi tiết:
- Nhân viên đăng ký nghỉ phép (annual, sick, unpaid, maternity, wedding, funeral)
- HR/Manager duyệt/từ chối đơn nghỉ
- Theo dõi số ngày phép còn lại theo năm
- Tự động tính phép theo thâm niên (Luật Lao động VN: 12 ngày + 1 ngày/5 năm)
- Lịch sử nghỉ phép
- Báo cáo nghỉ phép theo phòng ban

#### Loại nghỉ phép (theo Luật Lao động Việt Nam):
| Loại | Số ngày/năm | Ghi chú |
|------|-------------|---------|
| Phép năm (annual) | 12 + 1/5 năm | Tính theo thâm niên |
| Ốm đau (sick) | Theo BHXH | Cần giấy bác sĩ |
| Không lương (unpaid) | Không giới hạn | Cần duyệt |
| Thai sản (maternity) | 180 ngày | Nữ |
| Kết hôn (wedding) | 3 ngày | Có lương |
| Tang (funeral) | 3 ngày | Bố mẹ, vợ/chồng, con |
| Việc riêng (personal) | 1 ngày | Không lương |

### 4.2 Chấm Công (Attendance Tracking)

#### Chức năng chi tiết:
- Check-in / Check-out (thủ công qua web)
- Ghi nhận giờ vào/ra, tính tổng giờ làm
- Phân loại: đúng giờ, đi muộn, về sớm, vắng mặt
- Overtime (OT): đăng ký + duyệt + ghi nhận
- Báo cáo chấm công theo ngày/tuần/tháng
- Export bảng chấm công (Excel)

#### Quy tắc chấm công:
- Giờ làm chuẩn: 08:00 - 17:00 (configurable)
- Đi muộn: check-in sau 08:15
- Về sớm: check-out trước 16:45
- Vắng mặt: không check-in cả ngày (không có đơn nghỉ)
- OT: sau 17:30, cần đăng ký trước

### 4.3 Lịch Làm Việc (Work Schedule)

#### Chức năng chi tiết:
- Cấu hình ca làm việc (shift)
- Quản lý ngày lễ (theo lịch VN)
- Lịch trực (nếu có)
- Hiển thị lịch team/phòng ban

### 4.4 AI Phát Hiện Bất Thường

#### Chức năng chi tiết:
- Phân tích pattern chấm công bằng LLM
- Cảnh báo: đi muộn liên tục (>3 lần/tuần)
- Cảnh báo: vắng không phép
- Cảnh báo: OT quá nhiều (>20h/tuần)
- Gợi ý hành động cho HR

---

## 3. Nhóm 5: Lương & Phúc Lợi

### 5.1 Bảng Lương (Payroll)

#### Chức năng chi tiết:
- Cấu hình lương cơ bản cho từng nhân viên
- Tính lương hàng tháng tự động (cron job cuối tháng)
- Công thức: `Lương thực nhận = Lương gross - BHXH - BHYT - BHTN - Thuế TNCN + Phụ cấp + OT`
- Phụ cấp: ăn trưa, xăng xe, điện thoại, chức vụ (configurable)
- Khấu trừ: đi muộn, vắng không phép
- Lịch sử lương theo tháng

#### Công thức tính (theo luật VN 2024):

```
Lương gross = Lương cơ bản + Phụ cấp

BHXH (8%) = Lương đóng BH × 0.08
BHYT (1.5%) = Lương đóng BH × 0.015
BHTN (1%) = Lương đóng BH × 0.01
Tổng BH nhân viên = 10.5%

Giảm trừ gia cảnh:
- Bản thân: 11,000,000 VNĐ/tháng
- Người phụ thuộc: 4,400,000 VNĐ/người/tháng

Thu nhập chịu thuế = Lương gross - Tổng BH - Giảm trừ gia cảnh
Thuế TNCN = Tính theo biểu thuế lũy tiến 7 bậc

Lương NET = Lương gross - Tổng BH - Thuế TNCN
```

#### Biểu thuế TNCN lũy tiến:
| Bậc | Thu nhập chịu thuế/tháng | Thuế suất |
|-----|--------------------------|-----------|
| 1 | Đến 5 triệu | 5% |
| 2 | 5 - 10 triệu | 10% |
| 3 | 10 - 18 triệu | 15% |
| 4 | 18 - 32 triệu | 20% |
| 5 | 32 - 52 triệu | 25% |
| 6 | 52 - 80 triệu | 30% |
| 7 | Trên 80 triệu | 35% |

### 5.2 Phiếu Lương (Payslip)

#### Chức năng chi tiết:
- Tạo phiếu lương PDF cho từng nhân viên
- Gửi phiếu lương qua email (dùng Gmail module đã có)
- Nhân viên xem phiếu lương online
- Lịch sử phiếu lương

### 5.3 BHXH/BHYT/BHTN

#### Chức năng chi tiết:
- Tính đóng BH cho nhân viên và công ty
- Báo cáo đóng BH hàng tháng
- Theo dõi mức lương đóng BH (có trần)
- Export danh sách đóng BH

#### Tỷ lệ đóng (2024):
| Loại | Nhân viên | Công ty |
|------|-----------|---------|
| BHXH | 8% | 17.5% |
| BHYT | 1.5% | 3% |
| BHTN | 1% | 1% |
| **Tổng** | **10.5%** | **21.5%** |

### 5.4 AI Đề Xuất Lương

#### Chức năng chi tiết:
- Phân tích vị trí, kinh nghiệm, kỹ năng
- So sánh với mức lương hiện tại trong công ty
- Gợi ý range lương phù hợp
- Dùng khi tuyển mới hoặc review lương

---

## 4. Workflow Triển Khai Từng Bước

### PHASE 4A: Nghỉ Phép (2 tuần)

```
Tuần 1: Backend
├── Bước 1: Tạo module structure
│   ├── backend/src/modules/attendance/__init__.py
│   ├── backend/src/modules/attendance/domain/entities.py
│   ├── backend/src/modules/attendance/domain/enums.py
│   ├── backend/src/modules/attendance/domain/exceptions.py
│   ├── backend/src/modules/attendance/infrastructure/config.py
│   ├── backend/src/modules/attendance/infrastructure/repositories.py
│   ├── backend/src/modules/attendance/application/leave_service.py
│   ├── backend/src/modules/attendance/application/balance_service.py
│   ├── backend/src/modules/attendance/api/router.py
│   ├── backend/src/modules/attendance/api/schemas.py
│   ├── backend/src/modules/attendance/api/error_handler.py
│   └── backend/src/modules/attendance/container.py
│
├── Bước 2: Database migrations
│   ├── 010_create_leave_types_table.py
│   ├── 011_create_leave_balances_table.py
│   └── 012_create_leave_requests_table.py
│
├── Bước 3: Domain entities + enums
│   ├── LeaveType entity (annual, sick, unpaid, maternity, wedding, funeral)
│   ├── LeaveBalance entity (employee_id, leave_type_id, year, total, used, remaining)
│   ├── LeaveRequest entity (employee_id, type, start_date, end_date, status, reason)
│   └── LeaveStatus enum (pending, approved, rejected, cancelled)
│
├── Bước 4: Repository layer
│   ├── LeaveTypeRepository (CRUD)
│   ├── LeaveBalanceRepository (get_by_employee_year, deduct, restore)
│   └── LeaveRequestRepository (CRUD, list_by_employee, list_pending)
│
├── Bước 5: Application services
│   ├── LeaveService.submit_request() - validate + create
│   ├── LeaveService.approve_request() - update status + deduct balance
│   ├── LeaveService.reject_request() - update status + reason
│   ├── LeaveService.cancel_request() - restore balance
│   └── BalanceService.initialize_year() - tạo balance đầu năm
│
└── Bước 6: API endpoints
    ├── GET    /api/leave/types
    ├── GET    /api/leave/balance/{employee_id}
    ├── GET    /api/leave/requests?employee_id=&status=&page=
    ├── POST   /api/leave/requests
    ├── PUT    /api/leave/requests/{id}/approve
    ├── PUT    /api/leave/requests/{id}/reject
    ├── PUT    /api/leave/requests/{id}/cancel
    └── GET    /api/leave/calendar?department_id=&month=

Tuần 2: Frontend
├── Bước 7: Frontend pages
│   ├── /leave - Dashboard nghỉ phép (balance + lịch sử)
│   ├── /leave/request - Form đăng ký nghỉ
│   ├── /leave/approve - Danh sách đơn chờ duyệt (HR)
│   └── /leave/calendar - Lịch nghỉ phép team
│
├── Bước 8: Components
│   ├── LeaveBalanceCard - hiển thị số ngày còn lại
│   ├── LeaveRequestForm - form đăng ký
│   ├── LeaveRequestTable - bảng danh sách đơn
│   ├── LeaveCalendar - lịch hiển thị ai nghỉ
│   └── ApprovalActions - nút duyệt/từ chối
│
└── Bước 9: Integration + Testing
    ├── API client functions
    ├── Error handling
    └── Basic tests
```

### PHASE 4B: Chấm Công (2 tuần)

```
Tuần 3: Backend
├── Bước 1: Database migrations
│   ├── 013_create_work_schedules_table.py
│   ├── 014_create_attendance_records_table.py
│   ├── 015_create_overtime_requests_table.py
│   └── 016_create_holidays_table.py
│
├── Bước 2: Domain entities
│   ├── WorkSchedule (shift_name, start_time, end_time, late_threshold_minutes)
│   ├── AttendanceRecord (employee_id, date, check_in, check_out, status, work_hours)
│   ├── OvertimeRequest (employee_id, date, hours, reason, status)
│   ├── Holiday (date, name, is_recurring)
│   └── AttendanceStatus enum (present, late, early_leave, absent, on_leave, holiday)
│
├── Bước 3: Application services
│   ├── AttendanceService.check_in() - ghi nhận giờ vào
│   ├── AttendanceService.check_out() - ghi nhận giờ ra + tính status
│   ├── AttendanceService.get_monthly_report() - báo cáo tháng
│   ├── OvertimeService.submit_request()
│   ├── OvertimeService.approve/reject()
│   └── ScheduleService.get_employee_schedule()
│
├── Bước 4: API endpoints
│   ├── POST   /api/attendance/check-in
│   ├── POST   /api/attendance/check-out
│   ├── GET    /api/attendance/today
│   ├── GET    /api/attendance/report?employee_id=&month=&year=
│   ├── GET    /api/attendance/team?department_id=&date=
│   ├── POST   /api/overtime/requests
│   ├── PUT    /api/overtime/requests/{id}/approve
│   ├── GET    /api/holidays
│   └── POST   /api/holidays
│
└── Bước 5: ARQ Cron Jobs
    ├── auto_mark_absent() - chạy cuối ngày, đánh absent cho ai không check-in
    └── monthly_attendance_summary() - tổng hợp cuối tháng

Tuần 4: Frontend + AI
├── Bước 6: Frontend pages
│   ├── /attendance - Check-in/out + trạng thái hôm nay
│   ├── /attendance/report - Báo cáo chấm công cá nhân
│   ├── /attendance/team - Bảng chấm công team (HR)
│   ├── /attendance/overtime - Đăng ký/duyệt OT
│   └── /settings/holidays - Quản lý ngày lễ
│
├── Bước 7: AI Phát hiện bất thường
│   ├── Thêm method vào LLMAdapter: analyze_attendance_pattern()
│   ├── Prompt: phân tích data chấm công 30 ngày → cảnh báo
│   ├── API: GET /api/attendance/ai-alerts?department_id=
│   └── Frontend: AlertCard hiển thị cảnh báo trên dashboard
│
└── Bước 8: Export
    ├── GET /api/attendance/export?month=&year=&format=xlsx
    └── Dùng openpyxl (đã có trong dependencies)
```

### PHASE 5A: Bảng Lương (3 tuần)

```
Tuần 5: Backend - Cấu hình & Tính lương
├── Bước 1: Tạo module structure
│   ├── backend/src/modules/payroll/__init__.py
│   ├── backend/src/modules/payroll/domain/entities.py
│   ├── backend/src/modules/payroll/domain/enums.py
│   ├── backend/src/modules/payroll/domain/exceptions.py
│   ├── backend/src/modules/payroll/domain/tax_calculator.py
│   ├── backend/src/modules/payroll/infrastructure/config.py
│   ├── backend/src/modules/payroll/infrastructure/repositories.py
│   ├── backend/src/modules/payroll/application/payroll_service.py
│   ├── backend/src/modules/payroll/application/salary_service.py
│   ├── backend/src/modules/payroll/application/insurance_service.py
│   ├── backend/src/modules/payroll/api/router.py
│   ├── backend/src/modules/payroll/api/schemas.py
│   ├── backend/src/modules/payroll/api/error_handler.py
│   └── backend/src/modules/payroll/container.py
│
├── Bước 2: Database migrations
│   ├── 017_create_salary_configs_table.py
│   ├── 018_create_allowances_table.py
│   ├── 019_create_deductions_table.py
│   ├── 020_create_payroll_periods_table.py
│   ├── 021_create_payslips_table.py
│   └── 022_create_dependents_table.py
│
├── Bước 3: Domain entities
│   ├── SalaryConfig (employee_id, gross_salary, insurance_salary, effective_date)
│   ├── Allowance (employee_id, type, amount, is_taxable)
│   ├── Deduction (employee_id, type, amount, description)
│   ├── Dependent (employee_id, name, relationship, id_number)
│   ├── PayrollPeriod (month, year, status: draft/confirmed/paid)
│   └── Payslip (employee_id, period_id, gross, net, tax, insurance, breakdown_json)
│
├── Bước 4: Tax Calculator (Pure domain logic)
│   ├── calculate_insurance(gross, insurance_salary) → InsuranceBreakdown
│   ├── calculate_pit(taxable_income) → tax_amount (biểu lũy tiến 7 bậc)
│   ├── calculate_deduction(self_deduction, dependents_count) → total
│   └── calculate_net(gross, insurance, tax, allowances, deductions) → net
│
└── Bước 5: Payroll Service
    ├── PayrollService.calculate_employee(employee_id, month, year)
    ├── PayrollService.calculate_all(month, year) - batch tính cho tất cả
    ├── PayrollService.confirm_period(period_id) - lock bảng lương
    ├── PayrollService.mark_paid(period_id) - đánh dấu đã trả
    └── SalaryService.update_salary(employee_id, new_config)

Tuần 6: Backend - API + Payslip
├── Bước 6: API endpoints
│   ├── GET    /api/payroll/salary/{employee_id} - xem cấu hình lương
│   ├── PUT    /api/payroll/salary/{employee_id} - cập nhật lương
│   ├── GET    /api/payroll/allowances/{employee_id}
│   ├── POST   /api/payroll/allowances
│   ├── GET    /api/payroll/dependents/{employee_id}
│   ├── POST   /api/payroll/dependents
│   ├── POST   /api/payroll/calculate?month=&year= - tính lương tháng
│   ├── GET    /api/payroll/periods?year=
│   ├── GET    /api/payroll/periods/{period_id}/payslips
│   ├── GET    /api/payroll/payslips/{employee_id}?year=
│   ├── PUT    /api/payroll/periods/{period_id}/confirm
│   ├── PUT    /api/payroll/periods/{period_id}/mark-paid
│   └── GET    /api/payroll/payslips/{payslip_id}/pdf
│
├── Bước 7: Payslip PDF Generation
│   ├── Dùng thư viện: reportlab hoặc weasyprint
│   ├── Template payslip tiếng Việt
│   ├── Lưu PDF vào MinIO
│   └── API download PDF
│
├── Bước 8: Gửi Payslip qua Email
│   ├── Tích hợp với Gmail module đã có
│   ├── POST /api/payroll/periods/{period_id}/send-payslips
│   ├── Gửi email + đính kèm PDF cho từng nhân viên
│   └── Dùng SendService từ gmail module
│
└── Bước 9: ARQ Cron Job
    ├── auto_calculate_payroll() - tự động tính lương ngày 25 hàng tháng
    └── remind_payroll_confirmation() - nhắc HR confirm bảng lương

Tuần 7: Frontend
├── Bước 10: Frontend pages
│   ├── /payroll - Dashboard lương (tổng quan kỳ lương)
│   ├── /payroll/config/{employee_id} - Cấu hình lương nhân viên
│   ├── /payroll/periods - Danh sách kỳ lương
│   ├── /payroll/periods/{id} - Chi tiết kỳ lương (bảng lương tất cả NV)
│   ├── /payroll/payslips/{employee_id} - Lịch sử phiếu lương
│   └── /payroll/insurance - Báo cáo BHXH
│
├── Bước 11: Components
│   ├── PayrollTable - bảng lương tổng hợp
│   ├── PayslipDetail - chi tiết phiếu lương
│   ├── SalaryConfigForm - form cấu hình lương
│   ├── AllowanceManager - quản lý phụ cấp
│   ├── DependentManager - quản lý người phụ thuộc
│   └── InsuranceReport - báo cáo BH
│
└── Bước 12: AI Đề xuất lương
    ├── API: POST /api/payroll/ai-suggest?position_id=&experience_years=
    ├── LLM prompt: phân tích vị trí + kinh nghiệm + lương hiện tại trong công ty
    ├── Response: { min, max, recommended, reasoning }
    └── Frontend: SalarySuggestionCard
```

---

## 5. Database Schema

### Attendance Module Tables

```sql
-- Loại nghỉ phép
CREATE TABLE leave_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,        -- 'annual', 'sick', 'unpaid', etc.
    display_name VARCHAR(100) NOT NULL,       -- 'Phép năm', 'Nghỉ ốm'
    default_days_per_year INT DEFAULT 0,
    is_paid BOOLEAN DEFAULT TRUE,
    requires_approval BOOLEAN DEFAULT TRUE,
    requires_document BOOLEAN DEFAULT FALSE,  -- cần giấy tờ (giấy bác sĩ)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Số ngày phép còn lại
CREATE TABLE leave_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    leave_type_id UUID NOT NULL REFERENCES leave_types(id),
    year INT NOT NULL,
    total_days DECIMAL(5,1) NOT NULL,         -- tổng ngày được phép
    used_days DECIMAL(5,1) DEFAULT 0,         -- đã sử dụng
    remaining_days DECIMAL(5,1) NOT NULL,     -- còn lại
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, leave_type_id, year)
);

-- Đơn xin nghỉ
CREATE TABLE leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    leave_type_id UUID NOT NULL REFERENCES leave_types(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days DECIMAL(5,1) NOT NULL,         -- số ngày nghỉ (trừ T7/CN)
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',     -- pending, approved, rejected, cancelled
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ca làm việc
CREATE TABLE work_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,               -- 'Ca hành chính', 'Ca sáng'
    start_time TIME NOT NULL,                 -- 08:00
    end_time TIME NOT NULL,                   -- 17:00
    break_minutes INT DEFAULT 60,             -- nghỉ trưa
    late_threshold_minutes INT DEFAULT 15,    -- >15 phút = đi muộn
    early_leave_threshold_minutes INT DEFAULT 15,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bản ghi chấm công
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    date DATE NOT NULL,
    schedule_id UUID REFERENCES work_schedules(id),
    check_in TIMESTAMPTZ,
    check_out TIMESTAMPTZ,
    work_hours DECIMAL(4,2),                  -- tổng giờ làm
    overtime_hours DECIMAL(4,2) DEFAULT 0,
    status VARCHAR(20) NOT NULL,              -- present, late, early_leave, absent, on_leave, holiday
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, date)
);

-- Đăng ký OT
CREATE TABLE overtime_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    date DATE NOT NULL,
    planned_hours DECIMAL(4,2) NOT NULL,
    actual_hours DECIMAL(4,2),
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending, approved, rejected
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ngày lễ
CREATE TABLE holidays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    name VARCHAR(200) NOT NULL,               -- 'Tết Nguyên Đán', 'Quốc khánh'
    is_recurring BOOLEAN DEFAULT FALSE,       -- lặp lại hàng năm
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Payroll Module Tables

```sql
-- Cấu hình lương nhân viên
CREATE TABLE salary_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    gross_salary DECIMAL(15,0) NOT NULL,      -- lương gross (VNĐ)
    insurance_salary DECIMAL(15,0) NOT NULL,  -- lương đóng BH (có thể khác gross)
    effective_date DATE NOT NULL,             -- ngày hiệu lực
    contract_type VARCHAR(20),                -- probation, official, part_time
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phụ cấp
CREATE TABLE allowances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    type VARCHAR(50) NOT NULL,                -- 'lunch', 'transport', 'phone', 'position'
    display_name VARCHAR(100) NOT NULL,
    amount DECIMAL(15,0) NOT NULL,
    is_taxable BOOLEAN DEFAULT FALSE,         -- có tính thuế không
    is_active BOOLEAN DEFAULT TRUE,
    effective_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Người phụ thuộc (giảm trừ gia cảnh)
CREATE TABLE dependents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    full_name VARCHAR(200) NOT NULL,
    relationship VARCHAR(50) NOT NULL,        -- 'child', 'parent', 'spouse'
    date_of_birth DATE,
    id_number VARCHAR(20),                    -- CCCD/CMND
    tax_code VARCHAR(20),                     -- MST người phụ thuộc
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Kỳ lương
CREATE TABLE payroll_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month INT NOT NULL,                       -- 1-12
    year INT NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',       -- draft, confirmed, paid
    total_gross DECIMAL(18,0) DEFAULT 0,
    total_net DECIMAL(18,0) DEFAULT 0,
    total_tax DECIMAL(18,0) DEFAULT 0,
    total_insurance DECIMAL(18,0) DEFAULT 0,
    employee_count INT DEFAULT 0,
    confirmed_by UUID REFERENCES users(id),
    confirmed_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(month, year)
);

-- Phiếu lương chi tiết
CREATE TABLE payslips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id),
    period_id UUID NOT NULL REFERENCES payroll_periods(id),
    
    -- Lương cơ bản
    gross_salary DECIMAL(15,0) NOT NULL,
    working_days INT NOT NULL,                -- số ngày công thực tế
    standard_days INT NOT NULL,               -- số ngày công chuẩn tháng đó
    
    -- Phụ cấp
    total_allowances DECIMAL(15,0) DEFAULT 0,
    allowances_detail JSONB,                  -- [{type, name, amount}]
    
    -- Overtime
    overtime_hours DECIMAL(5,2) DEFAULT 0,
    overtime_amount DECIMAL(15,0) DEFAULT 0,
    
    -- Bảo hiểm
    bhxh_employee DECIMAL(15,0) DEFAULT 0,    -- 8%
    bhyt_employee DECIMAL(15,0) DEFAULT 0,    -- 1.5%
    bhtn_employee DECIMAL(15,0) DEFAULT 0,    -- 1%
    total_insurance DECIMAL(15,0) DEFAULT 0,  -- 10.5%
    
    -- Thuế
    taxable_income DECIMAL(15,0) DEFAULT 0,
    personal_deduction DECIMAL(15,0) DEFAULT 0,  -- 11,000,000
    dependent_deduction DECIMAL(15,0) DEFAULT 0, -- 4,400,000 × n
    pit_amount DECIMAL(15,0) DEFAULT 0,       -- thuế TNCN
    
    -- Khấu trừ khác
    other_deductions DECIMAL(15,0) DEFAULT 0,
    deductions_detail JSONB,                  -- [{type, reason, amount}]
    
    -- Kết quả
    net_salary DECIMAL(15,0) NOT NULL,
    
    -- Meta
    pdf_path VARCHAR(500),                    -- path trên MinIO
    sent_at TIMESTAMPTZ,                      -- đã gửi email chưa
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, period_id)
);
```

---

## 6. API Endpoints Tổng Hợp

### Attendance Module

```
# Nghỉ phép
GET    /api/leave/types                              # Danh sách loại nghỉ
GET    /api/leave/balance/{employee_id}?year=        # Số ngày phép còn
GET    /api/leave/requests?employee_id=&status=&page= # Danh sách đơn nghỉ
POST   /api/leave/requests                           # Nộp đơn nghỉ
PUT    /api/leave/requests/{id}/approve              # Duyệt đơn
PUT    /api/leave/requests/{id}/reject               # Từ chối đơn
PUT    /api/leave/requests/{id}/cancel               # Hủy đơn
GET    /api/leave/calendar?department_id=&month=&year= # Lịch nghỉ team

# Chấm công
POST   /api/attendance/check-in                      # Check-in
POST   /api/attendance/check-out                     # Check-out
GET    /api/attendance/today                          # Trạng thái hôm nay
GET    /api/attendance/my-report?month=&year=         # Báo cáo cá nhân
GET    /api/attendance/report?employee_id=&month=&year= # Báo cáo NV (HR)
GET    /api/attendance/team?department_id=&date=      # Bảng chấm công team
GET    /api/attendance/export?month=&year=&format=xlsx # Export Excel
GET    /api/attendance/ai-alerts?department_id=       # AI cảnh báo bất thường

# Overtime
POST   /api/overtime/requests                        # Đăng ký OT
GET    /api/overtime/requests?status=&page=           # Danh sách OT
PUT    /api/overtime/requests/{id}/approve            # Duyệt OT
PUT    /api/overtime/requests/{id}/reject             # Từ chối OT

# Cấu hình
GET    /api/schedules                                # Danh sách ca
POST   /api/schedules                                # Tạo ca mới
GET    /api/holidays?year=                           # Danh sách ngày lễ
POST   /api/holidays                                 # Thêm ngày lễ
```

### Payroll Module

```
# Cấu hình lương
GET    /api/payroll/salary/{employee_id}             # Xem cấu hình lương
PUT    /api/payroll/salary/{employee_id}             # Cập nhật lương
GET    /api/payroll/salary/{employee_id}/history     # Lịch sử thay đổi lương

# Phụ cấp
GET    /api/payroll/allowances/{employee_id}         # Danh sách phụ cấp
POST   /api/payroll/allowances                       # Thêm phụ cấp
PUT    /api/payroll/allowances/{id}                  # Sửa phụ cấp
DELETE /api/payroll/allowances/{id}                  # Xóa phụ cấp

# Người phụ thuộc
GET    /api/payroll/dependents/{employee_id}         # Danh sách NPT
POST   /api/payroll/dependents                       # Thêm NPT
PUT    /api/payroll/dependents/{id}                  # Sửa NPT
DELETE /api/payroll/dependents/{id}                  # Xóa NPT

# Tính lương
POST   /api/payroll/calculate?month=&year=           # Tính lương tháng (batch)
GET    /api/payroll/preview/{employee_id}?month=&year= # Preview lương 1 NV
PUT    /api/payroll/periods/{period_id}/confirm      # Confirm bảng lương
PUT    /api/payroll/periods/{period_id}/mark-paid    # Đánh dấu đã trả

# Kỳ lương & Phiếu lương
GET    /api/payroll/periods?year=                    # Danh sách kỳ lương
GET    /api/payroll/periods/{period_id}              # Chi tiết kỳ lương
GET    /api/payroll/periods/{period_id}/payslips     # Tất cả payslip trong kỳ
GET    /api/payroll/payslips/{employee_id}?year=     # Payslip cá nhân
GET    /api/payroll/payslips/{payslip_id}/pdf        # Download PDF

# Gửi payslip
POST   /api/payroll/periods/{period_id}/send-payslips # Gửi email tất cả
POST   /api/payroll/payslips/{payslip_id}/send       # Gửi email 1 NV

# Bảo hiểm
GET    /api/payroll/insurance/report?month=&year=    # Báo cáo đóng BH
GET    /api/payroll/insurance/export?month=&year=    # Export BH (Excel)

# AI
POST   /api/payroll/ai-suggest                       # AI đề xuất lương
       Body: { position_id, experience_years, skills }
       Response: { min, max, recommended, reasoning }
```

---

## 7. AI Integration

### 7.1 AI Phát Hiện Bất Thường Chấm Công

**Cách hoạt động:**
1. Cron job chạy hàng ngày (hoặc HR trigger thủ công)
2. Lấy data chấm công 30 ngày gần nhất của phòng ban
3. Gửi cho LLM phân tích pattern
4. LLM trả về danh sách cảnh báo

**Prompt template:**
```
Bạn là hệ thống phân tích chấm công HR. Phân tích dữ liệu sau và trả về 
cảnh báo dạng JSON array.

Dữ liệu chấm công 30 ngày:
- Nhân viên: {name} ({employee_code})
- Số ngày đi muộn: {late_count}
- Số ngày về sớm: {early_leave_count}  
- Số ngày vắng không phép: {absent_count}
- Tổng OT: {total_ot_hours}h
- Pattern: {daily_status_list}

Trả về JSON:
[{
  "employee_id": "uuid",
  "alert_type": "frequent_late|excessive_ot|unauthorized_absence|pattern_change",
  "severity": "low|medium|high",
  "message": "Mô tả ngắn gọn bằng tiếng Việt",
  "recommendation": "Gợi ý hành động cho HR"
}]
```

**Fallback khi LLM không khả dụng:**
- Rule-based alerts: đi muộn >3 lần/tuần = cảnh báo
- Không block workflow, chỉ thiếu phần AI analysis

### 7.2 AI Đề Xuất Lương

**Cách hoạt động:**
1. HR nhập: vị trí, số năm kinh nghiệm, kỹ năng
2. System lấy data lương hiện tại của vị trí tương tự trong công ty
3. Gửi cho LLM phân tích + đề xuất

**Prompt template:**
```
Bạn là chuyên gia tư vấn lương HR tại Việt Nam. Dựa trên thông tin sau,
đề xuất mức lương phù hợp.

Vị trí: {position_name}
Phòng ban: {department_name}
Kinh nghiệm: {experience_years} năm
Kỹ năng: {skills}

Dữ liệu lương nội bộ (cùng vị trí/phòng ban):
- Trung bình: {avg_salary} VNĐ
- Thấp nhất: {min_salary} VNĐ
- Cao nhất: {max_salary} VNĐ
- Số nhân viên: {count}

Trả về JSON:
{
  "min_salary": number,
  "max_salary": number,
  "recommended_salary": number,
  "reasoning": "Giải thích ngắn gọn bằng tiếng Việt",
  "market_comparison": "Nhận xét so với thị trường"
}
```

---

## 8. Dependencies Cần Thêm

```toml
# Thêm vào pyproject.toml [project.dependencies]
"reportlab>=4.0.0",          # PDF generation cho payslip
# HOẶC
"weasyprint>=62.0",          # PDF generation (đẹp hơn, cần system deps)
```

**Lưu ý:** Các thư viện khác đã có sẵn:
- `openpyxl` → export Excel (chấm công, BH)
- `openai` → LLM adapter (AI alerts, AI suggest)
- `arq` → cron jobs (auto calculate, reminders)
- `aioboto3` / MinIO → lưu PDF payslip
- Gmail module → gửi payslip qua email

---

## 9. Frontend Routes Mới

```
frontend/src/app/(dashboard)/
├── leave/
│   ├── page.tsx              # Dashboard nghỉ phép
│   ├── request/page.tsx      # Form đăng ký nghỉ
│   ├── approve/page.tsx      # Duyệt đơn (HR)
│   └── calendar/page.tsx     # Lịch nghỉ team
├── attendance/
│   ├── page.tsx              # Check-in/out hôm nay
│   ├── report/page.tsx       # Báo cáo cá nhân
│   ├── team/page.tsx         # Bảng chấm công team (HR)
│   └── overtime/page.tsx     # Đăng ký/duyệt OT
├── payroll/
│   ├── page.tsx              # Dashboard lương
│   ├── config/[id]/page.tsx  # Cấu hình lương NV
│   ├── periods/page.tsx      # Danh sách kỳ lương
│   ├── periods/[id]/page.tsx # Chi tiết kỳ lương
│   ├── payslips/page.tsx     # Phiếu lương cá nhân
│   └── insurance/page.tsx    # Báo cáo BHXH
└── settings/
    ├── schedules/page.tsx    # Quản lý ca làm việc
    └── holidays/page.tsx     # Quản lý ngày lễ
```

---

## 10. Tổng Kết Timeline

| Phase | Nội dung | Thời gian | Phụ thuộc |
|-------|----------|-----------|-----------|
| 4A | Nghỉ phép | 2 tuần | Employee module (đã có) |
| 4B | Chấm công + AI alerts | 2 tuần | Phase 4A (leave balance) |
| 5A | Bảng lương + Payslip | 3 tuần | Phase 4B (attendance data cho tính công) |
| 5B | BHXH + AI đề xuất lương | 1 tuần | Phase 5A |
| **Tổng** | | **8 tuần** | |

### Thứ tự ưu tiên nếu thời gian hạn chế:
1. **Nghỉ phép** (độc lập, dùng ngay)
2. **Chấm công** (cần cho tính lương)
3. **Bảng lương** (cần chấm công)
4. **AI features** (bonus, có thể bỏ qua nếu gấp)


---

## 11. Luồng Hoạt Động Chi Tiết (Activity Flows)

### 11.1 Luồng Đăng Ký Nghỉ Phép

```mermaid
sequenceDiagram
    participant NV as Nhân viên
    participant FE as Frontend
    participant API as FastAPI
    participant LS as LeaveService
    participant BS as BalanceService
    participant DB as PostgreSQL
    participant HR as HR Manager

    NV->>FE: Mở form đăng ký nghỉ
    FE->>API: GET /api/leave/balance/{employee_id}?year=2026
    API->>BS: get_balance(employee_id, year)
    BS->>DB: SELECT FROM leave_balances WHERE employee_id AND year
    DB-->>BS: {annual: 12, used: 3, remaining: 9}
    BS-->>API: LeaveBalance
    API-->>FE: Hiển thị số ngày phép còn lại

    NV->>FE: Chọn loại nghỉ, ngày bắt đầu/kết thúc, lý do
    FE->>API: POST /api/leave/requests
    Note over API: Body: {employee_id, leave_type_id, start_date, end_date, reason}

    API->>LS: submit_request(data)
    LS->>LS: Validate: start_date <= end_date
    LS->>LS: Tính total_days (trừ T7, CN, ngày lễ)
    LS->>DB: SELECT FROM holidays WHERE date BETWEEN start AND end
    LS->>BS: check_sufficient_balance(employee_id, type, total_days)
    BS->>DB: SELECT remaining_days FROM leave_balances
    
    alt Không đủ ngày phép
        BS-->>LS: InsufficientBalanceError
        LS-->>API: 422 "Không đủ ngày phép"
        API-->>FE: Hiển thị lỗi
    end

    LS->>DB: INSERT INTO leave_requests (status='pending')
    LS-->>API: LeaveRequest (status=pending)
    API-->>FE: "Đã nộp đơn thành công"
    FE-->>NV: Thông báo đơn đang chờ duyệt

    Note over HR: HR nhận thông báo có đơn mới (hoặc vào trang approve)
    HR->>FE: Mở trang duyệt đơn
    FE->>API: GET /api/leave/requests?status=pending
    API-->>FE: Danh sách đơn chờ duyệt

    alt HR Duyệt
        HR->>FE: Click "Duyệt"
        FE->>API: PUT /api/leave/requests/{id}/approve
        API->>LS: approve_request(request_id, approved_by)
        LS->>DB: UPDATE leave_requests SET status='approved', approved_by, approved_at
        LS->>BS: deduct_balance(employee_id, type, total_days)
        BS->>DB: UPDATE leave_balances SET used_days += total_days, remaining -= total_days
        LS-->>API: LeaveRequest (status=approved)
        API-->>FE: "Đã duyệt"
    else HR Từ chối
        HR->>FE: Click "Từ chối" + nhập lý do
        FE->>API: PUT /api/leave/requests/{id}/reject
        API->>LS: reject_request(request_id, reason)
        LS->>DB: UPDATE leave_requests SET status='rejected', rejection_reason
        LS-->>API: LeaveRequest (status=rejected)
        API-->>FE: "Đã từ chối"
    end
```


### 11.2 Luồng Chấm Công Hàng Ngày

```mermaid
sequenceDiagram
    participant NV as Nhân viên
    participant FE as Frontend
    participant API as FastAPI
    participant AS as AttendanceService
    participant DB as PostgreSQL
    participant CRON as ARQ Cron Job

    Note over NV: === BUỔI SÁNG - CHECK IN ===

    NV->>FE: Mở trang chấm công, click "Check-in"
    FE->>API: POST /api/attendance/check-in
    Note over API: Headers: Authorization (JWT → lấy employee_id)

    API->>AS: check_in(employee_id)
    AS->>DB: SELECT FROM attendance_records WHERE employee_id AND date=TODAY
    
    alt Đã check-in rồi
        AS-->>API: 409 "Đã check-in hôm nay"
        API-->>FE: Hiển thị lỗi
    end

    AS->>DB: SELECT FROM work_schedules WHERE is_default=true
    Note over AS: schedule.start_time = 08:00, late_threshold = 15 phút
    
    AS->>AS: Xác định status
    Note over AS: now = 08:05 → present (trong threshold)<br/>now = 08:20 → late (quá 15 phút)

    AS->>DB: INSERT INTO attendance_records (employee_id, date, check_in=NOW, status)
    AS-->>API: AttendanceRecord {check_in: "08:05", status: "present"}
    API-->>FE: "Check-in thành công lúc 08:05"
    FE-->>NV: Hiển thị trạng thái + giờ check-in

    Note over NV: === BUỔI CHIỀU - CHECK OUT ===

    NV->>FE: Click "Check-out"
    FE->>API: POST /api/attendance/check-out

    API->>AS: check_out(employee_id)
    AS->>DB: SELECT FROM attendance_records WHERE employee_id AND date=TODAY
    
    alt Chưa check-in
        AS-->>API: 400 "Chưa check-in hôm nay"
    end
    alt Đã check-out rồi
        AS-->>API: 409 "Đã check-out hôm nay"
    end

    AS->>AS: Tính work_hours = check_out - check_in - break_minutes
    AS->>AS: Tính overtime = max(0, check_out - schedule.end_time)
    AS->>AS: Cập nhật status nếu về sớm

    AS->>DB: UPDATE attendance_records SET check_out=NOW, work_hours, overtime_hours, status
    AS-->>API: AttendanceRecord {check_out: "17:30", work_hours: 8.5, overtime: 0.5}
    API-->>FE: "Check-out thành công lúc 17:30"

    Note over CRON: === CUỐI NGÀY 23:00 - AUTO MARK ABSENT ===

    CRON->>AS: auto_mark_absent(date=TODAY)
    AS->>DB: SELECT employees WHERE is_active=true
    AS->>DB: SELECT employee_ids FROM attendance_records WHERE date=TODAY
    AS->>DB: SELECT employee_ids FROM leave_requests WHERE status='approved' AND date IN range
    
    Note over AS: Nhân viên không check-in VÀ không có đơn nghỉ = ABSENT
    
    AS->>DB: INSERT INTO attendance_records (status='absent') FOR EACH missing employee
    AS-->>CRON: Marked 2 employees as absent
```


### 11.3 Luồng Đăng Ký & Duyệt Overtime (OT)

```mermaid
sequenceDiagram
    participant NV as Nhân viên
    participant FE as Frontend
    participant API as FastAPI
    participant OTS as OvertimeService
    participant DB as PostgreSQL
    participant HR as HR Manager

    NV->>FE: Mở form đăng ký OT
    NV->>FE: Chọn ngày, số giờ dự kiến, lý do
    FE->>API: POST /api/overtime/requests
    Note over API: Body: {date, planned_hours: 2, reason: "Deploy release"}

    API->>OTS: submit_request(employee_id, data)
    OTS->>OTS: Validate: date >= today
    OTS->>OTS: Validate: planned_hours <= 4 (max OT/ngày)
    OTS->>DB: SELECT SUM(planned_hours) FROM overtime_requests WHERE employee AND week
    
    alt Vượt quá 20h OT/tuần
        OTS-->>API: 422 "Vượt giới hạn OT tuần (max 20h)"
    end

    OTS->>DB: INSERT INTO overtime_requests (status='pending')
    OTS-->>API: OvertimeRequest (status=pending)
    API-->>FE: "Đã đăng ký OT thành công"

    HR->>FE: Xem danh sách OT chờ duyệt
    FE->>API: GET /api/overtime/requests?status=pending
    
    HR->>FE: Click "Duyệt"
    FE->>API: PUT /api/overtime/requests/{id}/approve
    API->>OTS: approve(request_id, approved_by)
    OTS->>DB: UPDATE overtime_requests SET status='approved'
    OTS-->>API: OK

    Note over NV: Sau khi làm OT xong và check-out
    Note over OTS: Hệ thống tự động ghi nhận actual_hours<br/>từ attendance_records.overtime_hours
```


### 11.4 Luồng Tính Lương Hàng Tháng

```mermaid
sequenceDiagram
    participant HR as HR Manager
    participant FE as Frontend
    participant API as FastAPI
    participant PS as PayrollService
    participant TC as TaxCalculator
    participant DB as PostgreSQL
    participant MINIO as MinIO
    participant GMAIL as Gmail Module
    participant CRON as ARQ Cron

    Note over CRON: === NGÀY 25 HÀNG THÁNG (TỰ ĐỘNG) ===
    CRON->>PS: auto_calculate_payroll(month, year)
    Note over HR: HOẶC HR trigger thủ công:

    HR->>FE: Chọn tháng/năm, click "Tính lương"
    FE->>API: POST /api/payroll/calculate?month=5&year=2026
    API->>PS: calculate_all(month=5, year=2026)

    PS->>DB: SELECT * FROM employees WHERE is_active=true
    Note over PS: Lặp qua từng nhân viên:

    loop Cho mỗi nhân viên
        PS->>DB: SELECT FROM salary_configs WHERE employee_id AND is_current=true
        Note over PS: gross_salary = 25,000,000 VNĐ

        PS->>DB: SELECT FROM attendance_records WHERE employee_id AND month=5
        Note over PS: working_days = 21, standard_days = 22

        PS->>DB: SELECT FROM overtime_requests WHERE employee_id AND month=5 AND status='approved'
        Note over PS: approved_ot_hours = 8h

        PS->>DB: SELECT FROM allowances WHERE employee_id AND is_active=true
        Note over PS: lunch=700k, transport=500k, phone=200k = 1,400,000

        PS->>DB: SELECT FROM dependents WHERE employee_id AND is_active=true
        Note over PS: dependents_count = 1

        PS->>TC: calculate_insurance(gross=25M, insurance_salary=25M)
        Note over TC: BHXH = 25M × 8% = 2,000,000<br/>BHYT = 25M × 1.5% = 375,000<br/>BHTN = 25M × 1% = 250,000<br/>Tổng BH = 2,625,000

        PS->>TC: calculate_deduction(dependents=1)
        Note over TC: Bản thân = 11,000,000<br/>NPT = 4,400,000 × 1 = 4,400,000<br/>Tổng giảm trừ = 15,400,000

        PS->>PS: Tính lương theo ngày công
        Note over PS: Lương thực tế = 25M × (21/22) = 23,863,636<br/>OT = (25M/22/8) × 8h × 1.5 = 1,704,545<br/>Tổng thu nhập = 23,863,636 + 1,400,000 + 1,704,545 = 26,968,181

        PS->>TC: calculate_pit(taxable_income)
        Note over TC: Thu nhập chịu thuế = 26,968,181 - 2,625,000 - 15,400,000 = 8,943,181<br/>Thuế bậc 1: 5M × 5% = 250,000<br/>Thuế bậc 2: 3,943,181 × 10% = 394,318<br/>Tổng thuế TNCN = 644,318

        PS->>PS: Tính NET
        Note over PS: NET = 26,968,181 - 2,625,000 - 644,318 = 23,698,863

        PS->>DB: INSERT INTO payslips (all breakdown fields)
    end

    PS->>DB: INSERT/UPDATE payroll_periods (status='draft', totals)
    PS-->>API: PayrollPeriod {status: 'draft', employee_count: 45, total_net: 1.2B}
    API-->>FE: "Đã tính lương cho 45 nhân viên"

    Note over HR: === HR REVIEW & CONFIRM ===

    HR->>FE: Xem chi tiết bảng lương, kiểm tra
    FE->>API: GET /api/payroll/periods/{period_id}/payslips
    API-->>FE: Danh sách payslip tất cả NV

    HR->>FE: Click "Xác nhận bảng lương"
    FE->>API: PUT /api/payroll/periods/{period_id}/confirm
    API->>PS: confirm_period(period_id, confirmed_by)
    PS->>DB: UPDATE payroll_periods SET status='confirmed', confirmed_by, confirmed_at
    Note over PS: Sau khi confirm, không thể sửa payslip

    Note over HR: === GỬI PHIẾU LƯƠNG ===

    HR->>FE: Click "Gửi phiếu lương cho tất cả"
    FE->>API: POST /api/payroll/periods/{period_id}/send-payslips

    API->>PS: send_all_payslips(period_id)
    
    loop Cho mỗi payslip
        PS->>PS: generate_pdf(payslip_data)
        Note over PS: Dùng reportlab tạo PDF tiếng Việt
        PS->>MINIO: Upload PDF → payslips/{year}/{month}/{employee_code}.pdf
        MINIO-->>PS: file_path

        PS->>DB: UPDATE payslips SET pdf_path=file_path

        PS->>GMAIL: send_email(to=employee.email, subject="Phiếu lương T5/2026", attachment=pdf)
        Note over GMAIL: Dùng SendService đã có trong gmail module
        GMAIL-->>PS: sent OK

        PS->>DB: UPDATE payslips SET sent_at=NOW()
    end

    PS-->>API: {sent: 45, failed: 0}
    API-->>FE: "Đã gửi phiếu lương cho 45 nhân viên"

    Note over HR: === ĐÁNH DẤU ĐÃ TRẢ LƯƠNG ===

    HR->>FE: Click "Đánh dấu đã trả lương"
    FE->>API: PUT /api/payroll/periods/{period_id}/mark-paid
    API->>PS: mark_paid(period_id)
    PS->>DB: UPDATE payroll_periods SET status='paid', paid_at=NOW()
```


### 11.5 Luồng AI Phát Hiện Bất Thường Chấm Công

```mermaid
sequenceDiagram
    participant HR as HR Manager
    participant FE as Frontend
    participant API as FastAPI
    participant AIS as AIAlertService
    participant LLM as LLM Adapter
    participant DB as PostgreSQL
    participant CRON as ARQ Cron

    Note over CRON: === CHẠY TỰ ĐỘNG MỖI SÁNG 07:00 ===
    CRON->>AIS: generate_daily_alerts()

    Note over HR: HOẶC HR trigger thủ công:
    HR->>FE: Mở dashboard, click "Phân tích chấm công"
    FE->>API: GET /api/attendance/ai-alerts?department_id=xxx
    API->>AIS: analyze_department(department_id)

    AIS->>DB: SELECT employees WHERE department_id=xxx AND is_active=true
    AIS->>DB: SELECT attendance_records WHERE date >= (TODAY - 30 days)
    
    Note over AIS: Tổng hợp data cho mỗi nhân viên:
    Note over AIS: - late_count: số ngày đi muộn<br/>- early_leave_count: số ngày về sớm<br/>- absent_count: vắng không phép<br/>- total_ot_hours: tổng OT<br/>- pattern: [present, late, late, absent, present, ...]

    AIS->>AIS: Rule-based pre-filter (không cần LLM)
    Note over AIS: Nếu late_count >= 3/tuần → flag<br/>Nếu absent_count >= 2/tháng → flag<br/>Nếu total_ot > 20h/tuần → flag

    alt Có nhân viên bị flag
        AIS->>LLM: analyze_attendance_pattern(flagged_employees_data)
        Note over LLM: Prompt: Phân tích pattern + đề xuất hành động
        
        alt LLM khả dụng
            LLM-->>AIS: JSON alerts [{employee_id, alert_type, severity, message, recommendation}]
        else LLM không khả dụng (timeout/error)
            AIS->>AIS: Fallback: dùng rule-based alerts
            Note over AIS: Tạo alert từ rules:<br/>late >= 3 → "Đi muộn thường xuyên"<br/>absent >= 2 → "Vắng không phép nhiều"
        end
    end

    AIS->>DB: INSERT INTO attendance_alerts (alerts data)
    AIS-->>API: List[AttendanceAlert]
    API-->>FE: Hiển thị danh sách cảnh báo

    FE-->>HR: Cards cảnh báo với severity color:
    Note over FE: 🔴 HIGH: "Nguyễn Văn A - Vắng không phép 3 ngày trong tháng"<br/>🟡 MEDIUM: "Trần Thị B - Đi muộn 4/5 ngày tuần này"<br/>🟢 LOW: "Lê Văn C - OT 22h tuần này, cần theo dõi"

    HR->>FE: Click vào alert để xem chi tiết
    FE->>API: GET /api/attendance/report?employee_id=xxx&month=5&year=2026
    API-->>FE: Chi tiết chấm công 30 ngày
```


### 11.6 Luồng AI Đề Xuất Lương

```mermaid
sequenceDiagram
    participant HR as HR Manager
    participant FE as Frontend
    participant API as FastAPI
    participant SS as SalaryService
    participant LLM as LLM Adapter
    participant DB as PostgreSQL

    HR->>FE: Mở form đề xuất lương (khi tuyển mới hoặc review)
    HR->>FE: Nhập: vị trí, số năm KN, kỹ năng
    FE->>API: POST /api/payroll/ai-suggest
    Note over API: Body: {position_id, experience_years: 3, skills: ["Python", "FastAPI"]}

    API->>SS: get_salary_suggestion(position_id, experience_years, skills)

    SS->>DB: SELECT position.name, department.name FROM positions JOIN departments
    Note over SS: position = "Backend Developer", department = "Engineering"

    SS->>DB: SELECT gross_salary FROM salary_configs<br/>JOIN employees ON employee_id<br/>WHERE position_id = xxx AND is_current = true
    Note over SS: Lương nội bộ cùng vị trí:<br/>- NV1: 20,000,000<br/>- NV2: 25,000,000<br/>- NV3: 30,000,000<br/>- AVG: 25,000,000

    SS->>LLM: suggest_salary(context_data)
    Note over LLM: Prompt bao gồm:<br/>- Vị trí: Backend Developer<br/>- Phòng ban: Engineering<br/>- Kinh nghiệm: 3 năm<br/>- Kỹ năng: Python, FastAPI<br/>- Lương nội bộ: min 20M, max 30M, avg 25M

    LLM-->>SS: JSON response
    Note over LLM: {<br/>  "min_salary": 22000000,<br/>  "max_salary": 28000000,<br/>  "recommended_salary": 25000000,<br/>  "reasoning": "Với 3 năm KN Python/FastAPI...",<br/>  "market_comparison": "Mức đề xuất nằm trong<br/>  khoảng trung bình thị trường IT VN"<br/>}

    SS-->>API: SalarySuggestion
    API-->>FE: Hiển thị đề xuất

    FE-->>HR: Card đề xuất:
    Note over FE: 💰 Đề xuất: 25,000,000 VNĐ/tháng<br/>📊 Range: 22M - 28M<br/>📝 "Với 3 năm kinh nghiệm Python/FastAPI,<br/>mức 25M phù hợp với mặt bằng nội bộ<br/>và thị trường IT Việt Nam 2026"

    HR->>FE: Tham khảo và quyết định mức lương cuối cùng
    HR->>FE: Nhập lương vào form cấu hình
    FE->>API: PUT /api/payroll/salary/{employee_id}
```


### 11.7 Luồng Khởi Tạo Đầu Năm (Balance Initialization)

```mermaid
sequenceDiagram
    participant CRON as ARQ Cron (1/1 hàng năm)
    participant BS as BalanceService
    participant DB as PostgreSQL

    Note over CRON: === NGÀY 1/1 MỖI NĂM ===
    CRON->>BS: initialize_year_balances(year=2027)

    BS->>DB: SELECT * FROM employees WHERE is_active=true
    BS->>DB: SELECT * FROM leave_types

    loop Cho mỗi nhân viên
        BS->>BS: Tính số ngày phép năm
        Note over BS: base = 12 ngày<br/>seniority_bonus = (years_since_start / 5) × 1<br/>Ví dụ: start_date = 2020 → 7 năm → bonus = 1<br/>total_annual = 12 + 1 = 13 ngày

        BS->>DB: SELECT remaining_days FROM leave_balances<br/>WHERE employee_id AND year=2026 AND type='annual'
        Note over BS: Phép năm cũ chưa dùng: 3 ngày<br/>Chuyển sang năm mới (tối đa 5 ngày): min(3, 5) = 3

        BS->>DB: INSERT INTO leave_balances<br/>(employee_id, type='annual', year=2027, total=13+3=16, used=0, remaining=16)
        
        Note over BS: Các loại khác (sick, wedding, funeral) reset về default
        BS->>DB: INSERT INTO leave_balances (type='wedding', total=3, used=0, remaining=3)
        BS->>DB: INSERT INTO leave_balances (type='funeral', total=3, used=0, remaining=3)
    end

    BS-->>CRON: Initialized balances for 50 employees
```

### 11.8 Luồng Hủy Đơn Nghỉ Phép

```mermaid
sequenceDiagram
    participant NV as Nhân viên
    participant FE as Frontend
    participant API as FastAPI
    participant LS as LeaveService
    participant BS as BalanceService
    participant DB as PostgreSQL

    NV->>FE: Xem danh sách đơn nghỉ của mình
    FE->>API: GET /api/leave/requests?employee_id=me&status=approved
    API-->>FE: Danh sách đơn đã duyệt

    NV->>FE: Click "Hủy đơn" (chỉ được hủy nếu start_date > today)
    FE->>API: PUT /api/leave/requests/{id}/cancel

    API->>LS: cancel_request(request_id, employee_id)
    LS->>DB: SELECT FROM leave_requests WHERE id=request_id
    
    LS->>LS: Validate: request.start_date > TODAY
    alt Đã qua ngày nghỉ
        LS-->>API: 422 "Không thể hủy đơn đã qua ngày"
    end

    LS->>LS: Validate: status IN ('pending', 'approved')
    alt Đã bị từ chối/đã hủy
        LS-->>API: 422 "Đơn không ở trạng thái có thể hủy"
    end

    LS->>DB: UPDATE leave_requests SET status='cancelled'

    alt Đơn đã được duyệt (cần hoàn phép)
        LS->>BS: restore_balance(employee_id, leave_type_id, total_days)
        BS->>DB: UPDATE leave_balances SET used_days -= total_days, remaining += total_days
    end

    LS-->>API: LeaveRequest (status=cancelled)
    API-->>FE: "Đã hủy đơn nghỉ thành công"
```


### 11.9 Luồng Xem Phiếu Lương (Nhân viên)

```mermaid
sequenceDiagram
    participant NV as Nhân viên
    participant FE as Frontend
    participant API as FastAPI
    participant PS as PayrollService
    participant DB as PostgreSQL
    participant MINIO as MinIO

    NV->>FE: Mở trang "Phiếu lương của tôi"
    FE->>API: GET /api/payroll/payslips/{employee_id}?year=2026
    
    API->>PS: get_employee_payslips(employee_id, year)
    PS->>DB: SELECT payslips.* FROM payslips<br/>JOIN payroll_periods ON period_id<br/>WHERE employee_id AND year=2026<br/>ORDER BY month DESC
    
    DB-->>PS: List[Payslip]
    PS-->>API: List[PayslipResponse]
    API-->>FE: Danh sách phiếu lương theo tháng

    FE-->>NV: Bảng: Tháng | Gross | Net | Thuế | BH | Trạng thái
    Note over FE: T5/2026 | 25,000,000 | 23,698,863 | 644,318 | 2,625,000 | ✅ Đã trả<br/>T4/2026 | 25,000,000 | 23,500,000 | 700,000 | 2,625,000 | ✅ Đã trả

    NV->>FE: Click "Xem chi tiết" tháng 5
    FE->>API: GET /api/payroll/payslips/{payslip_id}/pdf
    
    API->>PS: get_payslip_pdf(payslip_id)
    PS->>DB: SELECT pdf_path FROM payslips WHERE id=payslip_id
    PS->>MINIO: Download file from pdf_path
    MINIO-->>PS: PDF binary data
    PS-->>API: Response(content=pdf, media_type="application/pdf")
    API-->>FE: PDF file download

    FE-->>NV: Mở/tải PDF phiếu lương
```

### 11.10 Luồng Báo Cáo BHXH Hàng Tháng

```mermaid
sequenceDiagram
    participant HR as HR Manager
    participant FE as Frontend
    participant API as FastAPI
    participant IS as InsuranceService
    participant DB as PostgreSQL

    HR->>FE: Mở trang "Báo cáo BHXH", chọn tháng 5/2026
    FE->>API: GET /api/payroll/insurance/report?month=5&year=2026

    API->>IS: generate_insurance_report(month=5, year=2026)

    IS->>DB: SELECT e.*, sc.insurance_salary<br/>FROM employees e<br/>JOIN salary_configs sc ON e.id = sc.employee_id<br/>WHERE e.is_active=true AND sc.is_current=true

    loop Cho mỗi nhân viên
        IS->>IS: Tính đóng BH
        Note over IS: insurance_salary = 25,000,000<br/><br/>Nhân viên đóng:<br/>- BHXH: 25M × 8% = 2,000,000<br/>- BHYT: 25M × 1.5% = 375,000<br/>- BHTN: 25M × 1% = 250,000<br/><br/>Công ty đóng:<br/>- BHXH: 25M × 17.5% = 4,375,000<br/>- BHYT: 25M × 3% = 750,000<br/>- BHTN: 25M × 1% = 250,000
    end

    IS-->>API: InsuranceReport
    Note over IS: {<br/>  total_employees: 45,<br/>  total_employee_contribution: 118,125,000,<br/>  total_company_contribution: 241,875,000,<br/>  total_combined: 360,000,000,<br/>  details: [{employee, bhxh, bhyt, bhtn, ...}]<br/>}

    API-->>FE: Hiển thị bảng báo cáo BH

    HR->>FE: Click "Export Excel"
    FE->>API: GET /api/payroll/insurance/export?month=5&year=2026&format=xlsx
    API->>IS: export_to_excel(report_data)
    Note over IS: Dùng openpyxl tạo file Excel<br/>theo mẫu D02-TS (mẫu BHXH VN)
    IS-->>API: Excel binary
    API-->>FE: Download file .xlsx
```


### 11.11 Luồng Tổng Hợp: Từ Chấm Công → Tính Lương (End-to-End)

```mermaid
flowchart TD
    A[Nhân viên check-in/out hàng ngày] --> B[attendance_records được tạo]
    B --> C{Cuối ngày 23:00}
    C --> D[Cron: auto_mark_absent]
    D --> E[Đánh absent cho NV không check-in]
    
    F[Nhân viên nộp đơn nghỉ] --> G[HR duyệt]
    G --> H[leave_balances cập nhật]
    H --> I[attendance_records: status=on_leave]
    
    J[Nhân viên đăng ký OT] --> K[HR duyệt OT]
    K --> L[overtime_requests: status=approved]
    
    B --> M{Ngày 25 hàng tháng}
    I --> M
    L --> M
    
    M --> N[Cron: auto_calculate_payroll]
    N --> O[Đọc attendance_records → tính working_days]
    O --> P[Đọc overtime_requests → tính OT hours]
    P --> Q[Đọc salary_configs → lương gross]
    Q --> R[Đọc allowances → phụ cấp]
    R --> S[Đọc dependents → giảm trừ gia cảnh]
    S --> T[TaxCalculator: tính BH + thuế TNCN]
    T --> U[Tạo payslip cho mỗi NV]
    U --> V[Tạo payroll_period: status=draft]
    
    V --> W{HR review}
    W -->|OK| X[Confirm period]
    W -->|Sửa| Y[HR chỉnh sửa thủ công]
    Y --> W
    
    X --> Z[Generate PDF payslips]
    Z --> AA[Upload PDF → MinIO]
    AA --> AB[Gửi email qua Gmail module]
    AB --> AC[Mark period: status=paid]
    
    style A fill:#e1f5fe
    style F fill:#e1f5fe
    style J fill:#e1f5fe
    style N fill:#fff3e0
    style T fill:#fce4ec
    style AB fill:#e8f5e9
    style AC fill:#c8e6c9
```

### 11.12 State Diagram: Trạng Thái Đơn Nghỉ Phép

```mermaid
stateDiagram-v2
    [*] --> pending: NV nộp đơn
    pending --> approved: HR duyệt
    pending --> rejected: HR từ chối
    pending --> cancelled: NV hủy đơn
    approved --> cancelled: NV hủy (nếu chưa đến ngày)
    rejected --> [*]
    cancelled --> [*]
    approved --> [*]: Ngày nghỉ đã qua

    note right of pending: Chờ HR duyệt
    note right of approved: Đã trừ ngày phép
    note right of cancelled: Đã hoàn ngày phép (nếu đã duyệt)
```

### 11.13 State Diagram: Trạng Thái Kỳ Lương

```mermaid
stateDiagram-v2
    [*] --> draft: Tính lương (auto/manual)
    draft --> draft: HR chỉnh sửa
    draft --> confirmed: HR xác nhận
    confirmed --> paid: Đã chuyển lương
    paid --> [*]

    note right of draft: Có thể sửa payslip
    note right of confirmed: Lock - không sửa được<br/>Gửi payslip email
    note right of paid: Hoàn tất kỳ lương
```

---

## 12. Error Handling & Edge Cases

### Chấm Công
| Case | Xử lý |
|------|--------|
| Check-in 2 lần/ngày | Return 409 Conflict |
| Check-out mà chưa check-in | Return 400 Bad Request |
| Check-in ngày lễ | Cho phép (tính OT) |
| Check-in khi đang nghỉ phép | Cho phép (override leave) |
| Quên check-out | Cron cuối ngày đánh dấu "missing_checkout", HR sửa thủ công |
| Nhân viên mới (chưa có schedule) | Dùng default schedule |

### Nghỉ Phép
| Case | Xử lý |
|------|--------|
| Nghỉ phép chồng ngày | Return 422 "Trùng ngày với đơn khác" |
| Hủy đơn đã qua ngày | Return 422 "Không thể hủy" |
| Nghỉ quá số ngày phép | Return 422 "Không đủ ngày phép" |
| Nghỉ nửa ngày | total_days = 0.5 (hỗ trợ decimal) |
| Nhân viên mới (chưa đủ năm) | Tính pro-rata: 12 × (months_worked/12) |

### Lương
| Case | Xử lý |
|------|--------|
| NV mới vào giữa tháng | Tính pro-rata theo ngày |
| NV nghỉ việc giữa tháng | Tính đến ngày cuối làm |
| Thay đổi lương giữa tháng | Tính theo effective_date (chia 2 phần) |
| Lương đóng BH vượt trần | Cap tại mức trần BHXH (20 × lương cơ sở) |
| Kỳ lương đã confirm, cần sửa | Phải tạo kỳ điều chỉnh (adjustment period) |
| LLM timeout khi suggest lương | Return rule-based suggestion (avg ± 20%) |


---

## 13. Nguồn Dữ Liệu Chấm Công

### 13.1 Các Cách Nhập Dữ Liệu Chấm Công Vào Hệ Thống

```mermaid
flowchart LR
    subgraph "Nguồn dữ liệu"
        A[Web App - Click nút]
        B[API trực tiếp]
        C[Import Excel]
        D[Máy chấm công vân tay]
        E[QR Code]
    end

    subgraph "Backend"
        F[POST /api/attendance/check-in]
        G[POST /api/attendance/import]
    end

    subgraph "Database"
        H[(attendance_records)]
    end

    A --> F
    B --> F
    C --> G
    D -->|Webhook/CSV sync| G
    E --> F

    F --> H
    G --> H
```

#### Cách 1: Check-in qua Web App (Đơn giản nhất - NÊN LÀM TRƯỚC)

```
Nhân viên đăng nhập → Vào trang /attendance → Click nút "Check-in"
```

**Flow:**
1. NV mở trình duyệt, đăng nhập hệ thống
2. Vào trang `/attendance`
3. Hệ thống hiển thị trạng thái hôm nay (chưa check-in / đã check-in)
4. NV click nút **"Check-in"** → gọi `POST /api/attendance/check-in`
5. Backend ghi nhận thời gian hiện tại = `check_in`
6. Chiều NV click **"Check-out"** → gọi `POST /api/attendance/check-out`
7. Backend ghi nhận `check_out`, tính `work_hours`, xác định `status`

**Ưu điểm:** Đơn giản, không cần phần cứng, phù hợp đồ án
**Nhược điểm:** NV có thể gian lận (nhờ người khác click)

**Chống gian lận (tùy chọn nâng cao):**
- Ghi nhận IP address khi check-in
- Giới hạn chỉ check-in từ IP công ty (whitelist IP)
- Ghi nhận User-Agent (thiết bị)

#### Cách 2: Check-in bằng QR Code (Nâng cao hơn)

```
HR tạo QR code hàng ngày → NV quét bằng điện thoại → Hệ thống ghi nhận
```

**Flow:**
1. Hệ thống tự động tạo QR code mới mỗi ngày (chứa token + date)
2. QR code hiển thị trên màn hình ở cửa văn phòng
3. NV dùng điện thoại quét QR → mở link `POST /api/attendance/check-in?token=xxx`
4. Backend verify token (hợp lệ + đúng ngày) → ghi nhận check-in

**Ưu điểm:** Khó gian lận hơn (phải có mặt tại văn phòng)
**Nhược điểm:** Cần thêm logic tạo/verify QR token

#### Cách 3: Import từ máy chấm công (Tích hợp phần cứng)

```
Máy vân tay ghi log → Export CSV/Excel → HR import vào hệ thống
```

**Flow:**
1. Máy chấm công vân tay ghi nhận giờ vào/ra
2. Cuối ngày/tuần, HR export file CSV từ máy
3. HR upload file vào hệ thống: `POST /api/attendance/import`
4. Backend parse file, map employee_code → tạo attendance_records

**Format CSV mẫu:**
```csv
employee_code,date,check_in,check_out
NV-001,2026-05-21,08:05:00,17:30:00
NV-002,2026-05-21,08:20:00,17:00:00
NV-003,2026-05-21,,
```

**Ưu điểm:** Chính xác nhất (sinh trắc học)
**Nhược điểm:** Cần phần cứng, phức tạp hơn

#### Cách 4: HR nhập thủ công (Backup)

```
HR mở bảng chấm công → Nhập/sửa giờ cho từng NV
```

**Flow:**
1. HR vào trang `/attendance/team`
2. Chọn ngày, thấy bảng lưới NV × trạng thái
3. Click vào ô của NV → nhập giờ check-in/out thủ công
4. Gọi `PUT /api/attendance/{record_id}` hoặc `POST /api/attendance/manual`

**Dùng khi:** NV quên check-in, máy hỏng, sửa sai

---

### 13.2 Khuyến Nghị Cho Đồ Án

**Nên implement theo thứ tự:**

| Ưu tiên | Cách | Lý do |
|---------|------|-------|
| 1️⃣ | Web App click nút | Đơn giản nhất, demo được ngay |
| 2️⃣ | HR nhập thủ công | Cần cho edge cases |
| 3️⃣ | Import CSV/Excel | Tận dụng pattern import đã có |
| 4️⃣ | QR Code | Nâng cao, ấn tượng khi demo |

---

### 13.3 Seed Data - Tạo Dữ Liệu Mẫu Để Test & Demo

#### Script seed attendance data

Tạo file: `backend/scripts/seed_attendance.py`

```python
"""Seed script: Tạo dữ liệu chấm công mẫu cho 1 tháng.

Chạy: python -m scripts.seed_attendance
Yêu cầu: Đã có employees trong DB (chạy sau khi import NV)
"""

import asyncio
import random
from datetime import date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Config
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/vroom_hr"
SEED_MONTH = 5       # Tháng 5
SEED_YEAR = 2026
WORK_START = time(8, 0)    # 08:00
WORK_END = time(17, 0)     # 17:00


def random_check_in() -> time:
    """Tạo giờ check-in ngẫu nhiên: 70% đúng giờ, 20% muộn, 10% sớm."""
    roll = random.random()
    if roll < 0.70:
        # Đúng giờ: 07:45 - 08:10
        minutes = random.randint(-15, 10)
    elif roll < 0.90:
        # Đi muộn: 08:16 - 09:00
        minutes = random.randint(16, 60)
    else:
        # Đi sớm: 07:30 - 07:44
        minutes = random.randint(-30, -16)
    
    total_minutes = 8 * 60 + minutes  # 08:00 + offset
    return time(total_minutes // 60, total_minutes % 60)


def random_check_out(check_in: time) -> time:
    """Tạo giờ check-out: 80% đúng giờ, 10% về sớm, 10% OT."""
    roll = random.random()
    if roll < 0.80:
        # Đúng giờ: 17:00 - 17:15
        minutes = random.randint(0, 15)
    elif roll < 0.90:
        # Về sớm: 16:30 - 16:59
        minutes = random.randint(-30, -1)
    else:
        # OT: 17:30 - 20:00
        minutes = random.randint(30, 180)
    
    total_minutes = 17 * 60 + minutes
    return time(min(total_minutes // 60, 23), total_minutes % 60)


def determine_status(check_in: time, check_out: time | None) -> str:
    """Xác định trạng thái dựa trên giờ check-in/out."""
    if check_in is None:
        return "absent"
    
    late_threshold = time(8, 15)
    early_threshold = time(16, 45)
    
    if check_in > late_threshold:
        return "late"
    if check_out and check_out < early_threshold:
        return "early_leave"
    return "present"


def calculate_work_hours(check_in: time, check_out: time) -> float:
    """Tính số giờ làm việc (trừ 1h nghỉ trưa)."""
    cin = datetime.combine(date.today(), check_in)
    cout = datetime.combine(date.today(), check_out)
    diff = (cout - cin).total_seconds() / 3600
    return max(0, diff - 1.0)  # Trừ 1h break


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


async def seed():
    """Main seed function."""
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession)

    async with session_maker() as session:
        # Lấy danh sách employees
        from sqlmodel import select, text
        result = await session.execute(
            text("SELECT id, employee_code FROM employees WHERE is_active = true")
        )
        employees = result.fetchall()
        
        if not employees:
            print("❌ Không có nhân viên nào! Hãy import NV trước.")
            return

        print(f"📋 Tìm thấy {len(employees)} nhân viên")

        # Tạo data cho mỗi ngày trong tháng
        start_date = date(SEED_YEAR, SEED_MONTH, 1)
        if SEED_MONTH == 12:
            end_date = date(SEED_YEAR + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(SEED_YEAR, SEED_MONTH + 1, 1) - timedelta(days=1)

        records_created = 0
        current_date = start_date

        while current_date <= end_date:
            if is_weekend(current_date):
                current_date += timedelta(days=1)
                continue

            for emp_id, emp_code in employees:
                # 5% chance vắng mặt
                if random.random() < 0.05:
                    await session.execute(
                        text("""
                            INSERT INTO attendance_records 
                            (id, employee_id, date, status, created_at, updated_at)
                            VALUES (gen_random_uuid(), :emp_id, :date, 'absent', NOW(), NOW())
                            ON CONFLICT (employee_id, date) DO NOTHING
                        """),
                        {"emp_id": emp_id, "date": current_date}
                    )
                    records_created += 1
                    continue

                check_in = random_check_in()
                check_out = random_check_out(check_in)
                status = determine_status(check_in, check_out)
                work_hours = calculate_work_hours(check_in, check_out)
                overtime = max(0, work_hours - 8.0)

                check_in_dt = datetime.combine(current_date, check_in)
                check_out_dt = datetime.combine(current_date, check_out)

                await session.execute(
                    text("""
                        INSERT INTO attendance_records 
                        (id, employee_id, date, check_in, check_out, 
                         work_hours, overtime_hours, status, created_at, updated_at)
                        VALUES (gen_random_uuid(), :emp_id, :date, :check_in, :check_out,
                                :work_hours, :overtime, :status, NOW(), NOW())
                        ON CONFLICT (employee_id, date) DO NOTHING
                    """),
                    {
                        "emp_id": emp_id,
                        "date": current_date,
                        "check_in": check_in_dt,
                        "check_out": check_out_dt,
                        "work_hours": round(work_hours, 2),
                        "overtime": round(overtime, 2),
                        "status": status,
                    }
                )
                records_created += 1

            current_date += timedelta(days=1)

        await session.commit()
        print(f"✅ Đã tạo {records_created} bản ghi chấm công cho tháng {SEED_MONTH}/{SEED_YEAR}")


if __name__ == "__main__":
    asyncio.run(seed())
```

#### Script seed leave data

Tạo file: `backend/scripts/seed_leave.py`

```python
"""Seed script: Tạo dữ liệu nghỉ phép mẫu.

Tạo:
- Leave types (6 loại)
- Leave balances cho tất cả NV (năm hiện tại)
- Một số leave requests mẫu (pending, approved, rejected)
"""

import asyncio
import random
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/vroom_hr"

LEAVE_TYPES = [
    ("annual", "Phép năm", 12, True, True, False),
    ("sick", "Nghỉ ốm", 30, True, True, True),
    ("unpaid", "Không lương", 0, False, True, False),
    ("maternity", "Thai sản", 180, True, True, True),
    ("wedding", "Kết hôn", 3, True, True, False),
    ("funeral", "Tang", 3, True, True, False),
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession)

    async with session_maker() as session:
        # 1. Tạo leave types
        for code, name, days, is_paid, requires_approval, requires_doc in LEAVE_TYPES:
            await session.execute(
                text("""
                    INSERT INTO leave_types (id, name, display_name, default_days_per_year, 
                                            is_paid, requires_approval, requires_document)
                    VALUES (gen_random_uuid(), :name, :display_name, :days, 
                            :is_paid, :requires_approval, :requires_doc)
                    ON CONFLICT (name) DO NOTHING
                """),
                {
                    "name": code,
                    "display_name": name,
                    "days": days,
                    "is_paid": is_paid,
                    "requires_approval": requires_approval,
                    "requires_doc": requires_doc,
                }
            )
        print("✅ Tạo leave types xong")

        # 2. Lấy leave_type IDs
        result = await session.execute(text("SELECT id, name FROM leave_types"))
        type_map = {row.name: row.id for row in result.fetchall()}

        # 3. Lấy employees
        result = await session.execute(
            text("SELECT id, start_date FROM employees WHERE is_active = true")
        )
        employees = result.fetchall()

        if not employees:
            print("❌ Không có nhân viên!")
            return

        # 4. Tạo leave balances cho năm hiện tại
        current_year = 2026
        for emp_id, start_date in employees:
            # Tính phép năm theo thâm niên
            if start_date:
                years_worked = (date.today() - start_date).days // 365
                annual_days = 12 + (years_worked // 5)
            else:
                annual_days = 12

            # Random đã dùng 0-5 ngày
            used = random.randint(0, min(5, annual_days))

            await session.execute(
                text("""
                    INSERT INTO leave_balances 
                    (id, employee_id, leave_type_id, year, total_days, used_days, remaining_days)
                    VALUES (gen_random_uuid(), :emp_id, :type_id, :year, :total, :used, :remaining)
                    ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
                """),
                {
                    "emp_id": emp_id,
                    "type_id": type_map["annual"],
                    "year": current_year,
                    "total": annual_days,
                    "used": used,
                    "remaining": annual_days - used,
                }
            )

            # Balance cho wedding, funeral
            for lt in ["wedding", "funeral"]:
                await session.execute(
                    text("""
                        INSERT INTO leave_balances 
                        (id, employee_id, leave_type_id, year, total_days, used_days, remaining_days)
                        VALUES (gen_random_uuid(), :emp_id, :type_id, :year, 3, 0, 3)
                        ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING
                    """),
                    {"emp_id": emp_id, "type_id": type_map[lt], "year": current_year}
                )

        print(f"✅ Tạo leave balances cho {len(employees)} nhân viên")

        # 5. Tạo một số leave requests mẫu
        statuses = ["approved", "approved", "approved", "pending", "rejected"]
        for i in range(min(15, len(employees))):
            emp_id = employees[i].id
            start = date(2026, random.randint(1, 5), random.randint(1, 28))
            days = random.randint(1, 3)
            end = start + timedelta(days=days - 1)
            status = random.choice(statuses)

            await session.execute(
                text("""
                    INSERT INTO leave_requests
                    (id, employee_id, leave_type_id, start_date, end_date, 
                     total_days, reason, status, created_at, updated_at)
                    VALUES (gen_random_uuid(), :emp_id, :type_id, :start, :end,
                            :days, :reason, :status, NOW(), NOW())
                """),
                {
                    "emp_id": emp_id,
                    "type_id": type_map["annual"],
                    "start": start,
                    "end": end,
                    "days": days,
                    "reason": random.choice([
                        "Việc gia đình", "Đi du lịch", "Khám bệnh", 
                        "Nghỉ ngơi", "Việc cá nhân"
                    ]),
                    "status": status,
                }
            )

        await session.commit()
        print(f"✅ Tạo leave requests mẫu xong")


if __name__ == "__main__":
    asyncio.run(seed())
```

#### Script seed payroll data

Tạo file: `backend/scripts/seed_payroll.py`

```python
"""Seed script: Tạo dữ liệu lương mẫu.

Tạo:
- Salary configs cho tất cả NV
- Allowances mẫu
- Dependents mẫu
"""

import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/vroom_hr"

# Mức lương theo vị trí (VNĐ)
SALARY_RANGES = {
    "default": (12_000_000, 20_000_000),
    "developer": (18_000_000, 35_000_000),
    "senior": (25_000_000, 45_000_000),
    "manager": (30_000_000, 50_000_000),
    "intern": (5_000_000, 8_000_000),
}

ALLOWANCE_TYPES = [
    ("lunch", "Phụ cấp ăn trưa", 730_000, False),
    ("transport", "Phụ cấp xăng xe", 500_000, False),
    ("phone", "Phụ cấp điện thoại", 200_000, False),
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, class_=AsyncSession)

    async with session_maker() as session:
        # Lấy employees
        result = await session.execute(
            text("""
                SELECT e.id, e.employee_code, e.start_date, p.name as position_name
                FROM employees e
                LEFT JOIN positions p ON e.position_id = p.id
                WHERE e.is_active = true
            """)
        )
        employees = result.fetchall()

        if not employees:
            print("❌ Không có nhân viên!")
            return

        for emp in employees:
            # Xác định range lương theo vị trí
            pos_name = (emp.position_name or "").lower()
            if "senior" in pos_name or "lead" in pos_name:
                salary_range = SALARY_RANGES["senior"]
            elif "manager" in pos_name or "trưởng" in pos_name:
                salary_range = SALARY_RANGES["manager"]
            elif "dev" in pos_name or "engineer" in pos_name:
                salary_range = SALARY_RANGES["developer"]
            elif "intern" in pos_name or "thực tập" in pos_name:
                salary_range = SALARY_RANGES["intern"]
            else:
                salary_range = SALARY_RANGES["default"]

            gross = random.randint(salary_range[0] // 1_000_000, 
                                   salary_range[1] // 1_000_000) * 1_000_000
            # Lương đóng BH thường = gross hoặc thấp hơn
            insurance_salary = min(gross, 36_000_000)  # Trần BH 2024

            # Tạo salary config
            await session.execute(
                text("""
                    INSERT INTO salary_configs
                    (id, employee_id, gross_salary, insurance_salary, 
                     effective_date, contract_type, is_current)
                    VALUES (gen_random_uuid(), :emp_id, :gross, :insurance,
                            :effective, 'official', true)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "emp_id": emp.id,
                    "gross": gross,
                    "insurance": insurance_salary,
                    "effective": emp.start_date or "2026-01-01",
                }
            )

            # Tạo allowances
            for atype, aname, amount, taxable in ALLOWANCE_TYPES:
                await session.execute(
                    text("""
                        INSERT INTO allowances
                        (id, employee_id, type, display_name, amount, 
                         is_taxable, is_active, effective_date)
                        VALUES (gen_random_uuid(), :emp_id, :type, :name, :amount,
                                :taxable, true, '2026-01-01')
                    """),
                    {
                        "emp_id": emp.id,
                        "type": atype,
                        "name": aname,
                        "amount": amount,
                        "taxable": taxable,
                    }
                )

            # 40% NV có người phụ thuộc
            if random.random() < 0.4:
                dep_count = random.randint(1, 2)
                for _ in range(dep_count):
                    await session.execute(
                        text("""
                            INSERT INTO dependents
                            (id, employee_id, full_name, relationship, 
                             effective_from, is_active)
                            VALUES (gen_random_uuid(), :emp_id, :name, :rel,
                                    '2026-01-01', true)
                        """),
                        {
                            "emp_id": emp.id,
                            "name": random.choice([
                                "Nguyễn Văn Con", "Trần Thị Mẹ", 
                                "Lê Văn Bố", "Phạm Thị Con"
                            ]),
                            "rel": random.choice(["child", "parent", "spouse"]),
                        }
                    )

        await session.commit()
        print(f"✅ Tạo salary configs + allowances + dependents cho {len(employees)} NV")


if __name__ == "__main__":
    asyncio.run(seed())
```

---

### 13.4 Thứ Tự Chạy Seed Scripts

```bash
# 1. Đảm bảo đã có employees (import Excel hoặc tạo thủ công)
# 2. Chạy migrations cho attendance + payroll tables
cd backend
alembic upgrade head

# 3. Seed theo thứ tự:
python -m scripts.seed_leave        # Tạo leave types + balances + requests
python -m scripts.seed_attendance   # Tạo attendance records 1 tháng
python -m scripts.seed_payroll      # Tạo salary configs + allowances + dependents
```

### 13.5 Dữ Liệu Mẫu Sẽ Tạo Ra

| Loại | Số lượng (giả sử 20 NV) | Mô tả |
|------|--------------------------|-------|
| Leave types | 6 | annual, sick, unpaid, maternity, wedding, funeral |
| Leave balances | 60 | 3 loại × 20 NV |
| Leave requests | 15 | Mix: approved, pending, rejected |
| Attendance records | ~440 | 20 NV × 22 ngày làm việc |
| Salary configs | 20 | 1 per NV |
| Allowances | 60 | 3 loại × 20 NV |
| Dependents | ~8 | 40% NV có 1-2 NPT |

### 13.6 Kết Quả Demo Sau Khi Seed

Với data mẫu, bạn có thể demo:
- ✅ Dashboard chấm công: thấy ai đi muộn, vắng mặt
- ✅ Báo cáo tháng: bảng lưới NV × ngày với color-coded status
- ✅ AI alerts: phát hiện NV đi muộn nhiều (data random sẽ có ~20% late)
- ✅ Tính lương: có đủ data attendance + salary để tính payslip
- ✅ Nghỉ phép: có đơn pending để demo duyệt/từ chối
