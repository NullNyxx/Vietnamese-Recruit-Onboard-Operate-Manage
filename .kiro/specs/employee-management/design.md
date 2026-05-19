# Design Document: Employee Management

## Overview

The Employee Management module provides CRUD operations for employees, departments, and positions, bulk Excel import, and a MinIO-backed document vault. It follows the same modular monolith architecture as the Identity module with domain, application, infrastructure, and API layers.

**Key Design Decisions:**
- Auto-generated employee codes (NV-XXX, sequential)
- Soft-delete only (is_active=false), no hard delete
- MinIO for document storage (S3-compatible, self-hosted)
- Excel import matches by email (upsert semantics)
- Append-only document vault (keep all versions)
- Department/Position cascade protection (cannot delete if employees exist)

**Technology Choices:**
- Backend: FastAPI, SQLAlchemy 2.0 + SQLModel, Pydantic v2
- File storage: MinIO (via boto3/aioboto3 S3 client)
- Excel parsing: openpyxl
- All endpoints protected by JWT auth (from identity module)

## Architecture

### Module Structure

```
backend/src/modules/employee/
├── domain/
│   ├── __init__.py
│   ├── entities.py          # Employee, Department, Position, EmployeeDocument
│   └── exceptions.py        # Domain-specific exceptions
├── application/
│   ├── __init__.py
│   ├── employee_service.py  # Employee CRUD + search
│   ├── department_service.py # Department CRUD
│   ├── position_service.py  # Position CRUD
│   ├── import_service.py    # Excel import logic
│   └── document_service.py  # Document vault operations
├── infrastructure/
│   ├── __init__.py
│   ├── config.py            # EmployeeSettings
│   ├── employee_repository.py
│   ├── department_repository.py
│   ├── position_repository.py
│   ├── document_repository.py
│   ├── minio_client.py      # MinIO S3 adapter
│   └── excel_parser.py      # openpyxl wrapper
└── api/
    ├── __init__.py
    ├── router.py             # All /api/employees/* endpoints
    ├── schemas.py            # Pydantic request/response models
    └── dependencies.py       # DI for employee module
```

## Data Models

### Employee Entity

```python
class Employee(SQLModel, table=True):
    __tablename__ = "employees"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_code: str = Field(max_length=20, unique=True, nullable=False)
    full_name: str = Field(max_length=255, nullable=False)
    email: str = Field(max_length=255, unique=True, nullable=False)
    phone: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None)
    department_id: UUID | None = Field(default=None, foreign_key="departments.id")
    position_id: UUID | None = Field(default=None, foreign_key="positions.id")
    start_date: date | None = Field(default=None)
    id_number: str | None = Field(default=None, max_length=20)
    tax_code: str | None = Field(default=None, max_length=20)
    contract_type: str | None = Field(default=None, max_length=20)
    candidate_id: UUID | None = Field(default=None)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime
    updated_at: datetime
```

### Department Entity

```python
class Department(SQLModel, table=True):
    __tablename__ = "departments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True, nullable=False)
    description: str | None = Field(default=None)
    created_at: datetime
```

### Position Entity

```python
class Position(SQLModel, table=True):
    __tablename__ = "positions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True, nullable=False)
    department_id: UUID | None = Field(default=None, foreign_key="departments.id")
    created_at: datetime
```

### EmployeeDocument Entity

```python
class EmployeeDocument(SQLModel, table=True):
    __tablename__ = "employee_documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    employee_id: UUID = Field(foreign_key="employees.id", nullable=False)
    document_type: str = Field(max_length=50, nullable=False)
    file_name: str = Field(max_length=255, nullable=False)
    storage_path: str = Field(nullable=False)
    file_size: int = Field(nullable=False)
    mime_type: str = Field(max_length=100, nullable=False)
    description: str | None = Field(default=None)
    uploaded_at: datetime
```

## API Endpoints

| Method | Path | Handler |
|--------|------|---------|
| GET | /api/employees | list_employees |
| POST | /api/employees | create_employee |
| GET | /api/employees/:id | get_employee |
| PUT | /api/employees/:id | update_employee |
| DELETE | /api/employees/:id | delete_employee |
| POST | /api/employees/import | import_employees |
| GET | /api/employees/:id/documents | list_documents |
| POST | /api/employees/:id/documents | upload_document |
| GET | /api/employees/:id/documents/:docId/download | download_document |
| DELETE | /api/employees/:id/documents/:docId | delete_document |
| GET | /api/departments | list_departments |
| POST | /api/departments | create_department |
| PUT | /api/departments/:id | update_department |
| DELETE | /api/departments/:id | delete_department |
| GET | /api/positions | list_positions |
| POST | /api/positions | create_position |
| PUT | /api/positions/:id | update_position |
| DELETE | /api/positions/:id | delete_position |

## Error Handling

```python
class EmployeeError(Exception):
    status_code: int = 500
    error_code: str = "EMPLOYEE_ERROR"
    message: str = "An employee module error occurred"

class DuplicateEmailError(EmployeeError):
    status_code = 409
    error_code = "EMPLOYEE_DUPLICATE_EMAIL"
    message = "Employee with this email already exists"

class DepartmentNotFoundError(EmployeeError):
    status_code = 404
    error_code = "DEPARTMENT_NOT_FOUND"
    message = "Department not found"

class PositionNotFoundError(EmployeeError):
    status_code = 404
    error_code = "POSITION_NOT_FOUND"
    message = "Position not found"

class EmployeeNotFoundError(EmployeeError):
    status_code = 404
    error_code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found"

class DepartmentHasEmployeesError(EmployeeError):
    status_code = 409
    error_code = "DEPARTMENT_HAS_EMPLOYEES"
    message = "Cannot delete department with active employees"

class PositionHasEmployeesError(EmployeeError):
    status_code = 409
    error_code = "POSITION_HAS_EMPLOYEES"
    message = "Cannot delete position with active employees"

class FileTooLargeError(EmployeeError):
    status_code = 413
    error_code = "FILE_TOO_LARGE"
    message = "File exceeds maximum size of 10MB"

class UnsupportedFileTypeError(EmployeeError):
    status_code = 415
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "File type not supported"
```

## Testing Strategy

- Unit tests: validation logic, employee code generation, Excel row parsing
- Integration tests: full CRUD with real DB (testcontainers), MinIO operations
- Property tests: employee code uniqueness, search correctness
