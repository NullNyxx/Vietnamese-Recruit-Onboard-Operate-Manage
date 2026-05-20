---
inclusion: always
description: API design conventions for FastAPI backend - RESTful services, error handling, and request/response patterns.
---

# API Design Conventions (FastAPI / Python)

## URL Structure

- Use plural nouns for resource collections: `/employees`, `/departments`, `/positions`
- Use path parameters for resource identifiers: `/employees/{employee_id}`
- Use query parameters for filtering, sorting, pagination: `/employees?department_id=1&page=1&page_size=20`
- Nest sub-resources one level deep maximum: `/employees/{employee_id}/documents`
- Use kebab-case for multi-word paths: `/employee-documents`
- API prefix: `/api/v1/`

## HTTP Methods

- GET: retrieve resources (idempotent, cacheable)
- POST: create new resources
- PUT: full replacement of a resource
- PATCH: partial update of a resource
- DELETE: remove a resource (idempotent)

## Response Format

Use Pydantic response models directly (no envelope wrapper unless pagination):

```python
class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    email: str | None
    department: DepartmentResponse | None
```

For paginated responses:
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

## Error Responses

Use FastAPI HTTPException with structured detail:

```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "EMPLOYEE_NOT_FOUND", "message": f"Employee {id} not found"}
)
```

Domain exceptions are caught by error_handler middleware and mapped to HTTP status codes.

Status code mapping:
- 400: validation errors, malformed request
- 401: missing or invalid authentication
- 403: authenticated but not authorized
- 404: resource not found
- 409: conflict (duplicate, state mismatch)
- 422: unprocessable entity (Pydantic validation / business logic rejection)
- 500: unexpected server error

## Pagination

Use offset-based pagination with page/page_size:

```
GET /api/v1/employees?page=1&page_size=20
```

## Naming Conventions

- Request/response bodies: snake_case (Python/Pydantic convention)
- Database columns: snake_case
- URL paths: kebab-case for multi-word, snake_case acceptable for single module paths
- Query parameters: snake_case
- Python variables/functions: snake_case
- Python classes: PascalCase
- Pydantic models: PascalCase with suffix (e.g., `EmployeeCreate`, `EmployeeResponse`)

## Authentication

- Google OAuth2 flow for login
- JWT Bearer tokens in Authorization header
- Access tokens (short-lived) + Refresh tokens (long-lived, encrypted)
- Whitelist-based access control (config/whitelist.txt)
- Never pass credentials in URL query parameters

## Validation

- Validate all input via Pydantic schemas in the API layer
- Domain validation in service/entity layer (business rules)
- Return all validation errors at once (FastAPI does this by default)
- Use `Annotated[str, Field(max_length=255)]` for field constraints
- File uploads validated for type and size before processing
