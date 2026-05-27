"""FastAPI router for the Employee Management module.

Defines the /api/employees/*, /api/departments/*, /api/positions/*,
and /api/documents/* endpoints for employee CRUD, department/position
management, Excel import, and document vault operations.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from src.modules.employee.api.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    DocumentResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    ImportResult,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
    PromoteCandidateRequest,
)
from src.modules.employee.application.department_service import DepartmentService
from src.modules.employee.application.document_service import DocumentService
from src.modules.employee.application.employee_service import EmployeeService
from src.modules.employee.application.import_service import ImportService
from src.modules.employee.application.position_service import PositionService
from src.modules.employee.container import (
    get_department_service,
    get_document_service,
    get_employee_service,
    get_import_service,
    get_position_service,
)
from src.modules.identity.container import get_current_user
from src.modules.identity.domain.entities import User

# ---------------------------------------------------------------------------
# Type aliases for injected dependencies
# ---------------------------------------------------------------------------

CurrentUserDep = Annotated[User, Depends(get_current_user)]
EmployeeServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
PositionServiceDep = Annotated[PositionService, Depends(get_position_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

router = APIRouter(tags=["employees"])

employee_router = APIRouter(prefix="/api/employees", tags=["employees"])
department_router = APIRouter(prefix="/api/departments", tags=["departments"])
position_router = APIRouter(prefix="/api/positions", tags=["positions"])
document_router = APIRouter(prefix="/api/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Employee endpoints
# ---------------------------------------------------------------------------


@employee_router.get("", response_model=EmployeeListResponse)
async def list_employees(
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, description="Search in name or email"),
    department_id: UUID | None = Query(default=None, description="Filter by department"),
    position_id: UUID | None = Query(default=None, description="Filter by position"),
    is_active: bool | None = Query(default=True, description="Filter by active status"),
) -> EmployeeListResponse:
    """List employees with pagination and optional filters.

    Args:
        current_user: The authenticated user.
        employee_service: The employee service.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        search: Optional search query for name/email.
        department_id: Optional department filter.
        position_id: Optional position filter.
        is_active: Optional active status filter.

    Returns:
        Paginated list of employees.
    """
    items, total = await employee_service.list_employees(
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        position_id=position_id,
        is_active=is_active,
    )

    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(emp) for emp in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@employee_router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
) -> EmployeeResponse:
    """Get a single employee by ID.

    Args:
        employee_id: The UUID of the employee.
        current_user: The authenticated user.
        employee_service: The employee service.

    Returns:
        The employee details.
    """
    employee = await employee_service.get_employee(employee_id)
    return EmployeeResponse.model_validate(employee)


@employee_router.post("", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    body: EmployeeCreate,
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
) -> EmployeeResponse:
    """Create a new employee.

    Args:
        body: The employee creation data.
        current_user: The authenticated user.
        employee_service: The employee service.

    Returns:
        The newly created employee.
    """
    data = body.model_dump(exclude_unset=True)
    employee = await employee_service.create_employee(data)
    return EmployeeResponse.model_validate(employee)


@employee_router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    body: EmployeeUpdate,
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
) -> EmployeeResponse:
    """Update an existing employee.

    Args:
        employee_id: The UUID of the employee to update.
        body: The fields to update.
        current_user: The authenticated user.
        employee_service: The employee service.

    Returns:
        The updated employee.
    """
    data = body.model_dump(exclude_unset=True)
    employee = await employee_service.update_employee(employee_id, data)
    return EmployeeResponse.model_validate(employee)


@employee_router.delete("/{employee_id}", response_model=EmployeeResponse)
async def delete_employee(
    employee_id: UUID,
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
) -> EmployeeResponse:
    """Soft-delete an employee (set is_active=False).

    Args:
        employee_id: The UUID of the employee to soft-delete.
        current_user: The authenticated user.
        employee_service: The employee service.

    Returns:
        The soft-deleted employee.
    """
    employee = await employee_service.delete_employee(employee_id)
    return EmployeeResponse.model_validate(employee)


@employee_router.post("/promote", response_model=EmployeeResponse, status_code=201)
async def promote_candidate(
    body: PromoteCandidateRequest,
    current_user: CurrentUserDep,
    employee_service: EmployeeServiceDep,
) -> EmployeeResponse:
    """Promote a candidate to employee.

    Creates an employee record from candidate data, linking via candidate_id.

    Args:
        body: The candidate promotion data.
        current_user: The authenticated user.
        employee_service: The employee service.

    Returns:
        The newly created (or linked) employee.
    """
    data = body.model_dump(exclude_unset=True)
    employee = await employee_service.promote_candidate(data)
    return EmployeeResponse.model_validate(employee)


@employee_router.post("/import", response_model=ImportResult)
async def import_employees(
    current_user: CurrentUserDep,
    import_service: ImportServiceDep,
    file: UploadFile = File(..., description="Excel .xlsx file to import"),
) -> ImportResult:
    """Import employees from an Excel (.xlsx) file.

    Args:
        current_user: The authenticated user.
        import_service: The import service.
        file: The uploaded Excel file.

    Returns:
        Import result summary with success/error counts.
    """
    file_bytes = await file.read()
    result = await import_service.import_from_excel(file_bytes)
    return ImportResult(**result)


# ---------------------------------------------------------------------------
# Employee document endpoints
# ---------------------------------------------------------------------------


@employee_router.get("/{employee_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    employee_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> list[DocumentResponse]:
    """List all documents for an employee.

    Args:
        employee_id: The UUID of the employee.
        current_user: The authenticated user.
        document_service: The document service.

    Returns:
        List of document metadata records.
    """
    documents = await document_service.list_documents(employee_id)
    return [DocumentResponse.model_validate(doc) for doc in documents]


@employee_router.post(
    "/{employee_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def upload_document(
    employee_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
    file: UploadFile = File(..., description="Document file to upload"),
    document_type: str = Form(..., description="Document category (e.g., cccd, degree, contract)"),
    description: str | None = Form(default=None, description="Optional document description"),
) -> DocumentResponse:
    """Upload a document to an employee's document vault.

    Args:
        employee_id: The UUID of the employee.
        current_user: The authenticated user.
        document_service: The document service.
        file: The uploaded file.
        document_type: Category of the document.
        description: Optional description.

    Returns:
        The created document metadata.
    """
    file_data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    file_name = file.filename or "unnamed"

    document = await document_service.upload_document(
        employee_id=employee_id,
        document_type=document_type,
        file_name=file_name,
        file_data=file_data,
        content_type=content_type,
    )
    return DocumentResponse.model_validate(document)


# ---------------------------------------------------------------------------
# Document download/delete endpoints (by document ID)
# ---------------------------------------------------------------------------


@document_router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> Response:
    """Download a document by its ID.

    Args:
        document_id: The UUID of the document.
        current_user: The authenticated user.
        document_service: The document service.

    Returns:
        The file content with appropriate content-type headers.
    """
    document, file_data = await document_service.download_document(document_id)

    return Response(
        content=file_data,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.file_name}"',
        },
    )


@document_router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
) -> None:
    """Delete a document by its ID.

    Args:
        document_id: The UUID of the document.
        current_user: The authenticated user.
        document_service: The document service.
    """
    await document_service.delete_document(document_id)


# ---------------------------------------------------------------------------
# Department endpoints
# ---------------------------------------------------------------------------


@department_router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
) -> list[DepartmentResponse]:
    """List all departments.

    Args:
        current_user: The authenticated user.
        department_service: The department service.

    Returns:
        List of all departments.
    """
    departments = await department_service.list_departments()
    return [DepartmentResponse.model_validate(dept) for dept in departments]


@department_router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
) -> DepartmentResponse:
    """Create a new department.

    Args:
        body: The department creation data.
        current_user: The authenticated user.
        department_service: The department service.

    Returns:
        The newly created department.
    """
    data = body.model_dump(exclude_unset=True)
    department = await department_service.create_department(data)
    return DepartmentResponse.model_validate(department)


@department_router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    body: DepartmentUpdate,
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
) -> DepartmentResponse:
    """Update an existing department.

    Args:
        department_id: The UUID of the department to update.
        body: The fields to update.
        current_user: The authenticated user.
        department_service: The department service.

    Returns:
        The updated department.
    """
    data = body.model_dump(exclude_unset=True)
    department = await department_service.update_department(department_id, data)
    return DepartmentResponse.model_validate(department)


@department_router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: UUID,
    current_user: CurrentUserDep,
    department_service: DepartmentServiceDep,
) -> None:
    """Delete a department (cascade-protected).

    Args:
        department_id: The UUID of the department to delete.
        current_user: The authenticated user.
        department_service: The department service.
    """
    await department_service.delete_department(department_id)


# ---------------------------------------------------------------------------
# Position endpoints
# ---------------------------------------------------------------------------


@position_router.get("", response_model=list[PositionResponse])
async def list_positions(
    current_user: CurrentUserDep,
    position_service: PositionServiceDep,
) -> list[PositionResponse]:
    """List all positions.

    Args:
        current_user: The authenticated user.
        position_service: The position service.

    Returns:
        List of all positions.
    """
    positions = await position_service.list_positions()
    return [PositionResponse.model_validate(pos) for pos in positions]


@position_router.post("", response_model=PositionResponse, status_code=201)
async def create_position(
    body: PositionCreate,
    current_user: CurrentUserDep,
    position_service: PositionServiceDep,
) -> PositionResponse:
    """Create a new position.

    Args:
        body: The position creation data.
        current_user: The authenticated user.
        position_service: The position service.

    Returns:
        The newly created position.
    """
    data = body.model_dump(exclude_unset=True)
    position = await position_service.create_position(data)
    return PositionResponse.model_validate(position)


@position_router.put("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID,
    body: PositionUpdate,
    current_user: CurrentUserDep,
    position_service: PositionServiceDep,
) -> PositionResponse:
    """Update an existing position.

    Args:
        position_id: The UUID of the position to update.
        body: The fields to update.
        current_user: The authenticated user.
        position_service: The position service.

    Returns:
        The updated position.
    """
    data = body.model_dump(exclude_unset=True)
    position = await position_service.update_position(position_id, data)
    return PositionResponse.model_validate(position)


@position_router.delete("/{position_id}", status_code=204)
async def delete_position(
    position_id: UUID,
    current_user: CurrentUserDep,
    position_service: PositionServiceDep,
) -> None:
    """Delete a position (cascade-protected).

    Args:
        position_id: The UUID of the position to delete.
        current_user: The authenticated user.
        position_service: The position service.
    """
    await position_service.delete_position(position_id)


# ---------------------------------------------------------------------------
# Include sub-routers into the main router
# ---------------------------------------------------------------------------

router.include_router(employee_router)
router.include_router(department_router)
router.include_router(position_router)
router.include_router(document_router)
