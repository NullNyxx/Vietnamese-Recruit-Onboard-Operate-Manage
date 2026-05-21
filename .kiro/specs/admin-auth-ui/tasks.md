# Implementation Plan: Admin Auth UI

## Overview

This plan closes the gaps between the existing partial implementation and the full requirements for the VroomHR admin authentication management panel. Tasks focus on modifying existing files to add Vietnamese text, accessibility improvements, responsive design, validation enhancements, and property-based tests. The backend API is already complete — all work is frontend-only.

## Tasks

- [x] 1. Update validation schemas and utility functions
  - [x] 1.1 Update `admin-schemas.ts` with Vietnamese error messages and https:// validation
    - Modify `frontend/src/lib/api/admin-schemas.ts`
    - Change whitelist schema error messages to Vietnamese ("Giá trị phải có ít nhất 3 ký tự", "Phải là email hợp lệ (user@domain.com) hoặc domain (@domain.com)")
    - Add `.refine()` to `redirect_uri` requiring `https://` prefix with Vietnamese error "Redirect URI phải bắt đầu bằng https://"
    - Change all OAuth schema error messages to Vietnamese ("Client ID không được để trống", "Client Secret không được để trống", "Redirect URI không được để trống", "Redirect URI phải là URL hợp lệ")
    - Change role schema error message to Vietnamese ("Vai trò phải là 'admin' hoặc 'user'")
    - _Requirements: 7.3, 18.2, 18.5_

  - [x] 1.2 Create shared utility functions file
    - Create `frontend/src/lib/utils/format.ts`
    - Implement `formatDateVN(dateStr: string | null): string` — returns Vietnamese locale formatted date or "—" for null
    - Implement `getInitials(name: string): string` — returns ≤2 uppercase characters from name parts
    - Implement `validateDateRange(startDate: string, endDate: string): boolean` — returns false if end < start
    - Export all functions for use in components and tests
    - _Requirements: 8.2, 8.6, 10.9_

- [x] 2. Update OAuth components with Vietnamese text and validation improvements
  - [x] 2.1 Update `OAuthConfigForm` with Vietnamese text, blur validation, and placeholder
    - Modify `frontend/src/components/admin/oauth-config-form.tsx`
    - Replace all English text with Vietnamese: "Cấu hình hiện tại", "Thông tin xác thực Google OAuth đang sử dụng", "Cập nhật thông tin", "Gửi thông tin xác thực mới. Chúng sẽ được xác minh với Google trước khi áp dụng."
    - Change button labels: "Cập nhật cấu hình", "Đặt lại"
    - Change form labels: "Client ID", "Client Secret", "Redirect URI" (keep technical terms)
    - Change form descriptions to Vietnamese
    - Replace "Not configured" placeholder with italic "Chưa cấu hình"
    - Add `mode: "onBlur"` to `useForm` options for blur validation
    - Change success toast to Vietnamese: "Đã cập nhật cấu hình OAuth"
    - _Requirements: 6.4, 7.3, 7.5, 18.2_

  - [x] 2.2 Update OAuth page with Vietnamese text and retry button styling
    - Modify `frontend/src/app/(dashboard)/admin/oauth/page.tsx`
    - Replace page title with "Cấu hình OAuth"
    - Replace subtitle with "Quản lý thông tin xác thực Google OAuth cho đăng nhập"
    - Replace loading screen-reader text with Vietnamese: "Đang tải cấu hình OAuth..."
    - Replace "Try again" link with "Thử lại" styled as a Button with `variant="link"`
    - Add `aria-live="polite"` region wrapping the loading/error/content states
    - _Requirements: 6.7, 6.8, 13.1, 15.11_

  - [ ]* 2.3 Write property test for OAuth configuration validation (Property 2)
    - **Property 2: OAuth configuration validation correctness**
    - Create test in `frontend/src/__tests__/admin/admin-validation.property.test.ts`
    - Use fast-check to generate valid objects (non-empty client_id ≤255, non-empty client_secret ≤500, https:// URL ≤500) and verify schema accepts
    - Generate invalid objects (empty fields, non-https URLs, oversized strings) and verify schema rejects with appropriate field errors
    - **Validates: Requirements 7.3, 18.2, 18.5**

- [x] 3. Update Whitelist components with accessibility and responsive improvements
  - [x] 3.1 Add `aria-label` to source badges and mobile scroll wrapper in `WhitelistTable`
    - Modify `frontend/src/components/admin/whitelist-table.tsx`
    - Add `aria-label="Nguồn: File"` to the file source Badge
    - Add `aria-label="Nguồn: Database"` to the database source Badge
    - Wrap the `<Table>` in a `<div className="overflow-x-auto">` for mobile horizontal scrolling
    - _Requirements: 3.7, 16.5, 15.5_

  - [x] 3.2 Add entry count display and aria-live region to Whitelist page
    - Modify `frontend/src/app/(dashboard)/admin/whitelist/page.tsx`
    - Verify entry count is displayed in table header (already present — confirm format matches requirement)
    - Add `aria-live="polite"` wrapper around the table content area to announce loading/empty state changes
    - _Requirements: 3.6, 15.11_

  - [ ]* 3.3 Write property test for whitelist entry validation (Property 1)
    - **Property 1: Whitelist entry validation correctness**
    - Add test to `frontend/src/__tests__/admin/admin-validation.property.test.ts`
    - Use fast-check `fc.emailAddress()` to generate valid emails and verify schema accepts
    - Generate valid domain patterns (`@` + `fc.domain()`) and verify schema accepts
    - Generate arbitrary strings that match neither format and verify schema rejects
    - **Validates: Requirements 4.2, 18.1**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Update Users page with responsive column hiding and error state improvements
  - [x] 5.1 Add mobile column hiding and email in role change dialog
    - Modify `frontend/src/app/(dashboard)/admin/users/page.tsx`
    - Add `className="hidden sm:table-cell"` to Avatar `<TableHead>` and `<TableCell>`
    - Add `className="hidden sm:table-cell"` to "Đăng nhập lần cuối" `<TableHead>` and `<TableCell>`
    - Update `colSpan` in empty state to account for hidden columns on mobile
    - Add `aria-live="polite"` wrapper around the table body area
    - _Requirements: 8.10, 14.4, 15.11_

  - [x] 5.2 Add user email to role change confirmation dialog
    - Modify `frontend/src/components/admin/user-role-select.tsx`
    - Add `userEmail` prop to `UserRoleSelectProps` interface
    - Include user email in the confirmation dialog description text
    - Update the Users page to pass `userEmail={user.email}` to `UserRoleSelect`
    - _Requirements: 9.4_

  - [ ]* 5.3 Write property test for user initials derivation (Property 3)
    - **Property 3: User initials derivation**
    - Add test to `frontend/src/__tests__/admin/admin-validation.property.test.ts`
    - Use fast-check to generate arrays of non-empty strings joined by spaces
    - Verify `getInitials` returns a string of at most 2 uppercase characters
    - Verify each character is the first character of a space-separated name part
    - **Validates: Requirements 8.2**

- [x] 6. Update AuditLogTable with date range validation, mobile stacking, and details column
  - [x] 6.1 Add date range validation and mobile filter stacking to `AuditLogTable`
    - Modify `frontend/src/components/admin/audit-log-table.tsx`
    - Add date range validation: if endDate < startDate, display error message "Ngày kết thúc phải sau ngày bắt đầu" below the date filters and prevent API call
    - Change details column `max-w-[300px]` to `max-w-[200px]`
    - Add responsive classes to filter container: `flex flex-col sm:flex-row` for mobile stacking
    - Add `aria-live="polite"` to the table body area for screen reader announcements
    - _Requirements: 10.5, 10.7, 10.9, 15.11_

  - [ ]* 6.2 Write property test for date range validation (Property 5)
    - **Property 5: Date range validation**
    - Add test to `frontend/src/__tests__/admin/admin-validation.property.test.ts`
    - Use fast-check to generate pairs of dates
    - Verify that when endDate < startDate, validation rejects
    - Verify that when endDate >= startDate, validation accepts
    - **Validates: Requirements 10.9**

  - [ ]* 6.3 Write property test for date formatting (Property 4)
    - **Property 4: Date formatting round-trip**
    - Add test to `frontend/src/__tests__/admin/admin-validation.property.test.ts`
    - Use fast-check to generate valid Date objects mapped to ISO strings
    - Verify `formatDateVN` returns a non-empty string containing digits
    - Verify `formatDateVN(null)` returns "—"
    - **Validates: Requirements 8.6**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Accessibility and responsive polish across all components
  - [x] 8.1 Add aria-live regions and focus management to WhitelistAddForm
    - Modify `frontend/src/components/admin/whitelist-add-form.tsx`
    - After successful add, return focus to the input field using `inputRef.current?.focus()`
    - Add `aria-describedby` linking the input to its error message element
    - _Requirements: 4.7, 15.3_

  - [x] 8.2 Add minimum touch target sizes for mobile
    - Modify `frontend/src/components/admin/whitelist-table.tsx` — ensure delete button has `min-h-[44px] min-w-[44px]` on mobile via `sm:h-8 sm:w-8 h-11 w-11`
    - Modify `frontend/src/components/admin/audit-log-table.tsx` — ensure pagination buttons have minimum 44px touch targets on mobile
    - _Requirements: 14.5_

  - [x] 8.3 Ensure horizontal scroll containers on all data tables
    - Verify `frontend/src/app/(dashboard)/admin/users/page.tsx` table wrapper has `overflow-x-auto`
    - Verify `frontend/src/components/admin/audit-log-table.tsx` table wrapper has `overflow-x-auto` (already has `rounded-md border` div)
    - Add `overflow-x-auto` where missing
    - _Requirements: 14.4_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document
- All modifications target existing files — no new page components need to be created
- The backend API is already fully implemented; all tasks are frontend-only
- Vietnamese text must be used for all user-facing strings
- fast-check (already in devDependencies) is used for property-based tests

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2", "3.1", "3.2"] },
    { "id": 2, "tasks": ["2.3", "3.3", "5.1", "5.2", "6.1"] },
    { "id": 3, "tasks": ["5.3", "6.2", "6.3", "8.1", "8.2", "8.3"] }
  ]
}
```
