# Implementation Plan: Gmail Integration

## Overview

Implement the Gmail Integration module for Vroom HR following the existing clean architecture pattern (domain/application/infrastructure/api layers). The module enables OAuth2-based Gmail connectivity, periodic email polling via ARQ cron jobs, label management, email sending, and attachment handling. Implementation builds on existing Identity module infrastructure (OAuth_Grant, CryptoUtils) and follows the project's established patterns with SQLModel, FastAPI, and dependency injection.

## Tasks

- [x] 1. Set up module structure and domain layer
  - [x] 1.1 Create Gmail module directory structure and configuration
    - Create `backend/src/modules/gmail/` directory with all subdirectories (api/, application/, domain/, infrastructure/)
    - Create `__init__.py` files for all packages
    - Implement `GmailSettings` pydantic-settings class in `infrastructure/config.py` with all configuration fields (poll_interval, batch_size, timeouts, retry settings, attachment limits, label config, audit retention)
    - _Requirements: 4.1, 12.1, 12.2, 11.3, 11.1_

  - [x] 1.2 Implement domain entities and enums
    - Create `domain/enums.py` with `ConnectionStatus` enum (connected, disconnected, token_expired) and `EmailCategory` enum (recruitment, interview, onboarding)
    - Create `domain/entities.py` with SQLModel table classes: `EmailMessage`, `SyncCursor`, `GmailLabelMapping`, `EmailAttachment`, `GmailAuditLog`
    - Create `domain/exceptions.py` with domain-specific exceptions: `GmailNotConnectedException`, `GmailConnectFailedException`, `LabelNamespaceViolationException`, `GmailFetchError`, `GmailSendFailedException`, `RateLimitedException`
    - _Requirements: 5.1, 5.2, 5.7, 1.1, 1.2, 1.3, 1.4_

  - [x] 1.3 Create Alembic migration for Gmail tables
    - Create migration file `008_create_gmail_tables.py` with tables: `email_messages`, `sync_cursors`, `gmail_label_mappings`, `email_attachments`, `gmail_audit_logs`
    - Include all indexes, unique constraints, foreign keys, and default values as specified in design
    - _Requirements: 5.1, 5.2, 7.4, 15.1_

- [x] 2. Implement infrastructure layer — repositories and adapters
  - [x] 2.1 Implement EmailRepository
    - Create `infrastructure/email_repository.py` with methods: `batch_upsert`, `get_by_gmail_id`, `update_labels`, `mark_permanently_failed`, `increment_retry_count`, `get_failed_messages`
    - Implement upsert logic: insert new records, update only `label_ids` for existing records (same gmail_message_id)
    - Handle partial batch failures: log errors per message, continue with remaining
    - _Requirements: 5.1, 5.2, 5.3, 5.6, 5.7, 13.3, 13.5_

  - [x] 2.2 Implement SyncCursorRepository and LabelRepository
    - Create `infrastructure/sync_cursor_repository.py` with methods: `get_cursor`, `upsert_cursor`
    - Create `infrastructure/label_repository.py` with methods: `get_mappings`, `upsert_mappings`, `get_label_id_by_name`
    - _Requirements: 4.3, 4.4, 7.4_

  - [x] 2.3 Implement QuotaTracker (Redis-based)
    - Create `infrastructure/quota_tracker.py` with Redis sliding window implementation
    - Implement `consume`, `can_consume`, `wait_if_needed` methods
    - Track per-user quota units with 250 units/second limit
    - _Requirements: 12.1_

  - [x] 2.4 Implement AuditLogger
    - Create `infrastructure/audit_logger.py` with `log_operation` and `log_send` methods
    - Ensure no email body, snippet, or attachment data is logged
    - Handle logging failures gracefully (proceed with operation, log failure to app error log)
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [x] 2.5 Implement GmailAdapter
    - Create `infrastructure/gmail_adapter.py` with all Gmail API interaction methods
    - Implement `retry_with_backoff` utility with exponential backoff (1s, 2s, 4s), max 3 retries, 30s timeout per request
    - Implement `fetch_messages`, `fetch_history`, `get_message_body`, `send_message`, `get_attachment`, `modify_labels`, `batch_modify_labels`, `create_label`, `list_labels`, `revoke_token`, `refresh_access_token`
    - Integrate QuotaTracker for rate limiting before each API call
    - Handle HTTP 429 with Retry-After header logic (≤120s wait, >120s abort, no header → 5s wait)
    - _Requirements: 4.2, 4.3, 4.6, 6.1, 8.1, 8.3, 9.1, 10.1, 11.1, 12.1, 12.3, 12.4, 12.5, 12.6, 13.1_

  - [x]* 2.6 Write property tests for QuotaTracker
    - **Property 12: Quota tracking and throttling**
    - **Validates: Requirements 12.1**

  - [x]* 2.7 Write property tests for email persistence
    - **Property 2: Email persistence round-trip with defaults**
    - **Property 3: Duplicate prevention and label-only upsert**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.7**

- [x] 3. Implement application services — Connection and Labels
  - [x] 3.1 Implement ConnectionService
    - Create `application/connection_service.py` with `get_status`, `initiate_connect`, `handle_callback`, `disconnect` methods
    - Implement status determination logic: check OAuth_Grant existence, is_valid flag, and token_expires_at
    - Implement connect flow: return existing connection if valid, otherwise generate OAuth2 redirect URL with gmail.readonly, gmail.modify, gmail.send scopes
    - Implement callback handling: store encrypted tokens, trigger label initialization
    - Implement disconnect: revoke token (10s timeout, proceed on failure), mark grant invalid, remove scopes
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [x]* 3.2 Write property test for connection status determination
    - **Property 1: Connection status determination**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 3.3 Implement LabelService
    - Create `application/label_service.py` with `initialize_labels`, `add_label`, `remove_label`, `batch_add_label`, `validate_namespace` methods
    - Implement label initialization: create VroomHR/processed, VroomHR/recruitment, VroomHR/interview, VroomHR/onboarding if not existing, reuse existing label IDs
    - Implement retry logic for label creation (3 retries, exponential backoff)
    - Implement namespace validation: only allow labels with "VroomHR/" prefix
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4_

  - [x]* 3.4 Write property tests for label operations
    - **Property 6: Category-to-label mapping**
    - **Property 7: Label batch size limit**
    - **Property 8: Label namespace validation**
    - **Validates: Requirements 8.2, 8.3, 9.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement application services — Email Sync and Send
  - [x] 5.1 Implement EmailSyncService
    - Create `application/email_sync_service.py` with `poll_emails`, `manual_sync`, `_fetch_and_persist`, `_handle_token_refresh` methods
    - Implement first-poll logic: fetch emails from last 7 days when no SyncCursor exists
    - Implement incremental sync: fetch emails newer than stored history_id
    - Implement atomic cursor update: persist emails and update cursor in same transaction
    - Implement token refresh on 401: attempt refresh, retry once, mark invalid on failure
    - Implement manual sync rate limiting: 1 request per 30 seconds per user
    - Implement partial failure handling: save successful messages, record failed IDs with retry_count
    - Implement permanent failure: mark messages with 5+ consecutive failures as permanently failed
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.4, 5.5, 5.6, 13.2, 13.3, 13.4, 13.5, 14.1, 14.2, 14.3_

  - [x]* 5.2 Write property tests for email sync
    - **Property 13: Poll batch size limit**
    - **Property 14: Partial success with cursor update**
    - **Property 15: Permanent failure exclusion**
    - **Property 16: Manual sync rate limiting**
    - **Validates: Requirements 12.2, 13.3, 13.5, 14.2, 14.3**

  - [x] 5.3 Implement SendService
    - Create `application/send_service.py` with `send_email` and `_build_mime_message` methods
    - Implement MIME message construction: handle to (1-50), cc (optional, max 50), subject (max 500 chars), body_html, body_text, reply_to_message_id (In-Reply-To/References headers), attachments (max 10, each ≤10MB)
    - Implement send with retry: 3 retries with exponential backoff for 5xx, no retry for 4xx (except 401)
    - Store sent message metadata in EmailRepository
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x]* 5.4 Write property tests for send service
    - **Property 9: MIME message construction**
    - **Validates: Requirements 10.2**

  - [x] 5.5 Implement AttachmentService
    - Create `application/attachment_service.py` with `fetch_attachments` and `validate_attachment` methods
    - Implement validation: check MIME type against allowed list (pdf, docx, jpeg, png), check size ≤10MB
    - Implement fetch with retry (3 retries, exponential backoff), skip on failure
    - Track counts: successfully fetched vs skipped attachments
    - Limit to 20 attachments per email
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [x]* 5.6 Write property tests for attachment service
    - **Property 10: Attachment validation**
    - **Property 11: Attachment count invariant**
    - **Validates: Requirements 11.2, 11.3, 11.8**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement API layer and wiring
  - [x] 7.1 Implement API schemas
    - Create `api/schemas.py` with Pydantic request/response models: `ConnectionStatusResponse`, `ConnectResponse`, `SendEmailRequest`, `SendEmailResponse`, `MessageBodyResponse`, `LabelRemoveRequest`, `SyncResponse`, `ErrorResponse`
    - _Requirements: 1.1, 2.1, 2.2, 6.1, 6.2, 10.2, 14.1_

  - [x] 7.2 Implement API router
    - Create `api/router.py` with FastAPI endpoints:
      - `GET /api/gmail/status` — connection status check
      - `POST /api/gmail/connect` — initiate OAuth connection
      - `GET /api/gmail/callback` — OAuth2 callback handler
      - `POST /api/gmail/disconnect` — disconnect Gmail
      - `POST /api/gmail/sync` — manual sync trigger
      - `GET /api/gmail/messages/{message_id}/body` — fetch full email body
      - `POST /api/gmail/messages/{message_id}/labels/remove` — remove label
      - `POST /api/gmail/send` — send email
      - `POST /api/gmail/messages/{message_id}/attachments` — fetch attachments
    - All endpoints require authentication (HTTP 401 for unauthenticated)
    - _Requirements: 1.1, 1.5, 2.1, 2.2, 2.5, 3.1, 6.1, 6.3, 6.4, 6.5, 9.1, 9.3, 10.1, 14.1, 14.4_

  - [x] 7.3 Implement error handler
    - Create `api/error_handler.py` mapping domain exceptions to HTTP responses
    - Map all error codes: UNAUTHORIZED (401), GMAIL_CONNECT_FAILED (400), GMAIL_NOT_CONNECTED (403/409), GMAIL_FETCH_ERROR (502), MESSAGE_NOT_FOUND (404), LABEL_NAMESPACE_VIOLATION (400), GMAIL_LABEL_REMOVE_FAILED (502), GMAIL_SEND_FAILED (502), RATE_LIMITED (429)
    - _Requirements: 1.5, 2.4, 2.5, 3.1, 6.3, 6.4, 6.5, 9.3, 9.4, 10.5, 10.6, 14.3, 14.4_

  - [x] 7.4 Implement DI container and register module
    - Create `container.py` with dependency injection setup for all services and infrastructure components
    - Register Gmail router in `backend/src/main.py`
    - Wire up GmailAdapter, repositories, services, QuotaTracker, AuditLogger with proper dependencies
    - _Requirements: All (module wiring)_

  - [x]* 7.5 Write property tests for encryption and body decoding
    - **Property 4: Raw payload encryption round-trip**
    - **Property 5: Email body decoding**
    - **Validates: Requirements 5.4, 6.2**

- [x] 8. Implement ARQ worker and polling job
  - [x] 8.1 Implement ARQ worker configuration
    - Create `worker.py` with `poll_gmail_emails` cron job function
    - Configure ARQ cron to run every 5 minutes (configurable via GMAIL_POLL_INTERVAL_SECONDS)
    - Implement job logic: iterate connected users, call `EmailSyncService.poll_emails` for each
    - Skip users with Connection_Status != "connected"
    - Handle unhandled exceptions: log with stack trace, ARQ auto-retries next interval
    - _Requirements: 4.1, 4.5, 4.7, 4.8, 13.4_

  - [x]* 8.2 Write property tests for audit logging
    - **Property 17: Audit log completeness**
    - **Property 18: Audit log privacy**
    - **Validates: Requirements 15.1, 15.2, 15.3**

  - [x]* 8.3 Write unit tests for ARQ worker and integration flows
    - Test poll job skips disconnected users
    - Test poll job handles token refresh failure
    - Test manual sync cooldown enforcement
    - Test end-to-end fetch with mocked Gmail API (respx)
    - _Requirements: 4.1, 4.7, 4.8, 14.2_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The module reuses existing infrastructure: OAuth_Grant table, CryptoUtils (AES-256-GCM), ARQ worker, Redis, PostgreSQL
- All Gmail API interactions go through GmailAdapter with built-in rate limiting and retry logic

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "2.4"] },
    { "id": 3, "tasks": ["2.5", "2.6", "2.7"] },
    { "id": 4, "tasks": ["3.1", "3.3"] },
    { "id": 5, "tasks": ["3.2", "3.4"] },
    { "id": 6, "tasks": ["5.1", "5.3", "5.5"] },
    { "id": 7, "tasks": ["5.2", "5.4", "5.6"] },
    { "id": 8, "tasks": ["7.1"] },
    { "id": 9, "tasks": ["7.2", "7.3"] },
    { "id": 10, "tasks": ["7.4", "7.5"] },
    { "id": 11, "tasks": ["8.1"] },
    { "id": 12, "tasks": ["8.2", "8.3"] }
  ]
}
```
