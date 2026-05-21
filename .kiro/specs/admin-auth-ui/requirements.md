# Requirements Document

## Introduction

Admin Auth UI defines the complete UI/UX frontend design for the VroomHR admin authentication management panel. The feature covers all four admin pages (Whitelist, OAuth, Users, Audit Logs) with responsive layouts, accessibility compliance (WCAG 2.1 AA), consistent interaction patterns, and Vietnamese-language interface elements. The target users are non-technical HR staff who need a clear, simple interface to manage authentication settings without technical knowledge.

This spec builds upon the existing partial implementation (admin layout, whitelist-table, whitelist-add-form, oauth-config-form, user-role-select, audit-log-table) and defines the complete UI/UX requirements for production readiness.

## Glossary

- **Admin_Panel**: The web-based administration interface accessible at `/admin/*` routes, visible only to users with the Admin role
- **Admin_Page_Layout**: The shared layout structure wrapping all admin pages, including page header, breadcrumbs, and content area within the existing dashboard sidebar
- **Whitelist_Page**: The admin page at `/admin/whitelist` for managing email and domain whitelist entries
- **OAuth_Page**: The admin page at `/admin/oauth` for viewing and updating Google OAuth credentials
- **Users_Page**: The admin page at `/admin/users` for viewing all users and managing their roles
- **Audit_Logs_Page**: The admin page at `/admin/audit-logs` for viewing paginated, filterable audit trail entries
- **Confirmation_Dialog**: A modal dialog (AlertDialog) requiring explicit user confirmation before executing destructive or significant actions
- **Toast_Notification**: A non-blocking notification (sonner) displayed briefly to confirm action success or report errors
- **Empty_State**: A placeholder UI displayed when a data table or list contains zero entries
- **Loading_State**: A skeleton or spinner UI displayed while data is being fetched from the backend
- **Error_State**: A UI state displayed when a data fetch fails, offering a retry action
- **Source_Badge**: A visual indicator (Badge component) showing whether a whitelist entry originates from the file-based whitelist or the database
- **Responsive_Breakpoint**: The viewport width thresholds used for layout adaptation — mobile (<640px), tablet (640px–1024px), desktop (>1024px)
- **Inline_Validation**: Real-time form field validation feedback displayed as the user types or on blur, before form submission

## Requirements

### Requirement 1: Admin Page Layout Structure

**User Story:** As an HR administrator, I want a consistent page layout across all admin pages, so that I can navigate and understand the interface without confusion.

#### Acceptance Criteria

1. THE Admin_Page_Layout SHALL display a page header section containing a page title (h1, maximum 60 characters), a descriptive subtitle (maximum 120 characters), and an optional action buttons area aligned to the right of the title on viewports 640px and above
2. THE Admin_Page_Layout SHALL render all content within the existing dashboard sidebar layout without introducing a separate navigation structure
3. THE Admin_Page_Layout SHALL apply consistent vertical spacing (24px gap) between the page header section and the content sections
4. WHEN the viewport width is below 640px, THE Admin_Page_Layout SHALL stack page header elements vertically with the title first, subtitle second, and action buttons third, each on its own line
5. THE Admin_Page_Layout SHALL use Vietnamese language for all static text labels, headings, descriptions, and button labels
6. IF a page title exceeds the available horizontal space, THEN THE Admin_Page_Layout SHALL truncate the title with an ellipsis and display the full title on hover via a tooltip

### Requirement 2: Admin Navigation

**User Story:** As an HR administrator, I want clear navigation to all admin pages, so that I can quickly switch between whitelist, OAuth, users, and audit log management.

#### Acceptance Criteria

1. THE Admin_Panel SHALL display the admin navigation section in the sidebar only when the authenticated user has the Admin role
2. THE Admin_Panel SHALL apply a visually distinct background style to the currently active admin page link, differentiating it from inactive navigation links
3. WHILE the sidebar is in collapsed state, THE Admin_Panel SHALL display admin navigation items as icon-only buttons and show a tooltip containing the item label when the user hovers over each button
4. THE Admin_Panel SHALL group admin navigation items (Whitelist, OAuth, Users, Audit Logs) under a "Quản trị" section header separated from the main navigation by a horizontal divider element
5. IF a user without the Admin role navigates to any `/admin/*` URL, THEN THE Admin_Panel SHALL redirect the user to the root path (`/`)
6. WHILE the Admin_Panel is verifying the user role on an admin page, THE Admin_Panel SHALL display a loading indicator until the role check completes

### Requirement 3: Whitelist Page — Data Display

**User Story:** As an HR administrator, I want to see all whitelist entries in a clear table, so that I can understand who currently has login access.

#### Acceptance Criteria

1. THE Whitelist_Page SHALL display whitelist entries in a table with columns: Giá trị (value), Loại (type), Nguồn (source), Thêm bởi (added by), Ngày thêm (date added), and Hành động (actions)
2. THE Whitelist_Page SHALL display a Source_Badge for each entry indicating "File" (with a file icon) or "Database" origin
3. IF a whitelist entry originates from the file-based whitelist, THEN THE Whitelist_Page SHALL display the entry as read-only with a "Chỉ đọc" label in the Hành động column instead of a delete button
4. THE Whitelist_Page SHALL display the entry type as a Badge showing "Email" for exact_email entries and "Domain" for domain_pattern entries
5. WHEN the whitelist contains zero entries after loading completes, THE Whitelist_Page SHALL display an Empty_State with the message "Chưa có mục nào trong whitelist"
6. THE Whitelist_Page SHALL display a total entry count in the table header section representing the combined number of file-based and database entries currently shown
7. WHILE the viewport width is below 640px, THE Whitelist_Page SHALL render the table within a horizontally scrollable container so that no column content is truncated or hidden
8. WHILE whitelist data is being fetched from the API, THE Whitelist_Page SHALL display a loading indicator in place of the table
9. THE Whitelist_Page SHALL display entries sorted by creation date in descending order (newest first), with file-based entries (which have no creation date) appearing after database entries

### Requirement 4: Whitelist Page — Add Entry Interaction

**User Story:** As an HR administrator, I want to add new email addresses or domain patterns to the whitelist with immediate feedback, so that I can grant access quickly and confidently.

#### Acceptance Criteria

1. THE Whitelist_Page SHALL provide an inline form above the table with a text input (maximum 255 characters) and an "Thêm" (Add) button
2. IF the input value is neither a valid email address nor a valid domain pattern (format `@domain.com`), THEN THE Whitelist_Page SHALL display an inline validation error message below the input field before submission is allowed
3. WHEN the form is submitted with a valid value, THE Whitelist_Page SHALL display a loading spinner on the submit button, disable both the input field and the submit button, and prevent duplicate submissions until the request completes or 30 seconds elapse
4. WHEN the backend returns a successful response, THE Whitelist_Page SHALL display a Toast_Notification indicating the added entry value and refresh the table data
5. IF the backend returns an HTTP 409 Conflict (duplicate entry), THEN THE Whitelist_Page SHALL display a Toast_Notification with the error message "Mục này đã tồn tại trong whitelist"
6. IF the backend returns an HTTP 422 (invalid format), THEN THE Whitelist_Page SHALL display the backend-provided validation error inline below the input field
7. WHEN the add operation completes successfully, THE Whitelist_Page SHALL clear the input field and return focus to the input
8. IF the backend returns an unexpected error (network failure, timeout, or HTTP 5xx), THEN THE Whitelist_Page SHALL display a Toast_Notification with an error message indicating the operation failed and re-enable the form controls

### Requirement 5: Whitelist Page — Delete Entry Interaction

**User Story:** As an HR administrator, I want to remove whitelist entries with a confirmation step, so that I do not accidentally revoke someone's access.

#### Acceptance Criteria

1. THE Whitelist_Page SHALL display a delete button (trash icon) for each database-sourced entry and SHALL NOT display a delete button for file-sourced entries
2. WHEN the user clicks the delete button, THE Whitelist_Page SHALL open a Confirmation_Dialog stating the entry value and warning that the action cannot be undone
3. THE Confirmation_Dialog SHALL display "Xác nhận xóa" as the title and include the entry value in the description text
4. WHEN the user confirms deletion, THE Whitelist_Page SHALL display a loading state on the confirm button and disable both dialog buttons until the request completes
5. WHEN the backend returns a successful deletion response, THE Whitelist_Page SHALL close the dialog, display a success Toast_Notification indicating the removed entry value, and refresh the table data
6. IF the backend returns an error during deletion, THEN THE Whitelist_Page SHALL display an error Toast_Notification indicating the failure reason, keep the dialog open, re-enable both dialog buttons, and remove the loading state from the confirm button

### Requirement 6: OAuth Configuration Page — Display

**User Story:** As an HR administrator, I want to see the current OAuth configuration clearly, so that I can verify the authentication setup is correct.

#### Acceptance Criteria

1. THE OAuth_Page SHALL display the current OAuth configuration in a Card component showing: Client ID (full value), Client Secret (masked with asterisk characters showing only the last 4 characters), and Redirect URI (full value)
2. THE OAuth_Page SHALL display a Badge indicating the configuration source ("Database" or "Environment")
3. IF the OAuth configuration includes an `updated_at` timestamp, THEN THE OAuth_Page SHALL display the last updated date and time formatted in the user's browser locale
4. IF a configuration field value is null or an empty string, THEN THE OAuth_Page SHALL display italic placeholder text "Chưa cấu hình" in place of that field's value
5. THE OAuth_Page SHALL use a monospace font for the Client ID, Client Secret (masked), and Redirect URI values to improve readability of long strings
6. WHILE the viewport width is below 640px, THE OAuth_Page SHALL stack the configuration fields vertically in a single column instead of the two-column grid layout
7. WHILE the OAuth configuration is being fetched from the API, THE OAuth_Page SHALL display a loading spinner indicator
8. IF the API request to fetch OAuth configuration fails, THEN THE OAuth_Page SHALL display an error message describing the failure and a retry action that re-fetches the configuration

### Requirement 7: OAuth Configuration Page — Update Form

**User Story:** As an HR administrator, I want to update OAuth credentials with validation before submission, so that I do not accidentally break the login system.

#### Acceptance Criteria

1. THE OAuth_Page SHALL provide an update form in a separate Card below the current configuration display, with fields for Client ID (max 255 characters), Client Secret (max 500 characters), and Redirect URI (max 500 characters)
2. THE OAuth_Page SHALL mark all three fields as required with a red asterisk indicator
3. THE OAuth_Page SHALL validate Client ID as non-empty, Client Secret as non-empty, and Redirect URI as a valid URL format using Inline_Validation displayed on blur, and SHALL re-validate all fields on form submission before sending the request
4. WHEN the form is submitted with valid inputs, THE OAuth_Page SHALL display a loading spinner on the submit button and disable all form inputs and the Reset button until the request completes
5. WHEN the backend returns a successful response, THE OAuth_Page SHALL display a success Toast_Notification, update the current configuration display with the returned values, and reset all form fields to empty
6. IF the backend returns an HTTP 400 (validation failed against Google), THEN THE OAuth_Page SHALL display the backend-provided error message in a destructive alert banner above the form without clearing the form fields
7. IF the backend returns a non-400 error (network failure, HTTP 500, or other unexpected status), THEN THE OAuth_Page SHALL display an error Toast_Notification with a generic failure message
8. THE OAuth_Page SHALL provide a "Reset" button that clears all form fields to empty and dismisses any visible error banner
9. THE OAuth_Page SHALL use `type="password"` for the Client Secret input field to prevent shoulder-surfing

### Requirement 8: Users Page — Data Display

**User Story:** As an HR administrator, I want to see all system users with their roles and status, so that I can manage access permissions.

#### Acceptance Criteria

1. THE Users_Page SHALL display users in a table with columns: Avatar, Tên (name), Email, Vai trò (role), Trạng thái (status), and Đăng nhập lần cuối (last login)
2. THE Users_Page SHALL display user avatars as circular images with a text fallback showing the user's first 2 initials (uppercase, derived from the first character of each name part)
3. THE Users_Page SHALL display the user's role as an interactive Select dropdown with the options "admin" and "user", allowing role changes
4. WHEN the user selects a new role from the dropdown, THE Users_Page SHALL display a confirmation dialog stating the target user name and the new role before applying the change
5. THE Users_Page SHALL display user status as a Badge showing "Hoạt động" (active) when `is_active` is true or "Không hoạt động" (inactive) when `is_active` is false
6. THE Users_Page SHALL display the last login date formatted in Vietnamese locale (dd/MM/yyyy HH:mm), or a dash character ("—") if the user has never logged in
7. WHEN the user list is loading, THE Users_Page SHALL display 5 skeleton rows matching the table column layout
8. WHEN the user list is empty after a successful fetch, THE Users_Page SHALL display an Empty_State with the message "Không có người dùng nào"
9. IF the user list API request fails, THEN THE Users_Page SHALL display an error message indicating the data could not be loaded
10. WHEN the viewport width is below 640px, THE Users_Page SHALL hide the Avatar and Đăng nhập lần cuối columns to fit the table on smaller screens

### Requirement 9: Users Page — Role Change Interaction

**User Story:** As an HR administrator, I want to change user roles with a confirmation step, so that I do not accidentally grant or revoke admin access.

#### Acceptance Criteria

1. WHEN the administrator selects a different role from the dropdown, THE Users_Page SHALL open a Confirmation_Dialog before executing the change
2. IF the role change is a promotion to Admin, THEN THE Confirmation_Dialog SHALL describe that the user will gain full system management access including whitelist, OAuth, and user management
3. IF the role change is a demotion to User, THEN THE Confirmation_Dialog SHALL describe that the user will lose admin panel access
4. THE Confirmation_Dialog SHALL include the target user's name and email in the description text
5. WHEN the user confirms the role change, THE Users_Page SHALL display a loading state on the confirm button and disable both dialog buttons until the request completes
6. WHEN the backend returns a successful response, THE Users_Page SHALL close the dialog, display a success Toast_Notification, and refresh the user list
7. IF the backend returns an HTTP 400 (last admin or super admin protected), THEN THE Users_Page SHALL close the dialog, display an error Toast_Notification with the specific error message, and revert the dropdown to the original role value
8. IF the backend returns an HTTP 404 (user not found), THEN THE Users_Page SHALL close the dialog, display an error Toast_Notification, and refresh the user list
9. WHEN the user cancels the Confirmation_Dialog, THE Users_Page SHALL revert the dropdown to the original role value without making any API request

### Requirement 10: Audit Logs Page — Data Display and Filtering

**User Story:** As an HR administrator, I want to view and filter the audit trail, so that I can track who made configuration changes and when.

#### Acceptance Criteria

1. THE Audit_Logs_Page SHALL display audit entries in a table with columns: Thời gian (timestamp displayed in "DD/MM/YYYY HH:mm" format using the browser's local timezone), Admin (admin email), Hành động (action type), and Chi tiết (details)
2. THE Audit_Logs_Page SHALL display the action type as a color-coded Badge: green for whitelist_add, red for whitelist_remove, gray for oauth_update, and outline for role_change
3. THE Audit_Logs_Page SHALL provide a filter section above the table with: action type dropdown defaulting to "Tất cả" (options: Tất cả, Thêm whitelist, Xóa whitelist, Cập nhật OAuth, Thay đổi vai trò), start date input (initially empty), and end date input (initially empty)
4. WHEN a filter value changes, THE Audit_Logs_Page SHALL reset pagination to page 1 and re-fetch data with the updated filters
5. THE Audit_Logs_Page SHALL constrain the Chi tiết column to a maximum width of 200px, truncate overflowing text with an ellipsis (CSS text-overflow), and show the full text on hover via a title attribute
6. WHEN the audit log contains zero entries matching the current filters, THE Audit_Logs_Page SHALL display an Empty_State with the message "Không có bản ghi nào"
7. WHEN the viewport width is below 640px, THE Audit_Logs_Page SHALL stack the filter controls vertically
8. THE Audit_Logs_Page SHALL display entries sorted by timestamp in descending order (newest first)
9. IF the user selects an end date that is earlier than the start date, THEN THE Audit_Logs_Page SHALL display a validation error message below the date filters indicating the invalid range and SHALL NOT submit the filter request

### Requirement 11: Pagination

**User Story:** As an HR administrator, I want paginated data tables, so that I can browse large datasets without performance issues.

#### Acceptance Criteria

1. THE Audit_Logs_Page SHALL display pagination controls with "Trước" (Previous) and "Sau" (Next) buttons below the table
2. THE Audit_Logs_Page SHALL display pagination metadata in the format "Trang {current} / {total_pages} ({total_records} bản ghi)" between or adjacent to the navigation buttons
3. WHEN the user is on the first page, THE Audit_Logs_Page SHALL disable the "Trước" button and apply a visually muted style indicating it is non-interactive
4. WHEN the user is on the last page, THE Audit_Logs_Page SHALL disable the "Sau" button and apply a visually muted style indicating it is non-interactive
5. THE Audit_Logs_Page SHALL use a page size of 20 entries per page
6. WHEN the user clicks the "Sau" button, THE Audit_Logs_Page SHALL fetch and display the next page of audit log entries
7. WHEN the user clicks the "Trước" button, THE Audit_Logs_Page SHALL fetch and display the previous page of audit log entries
8. WHEN pagination buttons are clicked during a loading state, THE Audit_Logs_Page SHALL ignore the click
9. IF the total number of audit log entries is less than or equal to the page size, THEN THE Audit_Logs_Page SHALL disable both pagination buttons

### Requirement 12: Loading States

**User Story:** As an HR administrator, I want clear loading indicators, so that I know the system is working when I perform actions.

#### Acceptance Criteria

1. WHEN data is being fetched for the Whitelist_Page, THE Whitelist_Page SHALL display a horizontally and vertically centered loading message "Đang tải..." within the table content area
2. WHEN data is being fetched for the Users_Page, THE Users_Page SHALL display 5 skeleton rows matching the table column structure (avatar, name, email, role, status, last login)
3. WHEN data is being fetched for the Audit_Logs_Page, THE Audit_Logs_Page SHALL display a centered "Đang tải..." message spanning all columns within the table body
4. WHEN data is being fetched for the OAuth_Page, THE OAuth_Page SHALL display a centered spinning loader icon with a screen-reader-accessible label indicating the loading state
5. WHEN a form submission is in progress, THE Admin_Panel SHALL display a spinning Loader2 icon on the submit button, disable all form inputs, and disable the submit button to prevent duplicate submissions
6. WHEN a form submission completes (success or failure), THE Admin_Panel SHALL re-enable all form inputs and the submit button
7. THE Admin_Panel SHALL display a refresh button on the Whitelist_Page and Users_Page
8. WHILE data is loading on a page with a refresh button, THE Admin_Panel SHALL show a spinning animation on the refresh button icon and disable the refresh button to prevent concurrent fetch requests

### Requirement 13: Error States

**User Story:** As an HR administrator, I want clear error messages when something goes wrong, so that I can understand the problem and retry.

#### Acceptance Criteria

1. WHEN a data fetch fails on the OAuth_Page, THE OAuth_Page SHALL display an error icon, the error message from the API response body, and a "Thử lại" (Try again) link that re-triggers the data fetch
2. WHEN a data fetch fails on the Users_Page, THE Users_Page SHALL display an error alert banner with the error message from the API response body
3. WHEN a form submission fails with a server error (HTTP 5xx) or a non-validation error (HTTP 409, HTTP 404), THE Admin_Panel SHALL display the error message from the API response via a Toast_Notification that auto-dismisses after 5 seconds
4. WHEN a form submission fails with a validation error (HTTP 400), THE OAuth_Page SHALL display the error in a destructive-styled alert banner above the form that persists until dismissed or the form is reset
5. IF the admin session expires (HTTP 401) during any admin operation, THEN THE Admin_Panel SHALL redirect the user to the login page
6. IF the admin role is revoked (HTTP 403) during any admin operation, THEN THE Admin_Panel SHALL redirect the user to the application root page
7. IF a network error occurs (no response received) during any admin operation, THEN THE Admin_Panel SHALL display a Toast_Notification with an error message indicating a network connectivity problem and the original request SHALL not be retried automatically

### Requirement 14: Responsive Design

**User Story:** As an HR administrator, I want the admin panel to work on my tablet and phone, so that I can manage settings from any device.

#### Acceptance Criteria

1. WHEN the viewport width is below 640px (mobile), THE Admin_Panel SHALL collapse the sidebar to icon-only mode (maximum 64px wide) and allow the main content area to occupy the remaining viewport width
2. WHEN the viewport width is between 640px and 1024px (tablet), THE Admin_Panel SHALL display the sidebar in collapsed icon-only mode by default and provide a visible toggle button to expand or collapse the sidebar
3. WHEN the viewport width is above 1024px (desktop), THE Admin_Panel SHALL display the sidebar in expanded mode by default
4. THE Admin_Panel SHALL ensure all data tables are horizontally scrollable within their container when the table content exceeds the available container width, without causing the page itself to scroll horizontally
5. WHILE the viewport width is below 640px, THE Admin_Panel SHALL ensure all form inputs and buttons have a minimum touch target size of 44x44 CSS pixels
6. THE Admin_Panel SHALL ensure the Confirmation_Dialog is centered within the viewport, has a maximum width of 90vw and a maximum height of 90vh, and does not overflow the viewport on any screen size
7. THE Admin_Panel SHALL support viewports with a minimum width of 320px, ensuring all content remains accessible and no interactive elements are clipped or unreachable

### Requirement 15: Accessibility (WCAG 2.1 AA)

**User Story:** As an HR administrator who uses assistive technology, I want the admin panel to be fully accessible, so that I can perform all admin tasks regardless of my abilities.

#### Acceptance Criteria

1. THE Admin_Panel SHALL ensure all interactive elements (buttons, links, form inputs, select dropdowns) are reachable and operable via keyboard navigation in a logical tab order matching the visual layout
2. THE Admin_Panel SHALL provide visible focus indicators on all interactive elements that meet WCAG 2.1 AA contrast requirements (3:1 minimum against adjacent colors)
3. THE Admin_Panel SHALL associate all form inputs with visible labels using the `<label>` element or `aria-label` attribute, and SHALL associate validation error messages with their corresponding inputs using `aria-describedby`
4. THE Admin_Panel SHALL use `aria-hidden="true"` on decorative icons that do not convey meaning
5. THE Admin_Panel SHALL provide descriptive `aria-label` attributes on icon-only buttons (delete buttons, refresh buttons, sidebar toggle)
6. THE Admin_Panel SHALL ensure all text content meets WCAG 2.1 AA color contrast requirements (4.5:1 for normal text, 3:1 for large text)
7. WHEN a Confirmation_Dialog opens, THE Admin_Panel SHALL trap keyboard focus within the dialog and return focus to the triggering element when the dialog closes
8. THE Admin_Panel SHALL use semantic HTML landmarks (`<nav>`, `<main>`, `<header>`) and ARIA roles to support screen reader navigation
9. THE Admin_Panel SHALL announce Toast_Notifications to screen readers using `role="status"` or an ARIA live region
10. THE Admin_Panel SHALL provide the sidebar navigation with an `aria-label="Điều hướng chính"` for screen reader identification
11. WHEN loading states or error states change dynamically, THE Admin_Panel SHALL announce the state change to screen readers using an ARIA live region with `aria-live="polite"`

### Requirement 16: Visual Indicators for Data Source

**User Story:** As an HR administrator, I want to clearly distinguish between file-based and database-managed whitelist entries, so that I understand which entries I can modify.

#### Acceptance Criteria

1. THE Whitelist_Page SHALL display file-sourced entries with an `outline` variant Badge containing a FileText icon and the text "File"
2. THE Whitelist_Page SHALL display database-sourced entries with a `default` variant Badge with the text "Database"
3. THE Whitelist_Page SHALL visually disable the action column for file-sourced entries by showing "Chỉ đọc" text in muted-foreground color instead of a delete button
4. THE OAuth_Page SHALL display a `default` variant Badge with the text "Database" when the configuration is sourced from the database, and a `secondary` variant Badge with the text "Environment" when sourced from environment variables
5. THE Whitelist_Page SHALL include an `aria-label` or accessible text on each source Badge so that screen reader users can identify the data source without relying on visual styling alone

### Requirement 17: Confirmation Dialogs for Destructive Actions

**User Story:** As an HR administrator, I want confirmation prompts before destructive actions, so that I do not accidentally delete entries or change roles.

#### Acceptance Criteria

1. WHEN the user initiates a whitelist entry deletion, THE Admin_Panel SHALL open a Confirmation_Dialog before executing the delete operation
2. WHEN the user selects a different role for any user, THE Admin_Panel SHALL open a Confirmation_Dialog before executing the role change
3. THE Confirmation_Dialog SHALL use a destructive-styled confirm button (red background, `bg-destructive` class) for delete operations and a primary-styled confirm button for role change operations
4. THE Confirmation_Dialog SHALL display a title indicating the action type (e.g., "Xác nhận xóa" for deletion, "Xác nhận thay đổi" for role change) and include the specific affected item identifier (the entry value for whitelist deletions, the user's display name for role changes) in the description text
5. THE Confirmation_Dialog SHALL provide a "Hủy" (Cancel) button that closes the dialog without performing the action and without modifying any application state
6. WHEN a Confirmation_Dialog is open and the user presses the Escape key or clicks the backdrop overlay, THE Admin_Panel SHALL close the dialog without performing the action
7. WHILE a confirmed destructive action request is in progress, THE Confirmation_Dialog SHALL display a loading state on the confirm button and disable both the confirm and cancel buttons until the request completes or fails

### Requirement 18: Real-Time Validation Feedback

**User Story:** As an HR administrator, I want immediate feedback when I enter invalid data, so that I can correct mistakes before submitting.

#### Acceptance Criteria

1. WHEN the user submits the Whitelist_Page add form, IF the input value is neither a valid email address nor a valid Domain_Pattern, THEN THE Whitelist_Page SHALL display an error message below the input field indicating the value must be a valid email (user@domain.com) or domain pattern (@domain.com)
2. WHEN a field in the OAuth_Page update form loses focus (blur), THE OAuth_Page SHALL validate that field against its constraints (client_id: non-empty and at most 255 characters; client_secret: non-empty and at most 500 characters; redirect_uri: non-empty, valid URL starting with `https://`, at most 500 characters) and display a field-level error message below the input if validation fails
3. THE Admin_Panel SHALL display validation error messages in the destructive color text directly below the associated input field
4. WHEN the user modifies the value of a field that is displaying a validation error, THE Admin_Panel SHALL clear the validation error message for that field
5. THE OAuth_Page SHALL validate that the Redirect URI field contains a valid URL starting with `https://` and not exceeding 500 characters
6. IF the Admin_API returns a validation error (HTTP 422 or HTTP 409) after form submission, THEN THE Admin_Panel SHALL display the server-provided error message in the destructive color within the form, without clearing user input from the form fields
