# Recruitment — Feature Spec

## 1. Tổng quan

Module Recruitment quản lý toàn bộ quy trình tuyển dụng từ nhận CV đến chấp nhận/từ chối ứng viên. Tích hợp AI pipeline để xử lý CV tự động: upload → OCR (olmOCR) → PII redaction → LLM parsing → confidence routing. Hỗ trợ CV review queue cho trường hợp AI không đủ tự tin, deduplication ứng viên, và recruitment metrics.

## 2. Actors

| Actor                 | Mô tả                                                             |
| --------------------- | ----------------------------------------------------------------- |
| **HR Admin**          | Quản lý candidates, review CV, schedule interviews, accept/reject |
| **System (Pipeline)** | Tự động xử lý CV: OCR → parse → route                             |
| **LLM Service**       | Parse CV text thành structured data                               |
| **olmOCR Service**    | Trích xuất text từ PDF/image                                      |

## 3. Luồng hoạt động (User Flows)

### 3.1 CV Processing Pipeline

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              CV Processing Pipeline (660s timeout)       │
                    │                                                         │
Upload CV ──►│ Validate │──►│ Upload MinIO │──►│ OCR │──►│ PII Redact │──►│ LLM Parse │
                    │                                                         │
                    │         confidence ≥ 0.7          confidence < 0.7       │
                    │              │                         │                 │
                    │              ▼                         ▼                 │
                    │     Auto-create Candidate      Add to Review Queue       │
                    │     (status: new)              (status: needs_review)    │
                    └─────────────────────────────────────────────────────────┘
```

### 3.2 Chi tiết Pipeline Steps

```
HR Admin                Backend                 MinIO        olmOCR       LLM
 │                        │                      │             │           │
 │── POST /candidates     │                      │             │           │
 │   {file: cv.pdf} ─────►│                      │             │           │
 │                        │── Validate file       │             │           │
 │                        │   (size ≤ 10MB,       │             │           │
 │                        │    mime: pdf/docx/    │             │           │
 │                        │    jpg/png)           │             │           │
 │                        │── Check duplicate     │             │           │
 │                        │   (by email if known) │             │           │
 │                        │── Upload file ────────►│             │           │
 │                        │◄─ object_key ─────────│             │           │
 │                        │── Create CVDocument   │             │           │
 │                        │   (status: pending)   │             │           │
 │◄─ 202 Accepted ───────│                      │             │           │
 │                        │                      │             │           │
 │                        │══ ASYNC PIPELINE ════│═════════════│═══════════│
 │                        │── Send to OCR ───────────────────►│           │
 │                        │   (status: ocr_processing)        │           │
 │                        │◄─ extracted_text ─────────────────│           │
 │                        │── PII redaction       │             │           │
 │                        │── Send to LLM ───────────────────────────────►│
 │                        │   (status: llm_parsing)           │           │
 │                        │◄─ {parsed_data, confidence} ─────────────────│
 │                        │                      │             │           │
 │                        │── IF confidence ≥ 0.7:            │           │
 │                        │   Create Candidate (status: new)  │           │
 │                        │   CVDocument → completed          │           │
 │                        │── ELSE:                           │           │
 │                        │   CVDocument → needs_review       │           │
 │                        │   Add to review queue             │           │
```

### 3.3 CV Review Flow

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── GET /cv-review/queue ───►│                          │
 │◄─ [{cv_id, parsed_data,   │◄─ needs_review items ───│
 │    confidence, raw_text}]  │                          │
 │                            │                          │
 │── POST /cv-review/{id}/    │                          │
 │   submit                   │                          │
 │   {corrected_data} ───────►│── Update parsed_data ───►│
 │                            │── Create Candidate ──────►│
 │                            │── Status → completed      │
 │◄─ 200 OK ─────────────────│                          │
 │                            │                          │
 │── POST /cv-review/{id}/    │                          │
 │   retry ──────────────────►│── Re-run LLM (60s) ─────►│
 │                            │── Update results          │
 │◄─ 200 {new_parsed_data} ──│                          │
 │                            │                          │
 │── POST /cv-review/{id}/    │                          │
 │   dismiss ────────────────►│── Status → dismissed ────►│
 │◄─ 200 OK ─────────────────│                          │
```

### 3.4 Candidate State Transitions

```
HR Admin                    Backend                    Database
 │                            │                          │
 │── PUT /candidates/{id}/    │                          │
 │   status                   │                          │
 │   {status: "reviewing"} ──►│── Validate transition ──►│
 │                            │── Update status ─────────►│
 │                            │── Write audit log ───────►│
 │◄─ 200 OK ─────────────────│                          │
```

## 4. Business Rules

1. **BR-01**: File CV tối đa 10MB, MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `image/jpeg`, `image/png`.
2. **BR-02**: Pipeline timeout tổng: 660 giây (11 phút). Nếu quá → status `failed`.
3. **BR-03**: Confidence threshold: `≥ 0.7` → auto-accept (tạo candidate), `< 0.7` → needs_review.
4. **BR-04**: Deduplication: nếu email đã tồn tại trong candidates → reject upload, trả về existing candidate.
5. **BR-05**: LLM retry timeout: 60 giây per attempt, tối đa 3 retries.
6. **BR-06**: PII redaction: mask số CCCD, số điện thoại trong raw text trước khi lưu.
7. **BR-07**: Presigned URL cho CV download hết hạn sau 15 phút (900s).
8. **BR-08**: Candidate chỉ có thể chuyển status theo allowed transitions (xem State Machine).
9. **BR-09**: Mọi status change phải ghi recruitment audit log.
10. **BR-10**: Data retention: rejected candidates bị xóa sau 90 ngày (configurable).
11. **BR-11**: Max parallel pipeline tasks: 3 (tránh overload LLM/OCR services).
12. **BR-12**: olmOCR hỗ trợ chunking: max 20 pages per chunk cho PDF lớn.

## 5. Data Model

### Candidate

| Field            | Type        | Constraints             | Mô tả                            |
| ---------------- | ----------- | ----------------------- | -------------------------------- |
| id               | UUID        | PK                      | ID duy nhất                      |
| full_name        | String(255) | NOT NULL                | Họ tên ứng viên                  |
| email            | String(255) | UNIQUE, NOT NULL        | Email ứng viên                   |
| phone            | String(20)  | NULLABLE                | Số điện thoại                    |
| status           | Enum        | NOT NULL, DEFAULT 'new' | Trạng thái hiện tại              |
| source           | String(100) | NULLABLE                | Nguồn (email, website, referral) |
| applied_position | String(255) | NULLABLE                | Vị trí ứng tuyển                 |
| parsed_data      | JSON        | NULLABLE                | Dữ liệu CV đã parse (structured) |
| notes            | Text        | NULLABLE                | Ghi chú của HR                   |
| interview_date   | DateTime    | NULLABLE                | Ngày phỏng vấn                   |
| rejection_reason | Text        | NULLABLE                | Lý do từ chối                    |
| created_at       | DateTime    | NOT NULL                | Thời điểm tạo                    |
| updated_at       | DateTime    | NOT NULL                | Thời điểm cập nhật               |

### CVDocument

| Field                   | Type        | Constraints                  | Mô tả                            |
| ----------------------- | ----------- | ---------------------------- | -------------------------------- |
| id                      | UUID        | PK                           | ID duy nhất                      |
| candidate_id            | UUID        | FK → candidates.id, NULLABLE | Candidate liên kết (sau khi tạo) |
| file_name               | String(255) | NOT NULL                     | Tên file gốc                     |
| file_size               | Integer     | NOT NULL                     | Kích thước (bytes)               |
| mime_type               | String(100) | NOT NULL                     | MIME type                        |
| object_key              | String(500) | NOT NULL                     | MinIO object key                 |
| processing_status       | Enum        | NOT NULL, DEFAULT 'pending'  | Trạng thái pipeline              |
| ocr_text                | Text        | NULLABLE                     | Text trích xuất từ OCR           |
| parsed_data             | JSON        | NULLABLE                     | Kết quả LLM parse                |
| confidence_score        | Float       | NULLABLE                     | Điểm tin cậy (0.0 - 1.0)         |
| error_message           | Text        | NULLABLE                     | Lỗi nếu pipeline fail            |
| processing_started_at   | DateTime    | NULLABLE                     | Bắt đầu xử lý                    |
| processing_completed_at | DateTime    | NULLABLE                     | Hoàn thành xử lý                 |
| created_at              | DateTime    | NOT NULL                     | Thời điểm upload                 |

### RecruitmentAuditLog

| Field        | Type        | Constraints                  | Mô tả                                      |
| ------------ | ----------- | ---------------------------- | ------------------------------------------ |
| id           | UUID        | PK                           | ID duy nhất                                |
| actor_id     | UUID        | FK → users.id, NULLABLE      | Người thực hiện (NULL = system)            |
| candidate_id | UUID        | FK → candidates.id, NOT NULL | Candidate liên quan                        |
| action       | String(100) | NOT NULL                     | Hành động (status_change, cv_upload, etc.) |
| old_value    | String(255) | NULLABLE                     | Giá trị cũ                                 |
| new_value    | String(255) | NULLABLE                     | Giá trị mới                                |
| details      | JSON        | NULLABLE                     | Chi tiết bổ sung                           |
| created_at   | DateTime    | NOT NULL                     | Thời điểm                                  |

## 6. State Machine

### Candidate Status

```
                              ┌──────────────────┐
                              │       new        │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                    ┌─────────│    reviewing     │─────────┐
                    │         └──────────────────┘         │
                    │                  │                    │
                    ▼                  ▼                    ▼
         ┌──────────────┐   ┌──────────────────┐   ┌──────────┐
         │   rejected   │   │interview_scheduled│   │ accepted │
         └──────┬───────┘   └────────┬─────────┘   └────┬─────┘
                │                    │                    │
                │                    ▼                    │
                │           ┌──────────────────┐         │
                │           │    accepted      │         │
                │           └──────────────────┘         │
                │                    │                    │
                ▼                    ▼                    ▼
         ┌──────────────────────────────────────────────────────┐
         │                      archived                         │
         └──────────────────────────────────────────────────────┘
```

**Allowed Transitions:**

| From                | To                  | Điều kiện                    |
| ------------------- | ------------------- | ---------------------------- |
| new                 | reviewing           | HR bắt đầu xem xét           |
| reviewing           | interview_scheduled | Đặt lịch phỏng vấn           |
| reviewing           | accepted            | Chấp nhận trực tiếp          |
| reviewing           | rejected            | Từ chối                      |
| interview_scheduled | accepted            | Phỏng vấn đạt                |
| interview_scheduled | rejected            | Phỏng vấn không đạt          |
| accepted            | archived            | Đã promote hoặc archive      |
| rejected            | archived            | Archive sau retention period |

**Forbidden Transitions:**

- `new` → `accepted` (phải qua reviewing)
- `rejected` → `accepted` (phải tạo candidate mới)
- `archived` → bất kỳ status nào (terminal state)

### CV Processing Status

```
pending → ocr_processing → llm_parsing → completed
                                       → needs_review → completed (after review)
                                                     → dismissed
         (any stage) → failed (on error/timeout)
```

## 7. API Endpoints

### Candidates

| Method | Path                                      | Mô tả                                        | Auth  |
| ------ | ----------------------------------------- | -------------------------------------------- | ----- |
| GET    | `/api/recruitment/candidates`             | Danh sách candidates (paginated, filterable) | Admin |
| POST   | `/api/recruitment/candidates`             | Upload CV + tạo pipeline                     | Admin |
| GET    | `/api/recruitment/candidates/{id}`        | Chi tiết candidate                           | Admin |
| PUT    | `/api/recruitment/candidates/{id}`        | Cập nhật thông tin candidate                 | Admin |
| PUT    | `/api/recruitment/candidates/{id}/status` | Chuyển trạng thái                            | Admin |
| GET    | `/api/recruitment/candidates/{id}/cv`     | Download CV (presigned URL)                  | Admin |
| DELETE | `/api/recruitment/candidates/{id}`        | Xóa candidate + CV                           | Admin |

### CV Review

| Method | Path                                      | Mô tả                           | Auth  |
| ------ | ----------------------------------------- | ------------------------------- | ----- |
| GET    | `/api/recruitment/cv-review/queue`        | Danh sách CV cần review         | Admin |
| GET    | `/api/recruitment/cv-review/{id}`         | Chi tiết CV review item         | Admin |
| POST   | `/api/recruitment/cv-review/{id}/submit`  | Submit corrected data           | Admin |
| POST   | `/api/recruitment/cv-review/{id}/retry`   | Retry LLM parsing (60s timeout) | Admin |
| POST   | `/api/recruitment/cv-review/{id}/dismiss` | Dismiss (bỏ qua)                | Admin |

### Metrics

| Method | Path                                  | Mô tả                                     | Auth  |
| ------ | ------------------------------------- | ----------------------------------------- | ----- |
| GET    | `/api/recruitment/metrics`            | Recruitment metrics overview              | Admin |
| GET    | `/api/recruitment/metrics/processing` | Avg processing time, success/failure rate | Admin |
| GET    | `/api/recruitment/metrics/pipeline`   | Queue depth, active tasks                 | Admin |

## 8. Edge Cases & Error Handling

| Scenario                        | Xử lý                                                       |
| ------------------------------- | ----------------------------------------------------------- |
| Duplicate email khi upload CV   | 409 `CANDIDATE_EMAIL_EXISTS` — trả về existing candidate ID |
| Pipeline timeout (> 660s)       | CVDocument status → `failed`, error_message ghi timeout     |
| OCR service unavailable         | Retry 3 lần với exponential backoff, sau đó → `failed`      |
| LLM service unavailable         | Retry 3 lần, sau đó → `failed`                              |
| LLM trả về invalid JSON         | Status → `needs_review`, lưu raw response                   |
| File corrupt (không OCR được)   | Status → `failed`, error: `OCR_EXTRACTION_FAILED`           |
| Confidence = 0.7 exactly        | Auto-accept (threshold là `>=`)                             |
| MinIO unavailable khi upload    | 503 `STORAGE_UNAVAILABLE`                                   |
| Concurrent pipeline tasks > max | Queue thêm, xử lý khi có slot                               |
| CV review retry cũng fail       | Giữ status `needs_review`, tăng retry_count                 |
| Candidate đã archived bị update | 409 `CANDIDATE_ARCHIVED`                                    |
| Invalid status transition       | 422 `INVALID_STATUS_TRANSITION`                             |

## 9. Integration Points

| Module               | Cách tích hợp                                                                           |
| -------------------- | --------------------------------------------------------------------------------------- |
| **Employee**         | Candidate accepted → promote thành Employee qua `/api/employees/promote/{candidate_id}` |
| **Gmail**            | Nhận CV qua email → trigger pipeline; gửi email thông báo interview/rejection           |
| **Identity**         | Admin auth required; audit log ghi actor_id từ JWT                                      |
| **MinIO**            | Lưu trữ CV files, presigned URLs cho download                                           |
| **External: olmOCR** | HTTP POST để trích xuất text từ PDF/images                                              |
| **External: LLM**    | OpenAI-compatible API để parse CV text → structured data                                |

## 10. Configuration

| Env Variable                               | Default                         | Mô tả                             |
| ------------------------------------------ | ------------------------------- | --------------------------------- |
| `RECRUITMENT_LLM_BASE_URL`                 | `http://127.0.0.1:20128/v1`     | LLM API endpoint                  |
| `RECRUITMENT_LLM_API_KEY`                  | (empty)                         | LLM API key                       |
| `RECRUITMENT_LLM_MODEL`                    | `NullNyx-Combo`                 | Model name                        |
| `RECRUITMENT_LLM_INTENT_TIMEOUT_SECONDS`   | `15`                            | Timeout cho intent classification |
| `RECRUITMENT_LLM_PARSE_TIMEOUT_SECONDS`    | `30`                            | Timeout cho CV parsing            |
| `RECRUITMENT_LLM_MAX_RETRIES`              | `3`                             | Max retries cho LLM calls         |
| `RECRUITMENT_OLMOCR_ENDPOINT_URL`          | `https://olmocr.aibuddy.vn/ocr` | olmOCR endpoint                   |
| `RECRUITMENT_OLMOCR_TIMEOUT_SECONDS`       | `600`                           | Timeout per OCR request           |
| `RECRUITMENT_OLMOCR_MAX_RETRIES`           | `3`                             | Max retries cho OCR               |
| `RECRUITMENT_OLMOCR_MAX_PAGES_PER_CHUNK`   | `20`                            | Max pages per PDF chunk           |
| `RECRUITMENT_MINIO_BUCKET_NAME`            | `recruitment-cv`                | MinIO bucket                      |
| `RECRUITMENT_PRESIGNED_URL_EXPIRY_SECONDS` | `900`                           | Presigned URL TTL                 |
| `RECRUITMENT_MAX_PARALLEL_TASKS`           | `3`                             | Max concurrent pipeline tasks     |
| `RECRUITMENT_PIPELINE_TIMEOUT_SECONDS`     | `660`                           | Overall pipeline timeout          |
| `RECRUITMENT_MAX_FILE_SIZE_BYTES`          | `10485760`                      | Max file size (10MB)              |
| `RECRUITMENT_RETENTION_DAYS`               | `90`                            | Data retention for rejected       |
| `RECRUITMENT_AUTO_ACCEPT_THRESHOLD`        | `0.7`                           | Confidence auto-accept threshold  |
