# Implementation Plan: Gmail Frontend UI

## Overview

Implement the Gmail Frontend UI module for Vroom HR, providing HR users with a full-featured email interface integrated into the existing Next.js dashboard. The implementation follows the existing codebase patterns (client-side rendering, local state, fetch-based API client) and builds incrementally from API layer → core components → integration → polish.

## Tasks

- [x] 1. Set up Gmail API client and TypeScript interfaces
  - [x] 1.1 Create Gmail TypeScript interfaces in `frontend/src/lib/api/types.ts`
    - Add all Gmail-related interfaces: ConnectionStatus, ConnectionStatusResponse, ConnectResponse, EmailMessage, MessageBodyResponse, SendEmailRequest, SendEmailResponse, LabelRemoveRequest, SyncResponse, AttachmentMetadata, AttachmentsResponse
    - Add ApiError class definition
    - _Requirements: 14.3_

  - [x] 1.2 Create Gmail API client module at `frontend/src/lib/api/gmail.ts`
    - Implement typed functions: getStatus, connect, disconnect, syncEmails, getMessageBody, removeLabel, sendEmail, getAttachments
    - Follow the same pattern as existing `employees.ts` (fetch + handleResponse helper)
    - Handle error responses by throwing typed ApiError
    - _Requirements: 14.1, 14.2_

  - [x] 1.3 Export Gmail API client from barrel file `frontend/src/lib/api/index.ts`
    - Add `export * as gmailApi from "./gmail"` following existing pattern
    - _Requirements: 14.4_

- [x] 2. Implement Toast notification system and utility functions
  - [x] 2.1 Create ToastProvider component at `frontend/src/components/gmail/toast-provider.tsx`
    - Implement ToastContext with add/remove toast functions
    - Support success (auto-dismiss 5s) and error (persist until dismissed) variants
    - Position top-right, max 3 visible, stacked vertically
    - _Requirements: 12.3, 12.4_

  - [x] 2.2 Create utility functions for date formatting and file size formatting
    - Implement `formatRelativeDate` (Vietnamese: "Vừa xong", "X phút trước", "X giờ trước", "Hôm qua", "X ngày trước", dd/MM/yyyy)
    - Implement `formatFileSize` (B, KB, MB)
    - Implement `getLabelCategory` and `LABEL_COLORS` mapping
    - Place in `frontend/src/components/gmail/utils.ts`
    - _Requirements: 5.1, 5.4, 11.1_

- [x] 3. Checkpoint - Ensure API client and utilities compile correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Connection components
  - [x] 4.1 Create ConnectionPanel component at `frontend/src/components/gmail/connection-panel.tsx`
    - Display connected state: email address, green indicator, Disconnect button
    - Display disconnected state: prompt message, Connect Gmail button
    - Display token_expired state: warning message, Reconnect button
    - Display error state: error message with Retry button
    - Loading spinners on Connect/Disconnect buttons while in progress
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.4, 4.3_

  - [x] 4.2 Implement disconnect confirmation dialog
    - Show confirmation dialog when Disconnect is clicked
    - Only proceed with API call on confirm
    - _Requirements: 4.1, 4.2_

  - [ ]* 4.3 Write property test for route active state matching
    - **Property 1: Route active state matching**
    - **Validates: Requirements 1.3**

- [x] 5. Implement Email List and Sync components
  - [x] 5.1 Create EmailList component at `frontend/src/components/gmail/email-list.tsx`
    - Render each email with: sender name, sender email, subject, snippet (truncated 100 chars), relative date, paperclip icon for attachments, colored label badges
    - Sort emails by received_at descending (newest first)
    - Highlight selected email
    - Display skeleton loading state while fetching
    - Hide when not connected
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 5.2 Create SyncIndicator component at `frontend/src/components/gmail/sync-indicator.tsx`
    - Sync button triggers POST /api/gmail/sync
    - Display synced count on success and refresh email list
    - Handle 429 rate limit: show cooldown timer, disable button
    - Handle 409 not connected: refresh connection status
    - Spinning animation while sync in progress
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 5.3 Write property tests for email list rendering
    - **Property 2: Email list item rendering completeness**
    - **Property 3: Email list sorting invariant**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [ ]* 5.4 Write property test for label color determinism
    - **Property 9: Label color determinism**
    - **Validates: Requirements 5.4, 10.4**

- [x] 6. Implement Email Detail component
  - [x] 6.1 Create EmailDetail component at `frontend/src/components/gmail/email-detail.tsx`
    - Fetch and display full email body from GET /api/gmail/messages/{id}/body
    - Render HTML content in sandboxed iframe (srcDoc with sandbox attribute, no scripts, no external resources)
    - Render plain text with preserved whitespace and line breaks
    - Display metadata header: sender name, email, recipients, CC, subject, date (dd/MM/yyyy HH:mm)
    - Skeleton loading state while body loads
    - Error state with Retry button on HTTP 502
    - Reply button
    - Back button for mobile navigation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1_

  - [ ]* 6.2 Write property tests for email detail rendering
    - **Property 4: HTML content sandboxing**
    - **Property 5: Plain text formatting preservation**
    - **Property 6: Email metadata rendering**
    - **Validates: Requirements 7.2, 7.3, 7.6**

- [x] 7. Implement Label Manager and Attachment Viewer
  - [x] 7.1 Create LabelManager component at `frontend/src/components/gmail/label-manager.tsx`
    - Display current VroomHR labels as removable colored badges
    - Optimistic UI: remove badge immediately, restore on failure
    - Call POST /api/gmail/messages/{id}/labels/remove on remove click
    - Error toast on failure with badge restoration
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 7.2 Create AttachmentViewer component at `frontend/src/components/gmail/attachment-viewer.tsx`
    - Fetch attachment metadata from POST /api/gmail/messages/{id}/attachments
    - Display list with filename, formatted file size (KB/MB), MIME type icon
    - Download attachment on click with original filename
    - Loading indicator while fetching
    - Error state with Retry button on failure
    - MIME type icons: PDF icon for application/pdf, file-text for DOCX, image icon for JPEG/PNG
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 7.3 Write property test for attachment metadata rendering
    - **Property 10: Attachment metadata rendering**
    - **Validates: Requirements 11.1, 11.5**

- [x] 8. Implement Compose and Reply functionality
  - [x] 8.1 Create ComposeDialog component at `frontend/src/components/gmail/compose-dialog.tsx`
    - Modal overlay: full width on <640px, max-w-640px on larger viewports
    - Input fields: To (required, comma-separated multiple), CC (optional), Subject (required, max 500 chars), Body (rich text/HTML)
    - Validate: To has at least one valid email, Subject non-empty → enable Send button
    - Call POST /api/gmail/send on Send click
    - Success: close dialog, show success toast
    - Error: display error message, retain content for retry
    - Loading spinner on Send button while sending
    - Reply mode: pre-fill To (original sender), Subject ("Re: " prefix if not present), reply_to_message_id, show quoted original below body
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.2, 9.3, 9.4, 13.3_

  - [ ]* 8.2 Write property tests for compose validation and reply prefix
    - **Property 7: Compose form validation**
    - **Property 8: Reply subject prefix**
    - **Validates: Requirements 8.7, 9.2**

- [x] 9. Checkpoint - Ensure all components compile and render correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Integrate Gmail Page with routing and layout
  - [x] 10.1 Add Gmail navigation item to sidebar in `frontend/src/app/(dashboard)/layout.tsx`
    - Add `{ href: "/gmail", label: "Gmail", icon: Mail }` after Positions item
    - Import Mail icon from lucide-react
    - Active state handled by existing prefix matching logic
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 10.2 Create Gmail page at `frontend/src/app/(dashboard)/gmail/page.tsx`
    - Wrap with ToastProvider
    - Manage state: connectionStatus, selectedEmail, emails[], composeOpen, emailBody
    - Fetch connection status on mount
    - Fetch emails when connected
    - Handle global error routing (401 → /login, network errors → toast)
    - Responsive two-panel layout (≥1024px: EmailList left 380px + EmailDetail right) / single-panel (<1024px: show one at a time with back button)
    - Wire all components together: ConnectionPanel, EmailList, SyncIndicator, EmailDetail, LabelManager, AttachmentViewer, ComposeDialog
    - _Requirements: 1.1, 2.1, 3.1, 3.2, 3.3, 4.1, 4.2, 4.4, 5.5, 8.1, 12.1, 12.2, 12.5, 13.1, 13.2_

  - [ ]* 10.3 Write property tests for error handling behavior
    - **Property 11: Unauthorized redirect**
    - **Property 12: Network error notification**
    - **Validates: Requirements 12.1, 12.2**

- [x] 11. Add Next.js rewrite configuration for Gmail API proxy
  - [x] 11.1 Add `/api/gmail/:path*` rewrite rule in `frontend/next.config.js` (or `next.config.mjs`)
    - Proxy all `/api/gmail/*` requests to backend FastAPI server
    - Follow existing rewrite pattern used for other API routes
    - _Requirements: 14.1_

- [x] 12. Final checkpoint - Ensure full integration works
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The implementation uses TypeScript throughout, matching the existing frontend stack
- All components follow existing codebase patterns: client-side rendering, local state, fetch-based API calls
- Toast system is self-contained (no external library dependency)
- HTML email rendering uses sandboxed iframe for security

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.2"] },
    { "id": 2, "tasks": ["1.3", "4.1", "4.2"] },
    { "id": 3, "tasks": ["4.3", "5.1", "5.2"] },
    { "id": 4, "tasks": ["5.3", "5.4", "6.1"] },
    { "id": 5, "tasks": ["6.2", "7.1", "7.2"] },
    { "id": 6, "tasks": ["7.3", "8.1"] },
    { "id": 7, "tasks": ["8.2", "10.1", "11.1"] },
    { "id": 8, "tasks": ["10.2"] },
    { "id": 9, "tasks": ["10.3"] }
  ]
}
```
