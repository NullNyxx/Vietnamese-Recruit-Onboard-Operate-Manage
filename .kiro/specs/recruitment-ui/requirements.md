# Requirements Document

## Introduction

The Recruitment CV Pipeline UI provides the frontend interface for managing the automated CV recruitment pipeline. It enables HR users to browse candidates extracted from email CVs, review low-confidence parses, take actions on candidates (accept, reject, schedule interviews, send emails, archive), and monitor pipeline health metrics. The UI integrates into the existing Vroom HR dashboard shell with sidebar navigation, follows the established design system (shadcn/ui, TailwindCSS, dark mode), and communicates with the recruitment backend API endpoints.

## Glossary

- **Candidate_List_Page**: The page at `/recruitment` displaying a paginated, searchable, filterable table of all candidates extracted by the CV pipeline
- **Candidate_Detail_Page**: The page at `/recruitment/[id]` displaying full candidate information, parsed CV data, attached documents, and action buttons
- **CV_Review_Page**: The page at `/recruitment/review` displaying the queue of CV documents requiring manual review due to low confidence or parse failures
- **Metrics_Dashboard**: The page at `/recruitment/metrics` displaying pipeline processing statistics including success rate, failure rate, average processing time, and queue depth
- **Recruitment_API_Client**: The frontend service module that communicates with the backend recruitment API endpoints using fetch with proper authentication headers
- **Action_Dialog**: A modal dialog used to confirm destructive or significant candidate actions (reject, archive) or collect additional input (schedule interview, send email)
- **CV_Viewer**: A component that displays a candidate's CV document via a presigned URL in an embedded viewer or download link
- **Filter_Panel**: The toolbar section on the candidate list page containing search input, status filter, date range picker, confidence slider, and skills filter
- **Sidebar_Navigation**: The existing AppSidebar component extended with a recruitment section link

## Requirements

### Requirement 1: Sidebar Navigation Integration

**User Story:** As an HR user, I want a "Tuyển dụng" (Recruitment) section in the sidebar navigation, so that I can access the recruitment pipeline pages from anywhere in the application.

#### Acceptance Criteria

1. THE Sidebar_Navigation SHALL include a navigation item with label "Tuyển dụng", the lucide-react UserSearch icon, and href "/recruitment" positioned as the next entry immediately after the "Gmail" navigation item in the navItems array
2. WHEN the current route path starts with "/recruitment", THE Sidebar_Navigation SHALL apply the sidebar-accent background and sidebar-accent-foreground text color to the "Tuyển dụng" navigation item to indicate active state
3. WHILE the sidebar is in collapsed state, THE Sidebar_Navigation SHALL render the "Tuyển dụng" item as icon-only with a tooltip displaying "Tuyển dụng" on the right side
4. WHILE the sidebar is in expanded state, THE Sidebar_Navigation SHALL render the "Tuyển dụng" item displaying both the UserSearch icon and the "Tuyển dụng" text label

### Requirement 2: Candidate List Page — Layout and Data Display

**User Story:** As an HR user, I want to see all candidates in a paginated table with key information visible at a glance, so that I can quickly scan and find candidates of interest.

#### Acceptance Criteria

1. THE Candidate_List_Page SHALL display a data table with columns: Tên (name), Email, Số điện thoại (phone), Kỹ năng (skills displayed as badges, maximum 5 badges per row with a "+N" indicator if the candidate has more than 5 skills), Độ tin cậy (confidence score displayed as an integer percentage from 0% to 100%), Trạng thái (status displayed as a colored badge with a visually distinct color per status value: new, reviewing, interview_scheduled, accepted, rejected, archived), and Ngày tạo (created date formatted as dd/MM/yyyy)
2. THE Candidate_List_Page SHALL fetch data from `GET /api/recruitment/candidates` with pagination parameters (page, page_size) and display pagination controls showing current page, total pages, and page size selector with options 10, 20, 50 (default: 20), with results sorted by created date descending (newest first)
3. WHILE candidate data is being fetched, THE Candidate_List_Page SHALL display Skeleton placeholder rows matching the table column layout with at least 5 placeholder rows
4. IF the API returns an empty result set (total_count is 0), THEN THE Candidate_List_Page SHALL display a centered empty state message "Chưa có ứng viên nào" with an illustrative icon in place of the table body
5. IF the API request fails due to a network error or returns an HTTP status code of 4xx or 5xx, THEN THE Candidate_List_Page SHALL display an error state with the message "Không thể tải danh sách ứng viên" and a retry button that re-sends the original request with the same pagination parameters when clicked
6. WHEN a table row is clicked or activated via keyboard (Enter key on a focused row), THE Candidate_List_Page SHALL navigate to the Candidate_Detail_Page at `/recruitment/{candidate_id}`
7. WHEN the viewport width is below 768px, THE Candidate_List_Page SHALL switch from table layout to a card-based layout displaying one card per candidate with name, email, phone, status badge, confidence score, and created date
8. THE Candidate_List_Page SHALL display a page header with title "Tuyển dụng" and subtitle "Quản lý ứng viên từ pipeline CV tự động"

### Requirement 3: Candidate List Page — Search and Filters

**User Story:** As an HR user, I want to search and filter candidates by various criteria, so that I can quickly find specific candidates or narrow down the list to relevant subsets.

#### Acceptance Criteria

1. THE Filter_Panel SHALL include a search text input with placeholder "Tìm kiếm theo tên, email, số điện thoại..." and a maximum length of 100 characters that filters candidates by partial, case-insensitive match across name, email, phone, and skills fields, sending the `search` query parameter to the API
2. WHEN the user types in the search input, THE Candidate_List_Page SHALL debounce the input by 300ms before sending the filtered request to the API with the `search` query parameter
3. THE Filter_Panel SHALL include a status dropdown filter with options: Tất cả (all), Mới (new), Đang xem xét (reviewing), Đã lên lịch PV (interview_scheduled), Đã chấp nhận (accepted), Đã từ chối (rejected), Đã lưu trữ (archived), with "Tất cả" selected by default
4. THE Filter_Panel SHALL include a date range picker for filtering candidates by creation date in dd/MM/yyyy display format, sending `date_from` and `date_to` parameters to the API; IF the user selects a `date_from` value later than `date_to`, THEN THE Filter_Panel SHALL prevent submission and display an inline error message indicating the invalid range
5. THE Filter_Panel SHALL include a confidence score slider (range 0–100%) for filtering candidates with confidence at or above the selected threshold, sending `min_confidence` as a decimal (0.0–1.0) to the API, with a default value of 0 (no filtering)
6. THE Filter_Panel SHALL include a skills text input that accepts comma-separated skill names with a maximum of 10 skills and a maximum of 50 characters per skill, sending them as the `skills` array parameter to the API
7. WHEN any filter value changes, THE Candidate_List_Page SHALL reset pagination to page 1 and fetch updated results from the API with all active filter parameters
8. WHEN the user clicks the "Xóa bộ lọc" (Clear filters) button, THE Filter_Panel SHALL reset all filters to their default values: search input cleared, status set to "Tất cả", date range cleared (no date_from or date_to), confidence slider set to 0, and skills input cleared
9. IF the API returns an error while fetching filtered results, THEN THE Candidate_List_Page SHALL display an error message indicating the fetch failure and preserve the current filter values so the user can retry without re-entering criteria

### Requirement 4: Candidate Detail Page — Information Display

**User Story:** As an HR user, I want to see complete candidate information including parsed CV data and attached documents, so that I can evaluate the candidate thoroughly before taking action.

#### Acceptance Criteria

1. THE Candidate_Detail_Page SHALL fetch data from `GET /api/recruitment/candidates/{candidate_id}` and display the candidate's full name, email, phone number, current status (as a Badge component with a distinct background color per status value: new, reviewing, interview_scheduled, accepted, rejected, archived), confidence score (as a percentage from 0–100% with a colored progress bar where 0–49% uses the destructive color token, 50–74% uses the warning color token, and 75–100% uses the primary color token), and creation date formatted as dd/MM/yyyy
2. THE Candidate_Detail_Page SHALL display the parsed CV data in organized sections: Tóm tắt (summary as plain text paragraph), Kỹ năng (skills as a horizontal-wrap list of Badge components), Kinh nghiệm (experience as timeline entries each showing company name, role title, and duration), and Học vấn (education as list entries each showing institution name, degree, and graduation year)
3. IF a parsed CV section (skills, experience, or education) contains no entries, THEN THE Candidate_Detail_Page SHALL display a placeholder message indicating no data is available for that section (e.g., "Chưa có dữ liệu")
4. THE Candidate_Detail_Page SHALL display a list of attached CV documents with original filename, upload date formatted as dd/MM/yyyy, and processing status (pending, ocr_processing, llm_parsing, completed, needs_review, failed), where each document with a completed or needs_review processing status has a "Xem CV" button that opens the CV_Viewer
5. WHEN the "Xem CV" button is clicked, THE Candidate_Detail_Page SHALL fetch a presigned URL from `GET /api/recruitment/candidates/{candidate_id}/cv/{document_id}` and open the document in a new browser tab
6. IF the presigned URL fetch fails due to a storage service error or file not found, THEN THE Candidate_Detail_Page SHALL display an error notification via the Toast_System indicating the document could not be retrieved, without navigating away from the page
7. WHILE candidate detail data is being fetched, THE Candidate_Detail_Page SHALL display Skeleton placeholders for all content sections
8. IF the candidate is not found (404 response), THEN THE Candidate_Detail_Page SHALL display a "Không tìm thấy ứng viên" message with a link back to the candidate list
9. IF the detail API returns a server error (5xx response), THEN THE Candidate_Detail_Page SHALL display a generic error message indicating the data could not be loaded, with a retry button that re-fetches the candidate data
10. THE Candidate_Detail_Page SHALL include a breadcrumb trail: Tuyển dụng > [Candidate Name], where "Tuyển dụng" is a clickable link navigating to the candidate list page

### Requirement 5: Candidate Detail Page — Actions

**User Story:** As an HR user, I want to take actions on candidates (accept, reject, archive, schedule interview, send email) directly from the detail page, so that I can manage the recruitment workflow efficiently.

#### Acceptance Criteria

1. THE Candidate_Detail_Page SHALL display action buttons based on the candidate's current status following the valid state machine transitions: from "new" status — "Từ chối", "Lưu trữ", "Lên lịch phỏng vấn"; from "reviewing" status — "Chấp nhận", "Từ chối", "Lưu trữ", "Lên lịch phỏng vấn"; from "interview_scheduled" status — "Chấp nhận", "Từ chối", "Lưu trữ"; from "accepted", "rejected", or "archived" status — no state-transition buttons; and THE Candidate_Detail_Page SHALL always display the "Gửi email" button regardless of candidate status since it is not a state transition
2. WHEN the user clicks "Từ chối", THE Candidate_Detail_Page SHALL open an Action_Dialog requesting a rejection reason (required, textarea, minimum 10 characters, maximum 500 characters), and upon confirmation SHALL send a POST to `/api/recruitment/candidates/{candidate_id}/reject` with the reason
3. WHEN the user clicks "Chấp nhận", THE Candidate_Detail_Page SHALL open a confirmation Action_Dialog, and upon confirmation SHALL send a POST to `/api/recruitment/candidates/{candidate_id}/accept`
4. WHEN the user clicks "Lưu trữ", THE Candidate_Detail_Page SHALL open a confirmation Action_Dialog with warning text, and upon confirmation SHALL send a POST to `/api/recruitment/candidates/{candidate_id}/archive`
5. WHEN the user clicks "Lên lịch phỏng vấn", THE Candidate_Detail_Page SHALL open an Action_Dialog with fields for interview date/time (required, datetime picker, must be at least 1 hour in the future) and interviewer selection (required, multi-select from employee list, minimum 1 and maximum 10 interviewers), and upon confirmation SHALL send a POST to `/api/recruitment/candidates/{candidate_id}/schedule-interview`
6. WHEN the user clicks "Gửi email", THE Candidate_Detail_Page SHALL open an Action_Dialog with fields for email subject (required, maximum 200 characters) and body (required, textarea, minimum 1 character, maximum 5000 characters), and upon confirmation SHALL send a POST to `/api/recruitment/candidates/{candidate_id}/send-email`
7. WHILE an action request is in progress, THE Action_Dialog SHALL disable the confirm button and display a loading spinner
8. WHEN an action succeeds, THE Candidate_Detail_Page SHALL close the Action_Dialog, display a success toast notification, and refresh the candidate data to reflect the updated status
9. IF an action fails due to an invalid status transition (HTTP 409 response), THEN THE Candidate_Detail_Page SHALL display an error toast with message "Không thể thực hiện hành động này với trạng thái hiện tại" and close the Action_Dialog
10. IF an action fails due to a server error (HTTP 5xx response) or network failure, THEN THE Candidate_Detail_Page SHALL display an error toast with a message indicating the operation failed, and SHALL keep the Action_Dialog open with all user-entered data preserved so the user can retry
11. THE Candidate_Detail_Page SHALL disable action buttons that are not valid for the current candidate status, rendering them with 50% opacity and a tooltip stating which status transition is not permitted from the current status
12. WHEN an Action_Dialog is open, THE Action_Dialog SHALL close without submitting if the user presses the Escape key, clicks the cancel button, or clicks outside the dialog area, and SHALL preserve no draft data upon dismissal

### Requirement 6: CV Review Queue Page

**User Story:** As an HR user, I want to review CV documents that were parsed with low confidence or failed parsing, so that I can manually correct data and ensure no candidates are lost.

#### Acceptance Criteria

1. THE CV_Review_Page SHALL fetch data from `GET /api/recruitment/cv-review` with pagination parameters (page, page_size) and display a list of CV documents needing review, showing for each item: candidate name (from parsed_cv_data.name if available, otherwise "Không rõ tên"), original_filename, processing_status (needs_review or failed), confidence_score displayed as a percentage (0–100%), and created_at date formatted as dd/MM/yyyy
2. THE CV_Review_Page SHALL display pagination controls with page size options 10, 20, 50 (default: 20) and the list SHALL be sorted by created_at descending (newest first)
3. WHEN the user clicks a review item, THE CV_Review_Page SHALL expand an inline detail panel below the clicked item showing: the original parsed data (parsed_cv_data, read-only), an editable form pre-filled with the parsed values (name max 200 characters, email max 254 characters, phone max 20 characters, skills max 50 items, experience max 20 items, education max 10 items, summary max 500 characters), and a "Xem CV gốc" button to view the original document
4. WHEN the user submits corrections via the editable form, THE CV_Review_Page SHALL validate that name is non-empty and email is a valid email format, send a PUT to `/api/recruitment/cv-review/{cv_document_id}` with the corrected ParsedCV data, display a success toast upon 200 response, and remove the item from the displayed queue list
5. IF the PUT correction request returns a 422 validation error, THEN THE CV_Review_Page SHALL display the validation error details as inline error messages below the corresponding form fields and preserve all user-entered data
6. IF any API request (PUT, POST retry, or DELETE dismiss) returns a 404 error, THEN THE CV_Review_Page SHALL display an error toast indicating the CV document was not found and remove the stale item from the displayed list
7. WHEN the user clicks "Thử lại phân tích" (Retry parse), THE CV_Review_Page SHALL send a POST to `/api/recruitment/cv-review/{cv_document_id}/retry`, display a loading indicator on the item during processing (up to 60 seconds), and upon success refresh the item data with the updated response including new confidence_score and processing_status
8. WHEN the user clicks "Bỏ qua" (Dismiss), THE CV_Review_Page SHALL open a confirmation dialog and upon confirmation send a DELETE to `/api/recruitment/cv-review/{cv_document_id}/dismiss`, removing the item from the queue upon 204 response
9. IF the review queue is empty, THEN THE CV_Review_Page SHALL display a success state message "Không có CV nào cần xem xét" with a checkmark icon
10. WHILE review data is being fetched, THE CV_Review_Page SHALL display Skeleton placeholder cards matching the layout of review items

### Requirement 7: Metrics Dashboard Page

**User Story:** As an HR manager, I want to see pipeline processing metrics at a glance, so that I can monitor the health and performance of the automated CV pipeline.

#### Acceptance Criteria

1. THE Metrics_Dashboard SHALL fetch data from `GET /api/recruitment/metrics` and display four metric cards: Thời gian xử lý TB (average processing time converted from the API's millisecond value to seconds by dividing by 1000, displayed with 1 decimal place and a "s" suffix), Tỷ lệ thành công (success rate converted from the API's 0.0–1.0 ratio to a percentage by multiplying by 100, displayed with 1 decimal place and a "%" suffix), Tỷ lệ thất bại (failure rate converted from the API's 0.0–1.0 ratio to a percentage by multiplying by 100, displayed with 1 decimal place and a "%" suffix), and Hàng đợi (queue depth displayed as an integer count with no suffix)
2. THE Metrics_Dashboard SHALL display each metric card using the Card component with a descriptive icon (Clock icon for Thời gian xử lý TB, CheckCircle icon for Tỷ lệ thành công, XCircle icon for Tỷ lệ thất bại, ListQueue icon for Hàng đợi), metric label text, and the metric value rendered at a font size at least 1.5× the body text size
3. THE Metrics_Dashboard SHALL use a responsive grid layout: 1 column below 640px, 2 columns between 640px and 1023px, 4 columns at 1024px and above
4. WHILE metrics data is being fetched, THE Metrics_Dashboard SHALL display Skeleton placeholder cards matching the metric card layout
5. IF the metrics API returns an error, THEN THE Metrics_Dashboard SHALL display an error state with message "Không thể tải số liệu" and a retry button that re-fetches data from the metrics API when clicked
6. THE Metrics_Dashboard SHALL include a page header with title "Số liệu Pipeline" and subtitle "Thống kê xử lý CV trong 24 giờ qua"
7. THE Metrics_Dashboard SHALL apply color coding to metric values: success rate above 80% in green (success color token), failure rate above 20% in red (destructive color token), queue depth above 50 in amber (warning color token); values at or below these thresholds SHALL use the default foreground color token
8. THE Metrics_Dashboard SHALL automatically re-fetch metrics data every 30 seconds while the page is visible, and SHALL display a manual refresh button in the page header that triggers an immediate data re-fetch when clicked
9. WHEN the user clicks the manual refresh button, THE Metrics_Dashboard SHALL display a loading indicator on the refresh button until the fetch completes or fails, with a maximum timeout of 10 seconds

### Requirement 8: Recruitment API Client

**User Story:** As a developer, I want a centralized API client module for all recruitment endpoints, so that API calls are consistent, authenticated, and handle errors uniformly.

#### Acceptance Criteria

1. THE Recruitment_API_Client SHALL export typed functions for each backend endpoint: `listCandidates`, `getCandidate`, `getCVPresignedUrl`, `scheduleInterview`, `sendEmail`, `rejectCandidate`, `acceptCandidate`, `archiveCandidate`, `listReviewQueue`, `submitCorrection`, `retryParse`, `dismissReview`, `getMetrics`
2. THE Recruitment_API_Client SHALL include authentication credentials (cookies/session) with every request by using `credentials: "include"` in fetch options
3. IF the API returns a 401 response, THEN THE Recruitment_API_Client SHALL redirect the user to the login page at `/login` without throwing an error to the caller
4. THE Recruitment_API_Client SHALL define TypeScript interfaces for all request and response types matching the backend API schemas: `Candidate`, `CandidateListResponse`, `CVDocument`, `CVReviewItem`, `MetricsResponse`, `ScheduleInterviewRequest`, `SendEmailRequest`, `RejectRequest`, `ParsedCVInput`
5. IF the API returns a non-2xx response (other than 401) with a JSON body containing a message field, THEN THE Recruitment_API_Client SHALL throw a typed error containing the HTTP status code and the error message extracted from the response body
6. IF the API returns a non-2xx response (other than 401) with a non-JSON body or a JSON body without a message field, THEN THE Recruitment_API_Client SHALL throw a typed error containing the HTTP status code and a fallback message indicating the request failed with that status code
7. IF a network error occurs (fetch rejects due to network failure, DNS resolution failure, or connection refused), THEN THE Recruitment_API_Client SHALL throw a typed error with a status code of 0 and a message indicating a network connectivity failure
8. THE Recruitment_API_Client SHALL apply a request timeout of 30 seconds to each API call; IF the timeout is exceeded, THEN THE Recruitment_API_Client SHALL abort the request and throw a typed error with a status code of 0 and a message indicating the request timed out

### Requirement 9: Page Routing and Layout

**User Story:** As a user, I want recruitment pages to follow the existing app routing conventions, so that navigation feels consistent with the rest of the application.

#### Acceptance Criteria

1. THE application SHALL register recruitment pages under the `(dashboard)` route group at paths: `/recruitment` (candidate list), `/recruitment/[id]` (candidate detail), `/recruitment/review` (CV review queue), `/recruitment/metrics` (metrics dashboard)
2. THE recruitment pages SHALL render within the existing `(dashboard)/layout.tsx` layout shell (AppSidebar, header with Breadcrumbs, main content area) by being placed as route segments inside the `(dashboard)` route group, requiring no additional layout wrapper components within recruitment page files
3. THE Breadcrumbs component SHALL display breadcrumb trails for recruitment pages by mapping the path segment "recruitment" to the label "Tuyển dụng", "review" to "Xem xét CV", and "metrics" to "Số liệu" in the labelMap, resulting in: "Trang chủ > Tuyển dụng" for the list page, "Trang chủ > Tuyển dụng > Xem xét CV" for the review page, and "Trang chủ > Tuyển dụng > Số liệu" for the metrics page
4. WHEN a user navigates to `/recruitment/[id]`, THE Breadcrumbs component SHALL display "Trang chủ > Tuyển dụng > [Tên ứng viên]" where [Tên ứng viên] is the candidate's full name fetched from the candidate data, and SHALL display a placeholder text of "..." while the candidate name is loading
5. THE navItems array in `navigation.ts` SHALL include a recruitment entry with href "/recruitment" and label "Tuyển dụng", which makes it appear in both the AppSidebar navigation and the CommandBar searchable items
6. THE CommandBar SHALL include additional searchable navigation items beyond the sidebar entry: "Xem xét CV" linking to `/recruitment/review` and "Số liệu Pipeline" linking to `/recruitment/metrics`

### Requirement 10: Loading and Error States

**User Story:** As a user, I want consistent loading indicators and error handling across all recruitment pages, so that I always know the current state of the interface.

#### Acceptance Criteria

1. WHILE any recruitment page is fetching initial data, THE page SHALL display Skeleton components that replicate the number and approximate dimensions of the expected content elements (e.g., table rows, card grids, form fields) rather than a blank page or generic spinner
2. IF a network error occurs (no response from server within 15 seconds, or a connection failure), THEN THE page SHALL display an error message "Lỗi kết nối. Vui lòng kiểm tra mạng và thử lại." with a retry button
3. IF the API returns an HTTP error response (status 5xx or 4xx) without a parseable error message in the response body, THEN THE page SHALL display a generic error message "Đã xảy ra lỗi. Vui lòng thử lại." with a retry button
4. WHEN the user clicks a retry button after an error, THE page SHALL re-fetch the failed request, display the Skeleton loading state during the fetch, and replace the error state with the fetched content on success
5. WHILE a mutation (create, update, or delete action) is in progress, THE triggering button SHALL display a loading spinner and all other mutation-triggering buttons (create, update, delete, import, and submit buttons) on the same page SHALL be disabled to prevent concurrent mutations; navigation links and non-mutating controls (search, filter, pagination) SHALL remain enabled
6. WHEN a mutation succeeds, THE page SHALL display a success toast via the Toast_System and update the affected data in the current view (e.g., add the new row to the table, remove the deleted row, or update the modified fields) without requiring a full page reload
7. WHEN a mutation fails, THE page SHALL display an error toast via the Toast_System containing the error message from the API response, and re-enable all previously disabled action buttons within 200 milliseconds of receiving the error response
8. IF a mutation fails and the API response contains no error message, THEN THE page SHALL display an error toast via the Toast_System with the message "Đã xảy ra lỗi. Vui lòng thử lại."

### Requirement 11: Accessibility for Recruitment Pages

**User Story:** As a user with assistive technology, I want recruitment pages to be fully accessible, so that I can manage candidates using keyboard navigation and screen readers.

#### Acceptance Criteria

1. THE Candidate_List_Page table SHALL use proper semantic table markup (table, thead, tbody, th with scope="col") and include a caption or aria-label "Danh sách ứng viên"
2. THE Filter_Panel inputs SHALL each have a programmatically associated label element or aria-label describing the filter purpose
3. THE Action_Dialog components SHALL trap keyboard focus within the dialog when open, move focus to the first interactive element on open, return focus to the triggering button on close, and close the dialog when the user presses the Escape key
4. THE status badges SHALL convey status information through both color and a visible text label (e.g., "Mới", "Đang xem xét", "Đã chấp nhận", "Từ chối"), not relying on color alone
5. THE confidence score display SHALL include an aria-label with the numeric percentage value (e.g., aria-label="Độ tin cậy: 85%") and SHALL not rely solely on a visual indicator (such as a progress bar) to convey the score
6. WHEN data refresh completes after a user action (status change, filter applied, candidate deleted), THE page SHALL announce the update via an aria-live="polite" region indicating the result of the action
7. WHEN an error toast notification is displayed on a recruitment page, THE page SHALL announce the error message via an aria-live="assertive" region
8. THE Candidate_List_Page SHALL ensure all row-level actions (view detail, change status, delete) are operable via keyboard by providing focusable interactive controls (buttons or links) within each row that are reachable via Tab navigation
