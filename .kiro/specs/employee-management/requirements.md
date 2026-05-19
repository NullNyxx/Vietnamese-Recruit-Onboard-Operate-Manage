# Requirements Document

## Introduction

The Employee Management module provides centralized HR personnel management for Vroom HR. HR users can create, view, update, and soft-delete employees, import in bulk from Excel, manage departments and positions, and store personal documents (CCCD, degrees, contracts) in a secure document vault backed by MinIO. This module serves as foundation data for other modules (recruitment, interview) that need employee references.

## Glossary

- **System**: The Vroom HR Employee Management backend module
- **HR**: The human resources user who manages employees
- **Employee**: A person employed by the company, managed in the system
- **Department**: An organizational unit (e.g., Engineering, HR, Sales)
- **Position**: A job title within a department (e.g., Senior Developer, Manager)
- **Document_Vault**: MinIO-backed storage for employee personal documents
- **Employee_Code**: Auto-generated unique identifier in format NV-XXX (sequential)
- **Excel_Import**: Bulk create/update employees from .xlsx file
- **Soft_Delete**: Setting is_active=false without removing the database record

## Requirements

### Requirement 1: Employee List with Pagination and Search

**User Story:** As an HR user, I want to view a paginated list of employees with search and filter capabilities so that I can quickly find specific personnel.

#### Acceptance Criteria

1. WHEN HR navigates to /api/employees, THE System SHALL return a paginated list of active employees with default page_size=20
2. WHEN HR provides a search query, THE System SHALL return employees whose full_name or email contains the query (case-insensitive partial match)
3. WHEN HR filters by department_id, THE System SHALL return only employees belonging to that department
4. WHEN HR filters by position_id, THE System SHALL return only employees with that position
5. WHEN HR sets is_active=false filter, THE System SHALL return soft-deleted employees

### Requirement 2: Employee CRUD Operations

**User Story:** As an HR user, I want to create, view, update, and soft-delete employee records so that I can maintain accurate personnel data.

#### Acceptance Criteria

1. WHEN HR submits a valid employee creation form, THE System SHALL create an Employee record with an auto-generated employee_code (NV-XXX format)
2. WHEN HR submits an employee with a duplicate email, THE System SHALL return HTTP 409 with error code EMPLOYEE_DUPLICATE_EMAIL
3. WHEN HR requests an employee by ID, THE System SHALL return the full employee profile including department and position names
4. WHEN HR updates an employee record, THE System SHALL persist the changes and update the updated_at timestamp
5. WHEN HR deletes an employee, THE System SHALL set is_active=false (soft-delete) and the employee SHALL NOT appear in default list queries

### Requirement 3: Department and Position Management

**User Story:** As an HR user, I want to manage departments and positions so that I can organize employees into proper organizational units.

#### Acceptance Criteria

1. WHEN HR creates a department with a unique name, THE System SHALL persist it and make it available in employee forms
2. WHEN HR creates a position with a unique name, THE System SHALL persist it and make it available in employee forms
3. WHEN HR attempts to delete a department that has active employees, THE System SHALL return HTTP 409 Conflict
4. WHEN HR attempts to delete a position that has active employees, THE System SHALL return HTTP 409 Conflict
5. WHEN HR updates a department or position name, THE System SHALL reflect the change in all employee references

### Requirement 4: Excel Import

**User Story:** As an HR user, I want to import employees from an Excel file so that I can onboard multiple employees efficiently.

#### Acceptance Criteria

1. WHEN HR uploads a valid .xlsx file, THE System SHALL parse each row and create or update employees (matched by email)
2. WHEN a row has invalid data (missing required field, invalid email format), THE System SHALL skip that row and include it in the error report
3. WHEN a row references a department name that does not exist, THE System SHALL skip that row and report the error
4. WHEN import completes, THE System SHALL return a summary with total_rows, created count, updated count, and error details
5. THE System SHALL support both YYYY-MM-DD and DD/MM/YYYY date formats in Excel

### Requirement 5: Document Vault

**User Story:** As an HR user, I want to upload and manage employee documents so that personal records are stored securely and accessible when needed.

#### Acceptance Criteria

1. WHEN HR uploads a document for an employee, THE System SHALL store the file in MinIO at path employees/{employee_id}/{document_type}/{filename} and create a metadata record
2. WHEN HR uploads a document larger than 10MB, THE System SHALL return HTTP 413 Payload Too Large
3. WHEN HR uploads a file with unsupported MIME type, THE System SHALL return HTTP 415 Unsupported Media Type
4. WHEN HR requests to download a document, THE System SHALL return the file with correct content-type header
5. WHEN HR uploads a new version of the same document type, THE System SHALL keep the previous version (append-only, no overwrite)
6. WHEN an employee is soft-deleted, THE System SHALL retain all documents in MinIO (no deletion)

### Requirement 6: Employee Code Generation

**User Story:** As a system architect, I want employee codes to be auto-generated and unique so that each employee has a stable human-readable identifier.

#### Acceptance Criteria

1. WHEN a new employee is created, THE System SHALL assign the next sequential employee_code in format NV-{number padded to 3+ digits}
2. THE employee_code SHALL be unique across all employees (including soft-deleted)
3. THE employee_code SHALL NOT change after initial assignment

### Requirement 7: Candidate to Employee Promotion

**User Story:** As an HR user, I want to promote a candidate to employee so that hired candidates seamlessly transition into the employee system.

#### Acceptance Criteria

1. WHEN the recruitment module promotes a candidate, THE System SHALL create an Employee record with candidate's name, email, and phone
2. WHEN the promoted candidate's email already exists as an employee, THE System SHALL link the candidate to the existing employee record
3. THE System SHALL set candidate_id on the Employee record for traceability
