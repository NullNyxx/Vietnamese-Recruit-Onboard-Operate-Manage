---
inclusion: manual
---

# Harness Workflow Guide

Hướng dẫn chi tiết sử dụng Harness cho AI Agent trên Windows (WSL).

## Shell Command Template

Mọi harness command phải chạy qua WSL:

```bash
wsl -- /bin/bash -c "cd /mnt/c/Users/NullNyx/Projects/Vietnamese-Recruit-Onboard-Operate-Manage && /bin/bash scripts/harness <command>"
```

## Task Loop (cho mỗi task)

### 1. Classify (phân loại)

Xác định input type:

- `new_spec` — Spec mới cần decompose
- `spec_slice` — Implement một phần từ spec
- `change_request` — Sửa/thêm behavior
- `new_initiative` — Feature lớn cần nhiều stories
- `maintenance` — Technical/dependency work
- `harness_improvement` — Cải thiện process

Xác định lane:

- `tiny` — Low-risk, patch trực tiếp
- `normal` — Story-sized, cần story file
- `high_risk` — Ảnh hưởng auth/data/security

### 2. Record Intake

```bash
scripts/harness intake --type "change_request" --summary "Add pagination to /api/employees" --lane "normal" --flags "public_contracts" --docs "docs/product/overview.md"
```

### 3. Create Story (nếu normal/high-risk)

```bash
scripts/harness story add --id "US-001" --title "Employee list pagination" --lane "normal"
```

### 4. Do Work

Implement theo architecture rules.

### 5. Update Story Status

```bash
scripts/harness story update --id "US-001" --status "implemented" --unit 1 --integration 0
```

### 6. Record Trace

```bash
scripts/harness trace --summary "Implemented employee pagination" --outcome "completed" --changed "backend/src/modules/employee/api/router.py"
```

### 7. Record Friction (nếu có)

```bash
scripts/harness backlog add --title "Missing test fixtures" --pain "Had to manually create test data for every test"
```

## Query Commands

```bash
scripts/harness query stats      # Tổng quan
scripts/harness query matrix     # Story validation status
scripts/harness query backlog    # Improvement proposals
scripts/harness query intakes    # Recent classifications
scripts/harness query traces     # Recent executions
scripts/harness query friction   # Pain points
```

## Risk Checklist Flags

auth, authorization, data_model, audit_security, external_systems,
public_contracts, cross_platform, existing_behavior, weak_proof, multi_domain

## Lane Rules

| Lane      | Khi nào                 | Yêu cầu                                  |
| --------- | ----------------------- | ---------------------------------------- |
| tiny      | 0-1 flags, low impact   | Patch + run checks                       |
| normal    | 2-3 flags               | Story file + validation                  |
| high_risk | 4+ flags hoặc hard gate | Story folder + exec plan + human confirm |

Hard gates (luôn high-risk): auth, authorization, data loss, audit/security, external provider
