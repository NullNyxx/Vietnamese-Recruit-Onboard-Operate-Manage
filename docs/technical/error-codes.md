# Error Code Registry

Tài liệu này tổng hợp tất cả error codes từ tất cả modules trong hệ thống Vroom HR.

---

## Tổng quan

| Module       | Base Error Code                                                   | Số lượng exceptions |
| ------------ | ----------------------------------------------------------------- | ------------------- |
| Identity     | `AUTH_*`                                                          | 7                   |
| Employee     | `EMPLOYEE_*`, `DEPARTMENT_*`, `POSITION_*`, `FILE_*`              | 9                   |
| Attendance   | `LEAVE_*`, `ATTENDANCE_*`, `OVERTIME_*`, `SCHEDULE_*`             | 17                  |
| Gmail        | `GMAIL_*`, `UNAUTHORIZED`, `RATE_LIMITED`, `MESSAGE_*`, `LABEL_*` | 12                  |
| Recruitment  | `CANDIDATE_*`, `CV_*`, `PIPELINE_*`, `STORAGE_*`                  | 12                  |
| Payroll      | `PERIOD_*`, `SALARY_*`, `PAYSLIP_*`, `DEPENDENT_*`, `ALLOWANCE_*` | 11                  |
| Self-Service | (chưa có exceptions riêng)                                        | 0                   |

---

## Identity Module

### Base

| Error Code                | HTTP Status | Message                                          | Cause                            |
| ------------------------- | ----------- | ------------------------------------------------ | -------------------------------- |
| `AUTH_ERROR`              | 500         | An authentication error occurred                 | Base exception                   |
| `AUTH_INVALID_STATE`      | 400         | Invalid authentication state                     | CSRF state token invalid/expired |
| `AUTH_GOOGLE_ERROR`       | 502         | Failed to authenticate with Google               | OAuth token exchange failed      |
| `AUTH_ACCESS_DENIED`      | 403         | Access denied. Contact administrator.            | Email không trong whitelist      |
| `AUTH_INSUFFICIENT_SCOPE` | 400         | Please grant all requested permissions           | User declined OAuth scopes       |
| `AUTH_INVALID_TOKEN`      | 401         | Invalid or expired token                         | JWT invalid/expired/revoked      |
| `AUTH_RATE_LIMITED`       | 429         | Too many login attempts. Please try again later. | Per-IP rate limit exceeded       |

---

## Employee Module

### Employee Errors

| Error Code                 | HTTP Status | Message                                 | Cause                     |
| -------------------------- | ----------- | --------------------------------------- | ------------------------- |
| `EMPLOYEE_ERROR`           | 500         | An employee module error occurred       | Base exception            |
| `EMPLOYEE_DUPLICATE_EMAIL` | 409         | Employee with this email already exists | Email đã được sử dụng     |
| `EMPLOYEE_NOT_FOUND`       | 404         | Employee not found                      | Employee ID không tồn tại |

### Department Errors

| Error Code                 | HTTP Status | Message                                        | Cause                       |
| -------------------------- | ----------- | ---------------------------------------------- | --------------------------- |
| `DEPARTMENT_NOT_FOUND`     | 404         | Department not found                           | Department ID không tồn tại |
| `DEPARTMENT_HAS_EMPLOYEES` | 409         | Cannot delete department with active employees | Department còn employees    |

### Position Errors

| Error Code               | HTTP Status | Message                                      | Cause                     |
| ------------------------ | ----------- | -------------------------------------------- | ------------------------- |
| `POSITION_NOT_FOUND`     | 404         | Position not found                           | Position ID không tồn tại |
| `POSITION_HAS_EMPLOYEES` | 409         | Cannot delete position with active employees | Position còn employees    |

### File Errors

| Error Code              | HTTP Status | Message                           | Cause                          |
| ----------------------- | ----------- | --------------------------------- | ------------------------------ |
| `FILE_TOO_LARGE`        | 413         | File exceeds maximum size of 10MB | File upload > 10MB             |
| `UNSUPPORTED_FILE_TYPE` | 415         | File type not supported           | MIME type không được chấp nhận |

---

## Attendance Module

### Leave Errors

| Error Code                        | HTTP Status | Message                                                          | Cause                                  |
| --------------------------------- | ----------- | ---------------------------------------------------------------- | -------------------------------------- |
| `ATTENDANCE_ERROR`                | 500         | An attendance module error occurred                              | Base exception                         |
| `LEAVE_TYPE_NOT_FOUND`            | 404         | Leave type not found                                             | Leave type ID không tồn tại            |
| `LEAVE_REQUEST_NOT_FOUND`         | 404         | Leave request not found                                          | Leave request ID không tồn tại         |
| `INSUFFICIENT_LEAVE_BALANCE`      | 400         | Insufficient leave balance                                       | Số ngày nghỉ yêu cầu > số ngày còn lại |
| `LEAVE_OVERLAP`                   | 409         | Leave request overlaps with an existing approved/pending request | Trùng lặp ngày nghỉ                    |
| `INVALID_LEAVE_STATUS_TRANSITION` | 400         | Cannot transition from '{current}' to '{target}'                 | Invalid status transition              |
| `LEAVE_DATE_IN_PAST`              | 400         | Cannot cancel leave that has already started                     | Leave đã bắt đầu                       |

### Attendance Errors

| Error Code                    | HTTP Status | Message                     | Cause                              |
| ----------------------------- | ----------- | --------------------------- | ---------------------------------- |
| `ALREADY_CHECKED_IN`          | 400         | Already checked in today    | Đã check-in hôm nay                |
| `NOT_CHECKED_IN`              | 400         | Not checked in today        | Chưa check-in                      |
| `ALREADY_CHECKED_OUT`         | 400         | Already checked out today   | Đã check-out hôm nay               |
| `ATTENDANCE_RECORD_NOT_FOUND` | 404         | Attendance record not found | Attendance record ID không tồn tại |

### Overtime Errors

| Error Code                   | HTTP Status | Message                    | Cause                             |
| ---------------------------- | ----------- | -------------------------- | --------------------------------- |
| `OVERTIME_REQUEST_NOT_FOUND` | 404         | Overtime request not found | Overtime request ID không tồn tại |
| `OVERTIME_LIMIT_EXCEEDED`    | 400         | Overtime limit exceeded    | Vượt quá giới hạn OT/tuần         |

### Schedule/Holiday Errors

| Error Code           | HTTP Status | Message                 | Cause                     |
| -------------------- | ----------- | ----------------------- | ------------------------- |
| `SCHEDULE_NOT_FOUND` | 404         | Work schedule not found | Schedule ID không tồn tại |
| `EMPLOYEE_NOT_FOUND` | 404         | Employee not found      | Employee ID không tồn tại |

---

## Gmail Module

### Auth & Connection

| Error Code             | HTTP Status | Message                                   | Cause                   |
| ---------------------- | ----------- | ----------------------------------------- | ----------------------- |
| `GMAIL_ERROR`          | 500         | A Gmail module error occurred             | Base exception          |
| `UNAUTHORIZED`         | 401         | Missing or invalid authentication session | Session expired/invalid |
| `GMAIL_NOT_CONNECTED`  | 403         | Gmail is not connected                    | User chưa connect Gmail |
| `GMAIL_CONNECT_FAILED` | 400         | Gmail connection failed                   | OAuth callback failed   |

### Label & Message

| Error Code                  | HTTP Status | Message                                     | Cause                      |
| --------------------------- | ----------- | ------------------------------------------- | -------------------------- |
| `LABEL_NAMESPACE_VIOLATION` | 400         | Label must be within the VroomHR/ namespace | Label không đúng namespace |
| `MESSAGE_NOT_FOUND`         | 404         | Gmail message not found                     | Message ID không tồn tại   |

### API Errors

| Error Code                  | HTTP Status | Message                                     | Cause                  |
| --------------------------- | ----------- | ------------------------------------------- | ---------------------- |
| `GMAIL_FETCH_ERROR`         | 502         | Failed to fetch data from Gmail API         | Gmail API call failed  |
| `GMAIL_LABEL_REMOVE_FAILED` | 502         | Failed to remove label from Gmail message   | Label removal failed   |
| `GMAIL_SEND_FAILED`         | 502         | Failed to send email via Gmail              | Send email failed      |
| `RATE_LIMITED`              | 429         | Rate limit exceeded, please try again later | Manual sync rate limit |

---

## Recruitment Module

### Candidate & CV

| Error Code              | HTTP Status | Message                             | Cause                                    |
| ----------------------- | ----------- | ----------------------------------- | ---------------------------------------- |
| `RECRUITMENT_ERROR`     | 500         | A recruitment module error occurred | Base exception                           |
| `CANDIDATE_NOT_FOUND`   | 404         | Candidate not found                 | Candidate ID không tồn tại               |
| `CV_DOCUMENT_NOT_FOUND` | 404         | CV document not found               | CV document ID không tồn tại             |
| `CV_FILE_MISSING`       | 404         | CV file not found in storage        | File trong DB nhưng không có trong MinIO |

### Pipeline & Status

| Error Code                  | HTTP Status | Message                   | Cause                               |
| --------------------------- | ----------- | ------------------------- | ----------------------------------- |
| `INVALID_STATUS_TRANSITION` | 409         | Invalid status transition | Không thể chuyển sang trạng thái đó |

### External Services

| Error Code                    | HTTP Status | Message                          | Cause                         |
| ----------------------------- | ----------- | -------------------------------- | ----------------------------- |
| `STORAGE_SERVICE_UNAVAILABLE` | 502         | Storage service is unavailable   | MinIO unreachable             |
| `GMAIL_NOT_CONNECTED`         | 409         | Gmail is not connected           | Gmail chưa connect            |
| `PIPELINE_TIMEOUT`            | 504         | CV processing pipeline timed out | Xử lý CV quá thời gian (660s) |
| `OCR_EXTRACTION_FAILED`       | 502         | OCR text extraction failed       | OCR server failed             |
| `LLM_PARSE_FAILED`            | 502         | LLM CV parsing failed            | LLM không parse được CV       |

---

## Payroll Module

### Period & Payslip

| Error Code                 | HTTP Status | Message                  | Cause                    |
| -------------------------- | ----------- | ------------------------ | ------------------------ |
| `PERIOD_ALREADY_CONFIRMED` | 409         | Period already confirmed | Period đã được confirm   |
| `PERIOD_ALREADY_PAID`      | 409         | Period already paid      | Period đã được paid      |
| `PAYSLIP_NOT_FOUND`        | 404         | Payslip not found        | Payslip ID không tồn tại |
| `PAYROLL_PERIOD_NOT_FOUND` | 404         | Payroll period not found | Period ID không tồn tại  |

### Salary & Config

| Error Code                | HTTP Status | Message                 | Cause                               |
| ------------------------- | ----------- | ----------------------- | ----------------------------------- |
| `SALARY_NOT_CONFIGURED`   | 400         | Salary not configured   | Position chưa có salary config      |
| `SALARY_CONFIG_NOT_FOUND` | 404         | Salary config not found | Config ID không tồn tại             |
| `DUPLICATE_SALARY_CONFIG` | 409         | Duplicate salary config | Config đã tồn tại cho position/date |

### Allowances & Dependents

| Error Code            | HTTP Status | Message             | Cause                      |
| --------------------- | ----------- | ------------------- | -------------------------- |
| `DEPENDENT_NOT_FOUND` | 404         | Dependent not found | Dependent ID không tồn tại |
| `ALLOWANCE_NOT_FOUND` | 404         | Allowance not found | Allowance ID không tồn tại |

---

## Self-Service Module

Chưa có domain exceptions riêng. Sử dụng chung từ các modules khác (Employee, Attendance, Payroll).

---

## Response Format

Tất cả errors trả về theo format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

### Ví dụ

```json
// 404 Not Found
{
  "error": {
    "code": "EMPLOYEE_NOT_FOUND",
    "message": "Employee not found"
  }
}

// 409 Conflict
{
  "error": {
    "code": "LEAVE_OVERLAP",
    "message": "Leave request overlaps with an existing approved/pending request"
  }
}

// 502 Bad Gateway
{
  "error": {
    "code": "GMAIL_SEND_FAILED",
    "message": "Failed to send email via Gmail"
  }
}
```

---

## Error Handling Best Practices

### 1. Always catch specific exceptions

```python
try:
    employee = service.get_employee(employee_id)
except EmployeeNotFoundError:
    # Handle not found
    raise
except EmployeeError:
    # Handle other employee errors
    raise
```

### 2. Use error codes for programmatic handling

```python
if response.status_code == 409:
    error_code = response.json()["error"]["code"]
    if error_code == "LEAVE_OVERLAP":
        # Handle overlap specifically
```

### 3. Log full error details

```python
import logging
logger = logging.getLogger(__name__)

try:
    service.process()
except EmployeeError as e:
    logger.error(f"Employee error: {e.error_code} - {e.message}")
    raise
```

### 4. Don't expose internal details

```python
# Bad
raise EmployeeError(f"Database connection failed: {db_error}")

# Good
raise EmployeeError("Failed to process employee data")
```

---

## Adding New Error Codes

Khi thêm error code mới:

1. **Thêm vào module exceptions.py:**

```python
class NewErrorCodeError(EmployeeError):
    status_code = 400  # Hoặc 404, 409, etc.
    error_code = "NEW_ERROR_CODE"  # Uppercase with underscores
    message = "Human readable message"  # Tiếng Anh
```

2. **Đảm bảo format:**
   - Error code: UPPERCASE_WITH_UNDERSCORES
   - Message: Tiếng Anh, rõ ràng, không technical jargon
   - status_code: HTTP status code phù hợp

3. **Cập nhật docs/technical/error-codes.md**

4. **Thêm vào TEST_MATRIX.md nếu là business logic error**
