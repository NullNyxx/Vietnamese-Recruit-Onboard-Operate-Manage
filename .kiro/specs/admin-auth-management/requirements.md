# Requirements Document

## Introduction

Admin Auth Management provides a web-based administration panel for VroomHR that allows non-technical HR staff to manage OAuth configuration and login whitelist entries without direct server access. The feature extends the existing Identity & Auth module with role-based access control, database-backed whitelist storage with domain pattern support, and encrypted OAuth credential management with hot-reload capabilities.

## Glossary

- **Admin_Panel**: The web-based administration interface accessible only to users with the Admin role
- **Admin_API**: The set of FastAPI endpoints under `/api/admin/` that serve the Admin_Panel
- **Whitelist_Manager**: The service responsible for managing email whitelist entries in the database, supporting both exact emails and domain patterns
- **OAuth_Config_Manager**: The service responsible for managing OAuth provider credentials (client_id, client_secret, redirect_uri) stored encrypted in the database
- **Super_Admin**: The first administrator bootstrapped via environment variable or CLI command, who can promote other users to Admin role
- **Admin**: A user with the `admin` role who can access the Admin_Panel to manage whitelist and OAuth configuration
- **Regular_User**: A user with the `user` role who can only access standard HR application features
- **Domain_Pattern**: A whitelist entry in the format `@domain.com` that allows all email addresses from that domain
- **Exact_Email**: A whitelist entry containing a full email address for individual access control
- **Encryption_Service**: The existing AES-256-GCM CryptoUtils used to encrypt sensitive credentials at rest

## Requirements

### Requirement 1: Role-Based Access Control

**User Story:** As a system administrator, I want users to have distinct roles (admin vs regular user), so that only authorized personnel can manage authentication configuration.

#### Acceptance Criteria

1. THE Admin_API SHALL enforce that only users with the Admin role can access admin endpoints
2. WHEN a user without the Admin role attempts to access an Admin_API endpoint, THE Admin_API SHALL return an HTTP 403 Forbidden response
3. THE User entity SHALL include a `role` field with values limited to `admin` or `user`
4. WHEN a new user is auto-provisioned via OAuth login, THE system SHALL assign the `user` role by default

### Requirement 2: Super Admin Bootstrap

**User Story:** As a system deployer, I want to designate the first administrator via environment variable, so that the system can be initially configured without a pre-existing admin UI.

#### Acceptance Criteria

1. WHEN the application starts and the `AUTH_SUPER_ADMIN_EMAIL` environment variable is set, THE system SHALL ensure a user with that email has the Admin role
2. WHEN the Super_Admin logs in for the first time, THE system SHALL auto-provision the user with the Admin role instead of the default `user` role
3. IF the `AUTH_SUPER_ADMIN_EMAIL` environment variable is not set and no Admin user exists in the database, THEN THE system SHALL log a warning at startup indicating no administrator is configured
4. WHEN an Admin promotes another user to Admin role, THE Admin_API SHALL persist the role change in the database

### Requirement 3: Whitelist Management API

**User Story:** As an HR administrator, I want to add and remove email addresses and domain patterns from the login whitelist via a web interface, so that I can control who has access without editing server files.

#### Acceptance Criteria

1. WHEN an Admin submits a valid email address, THE Whitelist_Manager SHALL add the Exact_Email entry to the database
2. WHEN an Admin submits a valid domain pattern (format: `@domain.com`), THE Whitelist_Manager SHALL add the Domain_Pattern entry to the database
3. WHEN an Admin removes a whitelist entry, THE Whitelist_Manager SHALL delete the entry from the database
4. WHEN an Admin requests the whitelist, THE Admin_API SHALL return all entries with their type (exact_email or domain_pattern), creation timestamp, and the Admin who added the entry
5. IF an Admin submits a duplicate whitelist entry, THEN THE Whitelist_Manager SHALL return an HTTP 409 Conflict response
6. IF an Admin submits an invalid email format or invalid domain pattern, THEN THE Whitelist_Manager SHALL return an HTTP 422 response with a descriptive validation error
7. WHEN a whitelist entry is added or removed, THE Whitelist_Manager SHALL update the in-memory whitelist cache within 1 second without requiring a server restart

### Requirement 4: Whitelist Email Matching with Domain Patterns

**User Story:** As an HR administrator, I want to whitelist entire company domains, so that all employees from a domain are automatically allowed to log in.

#### Acceptance Criteria

1. WHEN a user attempts to log in, THE Whitelist_Manager SHALL check the email against both Exact_Email entries and Domain_Pattern entries
2. WHEN a Domain_Pattern `@example.com` exists, THE Whitelist_Manager SHALL allow any email ending with `@example.com` to pass the whitelist check
3. THE Whitelist_Manager SHALL perform case-insensitive matching for both Exact_Email and Domain_Pattern entries
4. WHEN both the file-based whitelist and database whitelist are configured, THE Whitelist_Manager SHALL merge entries from both sources (union of both sets)

### Requirement 5: OAuth Credential Management API

**User Story:** As an HR administrator, I want to update OAuth client credentials via the admin panel, so that I can rotate secrets or reconfigure the OAuth provider without server access.

#### Acceptance Criteria

1. WHEN an Admin submits new OAuth credentials (client_id, client_secret, redirect_uri), THE OAuth_Config_Manager SHALL encrypt the client_secret using the Encryption_Service and store all credentials in the database
2. WHEN the Admin_API returns OAuth configuration, THE Admin_API SHALL mask the client_secret (showing only the last 4 characters) and return the full client_id and redirect_uri
3. WHEN OAuth credentials are updated in the database, THE OAuth_Config_Manager SHALL apply the new credentials to the running application within 5 seconds without requiring a server restart
4. THE OAuth_Config_Manager SHALL validate that client_id is non-empty and redirect_uri is a valid URL before persisting
5. IF OAuth credentials are not configured in the database, THEN THE system SHALL fall back to the environment variable values (`AUTH_GOOGLE_CLIENT_ID`, `AUTH_GOOGLE_CLIENT_SECRET`, `AUTH_GOOGLE_REDIRECT_URI`)
6. WHEN an Admin updates OAuth credentials, THE Admin_API SHALL log an audit entry recording the Admin user, timestamp, and the fields that were changed

### Requirement 6: OAuth Configuration Validation

**User Story:** As an HR administrator, I want the system to validate OAuth credentials before applying them, so that a misconfiguration does not lock all users out.

#### Acceptance Criteria

1. WHEN an Admin submits new OAuth credentials, THE OAuth_Config_Manager SHALL attempt a test connection to the Google OAuth discovery endpoint to verify the client_id is recognized
2. IF the validation test fails, THEN THE OAuth_Config_Manager SHALL return an HTTP 400 response with a descriptive error and not persist the invalid credentials
3. WHEN OAuth credentials are updated, THE OAuth_Config_Manager SHALL retain the previous working credentials until the new credentials are validated

### Requirement 7: Admin Audit Logging

**User Story:** As a system administrator, I want all admin actions to be logged, so that I can trace who made configuration changes and when.

#### Acceptance Criteria

1. WHEN an Admin adds or removes a whitelist entry, THE Admin_API SHALL create an audit log entry containing the Admin user email, action type, target entry, and timestamp
2. WHEN an Admin updates OAuth credentials, THE Admin_API SHALL create an audit log entry containing the Admin user email, action type, changed fields (without secret values), and timestamp
3. WHEN an Admin changes a user's role, THE Admin_API SHALL create an audit log entry containing the Admin user email, action type, target user email, old role, new role, and timestamp
4. THE Admin_API SHALL provide an endpoint to retrieve audit logs with pagination and filtering by action type and date range

### Requirement 8: Admin Panel Frontend

**User Story:** As a non-technical HR administrator, I want a clear and simple web interface to manage whitelist and OAuth settings, so that I can perform admin tasks without technical knowledge.

#### Acceptance Criteria

1. THE Admin_Panel SHALL display a navigation section accessible only when the logged-in user has the Admin role
2. THE Admin_Panel SHALL provide a whitelist management page showing all current entries in a table with columns for entry value, type, added-by, and date added
3. THE Admin_Panel SHALL provide an inline form to add new whitelist entries with real-time validation feedback
4. THE Admin_Panel SHALL provide a delete action for each whitelist entry with a confirmation dialog
5. THE Admin_Panel SHALL provide an OAuth configuration page showing the current client_id, masked client_secret, and redirect_uri
6. THE Admin_Panel SHALL provide a form to update OAuth credentials with validation feedback before submission
7. THE Admin_Panel SHALL display a user management page listing all users with their roles, allowing Admins to promote users to Admin or demote Admins to Regular_User
8. IF a non-admin user navigates to an Admin_Panel URL, THEN THE frontend SHALL redirect the user to the main application page

### Requirement 9: Backward Compatibility with File-Based Whitelist

**User Story:** As a system deployer, I want the existing file-based whitelist to continue working alongside the new database whitelist, so that the migration is non-breaking.

#### Acceptance Criteria

1. WHILE the `AUTH_WHITELIST_FILE_PATH` environment variable points to an existing file, THE Whitelist_Manager SHALL continue to load entries from the file-based whitelist
2. THE Whitelist_Manager SHALL treat the union of file-based entries and database entries as the effective whitelist
3. WHEN an entry exists in both the file-based whitelist and the database, THE Whitelist_Manager SHALL not create a duplicate and the database entry takes precedence for metadata display
4. THE Admin_Panel SHALL display file-based entries as read-only (not deletable via the UI) with a visual indicator showing their source
