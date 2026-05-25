# Shared Infrastructure

Tài liệu này mô tả các thành phần shared infrastructure được sử dụng xuyên suốt trong backend.

---

## 1. Database Connection

### Engine & Session Factory

**File:** `backend/src/database.py`

```python
from sqlmodel import Session, create_engine
from src.modules.identity.infrastructure.config import AuthSettings

def _get_sync_database_url() -> str:
    settings = AuthSettings()
    database_url = settings.database_url
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("+asyncpg", "", 1)
    return database_url

engine = create_engine(_get_sync_database_url(), echo=False)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

### Sử dụng trong Services

Có 2 pattern chính để sử dụng database session:

#### Pattern 1: FastAPI Dependency Injection (Khuyên dùng)

```python
from fastapi import Depends
from sqlmodel import Session
from src.database import get_session

def my_service(session: Session = Depends(get_session)):
    # Session auto-managed by FastAPI
    result = session.exec(select(MyModel))
    return result
```

#### Pattern 2: Manual Session (cho batch jobs/scripts)

```python
from src.database import engine
from sqlmodel import Session

with Session(engine) as session:
    # Manual session management
    session.add(new_record)
    session.commit()
```

### Session Management Rules

1. **Always use dependency injection** cho HTTP handlers
2. **Always use context manager** cho scripts/batch jobs
3. **Never** store session as instance variable
4. **Always commit** at the end of successful operation
5. **Always rollback** on exception (get_session handles this automatically)

---

## 2. Dependency Injection Container

### Module Container Pattern

Mỗi module có `container.py` để wire dependencies:

```python
# backend/src/modules/employee/container.py
from fastapi import Depends
from sqlmodel import Session
from src.database import get_session

from .application.employee_service import EmployeeService
from .infrastructure.employee_repository import EmployeeRepository

def get_employee_repository(
    session: Session = Depends(get_session)
) -> EmployeeRepository:
    return EmployeeRepository(session)

def get_employee_service(
    repository: EmployeeRepository = Depends(get_employee_repository)
) -> EmployeeService:
    return EmployeeService(repository)
```

### Sử dụng trong Router

```python
# backend/src/modules/employee/api/router.py
from fastapi import APIRouter, Depends
from .container import get_employee_service
from .application.employee_service import EmployeeService

router = APIRouter()

@router.get("/employees")
def list_employees(
    service: EmployeeService = Depends(get_employee_service)
):
    return service.list_employees()
```

---

## 3. Error Handling

### Domain Exception Pattern

Mỗi module có exceptions kế thừa từ base exception:

```python
# backend/src/modules/employee/domain/exceptions.py
class EmployeeError(Exception):
    status_code: int = 500
    error_code: str = "EMPLOYEE_ERROR"
    message: str = "An employee module error occurred"

class EmployeeNotFoundError(EmployeeError):
    status_code = 404
    error_code = "EMPLOYEE_NOT_FOUND"
    message = "Employee not found"
```

### Exception Handler Registration

```python
# backend/src/modules/employee/api/error_handler.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.modules.employee.domain.exceptions import EmployeeError

def register_employee_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmployeeError)
    async def _employee_error_handler(request: Request, exc: EmployeeError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                }
            },
        )
```

### Đăng ký handlers trong main.py

```python
# backend/src/main.py
from src.modules.employee.api.error_handler import register_employee_error_handlers

def create_app() -> FastAPI:
    app = FastAPI()
    register_employee_error_handlers(app)
    return app
```

---

## 4. Configuration Management

### Settings Pattern

Dùng Pydantic Settings cho configuration:

```python
# backend/src/modules/identity/infrastructure/config.py
from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    database_url: str = "postgresql://..."
    secret_key: str
    google_client_id: str
    google_client_secret: str
    whitelist_file: str = "config/whitelist.txt"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### Sử dụng Settings

```python
from src.modules.identity.infrastructure.config import AuthSettings

settings = AuthSettings()
database_url = settings.database_url
```

---

## 5. Logging

### Logger Setup

```python
import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Usage
logger = setup_logger(__name__)
logger.info("Starting service...")
```

---

## 6. Current Infrastructure Status

### ✅ Có sẵn

| Component           | Status       | File                             |
| ------------------- | ------------ | -------------------------------- |
| Database connection | ✅ Active    | `src/database.py`                |
| Session factory     | ✅ Active    | `src/database.py`                |
| DI Container        | ✅ Active    | Mỗi module có `container.py`     |
| Error handlers      | ✅ Active    | Mỗi module có `error_handler.py` |
| Config management   | ✅ Active    | Pydantic Settings                |
| Logging             | ✅ Available | Standard logging                 |

### ❌ Chưa có / Cần implement

| Component                | Status            | Ghi chú                                      |
| ------------------------ | ----------------- | -------------------------------------------- |
| MinIO client             | ❌ Chưa implement | Cần tạo `src/infrastructure/minio_client.py` |
| Redis cache              | ❌ Chưa implement | Cần tạo `src/infrastructure/redis_client.py` |
| Background workers (ARQ) | ❌ Chưa implement | Cho batch jobs                               |
| Event bus                | ❌ Chưa implement | Cho cross-module events                      |
| File storage abstraction | ❌ Chưa implement | Unified interface cho file ops               |

---

## 7. Best Practices

### Khi tạo service mới

1. **Tạo domain exceptions** trước:

```python
# modules/xxx/domain/exceptions.py
class XXXError(Exception):
    status_code = 500
    error_code = "XXX_ERROR"
    message = "An error occurred"
```

2. **Tạo repository** cho data access:

```python
# modules/xxx/infrastructure/xxx_repository.py
class XXXRepository:
    def __init__(self, session: Session):
        self.session = session
```

3. **Tạo service** cho business logic:

```python
# modules/xxx/application/xxx_service.py
class XXXService:
    def __init__(self, repository: XXXRepository):
        self.repository = repository
```

4. **Wire trong container.py:**

```python
# modules/xxx/container.py
def get_xxx_service(
    repository: XXXRepository = Depends(get_xxx_repository)
) -> XXXService:
    return XXXService(repository)
```

5. **Register error handler:**

```python
# modules/xxx/api/error_handler.py
def register_xxx_error_handlers(app: FastAPI):
    @app.exception_handler(XXXError)
    async def handle_xxx_error(request, exc):
        ...
```

---

## 8. Migration Guide: Thêm Infrastructure mới

### Thêm MinIO Client

```python
# backend/src/infrastructure/minio_client.py
from minio import Minio
from typing import BinaryIO

class MinIOClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key)
        self.bucket = bucket

    def upload(self, object_name: str, data: BinaryIO, content_type: str):
        self.client.put_object(self.bucket, object_name, data, content_type)

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(self.bucket, object_name, expires)
```

### Thêm Redis Client

```python
# backend/src/infrastructure/redis_client.py
import redis
from typing import Optional

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self.client.get(key)

    def set(self, key: str, value: str, ex: int = None):
        self.client.set(key, value, ex=ex)
```

---

## 9. Testing Infrastructure

### Mock Database Session

```python
import pytest
from sqlmodel import Session, SQLModel
from src.database import engine

@pytest.fixture
def test_session():
    # Create tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Drop tables
    SQLModel.metadata.drop_all(engine)
```

### Mock Dependencies

```python
from unittest.mock import MagicMock

def test_employee_service():
    mock_repo = MagicMock()
    mock_repo.get.return_value = Employee(id="1", name="Test")

    service = EmployeeService(mock_repo)
    result = service.get_employee("1")

    assert result.name == "Test"
```
