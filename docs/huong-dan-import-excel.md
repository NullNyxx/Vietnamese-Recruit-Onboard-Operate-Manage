# Hướng dẫn Import Nhân viên từ Excel

## Tổng quan

Tính năng Import Excel cho phép HR thêm hàng loạt nhân viên vào hệ thống từ file `.xlsx`. Hệ thống sẽ:
- **Tạo mới** nhân viên nếu email chưa tồn tại
- **Cập nhật** nhân viên nếu email đã tồn tại (upsert)
- **Báo lỗi** cho các dòng không hợp lệ mà không ảnh hưởng đến các dòng khác

---

## Chuẩn bị trước khi import

Không cần chuẩn bị gì! Hệ thống sẽ **tự động tạo** phòng ban và chức vụ nếu chúng chưa tồn tại.

Ví dụ: nếu file Excel có `department_name = "Engineering"` mà phòng ban "Engineering" chưa có trong hệ thống, hệ thống sẽ tự tạo phòng ban đó.

> **Lưu ý:** Hãy kiểm tra chính tả tên phòng ban/chức vụ trong file Excel. Nếu có typo (ví dụ "Enginering" thay vì "Engineering"), hệ thống sẽ tạo phòng ban mới với tên sai đó.

---

## Định dạng file Excel

File phải là định dạng `.xlsx` (Microsoft Excel). Dòng đầu tiên là header, các dòng tiếp theo là dữ liệu.

### Các cột hỗ trợ

| Cột | Tên cột | Bắt buộc | Mô tả | Ví dụ |
|-----|---------|----------|-------|-------|
| A | full_name | ✅ Có | Họ tên đầy đủ | Nguyen Van An |
| B | email | ✅ Có | Email (phải hợp lệ, duy nhất) | an.nguyen@company.com |
| C | phone | Không | Số điện thoại | 0901234567 |
| D | date_of_birth | Không | Ngày sinh | 1995-03-15 hoặc 15/03/1995 |
| E | gender | Không | Giới tính | male / female / other |
| F | address | Không | Địa chỉ | 123 Nguyen Hue, Q1, TP.HCM |
| G | department_name | Không | Tên phòng ban (phải khớp chính xác) | Engineering |
| H | position_name | Không | Tên chức vụ (phải khớp chính xác) | Senior Developer |
| I | start_date | Không | Ngày bắt đầu làm việc | 2024-01-15 hoặc 15/01/2024 |
| J | id_number | Không | Số CMND/CCCD (9 hoặc 12 số) | 079095001234 |
| K | tax_code | Không | Mã số thuế | 8001234567 |
| L | contract_type | Không | Loại hợp đồng | full_time / part_time / intern / contractor |

### Quy tắc về header

- Header **không phân biệt hoa thường** (ví dụ: `Full Name`, `full_name`, `FULL_NAME` đều được)
- Dấu cách trong header sẽ được chuyển thành `_` (ví dụ: `Full Name` → `full_name`)
- Các cột không nhận diện được sẽ bị bỏ qua (không gây lỗi)

### Định dạng ngày tháng

Hệ thống hỗ trợ 3 cách nhập ngày:

| Định dạng | Ví dụ |
|-----------|-------|
| YYYY-MM-DD | 1995-03-15 |
| DD/MM/YYYY | 15/03/1995 |
| Excel Date (native) | Ô được format là Date trong Excel |

---

## Cách thực hiện import

### Bước 1: Truy cập trang Import

Từ trang **Employees** (`/employees`), click nút **Import** ở góc trên phải, hoặc truy cập trực tiếp `/employees/import`.

### Bước 2: Chọn file

- **Kéo thả** file `.xlsx` vào vùng upload, hoặc
- **Click** nút "Select File" để chọn từ máy tính

### Bước 3: Upload & Import

Click nút **"Upload & Import"** để bắt đầu quá trình import.

### Bước 4: Xem kết quả

Sau khi import xong, hệ thống hiển thị:
- **Total Rows**: Tổng số dòng dữ liệu đã xử lý
- **Successful**: Số dòng import thành công
- **Errors**: Số dòng bị lỗi

Nếu có lỗi, bảng chi tiết sẽ hiển thị:
- Số dòng bị lỗi (tính từ dòng 2 trong Excel, vì dòng 1 là header)
- Nội dung lỗi cụ thể

---

## Các lỗi thường gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|-----|-------------|----------------|
| Missing required field: full_name | Ô full_name trống | Điền họ tên vào ô |
| Missing required field: email | Ô email trống | Điền email vào ô |
| Invalid email format | Email không đúng định dạng | Kiểm tra lại email (phải có @) |
| Invalid date format | Ngày không đúng định dạng | Dùng YYYY-MM-DD hoặc DD/MM/YYYY |

> **Lưu ý:** Phòng ban và chức vụ không còn gây lỗi — hệ thống sẽ tự tạo nếu chưa tồn tại.

---

## Logic Upsert (Tạo mới / Cập nhật)

- Hệ thống **match bằng email** để xác định nhân viên đã tồn tại hay chưa
- Nếu email **chưa tồn tại** → tạo nhân viên mới với mã NV-XXX tự động
- Nếu email **đã tồn tại** → cập nhật thông tin nhân viên (trừ email)
- Điều này cho phép bạn import lại file đã sửa mà không lo tạo trùng

---

## File mẫu

File mẫu có sẵn tại: `docs/sample_employee_import.xlsx`

File chứa 10 nhân viên mẫu với đầy đủ các trường. Bạn có thể dùng file này để test hoặc làm template.

---

## Giới hạn

- Chỉ hỗ trợ file `.xlsx` (không hỗ trợ `.xls`, `.csv`)
- Tối đa ~500 dòng mỗi lần import (MVP)
- Dòng hoàn toàn trống sẽ được bỏ qua tự động
- Mỗi dòng lỗi được báo riêng, không ảnh hưởng đến các dòng hợp lệ khác
