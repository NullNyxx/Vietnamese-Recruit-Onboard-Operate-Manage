"""Pydantic request/response schemas for the Employee Management API.

Defines data transfer objects used by the employee router endpoints
for structured data validation and serialization.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

# ---------------------------------------------------------------------------
# Department schemas
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    """Request schema for creating a department.

    Attributes:
        name: Unique department name (required).
        description: Optional description of the department.
    """

    name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    """Request schema for updating a department.

    Attributes:
        name: New department name (optional).
        description: New description (optional).
    """

    name: str | None = None
    description: str | None = None


class DepartmentResponse(BaseModel):
    """Response schema for a department.

    Attributes:
        id: Unique department identifier.
        name: Department name.
        description: Department description, if any.
        created_at: When the department was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Position schemas
# ---------------------------------------------------------------------------


class PositionCreate(BaseModel):
    """Request schema for creating a position.

    Attributes:
        name: Unique position name (required).
        department_id: Optional department this position belongs to.
    """

    name: str
    department_id: UUID | None = None


class PositionUpdate(BaseModel):
    """Request schema for updating a position.

    Attributes:
        name: New position name (optional).
        department_id: New department association (optional).
    """

    name: str | None = None
    department_id: UUID | None = None


class PositionResponse(BaseModel):
    """Response schema for a position.

    Attributes:
        id: Unique position identifier.
        name: Position name.
        department_id: Associated department ID, if any.
        created_at: When the position was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    department_id: UUID | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Employee schemas
# ---------------------------------------------------------------------------


class EmployeeCreate(BaseModel):
    """Request schema for creating an employee.

    Attributes:
        full_name: Employee's full name (required).
        email: Employee's email address (required, must be unique).
        phone: Phone number (optional).
        date_of_birth: Date of birth (optional).
        gender: Gender (optional).
        address: Home address (optional).
        department_id: Assigned department (optional).
        position_id: Assigned position (optional).
        start_date: Employment start date (optional).
        id_number: National ID / CCCD number (optional).
        tax_code: Tax identification code (optional).
        contract_type: Type of employment contract (optional).
    """

    full_name: str
    email: EmailStr
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    start_date: date | None = None
    id_number: str | None = None
    tax_code: str | None = None
    contract_type: str | None = None


class PromoteCandidateRequest(BaseModel):
    """Request schema for promoting a candidate to employee.

    Attributes:
        full_name: Candidate's full name (required).
        email: Candidate's email address (required).
        candidate_id: UUID of the candidate for traceability (required).
        phone: Candidate's phone number (optional).
        department_id: Target department UUID (optional).
        position_id: Target position UUID (optional).
        start_date: Employment start date (optional).
    """

    full_name: str
    email: EmailStr
    candidate_id: UUID
    phone: str | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    start_date: date | None = None


class EmployeeUpdate(BaseModel):
    """Request schema for updating an employee (partial update).

    All fields are optional. Only provided fields will be updated.

    Attributes:
        full_name: Updated full name.
        email: Updated email address.
        phone: Updated phone number.
        date_of_birth: Updated date of birth.
        gender: Updated gender.
        address: Updated address.
        department_id: Updated department assignment.
        position_id: Updated position assignment.
        start_date: Updated start date.
        id_number: Updated national ID number.
        tax_code: Updated tax code.
        contract_type: Updated contract type.
    """

    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    start_date: date | None = None
    id_number: str | None = None
    tax_code: str | None = None
    contract_type: str | None = None


class EmployeeResponse(BaseModel):
    """Response schema for a single employee.

    Attributes:
        id: Unique employee identifier.
        employee_code: Auto-generated code in NV-XXX format.
        full_name: Employee's full name.
        email: Employee's email address.
        phone: Phone number, if provided.
        date_of_birth: Date of birth, if provided.
        gender: Gender, if provided.
        address: Home address, if provided.
        department_id: Assigned department ID, if any.
        position_id: Assigned position ID, if any.
        start_date: Employment start date, if provided.
        id_number: National ID number, if provided.
        tax_code: Tax code, if provided.
        contract_type: Contract type, if provided.
        candidate_id: Linked candidate ID, if promoted from recruitment.
        is_active: Whether the employee is active (not soft-deleted).
        created_at: When the employee record was created.
        updated_at: When the employee record was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_code: str
    full_name: str
    email: str
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None
    department_id: UUID | None = None
    position_id: UUID | None = None
    start_date: date | None = None
    id_number: str | None = None
    tax_code: str | None = None
    contract_type: str | None = None
    candidate_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    """Response schema for a paginated list of employees.

    Attributes:
        items: List of employee records for the current page.
        total: Total number of matching employees.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
    """

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Import schemas
# ---------------------------------------------------------------------------


class ImportError(BaseModel):
    """Describes a single row-level error during Excel import.

    Attributes:
        row: The row number in the Excel file (1-indexed).
        message: Description of the validation error.
    """

    row: int
    message: str


class ImportResult(BaseModel):
    """Response schema for the Excel import endpoint.

    Attributes:
        total_rows: Total number of data rows processed.
        success_count: Number of rows successfully imported.
        error_count: Number of rows that failed validation.
        errors: Detailed list of row-level errors.
    """

    total_rows: int
    success_count: int
    error_count: int
    errors: list[ImportError]


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    """Response schema for an employee document.

    Attributes:
        id: Unique document identifier.
        employee_id: The employee this document belongs to.
        document_type: Category of document (e.g., cccd, degree, contract).
        file_name: Original file name.
        file_size: File size in bytes.
        mime_type: MIME type of the file.
        description: Optional description of the document.
        uploaded_at: When the document was uploaded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    document_type: str
    file_name: str
    file_size: int
    mime_type: str
    description: str | None = None
    uploaded_at: datetime
