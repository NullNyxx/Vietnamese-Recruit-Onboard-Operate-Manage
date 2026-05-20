# Requirements Document

## Introduction

Module Gmail Frontend UI cung cấp giao diện người dùng cho tính năng Gmail Integration trong Vroom HR. Module này cho phép HR: (1) kết nối/ngắt kết nối tài khoản Gmail qua OAuth2, (2) xem danh sách email inbox với trạng thái đồng bộ, (3) đọc nội dung email chi tiết, (4) soạn và gửi email (bao gồm reply), (5) quản lý VroomHR labels trên email, và (6) xem/tải attachments. Frontend sử dụng Next.js 14, React 18, TypeScript, Tailwind CSS, và lucide-react icons, tích hợp với backend Gmail API endpoints đã có sẵn.

## Glossary

- **Gmail_Page**: Trang chính của Gmail UI nằm tại route /gmail trong dashboard, chứa toàn bộ giao diện email
- **Connection_Panel**: Component hiển thị trạng thái kết nối Gmail và các nút connect/disconnect
- **Email_List**: Component hiển thị danh sách email từ inbox với metadata (sender, subject, date, snippet)
- **Email_Detail**: Component hiển thị nội dung đầy đủ của một email khi được chọn
- **Compose_Dialog**: Dialog modal cho phép soạn email mới hoặc reply email
- **Label_Manager**: Component cho phép gắn/gỡ VroomHR labels trên email
- **Attachment_Viewer**: Component hiển thị danh sách attachments và cho phép tải về
- **Sync_Indicator**: Component hiển thị trạng thái đồng bộ và nút sync thủ công
- **Gmail_API_Client**: Module API client trong frontend/src/lib/api/ giao tiếp với backend Gmail endpoints
- **Connection_Status**: Trạng thái kết nối Gmail (connected, disconnected, token_expired) nhận từ backend
- **HR**: Người dùng HR đăng nhập hệ thống Vroom HR

## Requirements

### Requirement 1: Sidebar Navigation Integration

**User Story:** Là HR, tôi muốn truy cập trang Gmail từ sidebar navigation, để tôi có thể dễ dàng chuyển đổi giữa các tính năng HR và email.

#### Acceptance Criteria

1. THE Gmail_Page SHALL be accessible via a "Gmail" navigation item in the sidebar at route /gmail, positioned after the existing "Positions" item
2. THE sidebar navigation item SHALL display a Mail icon (from lucide-react) with the label "Gmail"
3. WHEN the current route is /gmail or starts with /gmail/, THE sidebar navigation item SHALL display in the active state using the existing active styling pattern (bg-primary/10 text-primary)

### Requirement 2: Gmail Connection Status Display

**User Story:** Là HR, tôi muốn thấy rõ trạng thái kết nối Gmail của mình, để tôi biết hệ thống có đang hoạt động bình thường không.

#### Acceptance Criteria

1. WHEN HR navigates to the Gmail_Page, THE Connection_Panel SHALL fetch Connection_Status from GET /api/gmail/status and display the current state (connected, disconnected, or token_expired)
2. WHILE Connection_Status is "connected", THE Connection_Panel SHALL display the connected Gmail email address, a green status indicator, and a "Disconnect" button
3. WHILE Connection_Status is "disconnected", THE Connection_Panel SHALL display a message prompting connection and a "Connect Gmail" button
4. WHILE Connection_Status is "token_expired", THE Connection_Panel SHALL display a warning message indicating the token has expired and a "Reconnect" button
5. IF the GET /api/gmail/status request fails with a network error or HTTP 5xx, THEN THE Connection_Panel SHALL display an error message with a "Retry" button

### Requirement 3: Gmail OAuth Connection Flow

**User Story:** Là HR, tôi muốn kết nối tài khoản Gmail của mình với hệ thống qua giao diện đơn giản, để hệ thống có thể đọc và gửi email thay tôi.

#### Acceptance Criteria

1. WHEN HR clicks the "Connect Gmail" button, THE Gmail_Page SHALL call POST /api/gmail/connect and redirect the browser to the returned redirect_url for Google OAuth2 consent
2. WHEN the OAuth2 flow completes successfully and the browser returns to the callback URL, THE Gmail_Page SHALL redirect HR back to /gmail and display Connection_Status as "connected"
3. IF POST /api/gmail/connect returns an error (HTTP 400 or 5xx), THEN THE Gmail_Page SHALL display an error toast notification with the error message from the response
4. WHILE the OAuth2 flow is in progress (after clicking Connect, before redirect), THE "Connect Gmail" button SHALL display a loading spinner and be disabled to prevent duplicate requests

### Requirement 4: Gmail Disconnect Flow

**User Story:** Là HR, tôi muốn có thể ngắt kết nối Gmail khỏi hệ thống, để tôi kiểm soát quyền truy cập dữ liệu email.

#### Acceptance Criteria

1. WHEN HR clicks the "Disconnect" button, THE Gmail_Page SHALL display a confirmation dialog asking HR to confirm the disconnection
2. WHEN HR confirms the disconnection, THE Gmail_Page SHALL call POST /api/gmail/disconnect and update the UI to show Connection_Status as "disconnected"
3. WHILE the disconnect request is in progress, THE "Disconnect" button SHALL display a loading spinner and be disabled
4. IF POST /api/gmail/disconnect fails with a network error, THEN THE Gmail_Page SHALL display an error toast notification and retain the current Connection_Status display

### Requirement 5: Email List Display

**User Story:** Là HR, tôi muốn xem danh sách email inbox, để tôi có thể nhanh chóng tìm và chọn email cần xử lý.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", THE Email_List SHALL display emails fetched from the local database with fields: sender name, sender email, subject, snippet (truncated to 100 characters), received date (relative format such as "2 giờ trước", "Hôm qua"), and label indicators
2. THE Email_List SHALL display emails sorted by received_at in descending order (newest first)
3. WHEN an email has has_attachments=true, THE Email_List SHALL display a paperclip icon indicator next to the email entry
4. WHEN an email has VroomHR labels applied, THE Email_List SHALL display colored badge indicators for each label (distinct colors for processed, recruitment, interview, onboarding)
5. WHILE Connection_Status is not "connected", THE Email_List SHALL be hidden and only the Connection_Panel SHALL be visible
6. WHILE the email list is loading, THE Email_List SHALL display a skeleton loading state with placeholder rows

### Requirement 6: Email Sync and Refresh

**User Story:** Là HR, tôi muốn đồng bộ email mới ngay lập tức khi cần, để tôi không phải đợi chu kỳ tự động 5 phút.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", THE Sync_Indicator SHALL display a "Sync" button that triggers POST /api/gmail/sync when clicked
2. WHEN the sync request succeeds, THE Sync_Indicator SHALL display the count of new emails fetched and refresh the Email_List
3. IF POST /api/gmail/sync returns HTTP 429 (rate limited), THEN THE Sync_Indicator SHALL display the remaining cooldown time in seconds and disable the Sync button until the cooldown expires
4. WHILE a sync request is in progress, THE Sync button SHALL display a spinning animation and be disabled
5. IF POST /api/gmail/sync fails with HTTP 409 (not connected), THEN THE Gmail_Page SHALL refresh Connection_Status and update the UI accordingly

### Requirement 7: Email Detail View

**User Story:** Là HR, tôi muốn đọc nội dung đầy đủ của một email, để tôi có thể xử lý thông tin chi tiết.

#### Acceptance Criteria

1. WHEN HR clicks on an email in the Email_List, THE Email_Detail SHALL fetch the full email body from GET /api/gmail/messages/{message_id}/body and display the content
2. WHEN the email body contains HTML content, THE Email_Detail SHALL render the HTML safely in a sandboxed container that prevents script execution and external resource loading
3. WHEN the email body contains only plain text, THE Email_Detail SHALL display the text with preserved line breaks and whitespace formatting
4. WHILE the email body is loading, THE Email_Detail SHALL display a skeleton loading state
5. IF GET /api/gmail/messages/{message_id}/body fails with HTTP 502, THEN THE Email_Detail SHALL display an error message with a "Retry" button
6. THE Email_Detail SHALL display email metadata at the top: sender name, sender email, recipient list, CC list (if present), subject, and received date in full format (dd/MM/yyyy HH:mm)

### Requirement 8: Email Compose

**User Story:** Là HR, tôi muốn soạn và gửi email mới từ giao diện Vroom HR, để tôi có thể liên lạc với ứng viên và nhân viên mà không cần mở Gmail.

#### Acceptance Criteria

1. WHILE Connection_Status is "connected", THE Gmail_Page SHALL display a "Compose" button that opens the Compose_Dialog
2. THE Compose_Dialog SHALL provide input fields for: To (required, supports multiple recipients separated by comma), CC (optional, supports multiple recipients), Subject (required, maximum 500 characters), and Body (required, rich text editor with HTML formatting)
3. WHEN HR clicks "Send" in the Compose_Dialog, THE Gmail_Page SHALL call POST /api/gmail/send with the composed email data
4. WHEN the send request succeeds, THE Compose_Dialog SHALL close and display a success toast notification
5. IF POST /api/gmail/send fails, THEN THE Compose_Dialog SHALL display the error message from the response and retain the composed content so HR can retry
6. WHILE the send request is in progress, THE "Send" button SHALL display a loading spinner and be disabled
7. THE Compose_Dialog SHALL validate that the To field contains at least one valid email address and the Subject field is not empty before enabling the Send button

### Requirement 9: Email Reply

**User Story:** Là HR, tôi muốn reply email trực tiếp từ giao diện đọc email, để cuộc hội thoại email được liên tục.

#### Acceptance Criteria

1. WHEN HR is viewing an email in Email_Detail, THE Email_Detail SHALL display a "Reply" button
2. WHEN HR clicks "Reply", THE Compose_Dialog SHALL open with pre-filled fields: To (original sender email), Subject (prefixed with "Re: " if not already present), and reply_to_message_id (the current message ID for threading)
3. WHEN a reply is sent successfully, THE Compose_Dialog SHALL close and display a success toast notification
4. THE Compose_Dialog SHALL display the original email content below the reply body as a quoted reference (read-only, visually distinguished with a left border)

### Requirement 10: Label Management

**User Story:** Là HR, tôi muốn gắn và gỡ VroomHR labels trên email, để tôi có thể phân loại và theo dõi trạng thái xử lý email.

#### Acceptance Criteria

1. WHEN HR is viewing an email in Email_Detail, THE Label_Manager SHALL display the current VroomHR labels applied to that email as removable badges
2. WHEN HR clicks the remove icon on a label badge, THE Label_Manager SHALL call POST /api/gmail/messages/{message_id}/labels/remove with the label name and update the UI to remove the badge
3. IF the label removal request fails, THEN THE Label_Manager SHALL display an error toast notification and restore the badge to its previous state
4. THE Label_Manager SHALL use distinct colors for each VroomHR label category: processed (gray), recruitment (blue), interview (orange), onboarding (green)

### Requirement 11: Attachment Viewing and Download

**User Story:** Là HR, tôi muốn xem và tải attachments từ email, để tôi có thể truy cập CV và hồ sơ ứng viên.

#### Acceptance Criteria

1. WHEN HR is viewing an email with has_attachments=true in Email_Detail, THE Attachment_Viewer SHALL fetch attachment metadata from POST /api/gmail/messages/{message_id}/attachments and display a list of attachments with filename, file size (formatted as KB/MB), and MIME type icon
2. WHEN HR clicks on an attachment, THE Attachment_Viewer SHALL download the attachment file to the user's device with the original filename
3. WHILE attachments are being fetched, THE Attachment_Viewer SHALL display a loading indicator
4. IF the attachment fetch request fails, THEN THE Attachment_Viewer SHALL display an error message indicating attachments could not be loaded with a "Retry" button
5. THE Attachment_Viewer SHALL display file type icons appropriate to the MIME type: PDF icon for application/pdf, file-text icon for DOCX, image icon for JPEG/PNG

### Requirement 12: Error Handling and Loading States

**User Story:** Là HR, tôi muốn giao diện phản hồi rõ ràng khi có lỗi hoặc đang tải, để tôi biết chuyện gì đang xảy ra và có thể hành động phù hợp.

#### Acceptance Criteria

1. WHEN any API request returns HTTP 401 (unauthorized), THE Gmail_Page SHALL redirect HR to the login page at /login
2. WHEN any API request fails due to network error (no response), THE Gmail_Page SHALL display a toast notification with message "Không thể kết nối server. Vui lòng thử lại."
3. THE Gmail_Page SHALL display toast notifications for success actions (email sent, sync complete, disconnect success) that auto-dismiss after 5 seconds
4. THE Gmail_Page SHALL display toast notifications for error actions that persist until manually dismissed by HR
5. WHILE any data-fetching operation is in progress, THE Gmail_Page SHALL display appropriate loading indicators (skeleton for lists, spinner for actions) without blocking other UI interactions

### Requirement 13: Responsive Layout

**User Story:** Là HR, tôi muốn giao diện Gmail hoạt động tốt trên các kích thước màn hình khác nhau, để tôi có thể sử dụng trên desktop và tablet.

#### Acceptance Criteria

1. WHILE the viewport width is 1024px or greater, THE Gmail_Page SHALL display a two-panel layout with Email_List on the left (fixed width 380px) and Email_Detail on the right (remaining width)
2. WHILE the viewport width is less than 1024px, THE Gmail_Page SHALL display a single-panel layout where Email_List and Email_Detail are shown one at a time with a back navigation button in Email_Detail
3. THE Compose_Dialog SHALL be displayed as a centered modal overlay that is responsive, taking full width on viewports less than 640px and a maximum width of 640px on larger viewports

### Requirement 14: Gmail API Client Module

**User Story:** Là developer, tôi muốn có một API client module riêng cho Gmail, để code frontend được tổ chức rõ ràng và dễ bảo trì.

#### Acceptance Criteria

1. THE Gmail_API_Client SHALL be implemented as a module at frontend/src/lib/api/gmail.ts following the same pattern as the existing employees.ts API module (using fetch with handleResponse helper)
2. THE Gmail_API_Client SHALL export typed functions for all Gmail backend endpoints: getStatus, connect, disconnect, syncEmails, getMessageBody, removeLabel, sendEmail, and getAttachments
3. THE Gmail_API_Client SHALL define TypeScript interfaces for all request and response types in frontend/src/lib/api/types.ts following the existing type definition pattern
4. THE Gmail_API_Client SHALL be re-exported from frontend/src/lib/api/index.ts as "gmailApi" following the existing barrel export pattern

