# Implementation Plan: Employee Management

## Overview

This plan implements the Employee Management module for Vroom HR. It follows the same modular monolith pattern as the Identity module with domain, application, infrastructure, and API layers at `backend/src/modules/employee/`.

## Tasks

- [x] 1. Set up module structure and configuration
  - [x] 1.1 Create the employee module directory structure
    - Create `backend/src/modules/employee/` with subdirectories: `domain/`, `application/`, `infrastructure/`, `api/`
    - Add `__init__.py` files to each package
    - _Requirements: Project structure from design_
  - [x] 1.2 Implement EmployeeSettings (Pydantic Settings)
    - Create `backend/src/modules/employee/infrastructure/config.py`
    - Define settings: minio_endpoint, minio_access_key, minio_secret_key, minio_bucket, max_file_size_mb
    - Use `env_prefix = "EMPLOYEE_"` for environment variable mapping
    - _Requirements: Design Configuration_
  - [x] 1.3 Create domain entities (SQLModel)
    - Create `backend/src/modules/employee/domain/entities.py`
    - Implement `Employee`, `Department`, `Position`, `EmployeeDocument` SQLModel table classes
    - Use `sa_column=Column(DateTime(timezone=True))` for all datetime fields
    - _Requirements: 2.1, 6.1, 6.2_
  - [x] 1.4 Create domain exceptions
    - Create `backend/src/modules/employee/domain/exceptions.py`
    - Implement: `EmployeeError`, `DuplicateEmailError`, `EmployeeNotFoundError`, `DepartmentNotFoundError`, `PositionNotFoundError`, `DepartmentHasEmployeesError`, `PositionHasEmployeesError`, `FileTooLargeError`, `UnsupportedFileTypeError`
    - _Requirements: 2.2, 3.3, 3.4, 5.2, 5.3_
  - [x] 1.5 Create Pydantic schemas
    - Create `backend/src/modules/employee/api/schemas.py`
    - Implement request/response models: `EmployeeCreate`, `EmployeeUpdate`, `EmployeeResponse`, `EmployeeListResponse`, `DepartmentCreate`, `DepartmentResponse`, `PositionCreate`, `PositionResponse`, `ImportResult`, `DocumentResponse`
    - _Requirements: 1.1, 2.1, 4.4_

- [x] 2. Implement infrastructure layer
  - [x] 2.1 Implement MinIO client adapter
    - Create `backend/src/modules/employee/infrastructure/minio_client.py`
    - Implement `upload_file(path, file_data, content_type) -> str` — upload to MinIO, return storage path
    - Implement `download_file(path) -> bytes` — download from MinIO
    - Implement `delete_file(path) -> None` — delete from MinIO
    - Use aioboto3 for async S3 operations
    - _Requirements: 5.1_
  - [x] 2.2 Implement Excel parser
    - Create `backend/src/modules/employee/infrastructure/excel_parser.py`
    - Implement `parse_excel(file_bytes) -> list[dict]` — parse .xlsx rows into dicts
    - Support date formats: YYYY-MM-DD and DD/MM/YYYY
    - Validate required fields per row, return errors for invalid rows
    - _Requirements: 4.1, 4.2, 4.5_
  - [x] 2.3 Implement Employee repository
    - Create `backend/src/modules/employee/infrastructure/employee_repository.py`
    - Implement: `list(page, page_size, search, department_id, position_id, is_active)`, `get_by_id`, `get_by_email`, `create`, `update`, `soft_delete`, `get_next_code`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.3, 2.4, 2.5, 6.1_
  - [x] 2.4 Implement Department repository
    - Create `backend/src/modules/employee/infrastructure/department_repository.py`
    - Implement: `list_all`, `get_by_id`, `get_by_name`, `create`, `update`, `delete`, `has_active_employees`
    - _Requirements: 3.1, 3.3, 3.5_
  - [x] 2.5 Implement Position repository
    - Create `backend/src/modules/employee/infrastructure/position_repository.py`
    - Implement: `list_all`, `get_by_id`, `get_by_name`, `create`, `update`, `delete`, `has_active_employees`
    - _Requirements: 3.2, 3.4, 3.5_
  - [x] 2.6 Implement Document repository
    - Create `backend/src/modules/employee/infrastructure/document_repository.py`
    - Implement: `list_by_employee`, `get_by_id`, `create`, `delete`
    - _Requirements: 5.1, 5.5_

- [x] 3. Implement application layer services
  - [x] 3.1 Implement EmployeeService
    - Create `backend/src/modules/employee/application/employee_service.py`
    - Implement: `list_employees`, `get_employee`, `create_employee`, `update_employee`, `delete_employee`, `promote_candidate`
    - Auto-generate employee_code on create
    - Validate email uniqueness, department/position existence
    - _Requirements: 1.1-1.5, 2.1-2.5, 6.1-6.3, 7.1-7.3_
  - [x] 3.2 Implement DepartmentService
    - Create `backend/src/modules/employee/application/department_service.py`
    - Implement: `list_departments`, `create_department`, `update_department`, `delete_department`
    - Check cascade protection before delete
    - _Requirements: 3.1-3.5_
  - [x] 3.3 Implement PositionService
    - Create `backend/src/modules/employee/application/position_service.py`
    - Implement: `list_positions`, `create_position`, `update_position`, `delete_position`
    - Check cascade protection before delete
    - _Requirements: 3.1-3.5_
  - [x] 3.4 Implement ImportService
    - Create `backend/src/modules/employee/application/import_service.py`
    - Implement: `import_from_excel(file_bytes) -> ImportResult`
    - Parse Excel, validate each row, upsert by email, collect errors
    - _Requirements: 4.1-4.5_
  - [x] 3.5 Implement DocumentService
    - Create `backend/src/modules/employee/application/document_service.py`
    - Implement: `list_documents`, `upload_document`, `download_document`, `delete_document`
    - Validate file size (max 10MB) and MIME type
    - Store in MinIO at employees/{employee_id}/{document_type}/{filename}
    - _Requirements: 5.1-5.6_

- [x] 4. Implement API layer
  - [x] 4.1 Implement employee router
    - Create `backend/src/modules/employee/api/router.py`
    - Implement all 18 endpoints as defined in the design
    - All endpoints require JWT auth (get_current_user dependency from identity module)
    - _Requirements: All_
  - [x] 4.2 Implement DI container for employee module
    - Create `backend/src/modules/employee/container.py`
    - Wire all services, repositories, and MinIO client via FastAPI Depends
    - Reuse database session from identity module's container
    - _Requirements: Design_
  - [x] 4.3 Implement error handler
    - Create `backend/src/modules/employee/api/error_handler.py`
    - Register exception handler for `EmployeeError` base class
    - _Requirements: 2.2, 3.3, 3.4, 5.2, 5.3_
  - [x] 4.4 Register employee router in main.py
    - Add `app.include_router(employee_router)` in `backend/src/main.py`
    - Register employee error handlers
    - _Requirements: Design_

- [x] 5. Database migrations
  - [x] 5.1 Create Alembic migrations
    - Create `004_create_departments_table.py` — departments table
    - Create `005_create_positions_table.py` — positions table with FK to departments
    - Create `006_create_employees_table.py` — employees table with FKs to departments, positions
    - Create `007_create_employee_documents_table.py` — employee_documents table with FK to employees
    - Add indexes: employees.email (unique), employees.employee_code (unique), employees.department_id, employees.position_id
    - _Requirements: 2.1, 6.2_

- [x] 6. Add MinIO to infrastructure
  - [x] 6.1 Update docker-compose.infra.yml
    - Add MinIO service (port 9000 API, 9001 console)
    - Add environment variables to backend .env
    - _Requirements: 5.1_

- [x] 7. Write unit tests
  - [x] 7.1 Write tests for employee service
    - Test employee code generation (sequential, NV-XXX format)
    - Test email uniqueness validation
    - Test soft-delete behavior
    - _Requirements: 2.1, 2.2, 2.5, 6.1-6.3_
  - [x] 7.2 Write tests for Excel parser
    - Test valid Excel parsing
    - Test invalid rows (missing fields, bad email, unknown department)
    - Test date format handling (YYYY-MM-DD and DD/MM/YYYY)
    - _Requirements: 4.1-4.5_
  - [x] 7.3 Write tests for document service
    - Test file size validation (>10MB rejected)
    - Test MIME type validation
    - Test storage path generation
    - _Requirements: 5.1-5.3_

- [x] 8. Final checkpoint
  - Run all tests, verify endpoints work via Swagger UI
  - Ensure existing identity module tests still pass

### Task Dependency Graph

```
1.1 -> 1.2
1.2 -> 1.3
1.3 -> 1.4
1.4 -> 1.5
1.5 -> 2.1
1.5 -> 2.2
1.5 -> 2.3
1.5 -> 2.4
1.5 -> 2.5
1.5 -> 2.6
2.1 -> 3.5
2.2 -> 3.4
2.3 -> 3.1
2.4 -> 3.2
2.5 -> 3.3
2.6 -> 3.5
3.1 -> 4.1
3.2 -> 4.1
3.3 -> 4.1
3.4 -> 4.1
3.5 -> 4.1
4.1 -> 4.2
4.2 -> 4.3
4.3 -> 4.4
4.4 -> 5.1
5.1 -> 6.1
6.1 -> 7.1
6.1 -> 7.2
6.1 -> 7.3
7.1 -> 8
7.2 -> 8
7.3 -> 8
```

## Notes

- All endpoints require JWT authentication from the identity module
- Reuse the shared database session pattern from identity module's container
- MinIO bucket should be auto-created on first upload if it doesn't exist
- Excel import is synchronous for MVP (< 500 rows expected); can move to background job later
- openpyxl and aioboto3 need to be added to pyproject.toml dependencies
