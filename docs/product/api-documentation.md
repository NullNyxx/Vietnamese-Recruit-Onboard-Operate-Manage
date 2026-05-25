# API Documentation

## OpenAPI / Swagger UI

Vroom HR uses FastAPI's built-in OpenAPI support. The API documentation is available at:

| Environment        | URL                          |
| ------------------ | ---------------------------- |
| Local              | `http://localhost:8000/docs` |
| Staging/Production | `https://<domain>/docs`      |

### OpenAPI JSON Schema

- **JSON**: `http://localhost:8000/openapi.json`
- **ReDoc**: `http://localhost:8000/redoc`

### Configuration

OpenAPI is configured in `backend/src/main.py`:

```python
app = FastAPI(
    title="Vroom HR",
    description="Vietnamese Recruit-Onboard-Operate-Manage platform",
    version="0.1.0",
    lifespan=lifespan,
)
```

### Adding API Documentation

Each module should add docstrings to routers and endpoints:

```python
@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    session: AsyncSession = Depends(get_session),
) -> list[EmployeeResponse]:
    """List all active employees.

    Returns a list of employees with their basic information.
    Only returns employees where `is_active=True`.
    """
    ...
```

### Schema Documentation

Request/Response schemas should include docstrings:

```python
class EmployeeCreate(BaseModel):
    """Request body for creating a new employee."""
    email: EmailStr
    full_name: str
    department_id: UUID
    # ...
```

## API Versioning

Currently using URL-based versioning:

| Version | Prefix     | Example             |
| ------- | ---------- | ------------------- |
| v1      | `/api/v1/` | `/api/v1/employees` |

### Base URL Structure

```
/api/v1/
├── /auth/          → Authentication (login, logout, refresh)
├── /admin/         → Admin-only endpoints
├── /employees/     → Employee CRUD
├── /candidates/    → Recruitment
├── /attendance/    → Check-in/out, leave, overtime
├── /payroll/       → Salary, payslips
├── /gmail/         → Gmail integration
└── /ess/           → Employee self-service
```

## Response Format

All API responses follow a consistent format.

### Success Responses

```json
{
  "data": { ... },
  "message": "Employee created successfully"
}
```

### Error Responses

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Invalid email format",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### Common Error Codes

| Code                  | HTTP Status | Description                       |
| --------------------- | ----------- | --------------------------------- |
| `UNAUTHORIZED`        | 401         | Missing or invalid authentication |
| `FORBIDDEN`           | 403         | Insufficient permissions          |
| `NOT_FOUND`           | 404         | Resource not found                |
| `VALIDATION_ERROR`    | 422         | Request validation failed         |
| `RATE_LIMIT_EXCEEDED` | 429         | Too many requests                 |
| `INTERNAL_ERROR`      | 500         | Server error                      |

## Authentication

See: [Authentication](./authentication.md)

## Rate Limiting

See: [Rate Limiting Strategy](./rate-limiting.md)

## API Testing

```bash
# Using httpx directly
curl http://localhost:8000/docs

# JSON schema
curl http://localhost:8000/openapi.json | jq
```
