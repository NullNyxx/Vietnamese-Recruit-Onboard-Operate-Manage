# Thiết Kế Luồng Hoạt Động: Chấm Công & Tính Lương

## Tổng Quan

Hệ thống quản lý chấm công và tính lương tự động tính toán lương net từ lương gross dựa trên dữ liệu chấm công, phụ cấp, bảo hiểm và thuế thu nhập cá nhân.

## Sơ Đồ Luồng Tổng Thể

`
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   HR NHẬP LIỆU │────▶│ QUẢN LÝ NHÂN VIÊN│────▶│ CẤU HÌNH LƯƠNG  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ GỬI PHIẾU LƯƠNG│◀────│ XÁC NHẬN & CHI   │◀────│ TÍNH TOÁN LƯƠNG │
│    QUA EMAIL   │     │    TRẢ LƯƠNG    │     │    TỰ ĐỘNG      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               ▲                        ▲
                               │                        │
                        ┌──────┴──────┐           ┌──────┴──────┐
                        │  TẠO KỲ    │           │  CHẤM CÔNG  │
                        │  LƯƠNG    │           │   HÀNG NGÀY │
                        └───────────┘           └─────────────┘
`

## Chi Tiết Từng Bước

### 1. Quản Lý Nhân Viên (Employee)

**Entity:** Employee
- Thông tin cá nhân: mã NV, họ tên, email, phone, ngày sinh
- Phòng ban & chức vụ: department_id, position_id
- Thông tin hợp đồng: contract_type, start_date
- Thông tin thuế: tax_code

**Luồng:**
1. HR tạo nhân viên mới (thủ công hoặc import Excel)
2. Hệ thống tự sinh mã NV theo format NV-XXX
3. Nhân viên được gán phòng ban & chức vụ

---

### 2. Cấu Hình Lương (Salary Configuration)

**Entity:** SalaryConfig (1-1 với Employee)
- gross_salary: Lương gross thỏa thuận (VND)
- insurance_salary: Lương tính bảo hiểm (VND)
- contract_type: Loại hợp đồng (official/probation/contractor)
- effective_date: Ngày hiệu lực

**Entity:** Allowance (N-1 với Employee)
- Loại phụ cấp: telephone, transport, meal, housing, responsibility, other
- Số tiền: amount (VND)
- Chịu thuế: is_taxable (boolean)
- Thời gian: effective_date → end_date

**Entity:** Dependent (N-1 với Employee)
- Tên người phụ thuộc
- Quan hệ: vợ/chồng, con, cha/mẹ
- Ngày sinh
- Khai báo giảm trừ thuế: tax_dependent

**Luồng:**
1. HR tạo SalaryConfig cho nhân viên
2. HR thêm các Allowance (nếu có)
3. HR khai báo Dependent (nếu có)

---

### 3. Chấm Công Hàng Ngày (Attendance)

**Entity:** WorkSchedule
- Ca làm việc: start_time, end_time
- Thời gian nghỉ trưa: break_minutes
- Ngưỡng迟到: late_threshold_minutes
- Ngưỡng về sớm: early_leave_threshold_minutes

**Entity:** AttendanceRecord (1-1 employee-date)
- Ngày làm việc: work_date
- Check-in/Check-out: check_in, check_out
- Số giờ làm: work_hours
- Số giờ OT: overtime_hours
- Trạng thái: present, late, early_leave, on_leave, absent, holiday

**Entity:** OvertimeRequest
- Ngày làm OT: work_date
- Số giờ dự kiến: planned_hours
- Số giờ thực tế: actual_hours
- Lý do: reason
- Trạng thái: pending → approved/rejected

**Entity:** LeaveRequest
- Loại nghỉ: leave_type_id
- Thời gian: start_date → end_date
- Số ngày: total_days
- Lý do: reason
- Trạng thái: pending → approved/rejected/cancelled

**Entity:** LeaveBalance
- Số ngày nghỉ phép còn lại: remaining_days
- Số ngày đã dùng: used_days
- Theo năm & loại nghỉ

**Luồng chấm công:**
1. Nhân viên check-in/check-out hàng ngày
2. Hệ thống tự tính trạng thái dựa trên giờ làm vs schedule
3. HR tạo & duyệt OvertimeRequest
4. HR tạo & duyệt LeaveRequest → tự động trừ LeaveBalance
5. Hệ thống exclude Holiday khỏi ngày làm việc

---

### 4. Tạo Kỳ Lương (Payroll Period)

**Entity:** PayrollPeriod
- Tháng/Năm: month, year
- Trạng thái: draft → calculating → confirmed → paid
- Tổng lương gross/net/tax/insurance
- Ngày xác nhận: confirmed_at
- Ngày chi trả: paid_at

**Trạng thái kỳ lương:**
| Status | Mô tả |
|--------|-------|
| draft | Mới tạo, chờ tính lương |
| calculating | Đang tính lương |
| confirmed | Đã xác nhận bởi kế toán |
| paid | Đã chi trả |

**Luồng:**
1. HR tạo PayrollPeriod cho tháng mới
2. Kiểm tra nếu kỳ đã tồn tại → return existing
3. Kỳ mới có status = draft

---

### 5. Tính Toán Lương (Payroll Calculation)

**Flow tính lương cho từng nhân viên:**

`
┌─────────────────────────────────────────────────────────────────┐
│                    BẮT ĐẦU TÍNH LƯƠNG                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Lấy SalaryConfig│
                    │    của NV       │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính lương theo ngày công:  │
              │ daily_rate = gross_salary /  │
              │           standard_work_days│
              │ actual_gross = daily_rate ×  │
              │           actual_work_days   │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │    Tính phụ cấp (Allowance) │
              │ total_allowances = Σ amount  │
              │ taxable = chịu thuế          │
              │ non_taxable = không chịu thuế│
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   Tính overtime (OT)         │
              │ hourly_rate = daily_rate / 8 │
              │ ot_amount = hourly_rate ×    │
              │   ot_hours × hệ số           │
              │ (1.5 ngày thường, 2.0 CN,    │
              │  3.0 ngày lễ)                 │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính thu nhập gross:         │
              │ gross_income = actual_gross +│
              │   total_allowances + ot_amount│
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính bảo hiểm (Insurance):   │
              │ insurance_premium =          │
              │   insurance_salary × 10.5%   │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính giảm trừ (Deduction):  │
              │ personal = 11,000,000 VND    │
              │ dependent = 4,400,000 VND    │
              │           × số người phụ thuộc│
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính thu nhập chịu thuế:     │
              │ taxable_income =             │
              │   gross_salary + taxable_     │
              │   allowances + ot_amount -   │
              │   insurance_premium -         │
              │   personal - dependent        │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính thuế TNCN (Progressive)│
              │ Áp dụng biểu thuế lũy tiến   │
              │ từng phần (5% → 35%)         │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Tính lương net:              │
              │ net_salary = gross_income -  │
              │   income_tax - insurance_    │
              │   premium                    │
              └──────────────┬───────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Lưu Payslip    │
                    └─────────────────┘
`

**Bảng biểu thuế lũy tiến (Việt Nam):**

| Thu nhập tháng (VND) | Thuế suất |
|---------------------|-----------|
| 0 - 5,000,000       | 5%        |
| 5,000,001 - 10,000,000 | 10%    |
| 10,000,001 - 18,000,000 | 15%   |
| 18,000,001 - 32,000,000 | 20%   |
| 32,000,001 - 52,000,000 | 25%   |
| 52,000,001 - 80,000,000 | 30%   |
| > 80,000,000         | 35%      |

**Tỷ lệ bảo hiểm (người lao động):**
- BHXH: 8%
- BHYT: 1.5%
- BHTN: 1%
- **Tổng: 10.5%**

**Luồng tính toán hàng loạt:**
1. Cập nhật period status = calculating
2. Xóa payslip cũ của kỳ (nếu có)
3. Lấy danh sách nhân viên active
4. Với mỗi nhân viên:
   - Lấy AttendanceRecord trong tháng
   - Lấy OvertimeRequest đã duyệt trong tháng
   - Tính actual_work_days (present + late + early_leave + on_leave)
   - Tính total_ot_hours
   - Gọi calculate_employee_payslip()
   - Bỏ qua nếu chưa có SalaryConfig
5. Cộng tổng gross/net/tax/insurance
6. Cập nhật period status = draft
7. Return danh sách payslip

---

### 6. Xác Nhận & Chi Trả (Confirm & Pay)

**Xác nhận (Confirm):**
- Chỉ khi status = draft hoặc calculating
- Cập nhật status = confirmed
- Lưu confirmed_at, confirmed_by (user_id)

**Đánh dấu đã trả (Mark Paid):**
- Chỉ khi status = confirmed
- Cập nhật status = paid
- Lưu paid_at = datetime.now()

---

### 7. Gửi Phiếu Lương Qua Email

**Entity:** Payslip
- Tất cả các trường đã tính
- PDF URL (lưu trữ MinIO)

**Luồng gửi email:**
1. HR gọi API /periods/{period_id}/send-payslips
2. Với mỗi payslip:
   - Generate PDF nếu chưa có
   - Upload lên MinIO → lưu pdf_url
   - Gửi email cho nhân viên qua Gmail SMTP
3. Return số lượng email đã gửi

**API Endpoints:**

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | /api/payroll/periods | Tạo kỳ lương |
| GET | /api/payroll/periods | Danh sách kỳ |
| GET | /api/payroll/periods/{id} | Chi tiết kỳ |
| POST | /api/payroll/periods/{id}/calculate | Tính lương |
| POST | /api/payroll/periods/{id}/confirm | Xác nhận |
| POST | /api/payroll/periods/{id}/mark-paid | Đánh dấu đã trả |
| POST | /api/payroll/periods/{id}/send-payslips | Gửi email |
| GET | /api/payroll/periods/{id}/payslips | Danh sách phiếu lương |
| GET | /api/payroll/payslips/{id}/pdf | Tải PDF |

---

## Quan Hệ Giữa Các Entity

`
Employee (1)─────────────(1) SalaryConfig
      │                       
      │ (N)                   
      ▼                       
Allowance ──────────────────► Dependent
      │                       
      │ (N)                   
      ▼                       
PayrollPeriod (1)─────────(N) Payslip
      │
      │ (N)
      ▼
AttendanceRecord ──────────► OvertimeRequest
`

---

## Xử Lý Ngoại Lệ

| Exception | Mô tả |
|-----------|-------|
| SalaryNotConfiguredError | Nhân viên chưa có SalaryConfig |
| DuplicateSalaryConfigError | SalaryConfig đã tồn tại |
| PayrollPeriodNotFoundError | Kỳ lương không tồn tại |
| PeriodAlreadyConfirmedError | Kỳ đã xác nhận |
| PeriodAlreadyPaidError | Kỳ đã được đánh dấu trả |
| AllowanceNotFoundError | Phụ cấp không tồn tại |
| DependentNotFoundError | Người phụ thuộc không tồn tại |

---

## Các Tính Năng Tự Động

1. **Tính trạng thái chấm công**: So sánh check-in/out với WorkSchedule
2. **Trừ phép khi duyệt LeaveRequest**: Cập nhật LeaveBalance
3. **Tính lương hàng loạt**: Tự động cho tất cả nhân viên active
4. **Generate PDF**: Tự động tạo phiếu lương khi tải về
5. **Upload MinIO**: Lưu trữ PDF vĩnh viễn