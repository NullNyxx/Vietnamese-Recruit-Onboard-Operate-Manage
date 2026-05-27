---
inclusion: always
---

# Dev Environment — WSL2 + Docker

## ⚠️ Quy tắc quan trọng

### 1. Backend PHẢI chạy trong WSL

PostgreSQL và Redis chạy trong Docker **bên trong WSL2**. Do WSL2 port forwarding
không đáng tin cậy với `asyncpg`, backend **bắt buộc** phải chạy trong WSL.

**KHÔNG BAO GIỜ** chạy backend trên Windows native — sẽ không kết nối được DB.

### 2. Lệnh khởi động backend

```bash
wsl -- /bin/bash -c "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/nullnyx/.local/bin && cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage/backend && .venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src"
```

### 3. Khi `.venv` bị hỏng hoặc cần tạo lại

```bash
wsl -- /bin/bash -c "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/nullnyx/.local/bin && cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage/backend && rm -rf .venv && uv sync"
```

**Lưu ý:** `.venv` phải được tạo bởi WSL (Linux Python), KHÔNG phải Windows Python.

### 4. Khi backend bị treo (socket hang up / ECONNRESET)

Kiểm tra theo thứ tự:

1. **Kiểm tra process bị stuck:**

   ```bash
   wsl -- /bin/bash -c "export PATH=/usr/local/bin:/usr/bin:/bin && ps aux | grep uvicorn"
   ```

   Nếu thấy process ở trạng thái `D+` (uninterruptible sleep) → kill -9

2. **Kiểm tra Docker containers:**

   ```bash
   wsl -- /bin/bash -c "export PATH=/usr/local/bin:/usr/bin:/bin && docker ps"
   ```

   Nếu PostgreSQL/Redis không chạy → `docker start vroom-postgres vroom-redis`

3. **Kiểm tra DB accessible:**

   ```bash
   wsl -- /bin/bash -c "export PATH=/usr/local/bin:/usr/bin:/bin && docker exec vroom-postgres pg_isready -U postgres"
   ```

4. **Khởi động lại backend** (dùng lệnh ở mục 2)

### 5. WSL PATH issue

WSL config có `appendWindowsPath=false`, nên khi chạy lệnh qua `wsl --` phải
luôn export PATH đầy đủ:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/nullnyx/.local/bin
```

### 6. Docker containers

| Service    | Container Name | Port |
| ---------- | -------------- | ---- |
| PostgreSQL | vroom-postgres | 5432 |
| Redis      | vroom-redis    | 6379 |

### 7. Frontend (Next.js) chạy trên Windows

Frontend chạy trên Windows (`pnpm dev` port 3000) và proxy API requests đến
`localhost:8000`. WSL2 tự động forward port 8000 từ WSL → Windows, nên frontend
có thể gọi backend bình thường.

### 8. KHÔNG xóa `.venv` từ Windows khi process WSL đang dùng

Nếu xóa `.venv` từ Windows trong khi uvicorn WSL đang chạy, process sẽ bị
stuck ở trạng thái `D+` và không thể kill bình thường. Luôn stop backend
trước khi thao tác với `.venv`.
