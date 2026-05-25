# Database Migrations Map

Tài liệu này map tất cả 26 alembic migrations trong project, cho thấy mỗi migration tạo/modify bảng nào và dependencies.

## Tổng quan

| Version | Module      | Tables Created/Modified                                         |
| ------- | ----------- | --------------------------------------------------------------- |
| 001     | identity    | users                                                           |
| 002     | identity    | oauth_grants                                                    |
| 003     | identity    | refresh_tokens                                                  |
| 004     | employee    | departments                                                     |
| 005     | employee    | positions                                                       |
| 006     | employee    | employees                                                       |
| 007     | employee    | employee_documents                                              |
| 008     | gmail       | gmail_credentials, gmail_labels                                 |
| 009     | recruitment | candidates, candidate_cv, recruitment_pipeline, pipeline_stages |
| 010     | identity    | users (add role column)                                         |
| 011     | identity    | whitelist_entries                                               |
| 012     | identity    | oauth_configs                                                   |
| 013     | identity    | audit_logs                                                      |
| 014     | attendance  | leave_types                                                     |
| 015     | attendance  | leave_balances                                                  |
| 016     | attendance  | leave_requests                                                  |
| 017     | attendance  | work_schedules                                                  |
| 018     | attendance  | attendance_records                                              |
| 019     | attendance  | overtime_requests                                               |
| 020     | attendance  | holidays                                                        |
| 021     | payroll     | salary_configs                                                  |
| 022     | payroll     | allowances                                                      |
| 023     | payroll     | dependents                                                      |
| 024     | payroll     | payroll_periods                                                 |
| 025     | payroll     | payslips                                                        |
| 026     | payroll     | position_salaries                                               |

---

## Chi tiết từng Migration

### 001_create_users_table.py

- **Creates:** `users`
- **Columns:** id, email, name, avatar_url, google_sub, created_at, last_login, is_active
- **Indexes:** ix_users_email (unique), ix_users_google_sub (unique)
- **Dependencies:** None (initial migration)
- **Module:** identity

### 002_create_oauth_grants_table.py

- **Creates:** `oauth_grants`
- **Columns:** id, code, client_id, redirect_uri, scope, expires_at, created_at
- **Dependencies:** None
- **Module:** identity

### 003_create_refresh_tokens_table.py

- **Creates:** `refresh_tokens`
- **Columns:** id, token, user_id, expires_at, created_at, is_revoked
- **Foreign Keys:** user_id → users.id
- **Dependencies:** 001
- **Module:** identity

### 004_create_departments_table.py

- **Creates:** `departments`
- **Columns:** id, name, code, description, manager_id, is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** employee

### 005_create_positions_table.py

- **Creates:** `positions`
- **Columns:** id, name, code, department_id, description, is_active, created_at, updated_at
- **Foreign Keys:** department_id → departments.id
- **Dependencies:** 004
- **Module:** employee

### 006_create_employees_table.py

- **Creates:** `employees`
- **Columns:** id, user_id, employee_code, first_name, last_name, full_name, date_of_birth, gender, phone, address, department_id, position_id, hire_date, contract_type, work_schedule_id, is_active, created_at, updated_at
- **Foreign Keys:** user_id → users.id, department_id → departments.id, position_id → positions.id, work_schedule_id → work_schedules.id (nullable)
- **Indexes:** ix_employees_employee_code (unique), ix_employees_user_id (unique)
- **Dependencies:** 001, 004, 005, 017 (nullable)
- **Module:** employee

### 007_create_employee_documents_table.py

- **Creates:** `employee_documents`
- **Columns:** id, employee_id, document_type, file_name, file_path, file_size, mime_type, uploaded_by, created_at
- **Foreign Keys:** employee_id → employees.id, uploaded_by → users.id
- **Dependencies:** 006
- **Module:** employee

### 008_create_gmail_tables.py

- **Creates:** `gmail_credentials`, `gmail_labels`
- **gmail_credentials:** id, user_id, access_token, refresh_token, token_expiry, created_at, updated_at
- **gmail_labels:** id, user_id, label_id, name, color, is_visible, created_at
- **Foreign Keys:** user_id → users.id
- **Dependencies:** 001
- **Module:** gmail

### 009_create_recruitment_tables.py

- **Creates:** `candidates`, `candidate_cv`, `recruitment_pipeline`, `pipeline_stages`
- **candidates:** id, email, full_name, phone, dob, address, source, status, pipeline_id, current_stage_id, applied_date, created_at, updated_at
- **candidate_cv:** id, candidate_id, file_name, file_path, parsed_data (JSON), parsed_at
- **recruitment_pipeline:** id, name, description, is_active, created_at
- **pipeline_stages:** id, pipeline_id, name, order, is_interview, is_rejection, created_at
- **Foreign Keys:** pipeline_id → recruitment_pipeline.id, current_stage_id → pipeline_stages.id
- **Dependencies:** None
- **Module:** recruitment

### 010_add_role_to_users.py

- **Modifies:** `users` table
- **Adds column:** role (enum: admin, hr, employee)
- **Dependencies:** 001
- **Module:** identity

### 011_create_whitelist_entries_table.py

- **Creates:** `whitelist_entries`
- **Columns:** id, email, full_name, department, is_active, created_at, created_by
- **Indexes:** ix_whitelist_entries_email (unique)
- **Foreign Keys:** created_by → users.id
- **Dependencies:** 001
- **Module:** identity

### 012_create_oauth_configs_table.py

- **Creates:** `oauth_configs`
- **Columns:** id, provider, client_id, client_secret_encrypted, redirect_uris (JSON), scopes (JSON), is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** identity

### 013_create_audit_logs_table.py

- **Creates:** `audit_logs`
- **Columns:** id, user_id, action, resource_type, resource_id, changes (JSON), ip_address, user_agent, created_at
- **Foreign Keys:** user_id → users.id
- **Dependencies:** 001
- **Module:** identity

### 014_create_leave_types_table.py

- **Creates:** `leave_types`
- **Columns:** id, name, code, description, default_days, is_paid, requires_approval, is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** attendance

### 015_create_leave_balances_table.py

- **Creates:** `leave_balances`
- **Columns:** id, employee_id, leave_type_id, year, total_days, used_days, remaining_days, created_at, updated_at
- **Foreign Keys:** employee_id → employees.id, leave_type_id → leave_types.id
- **Indexes:** ix_leave_balances_employee_year (unique composite)
- **Dependencies:** 006, 014
- **Module:** attendance

### 016_create_leave_requests_table.py

- **Creates:** `leave_requests`
- **Columns:** id, employee_id, leave_type_id, start_date, end_date, total_days, reason, status, approved_by, approved_at, rejected_reason, created_at, updated_at
- **Foreign Keys:** employee_id → employees.id, leave_type_id → leave_types.id, approved_by → users.id
- **Dependencies:** 006, 014
- **Module:** attendance

### 017_create_work_schedules_table.py

- **Creates:** `work_schedules`
- **Columns:** id, name, schedule_type, monday_start, monday_end, tuesday_start, tuesday_end, wednesday_start, wednesday_end, thursday_start, thursday_end, friday_start, friday_end, saturday_start, saturday_end, sunday_start, sunday_end, is_night_shift, is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** attendance

### 018_create_attendance_records_table.py

- **Creates:** `attendance_records`
- **Columns:** id, employee_id, date, check_in, check_out, work_hours, status, notes, created_at, updated_at
- **Foreign Keys:** employee_id → employees.id
- **Indexes:** ix_attendance_records_employee_date (unique composite)
- **Dependencies:** 006
- **Module:** attendance

### 019_create_overtime_requests_table.py

- **Creates:** `overtime_requests`
- **Columns:** id, employee_id, date, start_time, end_time, hours, reason, status, approved_by, approved_at, rejected_reason, created_at, updated_at
- **Foreign Keys:** employee_id → employees.id, approved_by → users.id
- **Dependencies:** 006
- **Module:** attendance

### 020_create_holidays_table.py

- **Creates:** `holidays`
- **Columns:** id, name, date, is_recurring, year, created_at
- **Dependencies:** None
- **Module:** attendance

### 021_create_salary_configs_table.py

- **Creates:** `salary_configs`
- **Columns:** id, effective_date, base_salary, insurance_rate_employee, insurance_rate_employer, tax_rate, night_hourly_rate, overtime_hourly_rate, is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** payroll

### 022_create_allowances_table.py

- **Creates:** `allowances`
- **Columns:** id, name, code, type, amount, is_taxable, is_active, created_at, updated_at
- **Dependencies:** None
- **Module:** payroll

### 023_create_dependents_table.py

- **Creates:** `dependents`
- **Columns:** id, employee_id, name, relationship, date_of_birth, id_card_number, tax_dependent, is_active, created_at, updated_at
- **Foreign Keys:** employee_id → employees.id
- **Dependencies:** 006
- **Module:** payroll

### 024_create_payroll_periods_table.py

- **Creates:** `payroll_periods`
- **Columns:** id, name, start_date, end_date, status, total_employees, total_gross, total_net, processed_by, processed_at, created_at, updated_at
- **Foreign Keys:** processed_by → users.id
- **Dependencies:** None
- **Module:** payroll

### 025_create_payslips_table.py

- **Creates:** `payslips`
- **Columns:** id, period_id, employee_id, basic_salary, allowances (JSON), deductions (JSON), gross_salary, net_salary, tax_amount, insurance_amount, status, created_at, updated_at
- **Foreign Keys:** period_id → payroll_periods.id, employee_id → employees.id
- **Indexes:** ix_payslips_period_employee (unique composite)
- **Dependencies:** 006, 024
- **Module:** payroll

### 026_create_position_salaries_table.py

- **Creates:** `position_salaries`
- **Columns:** id, position_id, effective_date, base_salary, is_active, created_at, updated_at
- **Foreign Keys:** position_id → positions.id
- **Dependencies:** 005
- **Module:** payroll

---

## Module Grouping

### Identity Module (5 migrations)

- 001: users
- 002: oauth_grants
- 003: refresh_tokens
- 010: users (add role)
- 011: whitelist_entries
- 012: oauth_configs
- 013: audit_logs

### Employee Module (4 migrations)

- 004: departments
- 005: positions
- 006: employees
- 007: employee_documents

### Gmail Module (1 migration)

- 008: gmail_credentials, gmail_labels

### Recruitment Module (1 migration)

- 009: candidates, candidate_cv, recruitment_pipeline, pipeline_stages

### Attendance Module (7 migrations)

- 014: leave_types
- 015: leave_balances
- 016: leave_requests
- 017: work_schedules
- 018: attendance_records
- 019: overtime_requests
- 020: holidays

### Payroll Module (6 migrations)

- 021: salary_configs
- 022: allowances
- 023: dependents
- 024: payroll_periods
- 025: payslips
- 026: position_salaries

---

## Dependencies Flow

```
001 (users) ─────┬──► 002, 003, 008, 010, 011, 013
                 │
004 (dept) ──────┼──► 005
                 │
005 (positions) ─┴──► 006, 026

006 (employees) ────► 007, 015, 016, 018, 019, 023, 025
                 │
014 (leave_types) ──► 015, 016
                 │
017 (work_schedules) ──► 006 (nullable)
                 │
024 (payroll_periods) ──► 025
```

---

## Notes

- Migration chain là linear (không có branches trong alembic)
- Tất cả FK references phải reference đến bảng đã được tạo ở migration trước đó
- Một số migrations có thể chạy song song nếu dùng `depends_on` nhưng hiện tại chain là linear
