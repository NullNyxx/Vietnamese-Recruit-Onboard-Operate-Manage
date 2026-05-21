# Hướng Dẫn Sử Dụng: Chấm Công & Nghỉ Phép

> Dành cho HR - Tất cả thao tác đều do HR thực hiện trên hệ thống.

---

## Mục Lục

1. [Khởi Động Hệ Thống](#1-khởi-động-hệ-thống)
2. [Tạo Dữ Liệu Mẫu (Lần Đầu)](#2-tạo-dữ-liệu-mẫu-lần-đầu)
3. [Quản Lý Nghỉ Phép](#3-quản-lý-nghỉ-phép)
4. [Chấm Công](#4-chấm-công)
5. [Quản Lý Overtime](#5-quản-lý-overtime)
6. [Cài Đặt (Ca Làm Việc & Ngày Lễ)](#6-cài-đặt)
7. [Báo Cáo & Xuất Excel](#7-báo-cáo--xuất-excel)

---

## 1. Khởi Động Hệ Thống

### Bước 1: Start Docker (PostgreSQL + Redis + MinIO)
```bash
docker-compose -f docker-compose.infra.yml up -d
```

### Bước 2: Chạy migrations
```bash
cd backend
alembic upgrade head
```

### Bước 3: Start backend
```bash
cd backend
uvicorn src.main:app --reload --port 8000
```

### Bước 4: Start frontend
```bash
cd frontend
npm run dev
```

### Bước 5: Truy cập
- Frontend: http://localhost:3000
- Swagger API docs: http://localhost:8000/docs
- Đăng nhập bằng Google (email phải nằm trong `backend/config/whitelist.txt`)

---

## 2. Tạo Dữ Liệu Mẫu (Lần Đầu)

### Import nhân viên (bắt buộc trước khi dùng chấm công/nghỉ phép)
1. Vào **Nhân viên** → **Import**
2. Upload file `docs/sample_employee_import.xlsx`
3. Hệ thống tự tạo phòng ban + chức vụ + nhân viên

### Seed dữ liệu nghỉ phép
```bash
cd backend
python -m scripts.seed_leave
```
Kết quả: Tạo leave balances cho tất cả NV + 15 đơn nghỉ mẫu

### Seed dữ liệu chấm công (1 tháng)
```bash
cd backend
python -m scripts.seed_attendance
```
Kết quả: ~440 bản ghi chấm công (20 NV × 22 ngày) với phân bố thực tế

---

## 3. Quản Lý Nghỉ Phép

### 3.1 Xem danh sách đơn nghỉ

**Đường dẫn:** Sidebar → **Nghỉ phép**

Trang hiển thị:
- Số đơn chờ duyệt
- Tổng số đơn
- Bảng danh sách tất cả đơn nghỉ (có trạng thái màu)

### 3.2 Tạo đơn nghỉ phép (HR tạo thay NV)

**Đường dẫn:** Nghỉ phép → nút **"Tạo đơn nghỉ"**

Các bước:
1. Chọn **Nhân viên** từ dropdown
2. Chọn **Loại nghỉ** (Phép năm, Nghỉ ốm, Không lương, Thai sản, Kết hôn, Tang)
3. Chọn **Từ ngày** và **Đến ngày**
4. Nhập **Lý do** (tùy chọn)
5. Click **"Tạo đơn"**

> Hệ thống tự động:
> - Tính số ngày nghỉ (trừ T7/CN)
> - Kiểm tra trùng ngày với đơn khác
> - Kiểm tra số ngày phép còn lại

### 3.3 Duyệt đơn nghỉ

**Đường dẫn:** Nghỉ phép → cột **Hành động**

- Click ✅ (tick xanh) → **Duyệt** đơn → Tự động trừ ngày phép
- Click ❌ (X đỏ) → **Từ chối** → Nhập lý do (tùy chọn)

### 3.4 Hủy đơn nghỉ

Chỉ hủy được nếu ngày nghỉ **chưa bắt đầu**:
- Đơn đang pending → hủy bình thường
- Đơn đã approved → hủy + **hoàn lại ngày phép**

### 3.5 Xem lịch nghỉ team

**Đường dẫn:** Nghỉ phép → **Lịch nghỉ** (hoặc `/leave/calendar`)

- Hiển thị lịch tháng dạng grid
- Mỗi ô ngày hiển thị ai đang nghỉ
- Màu xanh = đã duyệt, vàng = chờ duyệt
- Navigate giữa các tháng bằng nút ◀ ▶

### 3.6 Khởi tạo ngày phép đầu năm

Gọi API (hoặc qua Swagger):
```
POST /api/leave/balance/initialize
Body: {
  "employee_id": "uuid-của-nhân-viên",
  "year": 2026,
  "start_date": "2023-01-15"  // ngày bắt đầu làm (tính thâm niên)
}
```

Hệ thống tự tính: 12 ngày + 1 ngày/5 năm thâm niên.

---

## 4. Chấm Công

### 4.1 Xem tổng quan chấm công hôm nay

**Đường dẫn:** Sidebar → **Chấm công**

Dashboard hiển thị:
- Số NV có mặt / đi muộn / vắng mặt
- Bảng chi tiết: giờ vào, giờ ra, giờ làm, OT, trạng thái

### 4.2 Nhập chấm công thủ công (HR)

**Đường dẫn:** Chấm công → nút **"Bảng chấm công"** → `/attendance/team`

Các bước:
1. Chọn **Nhân viên**
2. Chọn **Ngày**
3. Chọn **Trạng thái** (Có mặt / Đi muộn / Về sớm / Vắng mặt / Nghỉ phép)
4. Nhập **Giờ vào** (VD: 08:05)
5. Nhập **Giờ ra** (VD: 17:30)
6. Nhập **Ghi chú** (tùy chọn)
7. Click **"Lưu chấm công"**

> Nếu NV đã có record ngày đó → hệ thống **cập nhật** (không tạo trùng)

### 4.3 Check-in / Check-out qua API

Nếu muốn dùng nút check-in (cho NV tự bấm hoặc HR bấm):

```
POST /api/attendance/check-in
Body: { "employee_id": "uuid" }

POST /api/attendance/check-out
Body: { "employee_id": "uuid" }
```

Hệ thống tự động:
- Xác định trạng thái (đúng giờ / muộn) dựa trên ca làm việc
- Tính giờ làm = check_out - check_in - nghỉ trưa
- Tính OT = giờ ra - giờ kết thúc ca

### 4.4 Trạng thái chấm công

| Trạng thái | Ý nghĩa | Điều kiện |
|------------|----------|-----------|
| 🟢 Có mặt | Check-in đúng giờ | Vào trước 08:15 |
| 🟡 Đi muộn | Check-in trễ | Vào sau 08:15 |
| 🟠 Về sớm | Check-out sớm | Ra trước 16:45 |
| 🔴 Vắng mặt | Không check-in | Không có record + không có đơn nghỉ |
| 🔵 Nghỉ phép | Có đơn nghỉ approved | Tự động bởi cron job |
| 🟣 Ngày lễ | Ngày lễ công ty | Theo bảng holidays |

### 4.5 Cron Job tự động đánh absent

Chạy lúc **23:00 hàng ngày** (cần start worker):
```bash
arq src.modules.attendance.worker.WorkerSettings
```

Logic:
- Lấy tất cả NV active
- Trừ đi NV đã có attendance record hôm nay
- Trừ đi NV có đơn nghỉ approved
- Trừ đi ngày lễ
- Còn lại → đánh `absent`

---

## 5. Quản Lý Overtime

**Đường dẫn:** Chấm công → nút **"Overtime"** → `/attendance/overtime`

### 5.1 Đăng ký OT

1. Chọn **Nhân viên**
2. Chọn **Ngày OT**
3. Nhập **Số giờ** (tối đa 4h/ngày)
4. Nhập **Lý do**
5. Click **"Đăng ký OT"**

> Giới hạn: max 4h/ngày, max 20h/tuần

### 5.2 Duyệt / Từ chối OT

Trong bảng danh sách OT:
- Click ✅ → Duyệt
- Click ❌ → Từ chối

---

## 6. Cài Đặt

### 6.1 Quản lý Ngày lễ

**Đường dẫn:** Settings → **Ngày lễ** (`/settings/holidays`)

- Xem danh sách ngày lễ theo năm
- Thêm ngày lễ mới (tên + ngày + lặp hàng năm?)
- Xóa ngày lễ

> Ngày lễ VN 2026 đã được seed sẵn (Tết, 30/4, 1/5, 2/9, Giỗ Tổ)

### 6.2 Quản lý Ca làm việc

**Đường dẫn:** Settings → **Ca làm việc** (`/settings/schedules`)

- Xem danh sách ca hiện có
- Tạo ca mới: tên, giờ bắt đầu/kết thúc, nghỉ trưa, ngưỡng muộn/về sớm
- Đánh dấu ca mặc định

> Ca mặc định đã seed: "Ca hành chính" 08:00-17:00, nghỉ trưa 60 phút, ngưỡng muộn 15 phút

---

## 7. Báo Cáo & Xuất Excel

### 7.1 Báo cáo chấm công cá nhân

**Đường dẫn:** Chấm công → **Báo cáo** (`/attendance/report`)

1. Nhập **Employee ID** (UUID)
2. Chọn **Năm** và **Tháng**
3. Click **"Xem báo cáo"**

Hiển thị:
- 6 cards thống kê: ngày có mặt, muộn, vắng, nghỉ phép, tổng giờ, tổng OT
- Bảng chi tiết từng ngày trong tháng

### 7.2 Xuất Excel

Trong trang báo cáo, sau khi xem report:
- Click nút **"Xuất Excel"**
- File .xlsx tải về với:
  - Tiêu đề: "BẢNG CHẤM CÔNG THÁNG X/YYYY"
  - Tổng kết: ngày có mặt, muộn, vắng, giờ làm, OT
  - Bảng chi tiết: ngày, thứ, check-in, check-out, giờ làm, OT, trạng thái
  - Màu sắc theo trạng thái (xanh=có mặt, vàng=muộn, đỏ=vắng, xanh dương=nghỉ phép)

---

## Lưu Ý Quan Trọng

1. **Phải có nhân viên trong DB** trước khi dùng chấm công/nghỉ phép (import Excel)
2. **Phải khởi tạo balance** trước khi tạo đơn nghỉ phép (dùng seed script hoặc API initialize)
3. **Ngưỡng muộn/về sớm** có thể thay đổi trong Settings → Ca làm việc
4. **Cron job** cần chạy riêng (`arq src.modules.attendance.worker.WorkerSettings`)
5. **Tất cả thời gian** lưu theo UTC, hiển thị theo timezone Việt Nam (UTC+7)
