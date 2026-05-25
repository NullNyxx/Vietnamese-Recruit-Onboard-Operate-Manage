# Seed Data & System Bootstrapping

Tài liệu này mô tả cách bootstrap dữ liệu ban đầu cho hệ thống Vroom HR.

---

## Tổng quan

Hiện tại hệ thống **không có seed scripts** tự động. Việc bootstrapping được thực hiện thủ công hoặc thông qua API. Tài liệu này hướng dẫn cách setup dữ liệu ban đầu.

---

## 1. Super Admin Bootstrap

### Cách 1: Qua config (khuyên dùng)

Super admin được định nghĩa trong config:

```python
# backend/src/modules/identity/infrastructure/config.py
from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    auth_super_admin_email: str = "admin@company.com"
    # ... other settings
```

Khi user có email này đăng nhập qua Google OAuth, họ sẽ được tạo với role `admin` tự động.

### Cách 2: Qua SQL trực tiếp

```sql
-- Tạo super admin user (sau khi chạy migrations)
INSERT INTO users (id, email, name, google_sub, role, is_active, created_at, last_login)
VALUES (
    gen_random_uuid(),
    'admin@company.com',
    'Admin User',
    'google-sub-id-here',
    'admin',
    true,
    NOW(),
    NOW()
);
```

---

## 2. Initial Department & Position Setup

### Qua API

```bash
# Tạo department
curl -X POST http://localhost:8000/api/employees/departments \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=..." \
  -d '{
    "name": "Engineering",
    "code": "ENG",
    "description": "Engineering Department"
  }'

# Tạo position
curl -X POST http://localhost:8000/api/employees/positions \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=..." \
  -d '{
    "name": "Senior Developer",
    "code": "ENG-001",
    "department_id": "<department-id>"
  }'
```

### Qua SQL (bulk insert)

```sql
-- Tạo departments
INSERT INTO departments (id, name, code, description, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Engineering', 'ENG', 'Engineering Department', true, NOW(), NOW()),
    (gen_random_uuid(), 'Human Resources', 'HR', 'HR Department', true, NOW(), NOW()),
    (gen_random_uuid(), 'Finance', 'FIN', 'Finance Department', true, NOW(), NOW()),
    (gen_random_uuid(), 'Marketing', 'MKT', 'Marketing Department', true, NOW(), NOW()),
    (gen_random_uuid(), 'Operations', 'OPS', 'Operations Department', true, NOW(), NOW());

-- Tạo positions (sau khi có departments)
INSERT INTO positions (id, name, code, department_id, description, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    name,
    code,
    id,
    description,
    true,
    NOW(),
    NOW()
FROM departments;
```

---

## 3. Leave Types Setup

### Default Leave Types

```sql
INSERT INTO leave_types (id, name, code, description, default_days, is_paid, requires_approval, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Annual Leave', 'ANNUAL', 'Nghỉ phép năm', 12, true, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Sick Leave', 'SICK', 'Nghỉ ốm', 10, true, false, true, NOW(), NOW()),
    (gen_random_uuid(), 'Unpaid Leave', 'UNPAID', 'Nghỉ không lương', 30, false, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Maternity Leave', 'MATERNITY', 'Nghỉ thai sản', 180, true, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Paternity Leave', 'PATERNITY', 'Nghỉ cha', 7, true, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Wedding Leave', 'WEDDING', 'Nghỉ cưới', 3, true, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Bereavement Leave', 'BEREAVEMENT', 'Nghỉ tang', 3, true, true, true, NOW(), NOW());
```

---

## 4. Work Schedules Setup

### Standard Work Schedule (9-18)

```sql
INSERT INTO work_schedules (id, name, schedule_type, monday_start, monday_end, tuesday_start, tuesday_end, wednesday_start, wednesday_end, thursday_start, thursday_end, friday_start, friday_end, saturday_start, saturday_end, sunday_start, sunday_end, is_night_shift, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'Standard (Mon-Fri)',
    'weekly',
    '09:00', '18:00',
    '09:00', '18:00',
    '09:00', '18:00',
    '09:00', '18:00',
    '09:00', '18:00',
    NULL, NULL,
    NULL, NULL,
    false,
    true,
    NOW(),
    NOW()
);
```

### Night Shift Schedule

```sql
INSERT INTO work_schedules (id, name, schedule_type, monday_start, monday_end, tuesday_start, tuesday_end, wednesday_start, wednesday_end, thursday_start, thursday_end, friday_start, friday_end, saturday_start, saturday_end, sunday_start, sunday_end, is_night_shift, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'Night Shift',
    'weekly',
    '22:00', '06:00',
    '22:00', '06:00',
    '22:00', '06:00',
    '22:00', '06:00',
    '22:00', '06:00',
    NULL, NULL,
    NULL, NULL,
    true,
    true,
    NOW(),
    NOW()
);
```

---

## 5. Salary Configuration Setup

### Default Salary Config

```sql
INSERT INTO salary_configs (
    id, effective_date, base_salary,
    insurance_rate_employee, insurance_rate_employer,
    tax_rate, night_hourly_rate, overtime_hourly_rate,
    is_active, created_at, updated_at
)
VALUES (
    gen_random_uuid(),
    '2024-01-01',
    5000000,  -- 5M VND base
    0.105,     -- 10.5% employee (8% BHXH + 1.5% BHYT + 1% BHTN)
    0.215,     -- 21.5% employer (14% BHXH + 1.5% BHYT + 6% BHTN)
    0.0,       -- Progressive tax, calculated separately
    50000,     -- 50K VND/hour night shift
    60000,     -- 60K VND/hour overtime
    true,
    NOW(),
    NOW()
);
```

### Allowances

```sql
INSERT INTO allowances (id, name, code, type, amount, is_taxable, is_active, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Meal Allowance', 'MEAL', 'fixed', 730000, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Transport Allowance', 'TRANSPORT', 'fixed', 500000, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Phone Allowance', 'PHONE', 'fixed', 200000, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Housing Allowance', 'HOUSING', 'fixed', 2000000, true, true, NOW(), NOW()),
    (gen_random_uuid(), 'Responsibility Allowance', 'RESPONSIBILITY', 'fixed', 1000000, true, true, NOW(), NOW());
```

---

## 6. Holidays Setup (2024)

```sql
INSERT INTO holidays (id, name, date, is_recurring, year, created_at)
VALUES
    (gen_random_uuid(), 'Tết Dương lịch', '2024-01-01', true, 2024, NOW()),
    (gen_random_uuid(), 'Tết Nguyên đán', '2024-02-10', false, 2024, NOW()),
    (gen_random_uuid(), 'Tết Nguyên đán', '2024-02-11', false, 2024, NOW()),
    (gen_random_uuid(), 'Tết Nguyên đán', '2024-02-12', false, 2024, NOW()),
    (gen_random_uuid(), 'Tết Nguyên đán', '2024-02-13', false, 2024, NOW()),
    (gen_random_uuid(), 'Giỗ Tổ Hùng Vương', '2024-04-18', true, 2024, NOW()),
    (gen_random_uuid(), 'Ngày Giải phóng miền Nam', '2024-04-30', true, 2024, NOW()),
    (gen_random_uuid(), 'Ngày Quốc tế Lao động', '2024-05-01', true, 2024, NOW()),
    (gen_random_uuid(), 'Ngày Quốc khánh', '2024-09-02', true, 2024, NOW());
```

---

## 7. OAuth Config Setup

### Google OAuth

```sql
INSERT INTO oauth_configs (
    id, provider, client_id, client_secret_encrypted,
    redirect_uris, scopes, is_active, created_at, updated_at
)
VALUES (
    gen_random_uuid(),
    'google',
    'your-google-client-id',
    'encrypted-secret-here',
    '["http://localhost:3000/api/identity/auth/google/callback", "https://your-domain.com/api/identity/auth/google/callback"]',
    '["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]',
    true,
    NOW(),
    NOW()
);
```

**Lưu ý:** `client_secret_encrypted` cần được mã hóa AES-256-GCM trước khi lưu vào DB.

---

## 8. Whitelist Setup

### Initial Whitelist

```bash
# Thêm vào whitelist file (config/whitelist.txt)
admin@company.com
hr@company.com
manager@company.com
developer@company.com
```

**Hoặc qua API:**

```bash
curl -X POST http://localhost:8000/api/identity/whitelist \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=..." \
  -d '{
    "email": "newuser@company.com",
    "full_name": "New User",
    "department": "Engineering"
  }'
```

---

## 9. Sample Data for Development

### Tạo test employees

```python
# Development script - chạy từ backend/
import sys
sys.path.insert(0, 'src')

from sqlmodel import Session, create_engine, select
from src.database import engine
from src.modules.employee.domain.entities import Employee, Department, Position
from src.modules.identity.domain.entities import User

def create_sample_data():
    with Session(engine) as session:
        # Check if data exists
        existing = session.exec(select(Department)).first()
        if existing:
            print("Data already exists, skipping...")
            return

        # Create departments
        dept1 = Department(name="Engineering", code="ENG", description="Dev team")
        dept2 = Department(name="HR", code="HR", description="HR team")
        session.add(dept1)
        session.add(dept2)
        session.flush()

        # Create positions
        pos1 = Position(name="Senior Developer", code="ENG-001", department_id=dept1.id)
        pos2 = Position(name="HR Manager", code="HR-001", department_id=dept2.id)
        session.add(pos1)
        session.add(pos2)
        session.flush()

        # Create sample employees
        emp1 = Employee(
            employee_code="EMP001",
            first_name="Nguyen",
            last_name="Van A",
            full_name="Nguyen Van A",
            department_id=dept1.id,
            position_id=pos1.id,
            hire_date="2024-01-01",
            contract_type="full_time"
        )
        session.add(emp1)

        session.commit()
        print("Sample data created!")

if __name__ == "__main__":
    create_sample_data()
```

---

## 10. Production Bootstrap Checklist

Trước khi go live, đảm bảo đã setup:

- [ ] Chạy tất cả alembic migrations
- [ ] Setup super admin user
- [ ] Configure Google OAuth credentials
- [ ] Cấu hình whitelist emails
- [ ] Tạo departments và positions
- [ ] Setup work schedules
- [ ] Setup leave types
- [ ] Setup salary configs
- [ ] Setup allowances
- [ ] Setup holidays cho năm hiện tại
- [ ] Cấu hình MinIO buckets (nếu dùng)
- [ ] Cấu hình Redis (nếu dùng)

---

## 11. Future: Seed Scripts

Nếu cần tự động hóa, có thể tạo seed script:

```python
# backend/scripts/seed.py
"""Seed script to bootstrap initial data."""
import sys
sys.path.insert(0, 'src')

from sqlmodel import Session
from src.database import engine
from src.modules.employee.domain.entities import Department, Position
# ...

def seed():
    with Session(engine) as session:
        # Seed logic here
        pass

if __name__ == "__main__":
    seed()
```

Chạy với:

```bash
python -m scripts.seed
```
