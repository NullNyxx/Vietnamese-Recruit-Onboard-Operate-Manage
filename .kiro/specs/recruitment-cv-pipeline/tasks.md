# Implementation Plan: Recruitment CV Pipeline

## Overview

This plan implements the automated CV recruitment pipeline as a new module at `backend/src/modules/recruitment/`. The implementation follows the modular monolith architecture with domain/application/infrastructure/api layers. Tasks are ordered to build foundational components first (domain models, infrastructure adapters), then application services, then API endpoints, with testing integrated throughout.

## Tasks

- [x] 1. Set up module structure, domain models, and database migrations
  - [x] 1.1 Create recruitment module directory structure and domain layer
    - Create `backend/src/modules/recruitment/` with subdirectories: `domain/`, `application/`, `infrastructure/`, `api/`
    - Create `__init__.py` files for each package
    - Implement domain entities: `Candidate`, `CVDocument`, `RecruitmentAuditLog` as SQLModel table classes
    - Implement value objects: `ParsedCV`, `ExperienceItem`, `EducationItem` as Pydantic BaseModel classes
    - Implement enums: `CandidateStatus`, `ProcessingStatus`, `EmailIntent`
    - Implement domain exceptions: `RecruitmentError`, `CandidateNotFoundError`, `CVDocumentNotFoundError`, `InvalidStatusTransitionError`, `CVFileNotFoundError`, `StorageServiceUnavailableError`, `GmailNotConnectedError`, `PipelineTimeoutError`, `OCRExtractionError`, `LLMParseError`
    - _Requirements: 5.1, 5.2, 5.7, 9.2, 9.3, 11.3, 12.3, 13.6_

  - [x] 1.2 Create Alembic migration for recruitment tables
    - Create migration `009_create_recruitment_tables.py` with tables: `candidates`, `cv_documents`, `recruitment_audit_logs`
    - Include all columns, indexes (email, status, processing_status, gmail_message_id, created_at), and foreign keys as defined in the design
    - Add JSONB columns for skills, experience, education, parsed_cv_json, parsed_cv_data, validation_errors, token_usage, previous_value, new_value
    - _Requirements: 5.1, 5.2, 5.7, 17.1_

  - [x] 1.3 Create RecruitmentSettings configuration class
    - Implement `RecruitmentSettings(BaseSettings)` with all configuration fields: LLM, olmOCR, MinIO, processing, data retention, presigned URL settings
    - Use `env_prefix="RECRUITMENT_"` and validate constraints (retention_days ge=30, le=365)
    - Register settings in module container/dependency injection
    - _Requirements: 1.1, 2.3, 3.2, 3.8, 4.1, 4.6, 15.1, 15.4, 16.4_

- [x] 2. Implement infrastructure adapters
  - [x] 2.1 Implement PIIRedactor service
    - Create `backend/src/modules/recruitment/infrastructure/pii_redactor.py`
    - Implement regex-based redaction for: CCCD/CMND (12 consecutive digits), MST (10-13 digits), bank accounts (8-19 digits), salary figures (numbers adjacent to VND/đ/triệu/tr or comma-formatted ≥ 1,000,000)
    - Replace matches with `[REDACTED]` placeholder while preserving surrounding text
    - Handle edge cases: overlapping patterns, Unicode Vietnamese text
    - _Requirements: 1.6, 4.2, 17.3_

  - [ ]* 2.2 Write property test for PII redaction (Property 2)
    - **Property 2: PII redaction replaces all sensitive patterns while preserving surrounding text**
    - **Validates: Requirements 1.6, 4.2**

  - [x] 2.3 Implement filename sanitizer utility
    - Create `backend/src/modules/recruitment/infrastructure/filename_sanitizer.py`
    - Remove path separators (/, \\) and invalid object storage characters
    - Truncate to 255 characters maximum
    - Disambiguate duplicate filenames within same email with numeric suffixes (_1, _2, etc.)
    - _Requirements: 2.4_

  - [ ]* 2.4 Write property test for filename sanitization (Property 14)
    - **Property 14: Filename sanitization produces valid storage paths**
    - **Validates: Requirements 2.4**

  - [x] 2.5 Implement RecruitmentMinIOClient
    - Create `backend/src/modules/recruitment/infrastructure/minio_client.py`
    - Implement methods: `upload_cv`, `download_cv`, `delete_cv`, `generate_presigned_url`
    - Follow existing employee module MinIO pattern
    - Storage path format: `storage/cv/{gmail_message_id}/{sanitized_filename}`
    - Presigned URL expiry: 15 minutes (configurable)
    - _Requirements: 2.4, 2.5, 7.2, 8.1_

  - [x] 2.6 Implement OCRAdapter for olmOCR integration
    - Create `backend/src/modules/recruitment/infrastructure/ocr_adapter.py`
    - Implement `extract_text` method: POST multipart/form-data to olmOCR endpoint
    - Handle PDF chunking for files > 20 pages using PyMuPDF (fitz): split, send chunks, concatenate with separator
    - Handle DOCX: extract text with python-docx, fallback to PDF conversion if < 50 chars and > 500KB
    - Handle image files (JPEG/PNG): send directly
    - Timeout: 600 seconds per request
    - Retry: 3 attempts with exponential backoff (5s, 10s, 20s)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12_

  - [x] 2.7 Implement LLMAdapter for OpenAI-compatible API
    - Create `backend/src/modules/recruitment/infrastructure/llm_adapter.py`
    - Implement `classify_intent` method: construct prompt with email metadata, call chat completions, parse response to EmailIntent enum
    - Implement `parse_cv` method: construct prompt with OCR text, call chat completions, parse JSON response to ParsedCV
    - Use openai Python SDK with custom base_url
    - Intent classification timeout: 15 seconds, CV parse timeout: 30 seconds
    - Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
    - Handle invalid JSON response: retry once with simplified prompt
    - _Requirements: 1.1, 1.2, 1.9, 1.10, 4.1, 4.6, 4.7_

  - [x] 2.8 Implement CandidateRepository and CVDocumentRepository
    - Create `backend/src/modules/recruitment/infrastructure/repositories.py`
    - CandidateRepository: CRUD, find_by_email, list with filters (status, date range, confidence, skills, search), paginated queries
    - CVDocumentRepository: CRUD, find_by_candidate_id, find_needs_review, find_by_gmail_message_id
    - Use SQLAlchemy async session pattern consistent with existing modules
    - _Requirements: 5.1, 5.2, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 2.9 Implement AuditRepository and audit logging helper
    - Create `backend/src/modules/recruitment/infrastructure/audit_repository.py`
    - Implement `log_audit` helper that creates RecruitmentAuditLog entries
    - Ensure PII is never included in audit log content (use PIIRedactor on change_summary)
    - Support querying by entity_id, user_id, operation_type, timestamp range
    - Graceful failure: if audit logging fails, log error but don't block the operation
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [ ]* 2.10 Write property test for audit PII exclusion (Property 13)
    - **Property 13: Audit logs never contain PII data**
    - **Validates: Requirements 17.3**

- [x] 3. Checkpoint - Ensure infrastructure layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement core application services — Intent Classification and CV Processing
  - [x] 4.1 Implement confidence score calculator
    - Create `backend/src/modules/recruitment/application/confidence.py`
    - Calculate score: name=0.25, email=0.25, phone=0.1, skills=0.1, experience=0.15, education=0.1, summary=0.05
    - Result always bounded [0.0, 1.0]
    - _Requirements: 4.3_

  - [ ]* 4.2 Write property test for confidence score calculation (Property 4)
    - **Property 4: Confidence score calculation is deterministic and bounded**
    - **Validates: Requirements 4.3**

  - [x] 4.3 Implement attachment validation logic
    - Create `backend/src/modules/recruitment/application/validators.py`
    - Validate MIME type against allowed set: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, image/jpeg, image/png
    - Validate file size ≤ 10MB (10,485,760 bytes)
    - _Requirements: 2.2, 2.3_

  - [ ]* 4.4 Write property test for attachment validation (Property 3)
    - **Property 3: Attachment validation accepts only allowed MIME types within size limit**
    - **Validates: Requirements 2.2, 2.3**

  - [x] 4.5 Implement IntentClassifierService
    - Create `backend/src/modules/recruitment/application/intent_classifier.py`
    - `classify_email`: fetch email metadata, apply PII redaction, construct prompt with subject/sender/snippet/attachment metadata, call LLM, parse intent
    - `process_classification_result`: apply Gmail label "VroomHR/recruitment" for CV intent, enqueue CV processing via ARQ
    - Handle classification failures: mark email as classification_failed
    - Handle unparseable LLM response: default to "Other", log warning
    - Log audit entry on completion
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [ ]* 4.6 Write property test for intent classification prompt construction (Property 1)
    - **Property 1: Intent classification prompt includes all required email metadata**
    - **Validates: Requirements 1.2, 1.3**

  - [x] 4.7 Implement CVProcessorService
    - Create `backend/src/modules/recruitment/application/cv_processor.py`
    - `process_cv_from_email`: orchestrate full pipeline — download attachments, validate, upload to MinIO, OCR, PII redact, LLM parse, confidence check, create candidate or flag for review
    - `process_single_attachment`: process one attachment through the pipeline with status tracking
    - `retry_llm_parse`: re-run LLM parse for manual review retry
    - Handle concurrency: max 3 parallel tasks via ARQ
    - Pipeline timeout: 660 seconds total
    - Track processing_status transitions: pending → ocr_processing → llm_parsing → completed/needs_review/failed
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 4.8, 4.9, 5.8, 16.1, 16.2, 16.4, 16.5, 16.6_

  - [ ]* 4.8 Write property test for confidence threshold routing (Property 5)
    - **Property 5: Confidence threshold determines automatic vs manual processing**
    - **Validates: Requirements 4.4, 4.5, 5.8**

- [x] 5. Implement Candidate management services
  - [x] 5.1 Implement CandidateService — create/update and deduplication
    - Create `backend/src/modules/recruitment/application/candidate_service.py`
    - `create_or_update_candidate`: check for existing candidate by email, create new or update existing (preserve status), link CV document, add Gmail label "VroomHR/processed"
    - Validate required fields: name non-empty ≤ 255 chars, email valid format ≤ 255 chars
    - Store complete parsed_cv_json on Candidate record
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [ ]* 5.2 Write property test for candidate field validation (Property 6)
    - **Property 6: Candidate field validation enforces name and email constraints**
    - **Validates: Requirements 5.1, 5.6**

  - [ ]* 5.3 Write property test for candidate deduplication (Property 7)
    - **Property 7: Candidate deduplication by email preserves existing status**
    - **Validates: Requirements 5.5**

  - [x] 5.4 Implement CandidateService — status transitions and actions
    - Implement status transition validation following the state machine:
      - new → reviewing, interview_scheduled, rejected, archived
      - reviewing → interview_scheduled, accepted, rejected, archived
      - interview_scheduled → accepted, rejected, archived
      - accepted → (no transitions)
      - rejected → (no transitions)
      - archived → (idempotent re-archive only)
    - `reject_candidate`: validate transition, store reason + rejected_at, audit log
    - `accept_candidate`: validate transition (only from interview_scheduled/reviewing), store accepted_at, emit domain event, audit log
    - `archive_candidate`: validate transition (not from accepted), store archived_at, idempotent for already-archived, audit log
    - `schedule_interview`: validate transition (not from rejected/archived), validate interviewer_ids against employee records, update status, emit domain event, audit log
    - `send_email_to_candidate`: validate Gmail connected, validate candidate email, send via Gmail adapter, support templates, audit log
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [ ]* 5.5 Write property test for status transitions (Property 8)
    - **Property 8: Candidate status transitions follow the valid state machine**
    - **Validates: Requirements 9.2, 9.3, 11.1, 11.3, 12.1, 12.3, 13.1, 13.6**

  - [ ]* 5.6 Write property test for archive idempotence (Property 11)
    - **Property 11: Archive action is idempotent**
    - **Validates: Requirements 13.3**

  - [x] 5.7 Implement CandidateService — list and search
    - `list_candidates`: paginated query with filters (status, date range, min_confidence, skills, search)
    - Search: case-insensitive partial match across name, email, phone, skills
    - Skills filter: OR logic, case-insensitive exact match per skill
    - Default sort: created_at descending
    - Return total_count alongside paginated results
    - Archived candidates excluded from default list (only shown when explicitly filtered)
    - `get_candidate`: full detail with linked CV documents and presigned URLs
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 7.1, 7.2, 7.3, 7.4, 7.5, 13.2_

  - [ ]* 5.8 Write property test for search/filter correctness (Property 9)
    - **Property 9: Search and filter results are correct subsets**
    - **Validates: Requirements 6.3, 6.4, 6.5**

  - [ ]* 5.9 Write property test for pagination invariants (Property 10)
    - **Property 10: Pagination invariants hold for candidate list queries**
    - **Validates: Requirements 6.1, 6.6**

- [x] 6. Checkpoint - Ensure application service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Review Service and Retention Job
  - [x] 7.1 Implement ReviewService
    - Create `backend/src/modules/recruitment/application/review_service.py`
    - `list_review_queue`: paginated list of CV documents with status needs_review or failed, sorted by created_at desc
    - `submit_correction`: validate corrected ParsedCV data (name 1-200 chars, email valid ≤ 254 chars), create/update candidate, set status to completed
    - `retry_parse`: re-run LLM parse on stored OCR text, 60 second timeout, update result
    - `dismiss`: mark CV document as "dismissed", exclude from review queue
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8_

  - [x] 7.2 Implement RetentionJob as ARQ scheduled task
    - Create `backend/src/modules/recruitment/application/retention_job.py`
    - Select candidates: status="rejected" AND rejected_at older than CANDIDATE_RETENTION_DAYS
    - Hard-delete: remove Candidate record, all associated CV_Documents from DB, delete files from MinIO
    - Process one candidate at a time; failure on one doesn't block others
    - Batch size: max 500 per run
    - Schedule: daily at 02:00 UTC (configurable)
    - Audit log each deletion with anonymized candidate_id hash
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

  - [ ]* 7.3 Write property test for retention job selection (Property 12)
    - **Property 12: Retention job selects only eligible candidates for deletion**
    - **Validates: Requirements 15.1, 15.6**

- [x] 8. Implement API layer — Routers and Schemas
  - [x] 8.1 Implement API schemas (Pydantic v2 request/response models)
    - Create `backend/src/modules/recruitment/api/schemas.py`
    - Request schemas: `CandidateListParams`, `ScheduleInterviewRequest`, `SendEmailRequest`, `RejectRequest`, `ParsedCVInput`
    - Response schemas: `CandidateListResponse`, `CandidateDetailResponse`, `CVDocumentResponse`, `CVReviewItemResponse`, `MetricsResponse`, `PaginatedResponse`
    - Include all field validations as defined in design (min/max lengths, ranges, formats)
    - _Requirements: 6.1, 6.2, 6.8, 7.1, 9.1, 9.7, 10.1, 11.6, 14.2_

  - [x] 8.2 Implement CandidateRouter (CRUD + actions)
    - Create `backend/src/modules/recruitment/api/candidate_router.py`
    - `GET /api/recruitment/candidates` — list with pagination, search, filters
    - `GET /api/recruitment/candidates/{candidate_id}` — detail view with CV documents
    - `GET /api/recruitment/candidates/{candidate_id}/cv/{document_id}` — view CV presigned URL
    - `POST /api/recruitment/candidates/{candidate_id}/schedule-interview` — schedule interview
    - `POST /api/recruitment/candidates/{candidate_id}/send-email` — send email
    - `POST /api/recruitment/candidates/{candidate_id}/reject` — reject candidate
    - `POST /api/recruitment/candidates/{candidate_id}/accept` — accept candidate
    - `POST /api/recruitment/candidates/{candidate_id}/archive` — archive candidate
    - Include authentication dependency, error handling (map domain exceptions to HTTP status codes)
    - _Requirements: 6.1, 6.7, 7.1, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.3, 9.5, 10.1, 10.4, 10.7, 10.8, 11.1, 11.3, 11.5, 12.1, 12.3, 12.5, 13.1, 13.5_

  - [x] 8.3 Implement CVReviewRouter
    - Create `backend/src/modules/recruitment/api/cv_review_router.py`
    - `GET /api/recruitment/cv-review` — list review queue with pagination
    - `PUT /api/recruitment/cv-review/{cv_document_id}` — submit correction
    - `POST /api/recruitment/cv-review/{cv_document_id}/retry` — retry LLM parse
    - `DELETE /api/recruitment/cv-review/{cv_document_id}/dismiss` — dismiss from queue
    - Include error handling for not-found and validation errors
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8_

  - [x] 8.4 Implement MetricsRouter
    - Create `backend/src/modules/recruitment/api/metrics_router.py`
    - `GET /api/recruitment/metrics` — return average_processing_time, success_rate, failure_rate, queue_depth
    - Calculate rolling 24-hour metrics from CV document processing records
    - _Requirements: 16.3_

  - [x] 8.5 Implement error handler middleware for recruitment module
    - Create `backend/src/modules/recruitment/api/error_handler.py`
    - Map domain exceptions to HTTP status codes and error response format
    - Follow existing employee module error_handler pattern
    - _Requirements: 6.8, 7.3, 7.4, 8.2, 8.3, 8.4, 8.5, 9.3, 9.5, 9.6, 9.7, 10.4, 10.5, 10.6, 10.7, 10.8, 11.3, 11.5, 11.6, 12.3, 12.5, 13.5, 13.6, 14.3, 14.8_

- [x] 9. Implement ARQ job registration and module wiring
  - [x] 9.1 Register ARQ jobs and wire module together
    - Create `backend/src/modules/recruitment/container.py` — dependency injection container
    - Register ARQ tasks: `process_cv_from_email`, `retention_cleanup`
    - Wire IntentClassifierService into Gmail poll job hook (cross-module integration via application service interface)
    - Register recruitment routers in `backend/src/main.py`
    - Ensure all dependencies are properly injected (settings, repositories, adapters)
    - _Requirements: 1.4, 2.7, 15.4, 16.2_

  - [ ]* 9.2 Write integration tests for CV processing pipeline
    - Test full pipeline flow with mocked olmOCR and LLM responses
    - Test error scenarios: OCR failure, LLM timeout, MinIO unavailable
    - Test concurrent processing (max 3 parallel tasks)
    - Test pipeline timeout (660s)
    - _Requirements: 16.1, 16.2, 16.4, 16.5_

  - [ ]* 9.3 Write integration tests for candidate API endpoints
    - Test CRUD operations, pagination, search, filters
    - Test all candidate actions (reject, accept, archive, schedule interview, send email)
    - Test error responses (404, 409, 422, 401)
    - Test authentication requirement
    - _Requirements: 6.1, 6.7, 7.5, 8.1, 9.1, 10.1, 11.1, 12.1, 13.1_

  - [ ]* 9.4 Write integration tests for CV review endpoints
    - Test review queue listing, correction submission, retry, dismiss
    - Test validation errors on correction submission
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8_

- [x] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The module follows the existing modular monolith pattern established by the employee module
- Cross-module communication with Gmail module uses application service interfaces (no direct imports)
- All datetime columns use `sa_column=Column(DateTime(timezone=True))` per project conventions
- Use `uv` for package management, `pytest` + `hypothesis` for testing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.5", "2.6", "2.7"] },
    { "id": 3, "tasks": ["2.2", "2.4", "2.8", "2.9"] },
    { "id": 4, "tasks": ["2.10", "4.1", "4.3"] },
    { "id": 5, "tasks": ["4.2", "4.4", "4.5"] },
    { "id": 6, "tasks": ["4.6", "4.7"] },
    { "id": 7, "tasks": ["4.8", "5.1"] },
    { "id": 8, "tasks": ["5.2", "5.3", "5.4", "5.7"] },
    { "id": 9, "tasks": ["5.5", "5.6", "5.8", "5.9"] },
    { "id": 10, "tasks": ["7.1", "7.2"] },
    { "id": 11, "tasks": ["7.3", "8.1"] },
    { "id": 12, "tasks": ["8.2", "8.3", "8.4", "8.5"] },
    { "id": 13, "tasks": ["9.1"] },
    { "id": 14, "tasks": ["9.2", "9.3", "9.4"] }
  ]
}
```
