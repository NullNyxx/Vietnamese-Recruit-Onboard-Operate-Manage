# Vroom HR - Vietnamese Recruit-Onboard-Operate-Manage

## Giới thiệu

**Vroom HR** là nền tảng quản lý nhân sự (HRM) dành cho doanh nghiệp Việt Nam. Tên dự án viết tắt từ **V**ietnamese **R**ecruit-**O**nboard-**O**perate-**M**anage, phản ánh 4 giai đoạn chính trong vòng đời quản lý nhân sự:

1. **Recruit** – Tuyển dụng ứng viên
2. **Onboard** – Tiếp nhận nhân viên mới
3. **Operate** – Vận hành công việc hàng ngày
4. **Manage** – Quản lý hồ sơ, tài liệu, phòng ban

---

## Kiến trúc hệ thống

Dự án sử dụng kiến trúc **monorepo** với 2 thành phần chính:

```
Vietnamese-Recruit-Onboard-Operate-Manage/
├── backend/          # API server (Python/FastAPI)
├── frontend/         # Giao diện web (Next.js/React)
├── docker-compose.yml
└── docker-compose.infra.yml
```

### Backend

| Thành phần | Công nghệ |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| Database | PostgreSQL 15 |
| Cache / Session | Redis 7 |
| Object Storage | MinIO (lưu tài liệu nhân viên) |
| Migration | Alembic |
| Authentication | OAuth2 + JWT (authlib, python-jose) |

Backend được tổ chức theo **kiến trúc module** (modular architecture) với các layer rõ ràng:

```
backend/src/modules/
├── identity/           # Module xác thực & phân quyền
│   ├── api/            # Router, schemas, error handlers
│   ├── application/    # Business logic (auth, oauth, token, whitelist)
│   ├── domain/         # Entities, exceptions
│   └── infrastructure/ # Repository, JWT utils, rate limiter
│
└── employee/           # Module quản lý nhân viên
    ├── api/            # Router, schemas, error handlers
    ├── application/    # Services (employee, department, position, document, import)
    ├── domain/         # Entities, exceptions
    └── infrastructure/ # Repository, MinIO client, Excel parser
```

### Frontend

| Thành phần | Công nghệ |
|---|---|
| Framework | Next.js 14 (App Router) |
| UI Library | React 18 |
| Styling | Tailwind CSS 3 |
| Icons | Lucide React |
| Utilities | clsx, tailwind-merge, class-variance-authority |

Cấu trúc frontend:

```
frontend/src/
├── app/
│   ├── login/                    # Trang đăng nhập
│   └── (dashboard)/              # Layout dashboard (cần xác thực)
│       ├── employees/            # Danh sách, thêm mới, import, chi tiết nhân viên
│       └── settings/             # Cài đặt phòng ban, chức vụ
├── components/                   # Components dùng chung
│   ├── ui/                       # UI primitives
│   ├── employee-form.tsx         # Form nhân viên
│   └── grant-warning-modal.tsx   # Modal cảnh báo quyền
└── lib/
    └── api/                      # API client
```

---

## Các tính năng chính

### 1. Xác thực & Phân quyền (Identity Module)

- Đăng nhập qua OAuth2 (Google hoặc provider khác)
- Quản lý JWT access token + refresh token
- Whitelist email được phép truy cập hệ thống
- Rate limiting chống brute-force
- Mã hóa token an toàn (cryptography)

### 2. Quản lý Nhân viên (Employee Module)

- **CRUD nhân viên**: Tạo, xem, sửa, xóa mềm (soft delete) nhân viên
- **Mã nhân viên tự động**: Format `NV-XXX`
- **Import Excel**: Nhập hàng loạt nhân viên từ file `.xlsx`
- **Quản lý tài liệu**: Upload/download tài liệu nhân viên (lưu trên MinIO)
  - Hỗ trợ nhiều loại tài liệu (CMND, hợp đồng, bằng cấp...)
  - Lưu trữ theo cấu trúc: `employees/{id}/{document_type}/{filename}`
  - Append-only: giữ lại tất cả phiên bản cũ

### 3. Quản lý Phòng ban & Chức vụ

- CRUD phòng ban (Department)
- CRUD chức vụ (Position), liên kết với phòng ban
- Ràng buộc: không xóa được phòng ban/chức vụ nếu còn nhân viên đang hoạt động

---

## Mô hình dữ liệu

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  Department  │◄────│   Position   │     │   EmployeeDocument   │
│──────────────│     │──────────────│     │──────────────────────│
│ id (UUID)    │     │ id (UUID)    │     │ id (UUID)            │
│ name         │     │ name         │     │ employee_id (FK)     │
│ description  │     │ department_id│     │ document_type        │
│ created_at   │     │ created_at   │     │ file_name            │
└──────────────┘     └──────────────┘     │ storage_path         │
                            │              │ file_size            │
                            ▼              │ mime_type            │
                     ┌──────────────┐     │ uploaded_at          │
                     │   Employee   │────►└──────────────────────┘
                     │──────────────│
                     │ id (UUID)    │
                     │ employee_code│
                     │ full_name    │
                     │ email        │
                     │ phone        │
                     │ date_of_birth│
                     │ gender       │
                     │ address      │
                     │ department_id│
                     │ position_id  │
                     │ start_date   │
                     │ id_number    │
                     │ tax_code     │
                     │ contract_type│
                     │ candidate_id │
                     │ is_active    │
                     └──────────────┘
```

---

## Hạ tầng & Triển khai

Dự án sử dụng **Docker Compose** để triển khai:

| Service | Port | Mô tả |
|---|---|---|
| `postgres` | 5432 | Database chính |
| `redis` | 6379 | Cache, session, rate limiting |
| `minio` | 9000 / 9001 | Object storage cho tài liệu |
| `backend` | 8000 | FastAPI server |
| `frontend` | 3000 | Next.js web app |

### Chạy dự án

```bash
# Chạy toàn bộ hệ thống
docker-compose up -d

# Chỉ chạy infrastructure (dev mode)
docker-compose -f docker-compose.infra.yml up -d

# Chạy migration database
cd backend
alembic upgrade head
```

---

## Công cụ phát triển

| Công cụ | Mục đích |
|---|---|
| Ruff | Linter + formatter cho Python |
| MyPy | Static type checking |
| Pytest | Unit & integration testing |
| Hypothesis | Property-based testing |
| ESLint | Linter cho TypeScript/React |

---

## Trạng thái hiện tại

Dự án đang trong giai đoạn phát triển ban đầu (v0.1.0). Các module đã được triển khai:

- ✅ Xác thực OAuth2 + JWT
- ✅ Quản lý nhân viên (CRUD + import Excel)
- ✅ Quản lý tài liệu nhân viên (MinIO)
- ✅ Quản lý phòng ban & chức vụ
- ✅ Giao diện dashboard cơ bản
- 🔲 Module tuyển dụng (Recruit)
- 🔲 Module onboarding
- 🔲 Báo cáo & thống kê
- 🔲 Quản lý chấm công & lương

---

## Cấu trúc thư mục đầy đủ

```
Vietnamese-Recruit-Onboard-Operate-Manage/
├── .gitignore
├── AGENTS.md                    # Hướng dẫn cho AI agents
├── README.md                    # README gốc (harness)
├── docker-compose.yml           # Docker full stack
├── docker-compose.infra.yml     # Docker chỉ infrastructure
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml           # Dependencies & config
│   ├── alembic.ini              # Alembic config
│   ├── alembic/versions/        # Database migrations
│   ├── config/whitelist.txt     # Email whitelist
│   └── src/
│       ├── main.py              # FastAPI entrypoint
│       └── modules/
│           ├── identity/        # Auth module
│           └── employee/        # Employee management module
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── src/
│       ├── middleware.ts        # Auth middleware
│       ├── app/                 # Next.js pages
│       ├── components/          # React components
│       └── lib/                 # Utilities & API client
├── docs/                        # Tài liệu dự án
└── harness-experimental/        # Agent collaboration harness
```
