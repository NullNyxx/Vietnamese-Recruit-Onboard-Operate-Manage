# Requirements Document

## Introduction

Module Recruitment CV Pipeline xử lý tự động hóa quy trình tuyển dụng từ email CV đến tạo hồ sơ ứng viên. Module bao gồm: (1) nhận diện email chứa CV từ Gmail inbox qua AI Intent Classifier, (2) trích xuất text từ file đính kèm (PDF/DOCX/image) bằng PaddleOCR, (3) parse text thành structured data qua LLM (litellm), (4) tạo Candidate record trong database, (5) quản lý Candidate Pool với 6 actions (View CV, Schedule Interview, Send Email, Reject, Accept/Pass, Archive), và (6) tìm kiếm/lọc ứng viên. Module phụ thuộc vào gmail-integration (email fetch, attachment download, label management) đã implement sẵn.

## Glossary

- **System**: Module Recruitment CV Pipeline trong Vroom HR backend
- **HR**: Người dùng HR duy nhất đăng nhập hệ thống, quản lý tuyển dụng
- **Intent_Classifier**: AI service sử dụng LLM (litellm) để phân loại email theo intent: CV, Partner, Event, Internal, Other
- **CV_Processor**: Application service điều phối pipeline xử lý CV: OCR → LLM parse → validate → persist
- **OCR_Adapter**: Infrastructure adapter giao tiếp với olmOCR server (https://olmocr.aibuddy.vn/ocr) qua HTTP multipart/form-data API. olmOCR là Vision Language Model (7B params) của Allen AI, trả về Markdown từ PDF/ảnh
- **LLM_Adapter**: Infrastructure adapter giao tiếp với LLM provider qua OpenAI-compatible API (9Router tại http://127.0.0.1:20128/v1, model "NullNyx-Combo"), có PII redaction. Sử dụng openai Python SDK với custom base_url
- **Candidate**: Domain entity đại diện cho một ứng viên, được tạo từ kết quả parse CV
- **Candidate_Pool**: Tập hợp tất cả Candidate records, hiển thị dưới dạng list view với search/filter
- **Parsed_CV**: Value object chứa structured data từ CV: name, email, phone, skills, experience, education, summary
- **CV_Document**: Entity đại diện cho file CV gốc đã lưu trên MinIO, liên kết với Candidate
- **PII_Redactor**: Service loại bỏ thông tin nhạy cảm (CCCD/CMND, MST, số tài khoản ngân hàng, lương) trước khi gửi text tới LLM
- **Candidate_Status**: Trạng thái lifecycle của ứng viên: new, reviewing, interview_scheduled, accepted, rejected, archived
- **Processing_Status**: Trạng thái xử lý CV trong pipeline: pending, ocr_processing, llm_parsing, completed, failed
- **Confidence_Score**: Điểm tin cậy (0.0–1.0) từ LLM parse, dùng để flag CV cần HR review thủ công
- **MinIO_Storage**: Object storage lưu file CV gốc tại path storage/cv/{message_id}.{ext}

## Requirements

### Requirement 1: AI Intent Classification cho Email

**User Story:** Là HR, tôi muốn hệ thống tự động phân loại email theo intent, để email chứa CV được chuyển vào pipeline tuyển dụng mà tôi không cần phân loại thủ công.

#### Acceptance Criteria

1. WHEN a new Email_Message is fetched by the Poll_Job, THE Intent_Classifier SHALL classify the email into one of the following intents: CV, Partner, Event, Internal, Other within a maximum processing time of 30 seconds per email (including PII redaction and LLM call) using the configured LLM endpoint (environment variable LLM_BASE_URL, default: "http://127.0.0.1:20128/v1") with model name (environment variable LLM_MODEL, default: "NullNyx-Combo") via OpenAI-compatible chat completions API
2. WHEN classifying an email, THE Intent_Classifier SHALL use the email subject, sender email address, sender name, and snippet (first 200 characters) as classification input, and SHALL include attachment metadata (filename, MIME type, count) as additional classification context
3. WHEN the email contains PDF, DOCX, or image attachments (JPEG/PNG), THE Intent_Classifier SHALL include the presence and count of these attachment types as a signal in the classification prompt so that the LLM considers attachment presence when determining intent
4. WHEN the Intent_Classifier determines intent is CV, THE System SHALL add the Gmail label "VroomHR/recruitment" to the email and enqueue the email for CV pipeline processing
5. WHEN the Intent_Classifier determines intent is Partner, Event, Internal, or Other, THE System SHALL store the classified intent on the Email_Message record without triggering CV pipeline processing
6. THE PII_Redactor SHALL replace CCCD/CMND numbers (12 consecutive digits), MST (10-13 consecutive digits), bank account numbers (8-19 consecutive digits), and salary figures (numbers followed by or preceded by "VND", "đ", "triệu", "tr", or comma-formatted numbers ≥ 1,000,000) with a placeholder token "[REDACTED]" in email text before sending to the LLM for classification
7. IF the PII_Redactor encounters an error during redaction processing, THEN THE System SHALL skip the classification for that email, mark the Email_Message as classification_failed, and log an error with the email_message_id indicating PII redaction failure
8. WHEN the LLM classification call completes, THE System SHALL log an audit entry with: operation_type "intent_classify", user_id, timestamp, email_message_id, classified_intent, and model_name
9. IF the LLM classification call fails after 3 retry attempts with exponential backoff (1s, 2s, 4s) where each individual LLM call times out after 15 seconds, THEN THE System SHALL mark the email as classification_failed and log an error with the email_message_id for manual review by HR
10. IF the LLM returns a response that cannot be parsed into one of the valid intents (CV, Partner, Event, Internal, Other), THEN THE System SHALL classify the email as "Other" and log a warning with the email_message_id and the raw LLM response

### Requirement 2: Lưu trữ file CV vào MinIO

**User Story:** Là HR, tôi muốn file CV gốc được lưu trữ an toàn, để tôi có thể xem lại bản gốc bất kỳ lúc nào.

#### Acceptance Criteria

1. WHEN an email is classified as CV intent AND has attachments, THE System SHALL download each attachment from Gmail via the Gmail_Adapter, up to a maximum of 20 attachments per email
2. WHEN downloading attachments, THE System SHALL validate file type against allowed MIME types: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, image/jpeg, image/png
3. WHEN downloading attachments, THE System SHALL validate file size does not exceed 10MB per file
4. WHEN an attachment passes validation, THE System SHALL sanitize the filename by removing path separators and special characters, truncating to a maximum of 255 characters, and upload the file to MinIO_Storage at path storage/cv/{gmail_message_id}/{sanitized_filename} with content-type metadata preserved; IF two attachments in the same email produce identical sanitized filenames, THEN THE System SHALL append a numeric suffix (_1, _2, etc.) to disambiguate
5. WHEN the file is stored successfully, THE System SHALL create a CV_Document record with: file_path, original_filename, mime_type, size_bytes, gmail_message_id, uploaded_at timestamp, and status set to "stored"
6. IF an attachment fails MIME type or size validation, THEN THE System SHALL skip that attachment, log a warning with gmail_message_id, filename, and rejection reason, and continue processing remaining attachments
7. IF the MinIO upload fails after 3 retry attempts with exponential backoff (1s, 2s, 4s), THEN THE System SHALL create a CV_Document record with status "upload_failed" and log an error; the next Poll_Job cycle SHALL retry failed uploads up to 5 total cycles, after which THE System SHALL mark the CV_Document status as "permanently_failed" and log a warning with gmail_message_id and filename

### Requirement 3: OCR Text Extraction (olmOCR)

**User Story:** Là HR, tôi muốn hệ thống trích xuất text từ file CV (kể cả scan/ảnh), để nội dung CV có thể được parse tự động.

#### Acceptance Criteria

1. WHEN a CV_Document is stored successfully in MinIO, THE OCR_Adapter SHALL download the file from MinIO and send it to the olmOCR server via POST /ocr (multipart/form-data, field "file") for text extraction
2. THE OCR_Adapter SHALL use the olmOCR endpoint configured via environment variable OLMOCR_API_URL (default: "https://olmocr.aibuddy.vn/ocr") to allow switching between self-hosted instances
3. WHEN olmOCR returns a successful response (HTTP 200 with JSON body containing "markdown" field), THE System SHALL store the returned markdown text on the CV_Document record as the ocr_output field
4. WHEN processing a PDF file up to 20 pages, THE OCR_Adapter SHALL send the entire PDF file directly to olmOCR; olmOCR processes all pages internally and returns a single markdown document with heading structure preserved
5. WHEN processing a PDF file exceeding 20 pages, THE OCR_Adapter SHALL split the PDF into chunks of 20 pages using PyMuPDF (fitz), send each chunk separately to olmOCR, and concatenate the returned markdown results in page order with a separator "--- CHUNK {n} ---" between each chunk
6. WHEN processing a DOCX file, THE System SHALL first extract embedded text directly using python-docx; IF the extracted text contains fewer than 50 characters while the file size exceeds 500 KB, THEN THE System SHALL convert the DOCX to PDF (using python-docx2pdf or equivalent) and send the PDF to olmOCR
7. WHEN processing an image file (JPG or PNG), THE OCR_Adapter SHALL send the image directly to olmOCR server as multipart/form-data with appropriate MIME type (image/jpeg or image/png)
8. THE OCR_Adapter SHALL set a timeout of 600 seconds (10 minutes) per olmOCR request to accommodate large PDF files requiring Vision Language Model processing
9. IF the olmOCR server returns a non-200 HTTP status or the response JSON does not contain a "markdown" field, THEN THE System SHALL retry the request up to 3 times with exponential backoff (5s, 10s, 20s); IF all retries fail, THEN THE System SHALL mark Processing_Status as "failed" with reason "ocr_failed" and log the error with CV_Document ID and HTTP status code
10. IF the olmOCR server is unreachable (ConnectionError or DNS failure), THEN THE System SHALL mark Processing_Status as "failed" with reason "ocr_service_unavailable" and log the error for alerting
11. IF the returned markdown text is empty or contains fewer than 50 characters, THEN THE System SHALL mark Processing_Status as "failed" with reason "ocr_insufficient_text" and flag the CV for manual review by HR
12. THE OCR_Adapter output format SHALL be Markdown, which may include: text with full Vietnamese diacritics, LaTeX formulas ($...$), HTML tables, and heading structure (#, ##, ...) — all of which SHALL be passed as-is to the LLM parse step

### Requirement 4: LLM Parse CV thành Structured Data

**User Story:** Là HR, tôi muốn thông tin ứng viên được trích xuất tự động từ CV, để tôi không cần nhập liệu thủ công.

#### Acceptance Criteria

1. WHEN OCR text extraction completes successfully with sufficient text (50 characters or more), THE LLM_Adapter SHALL parse the OCR markdown text into a Parsed_CV structured JSON using the configured LLM endpoint (environment variable LLM_BASE_URL, default: "http://127.0.0.1:20128/v1") with model (environment variable LLM_MODEL, default: "NullNyx-Combo") via OpenAI-compatible chat completions API. The Parsed_CV fields are: name (string, maximum 200 characters), email (string, maximum 254 characters), phone (string, maximum 20 characters), skills (list of strings, maximum 50 items), experience (list of objects with company, title, duration, description — maximum 20 items), education (list of objects with institution, degree, field, year — maximum 10 items), and summary (string, maximum 500 characters)
2. THE PII_Redactor SHALL replace CCCD/CMND numbers, MST, bank account numbers, and salary figures in the OCR text with a placeholder token "[REDACTED]" before sending to the LLM for parsing, preserving the surrounding text structure
3. WHEN the LLM returns a Parsed_CV, THE System SHALL assign a Confidence_Score between 0.0 and 1.0 calculated as: name present = 0.25, email present = 0.25, phone present = 0.1, skills non-empty = 0.1, experience non-empty = 0.15, education non-empty = 0.1, summary non-empty = 0.05
4. WHEN the Confidence_Score is 0.7 or above, THE System SHALL proceed to create a Candidate record automatically
5. WHEN the Confidence_Score is below 0.7, THE System SHALL flag the Parsed_CV for HR manual review and set Processing_Status to "needs_review"
6. IF the LLM parse operation exceeds 30 seconds, THEN THE System SHALL abort the request and mark Processing_Status as "failed" with reason "llm_timeout"
7. IF the LLM returns invalid JSON or a response that cannot be mapped to the Parsed_CV schema, THEN THE System SHALL retry the parse once with a simplified prompt; IF the retry also fails, THEN THE System SHALL mark Processing_Status as "failed" with reason "llm_parse_error"
8. WHEN the LLM parse call completes (success or failure), THE System SHALL log an audit entry with: operation_type "cv_parse", user_id, timestamp, cv_document_id, model_name, confidence_score, token_usage, and success/failure status
9. IF OCR text extraction produces fewer than 50 characters, THEN THE System SHALL skip LLM parsing and mark Processing_Status as "failed" with reason "insufficient_ocr_text"

### Requirement 5: Validate và tạo Candidate Record

**User Story:** Là HR, tôi muốn ứng viên mới tự động xuất hiện trong Candidate Pool sau khi CV được xử lý, để tôi có thể bắt đầu đánh giá ngay.

#### Acceptance Criteria

1. WHEN a Parsed_CV has Confidence_Score of 0.7 or above, THE System SHALL validate that required fields are present: name (non-empty string, maximum 255 characters) AND email (valid format containing exactly one "@" with non-empty local and domain parts, maximum 255 characters)
2. WHEN required fields are valid, THE System SHALL create a Candidate record with: name, email, phone (or empty string if not present in Parsed_CV), skills (or empty list if not present), experience (or empty list if not present), education (or empty list if not present), summary (or empty string if not present), source_email_message_id, cv_document_id, status set to "new", and created_at timestamp
3. WHEN a Candidate record is created, THE System SHALL mark the source Gmail message with label "VroomHR/processed" via the Gmail_Adapter
4. WHEN a Candidate record is created, THE System SHALL set Processing_Status to "completed" on the associated CV_Document
5. IF a Candidate with the same email already exists in the database, THEN THE System SHALL replace the existing Candidate record fields (name, phone, skills, experience, education, summary) with values from the new Parsed_CV, link the new CV_Document to the existing record, set updated_at timestamp, and retain the existing Candidate status unchanged
6. IF required field validation fails (name empty OR name exceeds 255 characters OR email invalid), THEN THE System SHALL set Processing_Status to "needs_review" on the associated CV_Document and store a validation_errors list on the CV_Document indicating which fields failed and the reason for each failure
7. THE System SHALL store the complete Parsed_CV JSON as a JSONB column on the Candidate record for future reference and search
8. IF a Parsed_CV has Confidence_Score below 0.7, THEN THE System SHALL set Processing_Status to "needs_review" on the associated CV_Document and store a validation_errors entry indicating low confidence score without creating or updating a Candidate record
9. IF the database operation to create or update the Candidate record fails, THEN THE System SHALL set Processing_Status to "failed" on the associated CV_Document and log the error with the cv_document_id and failure reason

### Requirement 6: Candidate Pool — List View

**User Story:** Là HR, tôi muốn xem danh sách tất cả ứng viên, để tôi có cái nhìn tổng quan về pipeline tuyển dụng.

#### Acceptance Criteria

1. WHEN HR requests GET /api/recruitment/candidates, THE System SHALL return a paginated list of Candidate records sorted by created_at descending (newest first) with default page_size of 20, maximum page_size of 100, minimum page number of 1, and return an empty list with total_count of 0 when no candidates exist
2. WHEN returning the candidate list, THE System SHALL include for each Candidate: id, name, email, phone, skills (up to the first 5 elements, or fewer if the candidate has fewer than 5), status, confidence_score (decimal value from 0.0 to 1.0), created_at, and has_cv flag
3. WHEN HR provides a search query parameter (between 1 and 200 characters), THE System SHALL search across Candidate name, email, phone, and skills fields using case-insensitive partial matching and return only candidates where at least one field contains the query substring
4. WHEN HR provides filter parameters, THE System SHALL support filtering by: status (one or more values from the set: new, reviewing, interview_scheduled, accepted, rejected, archived), created_at date range (from_date inclusive, to_date inclusive), and minimum confidence_score (decimal from 0.0 to 1.0)
5. WHEN HR provides a skills filter parameter (comma-separated list), THE System SHALL return Candidates whose skills array contains at least one of the specified skills using case-insensitive exact matching per skill (OR logic)
6. THE System SHALL return the total count of matching Candidates alongside the paginated results for pagination UI rendering
7. IF HR requests GET /api/recruitment/candidates without a valid authentication session, THEN THE System SHALL return HTTP 401 with error code UNAUTHORIZED
8. IF HR provides invalid filter parameters (unrecognized status value, malformed date format, or confidence_score outside 0.0–1.0), THEN THE System SHALL return HTTP 422 with an error message indicating which parameter is invalid without executing the query

### Requirement 7: Candidate Pool — Detail View

**User Story:** Là HR, tôi muốn xem chi tiết thông tin ứng viên, để tôi có thể đánh giá ứng viên đầy đủ trước khi ra quyết định.

#### Acceptance Criteria

1. WHEN HR requests GET /api/recruitment/candidates/{candidate_id} with a valid UUID format candidate_id, THE System SHALL return the full Candidate record including: id, name, email, phone, skills (list of strings), experience (list of objects), education (list of objects), summary, status (one of: new, reviewing, interview_scheduled, accepted, rejected, archived), confidence_score (0.0–1.0), created_at, updated_at, source_email_message_id, and all linked CV_Documents within 2 seconds response time (p95)
2. WHEN returning CV_Documents, THE System SHALL include for each document: id, original_filename, mime_type, size_bytes, uploaded_at, and a pre-signed MinIO URL valid for 15 minutes for direct file download; IF a pre-signed URL cannot be generated for a CV_Document (MinIO unavailable or file missing), THEN THE System SHALL return the document metadata with the URL field set to null and include an error indicator for that document
3. IF the candidate_id path parameter is not a valid UUID format, THEN THE System SHALL return HTTP 400 with error code INVALID_CANDIDATE_ID
4. IF the candidate_id does not exist in the database, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND
5. IF HR requests the detail view without a valid authentication session, THEN THE System SHALL return HTTP 401 with error code UNAUTHORIZED

### Requirement 8: Candidate Action — View CV

**User Story:** Là HR, tôi muốn xem file CV gốc của ứng viên, để tôi có thể đọc CV đầy đủ ngoài thông tin đã parse.

#### Acceptance Criteria

1. WHEN HR requests GET /api/recruitment/candidates/{candidate_id}/cv/{document_id}, THE System SHALL return HTTP 200 with a JSON response containing: a pre-signed MinIO download URL valid for 15 minutes, and file metadata including filename, mime_type, and size_bytes
2. IF the specified candidate_id does not reference an existing Candidate, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND
3. IF the CV_Document does not belong to the specified Candidate OR the document_id does not exist, THEN THE System SHALL return HTTP 404 with error code CV_DOCUMENT_NOT_FOUND
4. IF the file does not exist in MinIO (storage corruption), THEN THE System SHALL return HTTP 404 with error code CV_FILE_MISSING and log an error
5. IF the MinIO service is unreachable during pre-signed URL generation, THEN THE System SHALL return HTTP 502 with error code STORAGE_SERVICE_UNAVAILABLE

### Requirement 9: Candidate Action — Schedule Interview

**User Story:** Là HR, tôi muốn lên lịch phỏng vấn cho ứng viên trực tiếp từ Candidate Pool, để quy trình tuyển dụng diễn ra liền mạch.

#### Acceptance Criteria

1. WHEN HR requests POST /api/recruitment/candidates/{candidate_id}/schedule-interview with parameters: date (must be a future date), time, duration_minutes (minimum 15, maximum 180), interviewer_ids (list of 1 to 10 employee IDs), and optional notes (maximum 1000 characters), THE System SHALL validate that all required parameters are present, date is in the future, duration_minutes is within range, interviewer_ids contains at least 1 and at most 10 valid employee IDs, and create an interview scheduling request
2. WHEN the scheduling request is valid AND Candidate_Status is "new" or "reviewing", THE System SHALL update Candidate_Status to "interview_scheduled" and emit a domain event for the interview module to process
3. IF Candidate_Status is "rejected" or "archived", THEN THE System SHALL return HTTP 409 with error code INVALID_STATUS_TRANSITION and a message indicating the candidate cannot be scheduled for interview in the current status
4. WHEN the interview is scheduled successfully, THE System SHALL log an audit entry with: operation_type "schedule_interview", user_id, candidate_id, timestamp, and interviewer_ids
5. IF candidate_id does not correspond to an existing candidate record, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND and a message indicating the candidate does not exist
6. IF any interviewer_id in interviewer_ids does not correspond to an existing employee record, THEN THE System SHALL return HTTP 422 with error code INVALID_INTERVIEWER and a message indicating which interviewer IDs are invalid
7. IF any required parameter is missing or fails validation (date not in the future, duration_minutes outside 15–180 range, interviewer_ids empty or exceeds 10 entries), THEN THE System SHALL return HTTP 422 with error code VALIDATION_ERROR and a message indicating which parameters failed validation

### Requirement 10: Candidate Action — Send Email

**User Story:** Là HR, tôi muốn gửi email cho ứng viên trực tiếp từ Candidate Pool, để tôi có thể liên lạc nhanh mà không cần chuyển sang Gmail.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", WHEN HR requests POST /api/recruitment/candidates/{candidate_id}/send-email with parameters: subject (minimum 1 non-whitespace character, maximum 500 characters), body_html (maximum 100,000 characters), and optional template_name (maximum 100 characters), THE System SHALL send an email to the Candidate's email address via the Gmail_Adapter using the HR's authenticated Gmail account
2. WHEN template_name is provided AND the template exists, THE System SHALL load the email template, substitute Candidate fields (name, position applied) into template placeholders, and use the rendered content as the email body, ignoring the body_html parameter
3. WHEN the email is sent successfully, THE System SHALL log an audit entry with: operation_type "candidate_email_sent", user_id, candidate_id, timestamp (ISO 8601 UTC format), subject (truncated to 100 characters), and template_name (if applicable)
4. IF the candidate_id does not exist in the database, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND
5. IF the Candidate email address is empty or does not conform to RFC 5322 basic format validation, THEN THE System SHALL return HTTP 400 with error code INVALID_CANDIDATE_EMAIL
6. IF template_name is provided AND the template does not exist, THEN THE System SHALL return HTTP 400 with error code TEMPLATE_NOT_FOUND
7. IF Connection_Status is not "connected" when the request is made, THEN THE System SHALL return HTTP 409 with error code GMAIL_NOT_CONNECTED without calling the Gmail_Adapter
8. IF the Gmail send operation fails, THEN THE System SHALL return HTTP 502 with error code EMAIL_SEND_FAILED and the failure reason from the Gmail_Adapter

### Requirement 11: Candidate Action — Reject

**User Story:** Là HR, tôi muốn từ chối ứng viên không phù hợp, để pipeline tuyển dụng chỉ chứa ứng viên đang active.

#### Acceptance Criteria

1. WHEN HR requests POST /api/recruitment/candidates/{candidate_id}/reject with optional parameter: reason (maximum 1000 characters), THE System SHALL update Candidate_Status to "rejected", store the rejection reason and rejected_at timestamp, and return HTTP 200 with the updated candidate record
2. WHEN a Candidate is rejected, THE System SHALL retain the Candidate record and all associated data (CV_Documents, Parsed_CV) for the configured retention period (environment variable CANDIDATE_RETENTION_DAYS, default 90 days), after which the system SHALL hard-delete the candidate record and all associated files
3. IF Candidate_Status is already "rejected" or "archived", THEN THE System SHALL return HTTP 409 with error code INVALID_STATUS_TRANSITION indicating the current status and the attempted transition
4. WHEN the rejection is recorded, THE System SHALL log an audit entry with: operation_type "candidate_rejected", user_id, candidate_id, timestamp, and reason (truncated to 200 characters)
5. IF the candidate_id does not exist in the system, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND
6. IF the reason parameter exceeds 1000 characters, THEN THE System SHALL return HTTP 422 with error code VALIDATION_ERROR indicating the maximum allowed length

### Requirement 12: Candidate Action — Accept/Pass

**User Story:** Là HR, tôi muốn đánh dấu ứng viên đã pass phỏng vấn, để tôi có thể tiến hành onboarding.

#### Acceptance Criteria

1. WHEN HR requests POST /api/recruitment/candidates/{candidate_id}/accept, THE System SHALL update Candidate_Status to "accepted" and store accepted_at as a server-generated UTC timestamp
2. WHEN the acceptance is successfully persisted, THE System SHALL emit a domain event "candidate_accepted" containing candidate_id, name, and email for downstream modules (onboarding email pipeline) to consume
3. IF Candidate_Status is not "interview_scheduled" or "reviewing", THEN THE System SHALL return HTTP 409 with error code INVALID_STATUS_TRANSITION and a message indicating only candidates in "interview_scheduled" or "reviewing" status can be accepted
4. WHEN the acceptance is recorded, THE System SHALL log an audit entry with: operation_type "candidate_accepted", user_id, candidate_id, and timestamp
5. IF candidate_id does not match any existing Candidate record, THEN THE System SHALL return HTTP 404 with error code CANDIDATE_NOT_FOUND and a message indicating the candidate does not exist

### Requirement 13: Candidate Action — Archive

**User Story:** Là HR, tôi muốn archive ứng viên không còn relevant, để Candidate Pool gọn gàng mà vẫn giữ lại data cho tham khảo sau.

#### Acceptance Criteria

1. WHEN HR requests POST /api/recruitment/candidates/{candidate_id}/archive, THE System SHALL update Candidate_Status to "archived", store archived_at timestamp as UTC, and return the updated Candidate record
2. WHILE a Candidate has Candidate_Status "archived", THE System SHALL exclude the Candidate from default list view queries and only return the Candidate when HR explicitly filters by status "archived"
3. IF Candidate_Status is already "archived", THEN THE System SHALL return HTTP 200 idempotently with the existing Candidate record without modifying archived_at
4. WHEN the archive action is recorded, THE System SHALL log an audit entry with: operation_type "candidate_archived", user_id, candidate_id, previous_status, and timestamp
5. IF candidate_id does not exist in the system, THEN THE System SHALL return an error response indicating the candidate was not found
6. IF Candidate_Status is "accepted", THEN THE System SHALL return an error response indicating that candidates with status "accepted" cannot be archived

### Requirement 14: HR Manual Review cho CV parse thất bại hoặc confidence thấp

**User Story:** Là HR, tôi muốn xem và sửa thông tin CV mà hệ thống parse không chính xác, để không bỏ sót ứng viên tiềm năng.

#### Acceptance Criteria

1. WHEN Processing_Status is "needs_review" or "failed", THE System SHALL display the CV in a review queue accessible via GET /api/recruitment/cv-review with the OCR extracted text, partial Parsed_CV data (if available), and the original CV file link
2. WHEN HR requests PUT /api/recruitment/cv-review/{cv_document_id} with corrected Parsed_CV data, THE System SHALL validate the corrected data (name must be at least 1 non-whitespace character and at most 200 characters, email must be valid RFC 5322 format and at most 254 characters), create or update the Candidate record, and set Processing_Status to "completed"
3. IF HR submits corrected data via PUT /api/recruitment/cv-review/{cv_document_id} and validation fails, THEN THE System SHALL return an error response indicating which fields are invalid without modifying the CV_Document or creating a Candidate record
4. WHEN HR requests POST /api/recruitment/cv-review/{cv_document_id}/retry, THE System SHALL set Processing_Status to "processing", re-run the LLM parse step with the stored OCR text within 60 seconds, and update the Parsed_CV result
5. IF the LLM retry triggered via POST /api/recruitment/cv-review/{cv_document_id}/retry fails or times out, THEN THE System SHALL set Processing_Status back to "needs_review" and return an error response indicating the retry failure reason
6. WHEN HR requests DELETE /api/recruitment/cv-review/{cv_document_id}/dismiss, THE System SHALL mark the CV_Document as "dismissed" and exclude it from the review queue without creating a Candidate record
7. THE System SHALL return the review queue sorted by created_at descending with pagination (default page_size 20, maximum page_size 100)
8. IF HR requests any cv-review endpoint with a cv_document_id that does not exist, THEN THE System SHALL return an error response indicating the resource was not found

### Requirement 15: Data Retention và Candidate Deletion

**User Story:** Là system architect, tôi muốn dữ liệu ứng viên bị từ chối được xóa sau thời gian quy định, để hệ thống tuân thủ quy định bảo vệ dữ liệu cá nhân (NĐ 13/2023/NĐ-CP).

#### Acceptance Criteria

1. THE System SHALL hard-delete Candidate records with status "rejected" after the configured retention period (environment variable CANDIDATE_RETENTION_DAYS, default 90 days, minimum 30, maximum 365) counting from rejected_at timestamp
2. WHEN a Candidate record is hard-deleted, THE System SHALL delete all associated CV_Documents from MinIO_Storage and remove the Parsed_CV data from the database within the same logical operation, processing one candidate at a time so that a failure on one candidate does not prevent deletion of subsequent candidates
3. IF deletion of a CV_Document from MinIO_Storage fails during the retention job, THEN THE System SHALL skip that candidate record, log an error-level audit entry containing the candidate_id (anonymized hash) and failure reason, and retry deletion of that candidate on the next scheduled job run
4. THE System SHALL execute the retention cleanup as an ARQ scheduled job running daily at 02:00 UTC (configurable via environment variable), processing a maximum of 500 candidate records per run
5. WHEN a Candidate record is deleted by the retention job, THE System SHALL log an audit entry with: operation_type "candidate_data_deleted", candidate_id (anonymized hash), and timestamp
6. THE System SHALL NOT delete Candidates with status "new", "reviewing", "interview_scheduled", "accepted", or "archived" regardless of age

### Requirement 16: CV Processing Pipeline — End-to-End Performance

**User Story:** Là HR, tôi muốn CV được xử lý nhanh chóng, để ứng viên xuất hiện trong Candidate Pool trong thời gian hợp lý.

#### Acceptance Criteria

1. THE CV_Processor SHALL complete the full pipeline (attachment download + MinIO upload + olmOCR + LLM parse + Candidate creation) within 120 seconds per CV document for PDF or DOCX files up to 5 pages and up to 10MB in file size (olmOCR Vision Language Model requires longer processing time than traditional OCR)
2. WHEN multiple CVs arrive in a single email batch, THE System SHALL process CVs concurrently with a maximum of 3 parallel CV processing tasks, queuing any additional CVs beyond 3 for sequential processing as slots become available
3. THE System SHALL track processing duration for each CV and expose metrics via GET /api/recruitment/metrics endpoint: average_processing_time (rolling last 24 hours, in milliseconds), success_rate (percentage, rolling last 24 hours), failure_rate (percentage, rolling last 24 hours), and queue_depth (current number of pending CV tasks)
4. IF a CV processing task exceeds 660 seconds (11 minutes) total elapsed time, THEN THE System SHALL abort the task, mark Processing_Status as "failed" with reason "timeout", and log an error with the CV filename and the pipeline step that was executing at the time of timeout (olmOCR timeout alone is 600s)
5. IF an individual pipeline step (MinIO upload, olmOCR, or LLM parse) fails with a non-timeout error, THEN THE System SHALL retry that step up to 2 times with exponential backoff (5s, 10s), and if all retries fail, mark Processing_Status as "failed" with reason indicating the failed step name, and proceed to process remaining CVs in the batch
6. IF a CV document exceeds 5 pages or 10MB file size, THEN THE System SHALL skip processing for that document, mark Processing_Status as "skipped" with reason "exceeds_limit", and log a warning with the filename, page count, and file size

### Requirement 17: Audit Logging cho Recruitment Operations

**User Story:** Là system architect, tôi muốn mọi thao tác tuyển dụng được ghi log, để có thể truy vết khi cần debug hoặc audit compliance.

#### Acceptance Criteria

1. WHEN any state-changing action is performed on a Candidate (status change, data update, deletion) or on a recruitment-related entity (Interview scheduling, email template send, CV parsing request), THE System SHALL log an audit entry with: operation_type, user_id (or "system" for automated actions), entity_type, entity_id, timestamp (ISO 8601 UTC), previous_value, new_value, and a change_summary field describing what was modified (maximum 500 characters)
2. WHEN any LLM call is made (intent classification or CV parsing), THE System SHALL log: operation_type, model_name, token_usage (prompt_tokens, completion_tokens), latency_ms, and success/failure status
3. THE System SHALL NOT log the full OCR text, full CV content, or PII data (CCCD/CMND number, MST, bank account numbers, salary figures, home address, personal phone number, or personal email address) in audit logs
4. THE System SHALL retain recruitment audit log entries for a minimum of 365 days
5. IF the audit logging mechanism fails, THEN THE System SHALL proceed with the recruitment operation and record the logging failure in the application error log within 5 seconds of the failure occurrence
6. THE System SHALL support querying audit log entries by any combination of: entity_id, user_id, operation_type, and timestamp range, returning results within 2 seconds for queries spanning up to 90 days of data
