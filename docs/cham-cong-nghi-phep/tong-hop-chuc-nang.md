# Tổng Hợp Chức Năng & Kế Hoạch Phát Triển

## Mục Lục
- [A. Chức Năng Đã Có](#a-chức-năng-đã-có)
- [B. Đề Xuất Chức Năng Mới Cho HR (Tích Hợp AI)](#b-đề-xuất-chức-năng-mới-cho-hr-tích-hợp-ai)
- [C. Lộ Trình Xây Dựng](#c-lộ-trình-xây-dựng)

---

## A. Chức Năng Đã Có

### 1. 🔐 Xác Thực & Phân Quyền (Identity Module)

| Chức năng | Mô tả |
|-----------|--------|
| Google OAuth2 Login | Đăng nhập qua tài khoản Google với PKCE |
| JWT + Refresh Token | Access token (15 phút) + Refresh token (7 ngày), lưu trong httpOnly cookie |
| Whitelist Email | Chỉ cho phép email trong danh sách trắng đăng nhập |
| Rate Limiting | Giới hạn số lần đăng nhập theo IP |
| Grant Status | Kiểm tra trạng thái kết nối Gmail/Calendar |
| Logout | Revoke token và xóa cookie |

### 2. 👥 Quản Lý Nhân Sự (Employee Module)

| Chức năng | Mô tả |
|-----------|--------|
| CRUD Nhân viên | Tạo, xem, sửa, xóa (soft-delete) nhân viên |
| Tìm kiếm & Lọc | Tìm theo tên/email, lọc theo phòng ban, vị trí, trạng thái |
| Phân trang | Hỗ trợ phân trang (page/page_size) |
| Import Excel | Import danh sách nhân viên từ file .xlsx |
| Promote Candidate | Chuyển ứng viên thành nhân viên chính thức |
| Quản lý Phòng ban | CRUD phòng ban (departments) |
| Quản lý Vị trí | CRUD vị trí/chức danh (positions) |
| Kho Tài liệu | Upload, download, xóa tài liệu nhân viên (CCCD, bằng cấp, hợp đồng...) lưu trên MinIO |

### 3. 📧 Tích Hợp Gmail (Gmail Module)

| Chức năng | Mô tả |
|-----------|--------|
| Kết nối Gmail OAuth2 | Kết nối/ngắt kết nối tài khoản Gmail |
| Đồng bộ Email | Đồng bộ email tự động + thủ công (rate limit 30s) |
| Xem danh sách Email | Liệt kê email với phân trang |
| Xem nội dung Email | Lấy body email (plain text + HTML) |
| Gửi Email | Soạn và gửi email qua Gmail (hỗ trợ HTML, CC, reply, đính kèm) |
| Quản lý Label | Gắn/gỡ label VroomHR trên email |
| Tải Attachment | Fetch và validate đính kèm từ email |
| Quota Tracking | Theo dõi quota sử dụng Gmail API |
| Audit Logging | Ghi log mọi thao tác Gmail |

### 4. 🎯 Tuyển Dụng (Recruitment Module)

| Chức năng | Mô tả |
|-----------|--------|
| **AI - Phân loại Email** | LLM tự động phân loại email thành: cv, partner, event, internal, other |
| **AI - Parse CV** | OCR + LLM trích xuất thông tin CV (tên, email, kỹ năng, kinh nghiệm, học vấn) |
| PII Redaction | Ẩn thông tin cá nhân trước khi gửi cho LLM |
| Candidate Pool | Danh sách ứng viên với tìm kiếm, lọc theo status/ngày/confidence/skills |
| Chi tiết Ứng viên | Xem đầy đủ thông tin + CV đã parse |
| Xem CV (Presigned URL) | Download CV gốc qua presigned URL (15 phút) |
| Lên lịch Phỏng vấn | Đặt lịch phỏng vấn cho ứng viên |
| Gửi Email Ứng viên | Gửi email trực tiếp cho ứng viên qua Gmail |
| Từ chối Ứng viên | Reject với lý do |
| Chấp nhận Ứng viên | Accept sau phỏng vấn |
| Lưu trữ Ứng viên | Archive ứng viên |
| **CV Review Queue** | Hàng đợi review CV bị lỗi parse/confidence thấp |
| Sửa CV thủ công | HR nhập lại thông tin CV đúng |
| Retry LLM Parse | Thử lại parse CV bằng LLM |
| Dismiss CV | Bỏ qua CV không hợp lệ |
| **Pipeline Metrics** | Thống kê: thời gian xử lý TB, tỷ lệ thành công/thất bại, queue depth |
| Confidence Score | Điểm tin cậy cho mỗi CV đã parse |
| Retention Job | Tự động dọn dẹp dữ liệu cũ |

### 5. 🖥️ Giao Diện Frontend (Next.js)

| Trang | Mô tả |
|-------|--------|
| Login | Trang đăng nhập Google OAuth |
| Dashboard | Trang chính sau đăng nhập |
| Employees | Danh sách nhân viên + tìm kiếm/lọc |
| Employee Detail | Chi tiết nhân viên (xem/sửa) |
| New Employee | Form tạo nhân viên mới |
| Import Employee | Import từ Excel |
| Gmail | Giao diện email tích hợp |
| Settings/Departments | Quản lý phòng ban |
| Settings/Positions | Quản lý vị trí |

---

## B. Đề Xuất Chức Năng Mới Cho HR (Tích Hợp AI)

### 🤖 Nhóm 1: AI-Powered Recruitment (Nâng cấp)

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 1.1 | **AI Matching Score** | So sánh CV ứng viên với Job Description, cho điểm phù hợp (0-100%) | 🔴 Cao |
| 1.2 | **AI Ranking** | Xếp hạng ứng viên theo mức độ phù hợp với vị trí tuyển | 🔴 Cao |
| 1.3 | **AI Soạn Email Template** | Tự động soạn email mời phỏng vấn, từ chối, offer dựa trên context | 🟡 Trung bình |
| 1.4 | **AI Tóm tắt CV** | Tạo bản tóm tắt ngắn gọn từ CV dài cho HR đọc nhanh | 🟡 Trung bình |
| 1.5 | **AI Đề xuất câu hỏi phỏng vấn** | Gợi ý câu hỏi phỏng vấn dựa trên CV và vị trí | 🟢 Thấp |
| 1.6 | **Job Description Generator** | AI tạo JD từ yêu cầu ngắn gọn của HR | 🟡 Trung bình |

### 📊 Nhóm 2: HR Analytics & Dashboard

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 2.1 | **Dashboard Tổng quan HR** | Biểu đồ: số NV theo phòng ban, tỷ lệ nghỉ việc, tuyển dụng pipeline | 🔴 Cao |
| 2.2 | **Báo cáo Tuyển dụng** | Thống kê: time-to-hire, conversion rate, source effectiveness | 🔴 Cao |
| 2.3 | **AI Dự đoán nghỉ việc** | Phân tích pattern để cảnh báo nhân viên có nguy cơ nghỉ | 🟢 Thấp |
| 2.4 | **Báo cáo Nhân sự** | Export báo cáo theo phòng ban, thâm niên, giới tính, tuổi | 🟡 Trung bình |

### 📋 Nhóm 3: Onboarding & Offboarding

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 3.1 | **Checklist Onboarding** | Danh sách việc cần làm khi nhân viên mới vào (tài liệu, thiết bị, training) | 🔴 Cao |
| 3.2 | **AI Tạo Onboarding Plan** | Tự động tạo kế hoạch onboarding dựa trên vị trí và phòng ban | 🟡 Trung bình |
| 3.3 | **Checklist Offboarding** | Quy trình khi nhân viên nghỉ (thu hồi thiết bị, bàn giao, exit interview) | 🟡 Trung bình |
| 3.4 | **Template Hợp đồng** | Tự động điền thông tin vào mẫu hợp đồng lao động | 🟡 Trung bình |

### ⏰ Nhóm 4: Chấm Công & Nghỉ Phép

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 4.1 | **Quản lý Nghỉ phép** | Đăng ký, duyệt, theo dõi ngày phép còn lại | 🔴 Cao |
| 4.2 | **Chấm công** | Check-in/out, tính giờ làm, overtime | 🟡 Trung bình |
| 4.3 | **Lịch làm việc** | Quản lý ca, lịch trực, ngày lễ | 🟡 Trung bình |
| 4.4 | **AI Phát hiện bất thường** | Cảnh báo chấm công bất thường (đi muộn liên tục, vắng không phép) | 🟢 Thấp |

### 💰 Nhóm 5: Lương & Phúc Lợi

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 5.1 | **Bảng lương** | Tính lương, phụ cấp, khấu trừ, thuế TNCN | 🟡 Trung bình |
| 5.2 | **Payslip** | Tạo và gửi phiếu lương cho nhân viên | 🟡 Trung bình |
| 5.3 | **BHXH/BHYT** | Quản lý bảo hiểm xã hội, y tế, thất nghiệp | 🟢 Thấp |
| 5.4 | **AI Đề xuất lương** | Gợi ý mức lương dựa trên thị trường và kinh nghiệm | 🟢 Thấp |

### 🎓 Nhóm 6: Đào Tạo & Phát Triển

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 6.1 | **Quản lý Đào tạo** | Tạo khóa học, đăng ký, theo dõi tiến độ | 🟡 Trung bình |
| 6.2 | **AI Đề xuất Training** | Gợi ý khóa đào tạo phù hợp dựa trên skill gap | 🟢 Thấp |
| 6.3 | **Đánh giá Năng lực** | KPI, OKR, đánh giá 360 độ | 🟡 Trung bình |
| 6.4 | **Career Path** | Lộ trình phát triển nghề nghiệp cho từng vị trí | 🟢 Thấp |

### 🤝 Nhóm 7: Giao Tiếp & Thông Báo

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 7.1 | **Thông báo nội bộ** | Gửi thông báo cho nhân viên/phòng ban | 🟡 Trung bình |
| 7.2 | **AI Chatbot HR** | Bot trả lời câu hỏi thường gặp về chính sách, quy trình | 🔴 Cao |
| 7.3 | **Lịch Google Calendar** | Tích hợp lịch phỏng vấn, meeting với Google Calendar | 🟡 Trung bình |
| 7.4 | **Nhắc nhở tự động** | Nhắc hết hạn hợp đồng, sinh nhật, anniversary | 🟡 Trung bình |

### 📄 Nhóm 8: Quản Lý Tài Liệu Nâng Cao

| # | Chức năng | Mô tả | Độ ưu tiên |
|---|-----------|--------|-------------|
| 8.1 | **AI OCR Tài liệu** | Scan và trích xuất thông tin từ CCCD, bằng cấp, hợp đồng | 🟡 Trung bình |
| 8.2 | **Nhắc hết hạn** | Cảnh báo tài liệu sắp hết hạn (CCCD, hợp đồng, visa) | 🔴 Cao |
| 8.3 | **E-Signature** | Ký điện tử cho hợp đồng, quyết định | 🟢 Thấp |
| 8.4 | **Version Control** | Quản lý phiên bản tài liệu | 🟢 Thấp |

---

## C. Lộ Trình Xây Dựng

### Phase 1: Nền tảng HR cơ bản (4-6 tuần)
> Ưu tiên: Hoàn thiện những gì đã có + thêm chức năng thiết yếu

- [ ] **2.1** Dashboard Tổng quan HR
- [ ] **3.1** Checklist Onboarding
- [ ] **4.1** Quản lý Nghỉ phép
- [ ] **8.2** Nhắc hết hạn tài liệu
- [ ] **2.2** Báo cáo Tuyển dụng

### Phase 2: AI Enhancement (4-6 tuần)
> Ưu tiên: Tận dụng LLM đã tích hợp để nâng cấp tuyển dụng

- [ ] **1.1** AI Matching Score (CV vs JD)
- [ ] **1.2** AI Ranking ứng viên
- [ ] **7.2** AI Chatbot HR
- [ ] **1.3** AI Soạn Email Template
- [ ] **1.6** Job Description Generator

### Phase 3: Vận hành HR (6-8 tuần)
> Ưu tiên: Chức năng vận hành hàng ngày

- [ ] **4.2** Chấm công
- [ ] **4.3** Lịch làm việc
- [ ] **5.1** Bảng lương
- [ ] **5.2** Payslip
- [ ] **3.3** Checklist Offboarding
- [ ] **3.4** Template Hợp đồng
- [ ] **7.3** Tích hợp Google Calendar

### Phase 4: Nâng cao & Tối ưu (6-8 tuần)
> Ưu tiên: Chức năng nâng cao, AI prediction

- [ ] **6.1** Quản lý Đào tạo
- [ ] **6.3** Đánh giá Năng lực (KPI/OKR)
- [ ] **2.4** Báo cáo Nhân sự nâng cao
- [ ] **7.1** Thông báo nội bộ
- [ ] **7.4** Nhắc nhở tự động
- [ ] **1.4** AI Tóm tắt CV
- [ ] **1.5** AI Đề xuất câu hỏi phỏng vấn
- [ ] **8.1** AI OCR Tài liệu

### Phase 5: Premium Features (8+ tuần)
> Ưu tiên: Chức năng cao cấp, dự đoán

- [ ] **2.3** AI Dự đoán nghỉ việc
- [ ] **4.4** AI Phát hiện bất thường chấm công
- [ ] **5.3** BHXH/BHYT
- [ ] **5.4** AI Đề xuất lương
- [ ] **6.2** AI Đề xuất Training
- [ ] **6.4** Career Path
- [ ] **8.3** E-Signature
- [ ] **8.4** Version Control tài liệu
- [ ] **3.2** AI Tạo Onboarding Plan

---

## Ghi Chú Kỹ Thuật

### AI/LLM Integration Strategy
- **LLM hiện tại**: OpenAI-compatible API qua 9Router (local endpoint `http://127.0.0.1:20128/v1`)
- **Mở rộng**: Có thể switch sang OpenAI GPT-4, Claude, hoặc Gemini qua cùng interface
- **Pattern**: Tất cả AI features sử dụng chung `LLMAdapter` pattern đã có
- **PII Safety**: Mọi dữ liệu gửi LLM đều qua `PIIRedactor` trước

### Tech Stack Hiện Tại
- **Backend**: FastAPI (Python) + SQLAlchemy + Alembic + PostgreSQL
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Storage**: MinIO (S3-compatible)
- **Auth**: Google OAuth2 + JWT
- **AI**: OpenAI SDK (async) + OCR
- **Background Jobs**: ARQ (Redis-based)
- **Architecture**: Clean Architecture (Domain → Application → Infrastructure → API)

### Nguyên Tắc Phát Triển
1. Mỗi chức năng mới = 1 module riêng biệt (hoặc mở rộng module hiện có)
2. AI features luôn có fallback khi LLM không khả dụng
3. Audit log cho mọi thao tác quan trọng
4. Rate limiting cho mọi endpoint public
5. PII protection cho mọi dữ liệu gửi bên thứ 3
