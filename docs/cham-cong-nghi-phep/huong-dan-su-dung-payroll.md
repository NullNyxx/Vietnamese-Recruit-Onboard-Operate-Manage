# Hướng Dẫn Sử Dụng Payroll

> Cập nhật: 2026-05-25
> Phạm vi: module payroll hiện tại trong dự án

---

## 1. Payroll hiện làm được gì

Module payroll hiện hỗ trợ:

- Tạo kỳ lương theo tháng/năm
- Tính lương từ dữ liệu chấm công
- Tính thuế TNCN sau khi trừ bảo hiểm
- Cộng phụ cấp chịu thuế và không chịu thuế đúng vào net
- Lấy OT từ các yêu cầu OT đã duyệt
- Xác nhận kỳ lương
- Gửi payslip PDF qua Gmail
- Tải PDF payslip
- Lưu PDF lên MinIO
- Đánh dấu kỳ lương đã chi trả

---

## 2. Điều kiện để payroll chạy đúng

Trước khi dùng payroll, cần có đủ các dữ liệu sau:

1. Có nhân viên trong bảng `employees`
2. Có cấu hình lương trong `salary_configs`
3. Có dữ liệu chấm công trong `attendance_records`
4. Nếu có OT thì OT phải ở trạng thái `approved`
5. MinIO phải chạy để lưu PDF payslip
6. Gmail OAuth của user gửi mail phải còn hợp lệ và có scope `gmail.send`

---

## 3. Luồng vận hành chuẩn

### Bước 1: Chấm công hằng ngày

- Nhân viên được chấm công đều mỗi ngày
- Nếu có OT, phải tạo yêu cầu OT và duyệt
- Payroll sẽ dựa vào:
  - ngày công thực tế từ `attendance_records`
  - OT đã duyệt từ `overtime_requests`

### Bước 2: Tạo hoặc dùng kỳ lương

- Vào màn hình payroll periods
- Tạo kỳ lương theo `month/year` nếu chưa có
- Ví dụ: tính lương tháng 5 năm 2026 thì tạo kỳ `5/2026`

### Bước 3: Tính lương

- Bấm `Tính lương`
- Hệ thống sẽ:
  - đọc lương gross và lương BH
  - đọc phụ cấp
  - đọc người phụ thuộc
  - đọc chấm công
  - đọc OT đã duyệt
  - tính tax, insurance, net
  - tạo payslip cho từng nhân viên

### Bước 4: Xác nhận kỳ lương

- Sau khi HR kiểm tra xong, bấm `Xác nhận`
- Kỳ lương chuyển sang trạng thái `confirmed`

### Bước 5: Gửi phiếu lương

- Bấm `Gửi phiếu lương`
- Hệ thống sẽ:
  - tạo PDF payslip
  - lưu PDF vào MinIO
  - gửi email đến từng nhân viên

### Bước 6: Đánh dấu đã chi trả

- Sau khi công ty trả lương thật xong, bấm `Đánh dấu đã chi trả`
- Kỳ lương chuyển sang trạng thái `paid`

---

## 4. Tự động hóa hiện tại

### Đang có cron gì

Hệ thống hiện có 2 cron payroll:

1. `auto_calculate_payroll`
   - chạy vào **ngày 25 hằng tháng lúc 00:00**
   - tự tạo hoặc lấy kỳ lương của **tháng trước đó**
   - tự tính payslip cho kỳ đó

2. `remind_payroll_confirmation`
   - chạy vào **ngày 27 hằng tháng lúc 09:00**
   - chỉ nhắc HR xác nhận kỳ lương còn ở trạng thái `draft`

### Chưa tự động cái gì

Hiện tại hệ thống **chưa tự động** các bước sau:

- chưa tự `confirm` kỳ lương
- chưa tự `send payslips`
- chưa tự `mark paid`

Nghĩa là hiện tại payroll đang là:

- **tự tính lương** vào ngày 25
- **không tự gửi mail** nếu HR chưa xác nhận và chưa bấm gửi

---

## 5. Trả lời câu hỏi vận hành thực tế

### Có phải chỉ cần chấm công đều, tới ngày là hệ thống tự tính lương và tự gửi mail luôn không?

**Chưa hẳn.**

Đúng hiện tại là:

- Nếu chấm công đầy đủ, đến **ngày 25 hằng tháng** hệ thống sẽ **tự tính lương cho tháng trước**

Nhưng chưa đúng ở phần này:

- Hệ thống **chưa tự gửi mail về cho nhân viên**
- HR vẫn cần:
  1. vào kiểm tra kỳ lương
  2. bấm `Xác nhận`
  3. bấm `Gửi phiếu lương`

### Ví dụ thực tế

- Ngày **25/06/2026 00:00**
- Hệ thống sẽ tự tính lương cho **tháng 05/2026**
- Sau đó HR vào xem
- Nếu số liệu ổn:
  - bấm `Xác nhận`
  - bấm `Gửi phiếu lương`
- Nhân viên mới nhận được email payslip

---

## 6. Khi nào nên dùng auto hoàn toàn

Chỉ nên bật tự gửi mail hoàn toàn khi:

- dữ liệu chấm công đã ổn định
- quy tắc OT đã chuẩn
- phụ cấp và người phụ thuộc đã chuẩn
- HR không cần kiểm tra tay trước khi gửi

Nếu chưa đạt mấy điều này, nên giữ flow hiện tại:

- auto calculate
- HR review
- HR confirm
- HR send payslips

---

## 7. Các nút thao tác chính

Trong màn hình chi tiết kỳ lương, các nút có ý nghĩa như sau:

- `Tính lương`: tạo lại payslip cho toàn bộ nhân viên của kỳ
- `Xác nhận`: khóa kỳ lương ở trạng thái đã duyệt
- `Gửi phiếu lương`: gửi email payslip hàng loạt
- `Đánh dấu đã chi trả`: đánh dấu kỳ lương đã được thanh toán

---

## 8. Những lưu ý quan trọng

- Nếu employee không có email hợp lệ thì gửi payslip sẽ fail cho employee đó
- Nếu Gmail grant hết hạn thì gửi mail sẽ fail
- Nếu MinIO không chạy thì PDF payslip có thể không lưu được
- Nếu OT chưa duyệt thì payroll sẽ không tính OT đó
- Nếu thiếu `salary_config` thì employee đó sẽ bị bỏ qua khi tính lương

---

## 9. Gợi ý vận hành thật

Khuyến nghị quy trình vận hành thực tế như sau:

1. Chấm công đầy đủ mỗi ngày
2. Duyệt hết OT trước ngày 25
3. Ngày 25 để hệ thống tự tính lương
4. Ngày 25-26 HR kiểm tra bảng lương
5. Ngày 26 hoặc 27 HR xác nhận kỳ lương
6. HR bấm gửi payslip cho nhân viên
7. Sau khi chuyển khoản xong thì bấm `Đánh dấu đã chi trả`

---

## 10. Trạng thái hiện tại của dự án

Tính đến ngày 2026-05-25:

- tính lương hoạt động
- gửi payslip hoạt động
- Gmail đã test gửi thành công
- cron auto-calculate hoạt động
- flow auto-send hoàn toàn chưa bật

---

## 11. Nếu muốn nâng cấp tiếp

Nếu muốn payroll vận hành gần như tự động hoàn toàn, bước tiếp theo nên làm là:

- thêm cờ cấu hình `auto_send_payslips`
- chỉ tự gửi khi kỳ lương đã pass rule kiểm tra
- thêm dashboard cảnh báo employee gửi fail
- thêm log/audit rõ cho từng mail đã gửi
- thêm retry queue cho mail lỗi

## 12. Quy tắc tính bảo hiểm

Hệ thống tính bảo hiểm theo tỷ lệ quy định Việt Nam:

### Tỷ lệ đóng BH người lao động (trừ vào lương gross)

| Loại BH | Tỷ lệ |
|--------|-------|
| BHXH   | 8%    |
| BHYT   | 1.5%  |
| BHTN   | 1%    |
| **Tổng** | **10.5%** |

Công thức:
```
BH phải đóng = Lương BH × 10.5%
```

### Tỷ lệ đóng BH đơn vị (doanh nghiệp trả thêm)

| Loại BH | Tỷ lệ |
|--------|-------|
| BHXH   | 17%   |
| BHYT   | 3%    |
| BHTN   | 2%    |
| **Tổng** | **21.5%** |

> **Lưu ý**: Hệ thống hiện chỉ tính phần đóng của **người lao động** (10.5%) trừ vào lương net. Phần đóng của doanh nghiệp (21.5%) hiện **chưa tính** vào chi phí công ty.

### Cách hệ thống dùng lương BH

- Mỗi nhân viên có trường `insurance_salary` trong `salary_config`
- Nếu không nhập, mặc định dùng `gross_salary`
- Hệ thống dùng `insurance_salary × 10.5%` để tính BH trừ vào lương

### Kiểm tra số liệu BH

Xem trong payslip chi tiết của từng nhân viên:
- Trường `insurance_premium` = số BH phải đóng
- Trường `total_insurance` trong kỳ lương = tổng BH của toàn bộ nhân viên
