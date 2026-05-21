# Implementation Plan: Admin Auth Management

## Overview

This plan implements the admin authentication management feature for VroomHR, extending the existing `identity` module with role-based access control, database-backed whitelist management, encrypted OAuth credential management, audit logging, and an admin panel frontend. The implementation follows the project's layered architecture (domain → infrastructure → application → API) with FastAPI dependency injection on the backend and Next.js with shadcn/ui on the frontend.

## Tasks

- [x] 1. Database migrations and domain entities
  - [x] 1.1 Create Alembic migration to add `role` column to `users` table
    - Add `role` VARCHAR(10) NOT NULL DEFAULT 'user' column to existing `users` table
    - Add index `ix_users_role` on the role column
    - Update the existing `User` SQLModel entity in `backend/src/modules/identity/domain/entities.py` to include `role: UserRole` field with `UserRole` enum (`admin`, `user`)
    - _Requirements: 1.3, 1.4_

  - [x] 1.2 Create Alembic migration for `whitelist_entries` table
    - Create `whitelist_entries` table with columns: id (UUID PK), value (VARCHAR 255, UNIQUE), entry_type (VARCHAR 20), added_by_user_id (UUID FK to users), created_at (TIMESTAMPTZ)
    - Add indexes on `value` and `entry_type`
    - Create `WhitelistEntry` and `WhitelistEntryType` entities in `backend/src/modules/identity/domain/entities.py`
    - _Requirements: 3.1, 3.2_

  - [x] 1.3 Create Alembic migration for `oauth_configs` table
    - Create `oauth_configs` table with columns: id (UUID PK), provider (VARCHAR 50), client_id (VARCHAR 255), client_secret_enc (TEXT), redirect_uri (VARCHAR 500), is_active (BOOLEAN), created_at, updated_at (TIMESTAMPTZ), updated_by_user_id (UUID FK)
    - Add unique constraint on (provider, is_active)
    - Create `OAuthConfig` entity in `backend/src/modules/identity/domain/entities.py`
    - _Requirements: 5.1_

  - [x] 1.4 Create Alembic migration for `audit_logs` table
    - Create `audit_logs` table with columns: id (UUID PK), admin_user_id (UUID FK), admin_email (VARCHAR 255), action_type (VARCHAR 50), details (JSONB), created_at (TIMESTAMPTZ)
    - Add indexes on `action_type`, `created_at`, and `admin_user_id`
    - Create `AuditLog` and `AuditActionType` entities in `backend/src/modules/identity/domain/entities.py`
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Backend infrastructure layer (repositories)
  - [x] 2.1 Implement `WhitelistRepository`
    - Create `backend/src/modules/identity/infrastructure/whitelist_repository.py`
    - Implement methods: `add(entry)`, `remove(entry_id)`, `get_all()`, `exists(value)`
    - Follow the existing repository pattern (accepts `AsyncSession` in constructor)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 2.2 Implement `OAuthConfigRepository`
    - Create `backend/src/modules/identity/infrastructure/oauth_config_repository.py`
    - Implement methods: `get_active()`, `upsert(config)`
    - _Requirements: 5.1, 5.5_

  - [x] 2.3 Implement `AuditLogRepository`
    - Create `backend/src/modules/identity/infrastructure/audit_log_repository.py`
    - Implement methods: `create(log)`, `get_paginated(offset, limit, filters)`
    - Support filtering by action_type and date range
    - _Requirements: 7.1, 7.4_

- [x] 3. Backend application layer (services)
  - [x] 3.1 Implement `RoleService`
    - Create `backend/src/modules/identity/application/role_service.py`
    - Implement `promote_to_admin(target_user_id, admin_user)`, `demote_to_user(target_user_id, admin_user)`, `ensure_super_admin(email)`
    - Add protection against demoting the last admin and the super admin
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.4_

  - [x] 3.2 Implement `WhitelistManager` (composite whitelist with cache)
    - Create `backend/src/modules/identity/application/whitelist_manager.py`
    - Implement `is_allowed(email)` with case-insensitive matching against both exact emails and domain patterns
    - Implement `add_entry(value, admin)` with auto-detection of entry type and duplicate checking
    - Implement `remove_entry(entry_id, admin)`, `list_entries()`, `refresh_cache()`
    - Merge file-based whitelist (via existing `WhitelistLoader`) and database entries as a union
    - Mark file-based entries as read-only in listing
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 3.3 Write property tests for whitelist email matching
    - **Property 9: Whitelist email matching** — For any email and whitelist config, matching returns true iff email matches an exact entry or domain pattern (case-insensitive)
    - **Property 10: Whitelist source union** — Union of file and DB entries; email allowed by either source passes
    - **Property 11: Deduplication with database precedence** — Duplicate entries show DB metadata
    - Create `backend/tests/admin/test_whitelist_matching_properties.py`
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 9.2, 9.3**

  - [ ]* 3.4 Write property tests for whitelist CRUD operations
    - **Property 4: Whitelist entry addition** — Valid email/domain pattern persists with correct type
    - **Property 5: Whitelist entry removal round-trip** — Removed entries no longer appear
    - **Property 6: Whitelist listing completeness** — All DB entries returned with metadata
    - **Property 7: Duplicate entry detection** — Duplicate value returns 409, DB unchanged
    - **Property 8: Invalid input rejection** — Invalid format returns 422
    - Create `backend/tests/admin/test_whitelist_crud_properties.py`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [x] 3.5 Implement `OAuthConfigManager`
    - Create `backend/src/modules/identity/application/oauth_config_manager.py`
    - Implement `get_active_config()`, `update_config(client_id, client_secret, redirect_uri, admin)`, `validate_credentials(client_id)`, `get_effective_credentials()`
    - Use existing `CryptoUtils` for encryption/decryption of client_secret
    - Implement fallback to environment variables when no DB config exists
    - Implement validation against Google OAuth discovery endpoint
    - Retain previous credentials until new ones are validated
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3_

  - [ ]* 3.6 Write property tests for OAuth credential management
    - **Property 12: OAuth credential encryption round-trip** — Encrypt then decrypt produces original
    - **Property 13: Secret masking** — Masked output shows only last 4 chars, never full secret
    - **Property 14: OAuth credential validation** — Empty client_id or invalid redirect_uri rejected
    - Create `backend/tests/admin/test_oauth_properties.py`
    - **Validates: Requirements 5.1, 5.2, 5.4**

  - [x] 3.7 Implement `AuditService`
    - Create `backend/src/modules/identity/application/audit_service.py`
    - Implement `log_action(admin, action_type, details)` and `get_logs(page, page_size, action_type, start_date, end_date)`
    - Ensure secret values are never stored in audit details
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 3.8 Write property tests for audit logging
    - **Property 15: Audit log completeness** — Every admin action creates a log entry with required fields
    - **Property 16: Audit log query correctness** — Filtered/paginated queries return correct subset
    - Create `backend/tests/admin/test_audit_properties.py`
    - **Validates: Requirements 5.6, 7.1, 7.2, 7.3, 7.4**

- [x] 4. Checkpoint - Ensure all backend service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Backend API layer and super admin bootstrap
  - [x] 5.1 Implement `require_admin` dependency and admin router setup
    - Create `backend/src/modules/identity/api/admin_router.py`
    - Implement `require_admin` dependency that checks `current_user.role == UserRole.ADMIN` and raises HTTP 403 if not
    - Set up the admin APIRouter with prefix `/api/admin`
    - _Requirements: 1.1, 1.2_

  - [ ]* 5.2 Write property tests for role-based access enforcement
    - **Property 1: Role-based access enforcement** — Non-admin users get 403, admin users get access
    - **Property 2: Role field constraint** — Only "admin" or "user" accepted
    - **Property 3: Default role assignment** — New OAuth users get "user" role (except super admin)
    - Create `backend/tests/admin/test_role_properties.py`
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 5.3 Implement whitelist admin endpoints
    - Add `POST /api/admin/whitelist` — Add whitelist entry
    - Add `DELETE /api/admin/whitelist/{id}` — Remove whitelist entry
    - Add `GET /api/admin/whitelist` — List all entries (merged file + DB)
    - Create request/response schemas in `backend/src/modules/identity/api/schemas.py`
    - Wire audit logging into add/remove operations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.1_

  - [x] 5.4 Implement OAuth config admin endpoints
    - Add `POST /api/admin/oauth/config` — Update OAuth credentials (with validation)
    - Add `GET /api/admin/oauth/config` — Get current config (masked secret)
    - Wire audit logging into update operation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 6.1, 6.2, 6.3, 7.2_

  - [x] 5.5 Implement user management and audit log endpoints
    - Add `GET /api/admin/users` — List all users with roles
    - Add `PATCH /api/admin/users/{id}/role` — Change user role
    - Add `GET /api/admin/audit-logs` — Paginated audit logs with filters
    - Wire audit logging into role change operations
    - _Requirements: 2.4, 7.3, 7.4, 8.7_

  - [x] 5.6 Implement super admin bootstrap logic
    - Add startup event/lifespan handler that calls `RoleService.ensure_super_admin()` using `AUTH_SUPER_ADMIN_EMAIL` env var
    - Modify user auto-provisioning in `AuthService` to assign admin role when email matches super admin
    - Log warning if no super admin configured and no admin exists
    - Update `backend/src/modules/identity/infrastructure/config.py` to add `super_admin_email` setting
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 5.7 Update identity module DI container
    - Update `backend/src/modules/identity/container.py` to register new repositories and services
    - Add dependency functions for `WhitelistRepository`, `OAuthConfigRepository`, `AuditLogRepository`, `RoleService`, `WhitelistManager`, `OAuthConfigManager`, `AuditService`
    - Register admin router in `backend/src/main.py`
    - _Requirements: 1.1, 3.1, 5.1, 7.1_

- [x] 6. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend admin panel implementation
  - [x] 7.1 Create admin API client and types
    - Create `frontend/src/lib/api/admin.ts` with typed API functions for all admin endpoints
    - Define TypeScript types/interfaces for whitelist entries, OAuth config, audit logs, user roles
    - Create Zod schemas for form validation (`frontend/src/lib/api/admin-schemas.ts`)
    - _Requirements: 8.1, 8.2, 8.5_

  - [x] 7.2 Implement admin route guard and layout
    - Create `frontend/src/app/(dashboard)/admin/layout.tsx` with role-based access check
    - Redirect non-admin users to the main dashboard page
    - Add admin navigation section to the app sidebar (conditionally rendered for admin users)
    - _Requirements: 8.1, 8.8_

  - [x] 7.3 Implement whitelist management page
    - Create `frontend/src/app/(dashboard)/admin/whitelist/page.tsx`
    - Create `frontend/src/components/admin/whitelist-table.tsx` — Data table with columns: value, type, added-by, date
    - Create `frontend/src/components/admin/whitelist-add-form.tsx` — Inline form with Zod validation for email/domain pattern
    - Implement delete action with confirmation dialog
    - Mark file-based entries as read-only with visual indicator
    - _Requirements: 8.2, 8.3, 8.4, 9.4_

  - [x] 7.4 Implement OAuth configuration page
    - Create `frontend/src/app/(dashboard)/admin/oauth/page.tsx`
    - Create `frontend/src/components/admin/oauth-config-form.tsx` — Form showing current config with masked secret, update form with validation
    - Display validation feedback from backend (Google discovery check)
    - _Requirements: 8.5, 8.6_

  - [x] 7.5 Implement user management page
    - Create `frontend/src/app/(dashboard)/admin/users/page.tsx`
    - Create `frontend/src/components/admin/user-role-select.tsx` — Dropdown for role changes with confirmation dialog
    - Display all users in a table with role column
    - _Requirements: 8.7_

  - [x] 7.6 Implement audit log viewer page
    - Create `frontend/src/app/(dashboard)/admin/audit-logs/page.tsx`
    - Create `frontend/src/components/admin/audit-log-table.tsx` — Paginated table with date range picker and action type filter
    - _Requirements: 7.4, 8.1_

  - [ ]* 7.7 Write frontend tests for admin components
    - Create `frontend/src/__tests__/admin/admin-guard.test.tsx` — Route guard redirect behavior
    - Create `frontend/src/__tests__/admin/whitelist-page.test.tsx` — Whitelist table and form interactions
    - Create `frontend/src/__tests__/admin/oauth-page.test.tsx` — OAuth form validation and masking
    - Create `frontend/src/__tests__/admin/user-management.test.tsx` — Role change interactions
    - Use Vitest + fast-check for pure utility functions (masking, validation)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI + SQLModel + Hypothesis) and the frontend uses TypeScript (Next.js + shadcn/ui + Vitest + fast-check)
- All new backend code extends the existing `identity` module following the established layered architecture pattern
- The existing `WhitelistService` and `WhitelistLoader` are preserved for backward compatibility

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["3.1", "3.2", "3.5", "3.7"] },
    { "id": 3, "tasks": ["3.3", "3.4", "3.6", "3.8"] },
    { "id": 4, "tasks": ["5.1", "5.6"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "5.5", "5.7"] },
    { "id": 6, "tasks": ["7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.4", "7.5", "7.6"] },
    { "id": 8, "tasks": ["7.7"] }
  ]
}
```
