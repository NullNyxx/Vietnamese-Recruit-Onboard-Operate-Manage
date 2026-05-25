# Hướng Dẫn Sử Dụng Hệ Thống Lương (Payroll)

## Mục Lục
1. [Thiết lập lương theo vị trí](#1-thiết-lập-lương-theo-vị-trí)
2. [Cấu hình lương cho nhân viên](#2-cấu-hình-lương-cho-nhân-viên)
3. [Quản lý phụ cấp](#3-quản-lý-phụ-cấp)
4. [Quản lý người phụ thuộc](#4-quản-lý-người-phụ-thuộc)
5. [Tính lương hàng tháng](#5-tính-lương-hàng-tháng)
6. [Xác nhận và chi trả](#6-xác-nhận-và-chi-trả)
7. [Tải phiếu lương](#7-tải-phiếu-lương)

---

## 1. Thiết lập lương theo vị trí

### Mục đích
Thiết lập bảng lương (salary band) cho từng chức vụ. Mỗi position có thể có nhiều grade (A/B/C/D) với các mức min-mid-max.

### Cách thực hiện
1. Vào **Settings → Positions**
2. Chọn một vị trí (VD: Senior Developer)
3. Thêm salary band:
   - **Grade A**: min 15M, mid 20M, max 25M
   - **Grade B**: min 20M, mid 25M, max 30M

### API
```
POST /api/salary/position-salaries
{
  "position_id": "uuid",
  "grade": "A",
  "min_salary": 15000000,
  "mid_salary": 20000000,
  "max_salary": 25000000,
  "effective_date": "2026-01-01"
}

GET /api/salary/positions/salary-suggestions
```

---

## 2. Cấu hình lương cho nhân viên

### Mục đích
Gán lương gross, lương bảo hiểm và loại hợp đồng cho từng nhân viên.

### Cách thực hiện
1. Vào **Employees → Danh sách nhân viên**
2. Chọn nhân viên
3. Click **Cấu hình lương** hoặc vào `/payroll/config/{employee_id}`
4. Nhập thông tin:
   - **Lương gross**: Lương chính (VD: 20,000,000 VNĐ)
   - **Lương BH**: Lương đóng bảo hiểm (thường = 90% gross)
   - **Loại hợp đồng**: Chính thức / Thử việc / Hợp đồng
   - **Ngày hiệu lực**: Ngày bắt đầu áp dụng

### API
```
POST /api/salary/config
{
  "employee_id": "uuid",
  "gross_salary": 20000000,
  "insurance_salary": 18000000,
  "contract_type": "official",
  "effective_date": "2026-01-01"
}

GET /api/salary/config/{employee_id}
PUT /api/salary/config/{employee_id}
```

---

## 3. Quản lý phụ cấp

### Các loại phụ cấp
- **telephone**: Điện thoại
- **transport**: Xăng xe
- **meal**: Cơm trưa
- **housing**: Nhà ở
- **responsibility**: Trách nhiệm
- **other**: Khác

### Cách thực hiện
1. Vào **/payroll/config/{employee_id}**
2. Phần **Phụ cấp** → Click **Thêm phụ cấp**
3. Chọn loại, nhập số tiền, chọn có chịu thuế không

### API
```
POST /api/salary/allowances
{
  "employee_id": "uuid",
  "allowance_type": "transport",
  "amount": 2000000,
  "is_taxable": true
}

GET /api/salary/allowances/{employee_id}
DELETE /api/salary/allowances/{allowance_id}
```

---

## 4. Quản lý người phụ thuộc

### Mục đích
Giảm trừ gia cảnh (4.4M/người/tháng) khi tính thuế TNCN.

### Cách thực hiện
1. Vào **/payroll/config/{employee_id}**
2. Phần **Người phụ thuộc** → Click **Thêm NPT**
3. Nhập: Tên, quan hệ, ngày sinh, có giảm trừ thuế không

### API
```
POST /api/salary/dependents
{
  "employee_id": "uuid",
  "name": "Người thân 1",
  "relationship": "vợ",
  "date_of_birth": "1990-01-01",
  "tax_dependent": true
}

GET /api/salary/dependents/{employee_id}
DELETE /api/salary/dependents/{dependent_id}
```

---

## 5. Tính lương hàng tháng

### Quy trình

#### Bước 1: Tạo kỳ lương
1. Vào **/payroll/periods**
2. Click **Tạo kỳ lương**
3. Chọn tháng/năm (VD: 5/2026)

#### Bước 2: Tính lương
1. Click vào kỳ lương vừa tạo
2. Click **Tính lương**

**Logic tính:**
```
1. Lấy attendance records trong tháng
2. Đếm ngày công:
   - present, late, early_leave, on_leave = 1 ngày công
   - absent, holiday = 0 ngày công

3. Tính lương:
   daily_rate = gross_salary / 26
   actual_gross = daily_rate × số ngày thực tế

4. Cộng:
   + Phụ cấp (allowances)
   + Tiền OT (overtime_hours × hệ số)

5. Trừ:
   - BHXH 8% + BHYT 1.5% + BHTN 1% = 10.5%
   - Thuế TNCN (lũy tiến 7 bậc)
   = LƯƠNG NET
```

#### Bước 3: Xem và chỉnh sửa
- Xem danh sách nhân viên và lương chi tiết
- Có thể điều chỉnh thủ công nếu cần

### API
```
POST /api/payroll/periods
{
  "month": 5,
  "year": 2026
}

POST /api/payroll/periods/{period_id}/calculate

GET /api/payroll/periods/{period_id}/employees
```

---

## 6. Xác nhận và chi trả

### Quy trình

1. **Review**: HR kiểm tra bảng lương
2. **Confirm**: Click **Xác nhận** → Trạng thái chuyển thành "Đã duyệt"
3. **Paid**: Sau khi chi trả, click **Đánh dấu đã chi trả** → Trạng thái "Đã chi trả"

### API
```
POST /api/payroll/periods/{period_id}/confirm?confirmed_by={user_id}
POST /api/payroll/periods/{period_id}/mark-paid
```

---

## 7. Tải phiếu lương

### Cho nhân viên
1. Vào **/payroll/payslips**
2. Xem lịch sử lương
3. Click **Download PDF** để tải phiếu lương chi tiết

### Nội dung PDF
- Thông tin nhân viên
- Lương gross, phụ cấp, OT
- Các khoản khấu trừ (BH, thuế)
- Lương net thực nhận

### API
```
GET /api/payroll/payslips/{employee_id}
GET /api/payroll/payslips/{payslip_id}/pdf
```

---

## Công thức tính lương chi tiết

### Lương ngày
```
Lương ngày = Lương gross ÷ 26 ngày
```

### Lương thực tế
```
Lương thực tế = Lương ngày × Số ngày đi làm thực tế
```

### Các khoản cộng (+)
| Khoản | Mô tả |
|-------|-------|
| Phụ cấp | Điện thoại, xăng xe, cơm trưa... |
| OT | Tiền làm thêm giờ |

### Các khoản trừ (-)
| Khoản | Tỷ lệ |
|-------|-------|
| BHXH | 8% |
| BHYT | 1.5% |
| BHTN | 1% |
| **Tổng BH** | **10.5%** |
| Thuế TNCN | Lũy tiến 7 bậc |

### Thuế TNCN (lũy tiến)
| Thu nhập/tháng | Thuế suất |
|---------------|-----------|
| ≤ 5M | 5% |
| 5M - 10M | 10% |
| 10M - 18M | 15% |
| 18M - 32M | 20% |
| 32M - 52M | 25% |
| 52M - 80M | 30% |
| > 80M | 35% |

### Giảm trừ
- Cá nhân: 11M/tháng
- Người phụ thuộc: 4.4M/người/tháng

### Lương Net
```
Net = Thực tế + Phụ cấp + OT - BH - Thuế TNCN
```

---

## Các trạng thái chấm công được tính công

| Status | Ngày công | Giải thích |
|--------|-----------|------------|
| present | ✅ 1 | Đi đúng giờ |
| late | ✅ 1 | Đi muộn (< 15p) |
| early_leave | ✅ 1 | Về sớm (< 15p) |
| on_leave | ✅ 1 | Nghỉ phép có phép (đã duyệt) |
| absent | ❌ 0 | Nghỉ không phép |
| holiday | ❌ 0 | Ngày lễ |

---

## Troubleshooting

### Lỗi không tính được lương
- Kiểm tra nhân viên đã có salary config chưa
- Vào `/payroll/config/{employee_id}` để thêm

### Lương bị sai
- Kiểm tra số ngày công trong attendance
- Kiểm tra phụ cấp đã thêm chưa
- Kiểm tra nghỉ phép đã duyệt chưa

### PDF không tải được
- Kiểm tra backend đang chạy
- Kiểm tra reportlab đã cài đặt

---

## Liên hệ hỗ trợ
Email: hr@vroom-hr.com
Hotline: 1900-xxxx