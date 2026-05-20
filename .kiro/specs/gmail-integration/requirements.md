# Requirements Document

## Introduction

Module Gmail Integration cung cấp khả năng kết nối Gmail của HR với hệ thống Vroom HR thông qua OAuth2. Module này chịu trách nhiệm: (1) khởi tạo kết nối OAuth2 với Gmail API, (2) fetch email định kỳ qua background job (ARQ cron mỗi 5 phút), (3) quản lý Gmail labels để đánh dấu trạng thái xử lý email, và (4) gửi email từ tài khoản HR. Đây là module nền tảng (prerequisite) cho E04 (Inbox & Classifier) và E05 (CV Pipeline).

## Glossary

- **System**: Module Gmail Integration trong Vroom HR backend
- **HR**: Người dùng HR duy nhất đăng nhập hệ thống, sở hữu tài khoản Google Workspace
- **Gmail_Adapter**: Infrastructure adapter giao tiếp với Gmail API, nằm tại backend/src/integrations/gmail/
- **OAuth_Grant**: Bản ghi OAuth2 credentials (encrypted access + refresh token) đã lưu trong bảng oauth_grants từ module Identity
- **Email_Message**: Domain entity đại diện cho một email đã fetch từ Gmail, lưu metadata trong PostgreSQL
- **Gmail_Label**: Nhãn (label) trên Gmail dùng để phân loại và đánh dấu trạng thái xử lý email
- **Sync_Cursor**: Giá trị history_id hoặc page token dùng để theo dõi vị trí đồng bộ, chỉ fetch email mới kể từ lần poll trước
- **Poll_Job**: ARQ cron job chạy định kỳ (mặc định 5 phút) để fetch email mới từ Gmail
- **Batch_Size**: Số lượng email tối đa fetch trong một lần poll (mặc định 100, tuân thủ Gmail API rate limit 250 quota units/user/second)
- **Email_Repository**: Repository lưu trữ Email_Message metadata trong PostgreSQL
- **Connection_Status**: Trạng thái kết nối Gmail của HR (connected, disconnected, token_expired)

## Requirements

### Requirement 1: Kiểm tra trạng thái kết nối Gmail

**User Story:** Là HR, tôi muốn biết Gmail của mình đã kết nối với hệ thống chưa, để tôi có thể bắt đầu sử dụng các tính năng inbox.

#### Acceptance Criteria

1. WHEN HR requests GET /api/gmail/status, THE System SHALL return Connection_Status reflecting the current state of the Gmail OAuth_Grant (connected, disconnected, or token_expired) along with the connected Gmail email address (if connected)
2. WHEN the OAuth_Grant exists AND is_valid is true AND token_expires_at is in the future, THE System SHALL report Connection_Status as "connected"
3. WHEN no OAuth_Grant exists for the current user with Gmail scopes, THE System SHALL report Connection_Status as "disconnected"
4. WHEN the OAuth_Grant exists AND is_valid is false, THE System SHALL report Connection_Status as "token_expired"
5. WHEN HR requests GET /api/gmail/status without a valid authentication session, THE System SHALL return HTTP 401 with error code UNAUTHORIZED

### Requirement 2: Kích hoạt kết nối Gmail

**User Story:** Là HR, tôi muốn kết nối tài khoản Gmail của mình với hệ thống, để hệ thống có thể đọc và gửi email thay tôi.

#### Acceptance Criteria

1. WHEN HR requests POST /api/gmail/connect AND the OAuth_Grant already has gmail.readonly, gmail.modify, gmail.send scopes AND is_valid is true AND token_expires_at is in the future, THE System SHALL return HTTP 200 with Connection_Status "connected" without re-initiating OAuth flow
2. WHEN HR requests POST /api/gmail/connect AND no valid Gmail OAuth_Grant exists (no record, or is_valid is false, or token_expires_at is in the past), THE System SHALL return HTTP 200 with a JSON body containing a redirect_url to Google OAuth2 consent screen requesting scopes: gmail.readonly, gmail.modify, gmail.send
3. WHEN the OAuth2 callback succeeds with all required Gmail scopes granted (gmail.readonly, gmail.modify, gmail.send), THE System SHALL store the encrypted tokens by creating a new OAuth_Grant record (first connection) or updating the existing record (reconnection), and set Connection_Status to "connected"
4. IF the OAuth2 callback fails OR HR denies Gmail scopes OR the callback grants only a subset of the required scopes, THEN THE System SHALL return HTTP 400 with error code GMAIL_CONNECT_FAILED and a message indicating the reason for failure
5. WHEN HR requests POST /api/gmail/connect without a valid authentication session, THE System SHALL return HTTP 401 with error code UNAUTHORIZED

### Requirement 3: Ngắt kết nối Gmail

**User Story:** Là HR, tôi muốn có thể ngắt kết nối Gmail khỏi hệ thống, để tôi kiểm soát quyền truy cập dữ liệu email của mình.

#### Acceptance Criteria

1. WHEN HR requests POST /api/gmail/disconnect AND Connection_Status is "connected" or "token_expired", THE System SHALL revoke the Gmail OAuth2 token via Google's revocation endpoint with a timeout of 10 seconds, then mark the OAuth_Grant as invalid (is_valid=false), remove Gmail scopes from the grant record, and return HTTP 200 with Connection_Status "disconnected"
2. WHEN the Google revocation endpoint call fails or times out, THE System SHALL still mark the OAuth_Grant as invalid (is_valid=false) and remove Gmail scopes from the grant record, and return HTTP 200 with Connection_Status "disconnected"
3. WHEN Gmail is disconnected, THE System SHALL set Connection_Status to "disconnected" so that the Poll_Job skips execution for that user until reconnection, and THE System SHALL retain all previously fetched Email_Message records in the database without deletion
4. IF HR requests POST /api/gmail/disconnect AND Connection_Status is already "disconnected", THEN THE System SHALL return HTTP 200 with Connection_Status "disconnected" without calling Google's revocation endpoint

### Requirement 4: Fetch email mới theo lịch (Polling)

**User Story:** Là HR, tôi muốn hệ thống tự động lấy email mới từ Gmail định kỳ, để tôi không cần kiểm tra Gmail thủ công.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", THE Poll_Job SHALL execute every 5 minutes (configurable via environment variable GMAIL_POLL_INTERVAL_SECONDS, default 300, minimum 60, maximum 3600)
2. WHEN the Poll_Job executes AND no Sync_Cursor exists for the user (first poll after connection), THE Gmail_Adapter SHALL perform an initial sync by fetching emails from the most recent 7 days using Gmail API messages.list with a maximum of 100 messages per batch
3. WHEN the Poll_Job executes AND a Sync_Cursor exists, THE Gmail_Adapter SHALL fetch emails newer than the stored Sync_Cursor using Gmail API history.list or messages.list with a maximum of 100 messages per batch
4. WHEN new emails are fetched AND persisted successfully to the Email_Repository, THE System SHALL update the Sync_Cursor to the latest history_id atomically within the same database transaction
5. WHEN the Poll_Job executes AND no new emails are found, THE System SHALL retain the current Sync_Cursor unchanged and complete the poll cycle without error
6. WHEN the Poll_Job fetches emails, THE Gmail_Adapter SHALL retrieve message metadata: id, threadId, subject, from, to, cc, date, snippet, labelIds, and hasAttachments flag
7. IF the Gmail API returns HTTP 401 (token expired), THEN THE System SHALL attempt to refresh the Google access token using the stored refresh token before retrying the fetch once
8. IF the token refresh fails, THEN THE System SHALL mark the OAuth_Grant as invalid, set Connection_Status to "token_expired", and stop the Poll_Job for that user

### Requirement 5: Lưu trữ email metadata

**User Story:** Là HR, tôi muốn email đã fetch được lưu lại trong hệ thống, để tôi có thể xem và tìm kiếm mà không cần truy cập Gmail trực tiếp.

#### Acceptance Criteria

1. WHEN new emails are fetched, THE Email_Repository SHALL persist each Email_Message with fields: gmail_message_id, gmail_thread_id, subject (maximum 998 characters, truncated if longer), sender_email, sender_name, recipient_emails (list, maximum 50 recipients), cc_emails (list, maximum 50 recipients), received_at, snippet (maximum 200 characters), label_ids, has_attachments, and raw_payload (encrypted)
2. THE Email_Repository SHALL use gmail_message_id as a unique constraint to prevent duplicate email records
3. WHEN an email already exists in the database (same gmail_message_id), THE System SHALL update only the label_ids field to reflect current Gmail state
4. WHEN storing raw_payload, THE System SHALL encrypt the content using AES-256-GCM with the encryption key from environment configuration
5. IF the encryption key is not configured or is invalid (not a valid AES-256 key), THEN THE System SHALL reject the persist operation, skip the affected message, and log an error indicating encryption configuration failure
6. IF a database persist operation fails for an individual Email_Message, THEN THE System SHALL log the error with the gmail_message_id and continue persisting remaining messages in the batch without rolling back successfully saved records
7. WHEN an email is fetched with missing or empty subject, sender_email, or sender_name fields, THE Email_Repository SHALL persist the record using an empty string as the default value for the missing field

### Requirement 6: Fetch nội dung email đầy đủ (On-demand)

**User Story:** Là HR, tôi muốn xem nội dung đầy đủ của một email khi cần, để tôi có thể đọc chi tiết và xử lý.

#### Acceptance Criteria

1. WHEN HR requests GET /api/gmail/messages/{message_id}/body AND Connection_Status is "connected", THE Gmail_Adapter SHALL fetch the full message body (text/plain and text/html parts) from Gmail API within 10 seconds
2. WHEN the full body is fetched, THE System SHALL return the base64-decoded content with both plain text and HTML versions; IF only one content type is available, THEN THE System SHALL return that content type and set the other to null
3. IF the Gmail API call fails, THEN THE System SHALL return HTTP 502 with error code GMAIL_FETCH_ERROR and a message indicating the failure reason
4. IF the message_id does not exist in Gmail (HTTP 404 from Gmail API), THEN THE System SHALL return HTTP 404 with error code MESSAGE_NOT_FOUND
5. IF Connection_Status is not "connected" when the request is made, THEN THE System SHALL return HTTP 403 with error code GMAIL_NOT_CONNECTED

### Requirement 7: Quản lý Gmail Labels — Khởi tạo

**User Story:** Là HR, tôi muốn hệ thống tự động tạo các labels cần thiết trên Gmail, để email được phân loại rõ ràng.

#### Acceptance Criteria

1. WHEN Connection_Status changes from "disconnected" to "connected" (including first connection and reconnection after disconnect), THE System SHALL create the following Gmail labels if they do not already exist: "VroomHR/processed", "VroomHR/recruitment", "VroomHR/interview", "VroomHR/onboarding"
2. WHEN creating labels, THE System SHALL use a "VroomHR/" prefix namespace to avoid conflicts with existing user labels
3. WHEN labels already exist with the same names, THE System SHALL reuse the existing label IDs without creating duplicates
4. WHEN labels are created or reused successfully, THE System SHALL store the mapping between label names and Gmail label IDs in the database, replacing any previously stored mapping for that user
5. IF the Gmail API fails to create one or more labels, THEN THE System SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s), and if all retries fail, THE System SHALL log the error and set Connection_Status to "connected" while marking label initialization as incomplete for retry on the next Poll_Job cycle

### Requirement 8: Gắn label lên email

**User Story:** Là HR (hoặc hệ thống tự động), tôi muốn gắn label lên email đã xử lý, để tôi biết email nào đã được hệ thống xử lý và thuộc danh mục nào.

#### Acceptance Criteria

1. WHEN the system or HR marks an email as processed, THE Gmail_Adapter SHALL add the "VroomHR/processed" label to that message via Gmail API messages.modify and update the label_ids field in the local Email_Message record
2. WHEN the system classifies an email into a category (recruitment, interview, onboarding), THE Gmail_Adapter SHALL add the corresponding "VroomHR/{category}" label to that message and update the label_ids field in the local Email_Message record
3. IF more than one message requires label modification in a single operation, THEN THE Gmail_Adapter SHALL use batch request (messages.batchModify) with a maximum of 100 messages per batch call to minimize API quota usage
4. IF the Gmail API label modification fails, THEN THE System SHALL log the error and retry up to 3 times with exponential backoff (1s, 2s, 4s)
5. IF all 3 retry attempts for a label modification fail, THEN THE System SHALL log the failure with message_id and intended label, and record the message ID for retry in the next poll cycle

### Requirement 9: Gỡ label khỏi email

**User Story:** Là HR, tôi muốn có thể gỡ label khỏi email nếu phân loại sai, để email được xử lý lại đúng cách.

#### Acceptance Criteria

1. WHEN HR requests POST /api/gmail/messages/{message_id}/labels/remove with a label name within the "VroomHR/" namespace, THE Gmail_Adapter SHALL remove the specified label from that message via Gmail API messages.modify
2. WHEN the "VroomHR/processed" label is removed from an email, THE System SHALL set the Email_Message processing status to unprocessed in the local database and remove any associated category classification (recruitment, interview, onboarding) so the email is eligible for re-classification
3. IF HR requests removal of a label that is NOT within the "VroomHR/" namespace, THEN THE System SHALL reject the request with HTTP 400 and error code LABEL_NAMESPACE_VIOLATION
4. IF the Gmail API label removal call fails, THEN THE System SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s) and return HTTP 502 with error code GMAIL_LABEL_REMOVE_FAILED if all retries are exhausted

### Requirement 10: Gửi email từ tài khoản HR

**User Story:** Là HR, tôi muốn hệ thống gửi email từ tài khoản Gmail của tôi, để ứng viên và nhân viên nhận email chính thức từ HR.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", WHEN the system needs to send an email (interview invite, reject, congrats, onboarding), THE Gmail_Adapter SHALL send via Gmail API messages.send using the HR's authenticated account
2. WHEN sending an email, THE Gmail_Adapter SHALL accept parameters: to (list, minimum 1, maximum 50 recipients), cc (list, optional, maximum 50 recipients), subject (maximum 500 characters), body_html, body_text (at least one of body_html or body_text must be provided), reply_to_message_id (optional for threading), and attachments (list, optional, maximum 10 files, each file not exceeding 10MB)
3. WHEN reply_to_message_id is provided, THE Gmail_Adapter SHALL set the In-Reply-To and References headers to maintain email thread continuity
4. WHEN an email is sent successfully, THE System SHALL store the sent message metadata (gmail_message_id, thread_id, recipients, subject, sent_at) in the Email_Repository
5. IF the Gmail API send returns HTTP 5xx, THEN THE Gmail_Adapter SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s) before returning an error with code GMAIL_SEND_FAILED and the Gmail API error response
6. IF the Gmail API send fails with a non-retryable error (HTTP 4xx other than 401), THEN THE System SHALL return an error with code GMAIL_SEND_FAILED and include the Gmail API error response
7. IF Connection_Status is not "connected" when a send is attempted, THEN THE System SHALL reject the request with error code GMAIL_NOT_CONNECTED without calling the Gmail API

### Requirement 11: Fetch email attachments

**User Story:** Là HR, tôi muốn hệ thống tải attachment từ email (CV, hồ sơ), để pipeline xử lý CV và hồ sơ nhân viên hoạt động tự động.

#### Acceptance Criteria

1. WHEN an Email_Message has has_attachments=true AND the system requests attachment download, THE Gmail_Adapter SHALL fetch attachment data via Gmail API messages.attachments.get for each attachment in the message, up to a maximum of 20 attachments per email
2. WHEN an attachment is fetched, THE System SHALL validate file type against allowed MIME types: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, image/jpeg, image/png
3. WHEN an attachment is fetched, THE System SHALL validate file size does not exceed 10MB
4. IF the attachment MIME type is not in the allowed list, THEN THE System SHALL skip the attachment and log a warning with the message_id and MIME type
5. IF the attachment size exceeds 10MB, THEN THE System SHALL skip the attachment and log a warning with the message_id and file size
6. WHEN an attachment passes validation, THE System SHALL store the attachment binary data and metadata (original filename, MIME type, size in bytes, gmail_message_id, attachment_id) and make it available for downstream pipeline consumption
7. IF the Gmail API returns an error when fetching an attachment, THEN THE System SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s), and if all retries fail, skip the attachment and log an error with the message_id and attachment_id
8. WHEN all attachments for an Email_Message have been processed, THE System SHALL record the count of successfully fetched attachments and the count of skipped attachments for that message

### Requirement 12: Rate limiting và quota management

**User Story:** Là system architect, tôi muốn hệ thống tuân thủ Gmail API rate limits, để tài khoản HR không bị Google tạm khóa API access.

#### Acceptance Criteria

1. THE Gmail_Adapter SHALL track quota unit consumption and delay outgoing API calls when the rolling per-second usage reaches 250 quota units per user, ensuring no request is sent that would exceed the limit
2. WHEN fetching emails in batch, THE Gmail_Adapter SHALL process a maximum of 100 messages per poll cycle
3. IF the Gmail API returns HTTP 429 (rate limit exceeded) AND the response includes a Retry-After header with a value of 120 seconds or less, THEN THE Gmail_Adapter SHALL wait for the duration specified in the Retry-After header before retrying the failed request
4. IF the Gmail API returns HTTP 429 (rate limit exceeded) AND the response does not include a Retry-After header, THEN THE Gmail_Adapter SHALL wait 5 seconds before retrying the failed request
5. IF the Gmail API returns HTTP 429 AND the Retry-After header specifies a duration greater than 120 seconds, THEN THE Gmail_Adapter SHALL abort the current operation and log an error indicating the requested backoff exceeds the maximum allowed wait time
6. IF the Gmail API returns HTTP 429 three consecutive times within a single poll cycle, THEN THE System SHALL abort the current poll cycle and log an error with severity WARNING

### Requirement 13: Error handling và resilience

**User Story:** Là system architect, tôi muốn hệ thống xử lý lỗi Gmail API gracefully, để một lỗi tạm thời không làm mất dữ liệu hoặc dừng toàn bộ hệ thống.

#### Acceptance Criteria

1. IF the Gmail API returns HTTP 5xx (server error), THEN THE Gmail_Adapter SHALL retry the request up to 3 times with exponential backoff (1s, 2s, 4s), where each individual request times out after 30 seconds of no response
2. IF all retry attempts for a request fail, THEN THE System SHALL log the error with context (endpoint, parameters, response status, response body) and continue processing remaining items in the batch
3. WHEN a poll cycle encounters errors for some messages but succeeds for others, THE System SHALL save successfully fetched messages to the Email_Repository, record failed message IDs with a retry counter, and update the Sync_Cursor only up to the latest successfully processed history_id
4. IF the Poll_Job itself crashes due to an unhandled exception, THEN THE System SHALL log the error with stack trace and the ARQ worker SHALL automatically retry the job in the next scheduled interval without advancing the Sync_Cursor
5. IF a message has failed fetching in 5 consecutive poll cycles, THEN THE System SHALL mark that message as permanently failed, log a warning with the message ID, and exclude it from future retry attempts

### Requirement 14: Manual sync trigger

**User Story:** Là HR, tôi muốn có thể kích hoạt đồng bộ email thủ công, để tôi không cần đợi 5 phút khi cần xem email mới ngay.

#### Acceptance Criteria

1. WHEN HR requests POST /api/gmail/sync AND Connection_Status is "connected", THE System SHALL trigger an immediate email fetch (same logic as Poll_Job) outside the regular schedule and return HTTP 200 with the count of new emails fetched
2. WHEN a manual sync is triggered, THE System SHALL apply rate limiting of maximum 1 manual sync per 30 seconds per user
3. IF a manual sync is requested within 30 seconds of the previous manual sync, THEN THE System SHALL return HTTP 429 with a message indicating the remaining cooldown time in seconds
4. IF HR requests POST /api/gmail/sync AND Connection_Status is not "connected", THEN THE System SHALL return HTTP 409 with error code GMAIL_NOT_CONNECTED and a message indicating the current Connection_Status

### Requirement 15: Audit logging cho Gmail operations

**User Story:** Là system architect, tôi muốn mọi thao tác Gmail được ghi log, để có thể truy vết khi cần debug hoặc audit.

#### Acceptance Criteria

1. WHEN any Gmail API operation is performed (fetch, send, label modify), THE System SHALL log an audit entry with: operation_type, user_id, timestamp (ISO 8601 UTC format), message_count (for batch operations, 0 for single-message operations), and success/failure status
2. WHEN an email is sent via the system, THE System SHALL log: recipient_emails (up to 50 recipients, truncated with count indicator if exceeded), subject (truncated to 100 characters), template_name (if applicable, otherwise omitted), and sent_at (ISO 8601 UTC format)
3. THE System SHALL NOT log email body content, email preview/snippet text, or attachment binary data in audit logs to protect privacy
4. IF the audit logging mechanism fails during a Gmail API operation, THEN THE System SHALL proceed with the Gmail operation and record the logging failure in the application error log with: operation_type, user_id, timestamp, and failure reason
5. THE System SHALL retain audit log entries for a minimum of 90 days, after which entries MAY be archived or deleted
