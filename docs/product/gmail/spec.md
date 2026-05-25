# Gmail Integration — Feature Spec

## 1. Tổng quan

Module Gmail Integration kết nối hệ thống Vroom HR với Gmail API để gửi/nhận email phục vụ các module khác (recruitment, payroll, attendance reports). Hỗ trợ OAuth2 connection management, email sync (scheduled + manual), gửi email với attachments, quản lý labels trong namespace VroomHR/, và audit logging cho mọi thao tác Gmail.

## 2. Actors

| Actor                  | Mô tả                                                                     |
| ---------------------- | ------------------------------------------------------------------------- |
| **HR Admin**           | Connect/disconnect Gmail, manual sync, gửi email, quản lý labels          |
| **System (Scheduler)** | Scheduled polling mỗi 300s để sync emails mới                             |
| **Other Modules**      | Recruitment (gửi thông báo), Payroll (gửi payslips), Attendance (reports) |

## 3. Luồng hoạt động (User Flows)

### 3.1 Gmail Connection Flow

```
HR Admin                    Backend                    Google
 │                            │                          │
 │── POST /api/gmail/connect ►│                          │
 │                            │── Generate OAuth URL      │
 │                            │   (scopes: gmail.send,    │
 │                            │    gmail.readonly,        │
 │                            │    gmail.labels,          │
 │                            │    gmail.modify)          │
 │◄─ {auth_url} ─────────────│                          │
 │                            │                          │
 │── Redirect to Google ──────────────────────────────────►│
 │── Consent ─────────────────────────────────────────────►│
 │◄─ Callback with code ─────────────────────────────────── │
 │                            │                          │
 │── GET /api/gmail/callback  │                          │
 │   ?code=X ────────────────►│── Exchange code ─────────►│
 │                            │◄─ access + refresh token ─│
 │                            │── Encrypt tokens (AES)    │
 │                            │── Store in DB             │
 │                            │── Create VroomHR/ labels ─►│
 │                            │── Start initial sync      │
 │◄─ 200 {connected: true} ──│                          │
```

### 3.2 Email Sync Flow (Scheduled)

```
System (Scheduler)          Backend                    Gmail API       Database
 │                            │                          │               │
 │── Every 300s ─────────────►│                          │               │
 │                            │── Get sync cursor ───────────────────────►│
 │                            │── List messages since ───►│               │
 │                            │   cursor (batch_size=100) │               │
 │                            │◄─ message_ids ───────────│               │
 │                            │── For each message:       │               │
 │                            │   ├─ Fetch headers ──────►│               │
 │                            │   ├─ Extract metadata     │               │
 │                            │   └─ Upsert to DB ───────────────────────►│
 │                            │── Update sync cursor ────────────────────►│
 │                            │── Write audit log ───────────────────────►│
 │◄─ Done (N synced) ────────│                          │               │
```

### 3.3 Manual Sync (with cooldown)

```
HR Admin                    Backend                    Redis
 │                            │                          │
 │── POST /api/gmail/sync ───►│                          │
 │                            │── Check cooldown ────────►│
 │                            │   (30s since last sync)   │
 │                            │◄─ OK / COOLDOWN ─────────│
 │                            │                          │
 │                            │── IF cooldown active:     │
 │◄─ 429 SYNC_COOLDOWN ──────│                          │
 │                            │                          │
 │                            │── ELSE: run sync          │
 │                            │── Set cooldown key ──────►│
 │◄─ 200 {synced: N} ────────│                          │
```

### 3.4 Send Email Flow

```
HR Admin / Module           Backend                    Gmail API
 │                            │                          │
 │── POST /api/gmail/send     │                          │
 │   {to, subject, body_html, │                          │
 │    cc, reply_to_message_id,│                          │
 │    attachments} ──────────►│── Validate recipients     │
 │                            │── Build MIME message       │
 │                            │   (multipart if attach)   │
 │                            │── Set threading headers   │
 │                            │   (In-Reply-To, References)│
 │                            │── Send via Gmail API ────►│
 │                            │◄─ {message_id, thread_id} │
 │                            │── Store in DB             │
 │                            │── Write audit log         │
 │◄─ 200 {message_id} ───────│                          │
```

### 3.5 Label Management

```
HR Admin                    Backend                    Gmail API
 │                            │                          │
 │── GET /api/gmail/labels ──►│── List labels with       │
 │                            │   prefix "VroomHR/" ────►│
 │◄─ [{name, id, count}] ────│◄─ labels ────────────────│
 │                            │                          │
 │── POST /api/gmail/labels   │                          │
 │   {name: "custom"} ───────►│── Create "VroomHR/custom"►│
 │◄─ 201 {label} ────────────│◄─ label_id ──────────────│
 │                            │                          │
 │── PUT /api/gmail/messages/ │                          │
 │   {id}/labels              │                          │
 │   {add: ["recruitment"]} ─►│── Modify message labels ─►│
 │◄─ 200 OK ─────────────────│                          │
```

## 4. Business Rules

### Connection

1. **BR-01**: Chỉ 1 Gmail account connected tại một thời điểm (per system, không per user).
2. **BR-02**: Disconnect phải revoke token tại Google trước khi xóa local.
3. **BR-03**: Required OAuth scopes: `gmail.send`, `gmail.readonly`, `gmail.labels`, `gmail.modify`.
4. **BR-04**: Tokens encrypted AES-256-GCM trước khi lưu DB (dùng chung key với Identity module).

### Sync

5. **BR-05**: Scheduled sync interval: 300 giây (5 phút).
6. **BR-06**: Manual sync cooldown: 30 giây giữa 2 lần sync.
7. **BR-07**: Batch size per sync: tối đa 100 messages.
8. **BR-08**: Initial sync: lấy emails 7 ngày gần nhất khi connect lần đầu.
9. **BR-09**: Sync chỉ lấy headers (subject, from, to, date) — body fetch on-demand.

### Sending

10. **BR-10**: Email gửi hỗ trợ: HTML body, plain text fallback, CC, reply threading, attachments.
11. **BR-11**: Reply threading: set `In-Reply-To` và `References` headers từ `reply_to_message_id`.
12. **BR-12**: Attachments: max size 10MB per file, max 20 attachments per email.
13. **BR-13**: Allowed MIME types cho attachments: pdf, docx, jpeg, png.

### Labels

14. **BR-14**: Tất cả labels do VroomHR tạo phải có prefix `VroomHR/`.
15. **BR-15**: Required labels (tạo khi connect): `VroomHR/processed`, `VroomHR/recruitment`, `VroomHR/interview`, `VroomHR/onboarding`.
16. **BR-16**: Không được xóa/rename required labels.

### Quota & Reliability

17. **BR-17**: Quota tracking: 250 units/second per user (Gmail API limit).
18. **BR-18**: Retry: max 3 attempts với exponential backoff (base 1s).
19. **BR-19**: Permanent failure threshold: 5 consecutive failures → mark connection as broken.
20. **BR-20**: Honor `Retry-After` header, max 120 seconds.

### Audit

21. **BR-21**: Mọi Gmail operation phải ghi audit log (action, actor, timestamp, status).
22. **BR-22**: Audit retention: 90 ngày.
23. **BR-23**: Subject trong audit log truncate tại 100 ký tự.

## 5. Data Model

### EmailMessage

| Field            | Type                       | Constraints             | Mô tả                               |
| ---------------- | -------------------------- | ----------------------- | ----------------------------------- |
| id               | UUID                       | PK                      | ID duy nhất                         |
| gmail_message_id | String(255)                | UNIQUE, NOT NULL        | Gmail message ID                    |
| thread_id        | String(255)                | NOT NULL                | Gmail thread ID                     |
| subject          | String(500)                | NULLABLE                | Tiêu đề                             |
| from_email       | String(255)                | NOT NULL                | Người gửi                           |
| to_emails        | JSON                       | NOT NULL                | Danh sách người nhận                |
| cc_emails        | JSON                       | NULLABLE                | CC list                             |
| date             | DateTime                   | NOT NULL                | Ngày gửi/nhận                       |
| snippet          | Text                       | NULLABLE                | Preview text                        |
| label_ids        | JSON                       | NULLABLE                | Gmail label IDs                     |
| has_attachments  | Boolean                    | NOT NULL, DEFAULT false | Có attachment                       |
| is_read          | Boolean                    | NOT NULL, DEFAULT false | Đã đọc                              |
| direction        | Enum('inbound','outbound') | NOT NULL                | Chiều email                         |
| body_text        | Text                       | NULLABLE                | Plain text body (fetched on-demand) |
| body_html        | Text                       | NULLABLE                | HTML body (fetched on-demand)       |
| synced_at        | DateTime                   | NOT NULL                | Thời điểm sync                      |

### SyncCursor

| Field           | Type        | Constraints         | Mô tả                          |
| --------------- | ----------- | ------------------- | ------------------------------ |
| id              | UUID        | PK                  | ID duy nhất                    |
| cursor_type     | String(50)  | UNIQUE, NOT NULL    | Loại cursor (e.g., 'messages') |
| history_id      | String(100) | NOT NULL            | Gmail history ID               |
| last_sync_at    | DateTime    | NOT NULL            | Lần sync cuối                  |
| messages_synced | Integer     | NOT NULL, DEFAULT 0 | Tổng messages đã sync          |

### GmailLabelMapping

| Field          | Type        | Constraints             | Mô tả                      |
| -------------- | ----------- | ----------------------- | -------------------------- |
| id             | UUID        | PK                      | ID duy nhất                |
| gmail_label_id | String(255) | UNIQUE, NOT NULL        | Gmail label ID             |
| label_name     | String(255) | NOT NULL                | Tên label (without prefix) |
| full_name      | String(255) | NOT NULL                | Tên đầy đủ (VroomHR/xxx)   |
| is_required    | Boolean     | NOT NULL, DEFAULT false | Label bắt buộc             |
| message_count  | Integer     | DEFAULT 0               | Số messages có label này   |
| created_at     | DateTime    | NOT NULL                | Thời điểm tạo              |

### EmailAttachment

| Field               | Type        | Constraints                      | Mô tả                 |
| ------------------- | ----------- | -------------------------------- | --------------------- |
| id                  | UUID        | PK                               | ID duy nhất           |
| message_id          | UUID        | FK → email_messages.id, NOT NULL | Email chứa attachment |
| gmail_attachment_id | String(255) | NOT NULL                         | Gmail attachment ID   |
| filename            | String(255) | NOT NULL                         | Tên file              |
| mime_type           | String(100) | NOT NULL                         | MIME type             |
| size_bytes          | Integer     | NOT NULL                         | Kích thước            |
| is_fetched          | Boolean     | NOT NULL, DEFAULT false          | Đã download chưa      |

### GmailAuditLog

| Field             | Type                               | Constraints             | Mô tả                                 |
| ----------------- | ---------------------------------- | ----------------------- | ------------------------------------- |
| id                | UUID                               | PK                      | ID duy nhất                           |
| actor_id          | UUID                               | FK → users.id, NULLABLE | Người thực hiện (NULL = system)       |
| action            | String(100)                        | NOT NULL                | Hành động (send, sync, connect, etc.) |
| target_message_id | String(255)                        | NULLABLE                | Gmail message ID liên quan            |
| subject_preview   | String(100)                        | NULLABLE                | Subject truncated                     |
| status            | Enum('success','failed','partial') | NOT NULL                | Kết quả                               |
| error_message     | Text                               | NULLABLE                | Lỗi nếu failed                        |
| details           | JSON                               | NULLABLE                | Chi tiết bổ sung                      |
| created_at        | DateTime                           | NOT NULL                | Thời điểm                             |

## 6. State Machine

### Gmail Connection Status

```
┌──────────────┐     connect      ┌─────────────┐
│ disconnected │ ────────────────► │  connected  │
└──────────────┘                  └──────┬──────┘
       ▲                                 │
       │         disconnect              │
       └─────────────────────────────────┘
       ▲                                 │
       │     5 consecutive failures      │
       │         ┌────────┐              │
       └─────────│ broken │◄─────────────┘
                 └────────┘
                      │ reconnect (admin action)
                      ▼
              ┌──────────────┐
              │ disconnected │ (must re-connect)
              └──────────────┘
```

### Email Sync State

```
idle → syncing → idle (success)
              → error (retry next cycle)
              → broken (after 5 failures)
```

## 7. API Endpoints

### Connection

| Method | Path                    | Mô tả                     | Auth  |
| ------ | ----------------------- | ------------------------- | ----- |
| GET    | `/api/gmail/status`     | Trạng thái connection     | Admin |
| POST   | `/api/gmail/connect`    | Bắt đầu OAuth flow        | Admin |
| GET    | `/api/gmail/callback`   | OAuth callback            | Admin |
| POST   | `/api/gmail/disconnect` | Disconnect + revoke token | Admin |

### Messages

| Method | Path                            | Mô tả                          | Auth  |
| ------ | ------------------------------- | ------------------------------ | ----- |
| GET    | `/api/gmail/messages`           | Danh sách messages (paginated) | Admin |
| GET    | `/api/gmail/messages/{id}`      | Chi tiết message (fetch body)  | Admin |
| GET    | `/api/gmail/messages/{id}/body` | Fetch body (plain + HTML)      | Admin |
| POST   | `/api/gmail/send`               | Gửi email                      | Admin |

### Sync

| Method | Path                     | Mô tả                        | Auth  |
| ------ | ------------------------ | ---------------------------- | ----- |
| POST   | `/api/gmail/sync`        | Manual sync (30s cooldown)   | Admin |
| GET    | `/api/gmail/sync/status` | Sync status + last sync time | Admin |

### Labels

| Method | Path                              | Mô tả                         | Auth  |
| ------ | --------------------------------- | ----------------------------- | ----- |
| GET    | `/api/gmail/labels`               | Danh sách VroomHR labels      | Admin |
| POST   | `/api/gmail/labels`               | Tạo label mới                 | Admin |
| DELETE | `/api/gmail/labels/{id}`          | Xóa label (non-required only) | Admin |
| PUT    | `/api/gmail/messages/{id}/labels` | Add/remove labels cho message | Admin |

### Attachments

| Method | Path                                   | Mô tả                 | Auth  |
| ------ | -------------------------------------- | --------------------- | ----- |
| GET    | `/api/gmail/messages/{id}/attachments` | Danh sách attachments | Admin |
| GET    | `/api/gmail/attachments/{id}/download` | Download attachment   | Admin |

### Audit

| Method | Path                    | Mô tả                            | Auth  |
| ------ | ----------------------- | -------------------------------- | ----- |
| GET    | `/api/gmail/audit-logs` | Danh sách audit logs (paginated) | Admin |

## 8. Edge Cases & Error Handling

| Scenario                    | Xử lý                                                    |
| --------------------------- | -------------------------------------------------------- |
| Gmail token expired         | Auto-refresh using refresh_token; nếu fail → mark broken |
| Manual sync during cooldown | 429 `SYNC_COOLDOWN_ACTIVE` — header `Retry-After: Ns`    |
| Gmail API quota exceeded    | 429 from Google → honor Retry-After, log warning         |
| Send email fail             | Retry 3 lần, sau đó → audit log status=failed            |
| Attachment > 10MB           | 413 `ATTACHMENT_TOO_LARGE`                               |
| Attachment MIME not allowed | 415 `UNSUPPORTED_ATTACHMENT_TYPE`                        |
| > 20 attachments            | 400 `TOO_MANY_ATTACHMENTS`                               |
| Delete required label       | 403 `CANNOT_DELETE_REQUIRED_LABEL`                       |
| Disconnect khi đang sync    | Wait for sync complete, then disconnect                  |
| Body fetch timeout (10s)    | 504 `BODY_FETCH_TIMEOUT`                                 |
| Gmail API unavailable       | Retry with backoff; after 5 failures → connection broken |
| Duplicate message (re-sync) | Upsert by gmail_message_id (idempotent)                  |
| Token revocation fails      | Log warning, still clear local tokens                    |

## 9. Integration Points

| Module           | Cách tích hợp                                                                    |
| ---------------- | -------------------------------------------------------------------------------- |
| **Identity**     | Dùng chung OAuth token encryption key; admin auth required                       |
| **Recruitment**  | Nhận CV qua email → trigger recruitment pipeline; gửi interview/rejection emails |
| **Payroll**      | Gửi batch payslip emails                                                         |
| **Attendance**   | Gửi monthly attendance report                                                    |
| **Self-Service** | Không trực tiếp — thông qua admin actions                                        |

## 10. Configuration

| Env Variable                         | Default                                      | Mô tả                        |
| ------------------------------------ | -------------------------------------------- | ---------------------------- |
| `GMAIL_POLL_INTERVAL_SECONDS`        | `300`                                        | Sync interval (giây)         |
| `GMAIL_BATCH_SIZE`                   | `100`                                        | Max messages per sync        |
| `GMAIL_INITIAL_SYNC_DAYS`            | `7`                                          | Ngày lookback khi connect    |
| `GMAIL_MANUAL_SYNC_COOLDOWN_SECONDS` | `30`                                         | Cooldown giữa manual syncs   |
| `GMAIL_QUOTA_UNITS_PER_SECOND`       | `250`                                        | Gmail API quota limit        |
| `GMAIL_MAX_RETRIES`                  | `3`                                          | Max retry attempts           |
| `GMAIL_RETRY_BACKOFF_BASE`           | `1.0`                                        | Exponential backoff base (s) |
| `GMAIL_MAX_RETRY_AFTER_SECONDS`      | `120`                                        | Max Retry-After to honor     |
| `GMAIL_PERMANENT_FAILURE_THRESHOLD`  | `5`                                          | Failures before broken       |
| `GMAIL_API_TIMEOUT_SECONDS`          | `30`                                         | General API timeout          |
| `GMAIL_REVOCATION_TIMEOUT_SECONDS`   | `10`                                         | Token revocation timeout     |
| `GMAIL_BODY_FETCH_TIMEOUT_SECONDS`   | `10`                                         | Body fetch timeout           |
| `GMAIL_MAX_ATTACHMENT_SIZE_BYTES`    | `10485760`                                   | Max attachment (10MB)        |
| `GMAIL_MAX_ATTACHMENTS_PER_EMAIL`    | `20`                                         | Max attachments per email    |
| `GMAIL_ALLOWED_MIME_TYPES`           | `pdf,docx,jpeg,png`                          | Allowed attachment types     |
| `GMAIL_LABEL_PREFIX`                 | `VroomHR/`                                   | Label namespace prefix       |
| `GMAIL_REQUIRED_LABELS`              | `processed,recruitment,interview,onboarding` | Auto-created labels          |
| `GMAIL_AUDIT_RETENTION_DAYS`         | `90`                                         | Audit log retention          |
| `GMAIL_AUDIT_SUBJECT_MAX_LENGTH`     | `100`                                        | Subject truncation length    |
