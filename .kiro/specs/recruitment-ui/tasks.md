# Implementation Plan: Recruitment UI

## Overview

Build the complete frontend interface for the automated CV recruitment pipeline, integrating into the existing Vroom HR dashboard. Implementation follows a bottom-up approach: API client and utilities first, then shared components, then page-level compositions, and finally navigation/routing integration.

## Tasks

- [x] 1. Set up API client and utility modules
  - [x] 1.1 Create the Recruitment API client module at `frontend/src/lib/api/recruitment.ts`
    - Define all TypeScript interfaces (`Candidate`, `CandidateListResponse`, `CVDocument`, `CVReviewItem`, `MetricsResponse`, `ScheduleInterviewRequest`, `SendEmailRequest`, `RejectRequest`, `ParsedCVInput`, etc.)
    - Implement `fetchWithTimeout` with 30-second AbortController timeout
    - Implement `handleResponse<T>` following the existing `gmail.ts` pattern with 401 redirect, JSON error extraction, and fallback messages
    - Export typed functions: `listCandidates`, `getCandidate`, `getCVPresignedUrl`, `scheduleInterview`, `sendEmail`, `rejectCandidate`, `acceptCandidate`, `archiveCandidate`, `listReviewQueue`, `submitCorrection`, `retryParse`, `dismissReview`, `getMetrics`
    - All requests must use `credentials: "include"`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x]* 1.2 Write property tests for API client error handling
    - **Property 9: API client error handling**
    - **Property 10: API client credentials inclusion**
    - **Property 11: API client 401 redirect**
    - **Validates: Requirements 8.2, 8.3, 8.5, 8.6, 8.7, 8.8**

  - [x] 1.3 Create recruitment utilities at `frontend/src/lib/recruitment-utils.ts`
    - Define `VALID_TRANSITIONS` state machine mapping
    - Define `STATUS_LABELS` with Vietnamese labels
    - Define `STATUS_COLORS` with dark mode support
    - Implement helper functions: `getValidActions(status)`, `formatConfidence(score)`, `formatDate(isoString)`
    - _Requirements: 5.1, 5.11, 11.4_

- [x] 2. Build shared recruitment components
  - [x] 2.1 Create `CandidateStatusBadge` at `frontend/src/components/recruitment/candidate-status-badge.tsx`
    - Map status enum to Vietnamese label + color variant using Badge component
    - Ensure both color and text label are always displayed (accessibility)
    - _Requirements: 2.1, 11.4_

  - [x]* 2.2 Write property test for status badge accessibility
    - **Property 12: Status badges convey information through color and text**
    - **Validates: Requirements 11.4**

  - [x] 2.3 Create `ConfidenceScore` at `frontend/src/components/recruitment/confidence-score.tsx`
    - Render percentage text + colored progress bar (destructive 0–49%, warning 50–74%, primary 75–100%)
    - Include `aria-label` with format "Độ tin cậy: {percentage}%"
    - _Requirements: 4.1, 11.5_

  - [x]* 2.4 Write property test for confidence score aria-label
    - **Property 13: Confidence score accessible label**
    - **Validates: Requirements 11.5**

  - [x] 2.5 Create `MetricCard` at `frontend/src/components/recruitment/metric-card.tsx`
    - Extend existing StatCard with conditional color coding based on thresholds
    - Success rate > 80% → green, failure rate > 20% → red, queue depth > 50 → amber
    - Render icon, label, and value at 1.5× body text size
    - _Requirements: 7.1, 7.2, 7.7_

  - [x]* 2.6 Write property tests for metric card display
    - **Property 7: Metrics value display conversions**
    - **Property 8: Metrics color coding thresholds**
    - **Validates: Requirements 7.1, 7.7**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Build filter panel and action components
  - [x] 4.1 Create `CandidateFilterPanel` at `frontend/src/components/recruitment/candidate-filter-panel.tsx`
    - Search input with 300ms debounce, placeholder "Tìm kiếm theo tên, email, số điện thoại...", max 100 chars
    - Status dropdown with Vietnamese labels and "Tất cả" default
    - Date range picker in dd/MM/yyyy format with invalid range validation
    - Confidence slider (0–100%) converting to decimal for API
    - Skills text input (comma-separated, max 10 items, max 50 chars each)
    - "Xóa bộ lọc" clear button resetting all filters
    - All inputs have programmatically associated labels or aria-labels
    - Emit filter change callbacks that reset pagination to page 1
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 11.2_

  - [x]* 4.2 Write property tests for filter panel logic
    - **Property 1: Date range validation rejects invalid ranges**
    - **Property 2: Confidence slider decimal conversion**
    - **Property 3: Skills input parsing**
    - **Property 4: Filter change resets pagination**
    - **Validates: Requirements 3.4, 3.5, 3.6, 3.7**

  - [x] 4.3 Create `CandidateActions` at `frontend/src/components/recruitment/candidate-actions.tsx`
    - Read candidate status and render valid action buttons per state machine
    - Disable invalid transition buttons with 50% opacity and tooltip
    - Always show "Gửi email" button regardless of status
    - Manage dialog open state for each action type
    - _Requirements: 5.1, 5.11_

  - [x]* 4.4 Write property test for action buttons state machine
    - **Property 5: Action buttons match state machine transitions**
    - **Validates: Requirements 5.1, 5.11**

  - [x] 4.5 Create action dialog components at `frontend/src/components/recruitment/`
    - `reject-dialog.tsx`: Textarea for reason (required, 10–500 chars)
    - `accept-dialog.tsx`: Simple confirmation dialog
    - `archive-dialog.tsx`: Confirmation with warning text
    - `schedule-interview-dialog.tsx`: Date/time picker (≥1hr future) + multi-select interviewers (1–10)
    - `send-email-dialog.tsx`: Subject (max 200 chars) + body textarea (1–5000 chars)
    - All dialogs: trap focus, close on Escape/cancel/outside click, disable confirm while loading, preserve data on 5xx errors
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.12, 11.3_

- [x] 5. Build CV-related components
  - [x] 5.1 Create `CVSections` at `frontend/src/components/recruitment/cv-sections.tsx`
    - Render summary paragraph, skills badges, experience timeline, education list
    - Show "Chưa có dữ liệu" placeholder for empty sections
    - _Requirements: 4.2, 4.3_

  - [x] 5.2 Create `DocumentList` at `frontend/src/components/recruitment/document-list.tsx`
    - List CV documents with filename, upload date (dd/MM/yyyy), processing status
    - "Xem CV" button for completed/needs_review documents
    - Fetch presigned URL and open in new tab on click
    - Show error toast if presigned URL fetch fails
    - _Requirements: 4.4, 4.5, 4.6_

  - [x] 5.3 Create `CorrectionForm` at `frontend/src/components/recruitment/correction-form.tsx`
    - react-hook-form + zod validated form for ParsedCVInput fields
    - Pre-fill with existing parsed data
    - Validate: name non-empty (1–200 chars), email valid format, phone max 20 chars, skills max 50 items, experience max 20 items, education max 10 items, summary max 500 chars
    - Display inline validation errors from 422 responses
    - _Requirements: 6.3, 6.4, 6.5_

  - [x]* 5.4 Write property test for CV correction form validation
    - **Property 6: CV correction form validation**
    - **Validates: Requirements 6.4**

  - [x] 5.5 Create `ReviewItem` at `frontend/src/components/recruitment/review-item.tsx`
    - Expandable item showing candidate name, filename, status, confidence, date
    - Inline detail panel with original parsed data (read-only) + CorrectionForm
    - "Xem CV gốc" button, "Thử lại phân tích" button (with 60s loading), "Bỏ qua" button (with confirmation dialog)
    - _Requirements: 6.1, 6.3, 6.7, 6.8_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Build page-level compositions
  - [x] 7.1 Create Candidate List page at `frontend/src/app/(dashboard)/recruitment/page.tsx`
    - Page header: "Tuyển dụng" title, "Quản lý ứng viên từ pipeline CV tự động" subtitle
    - Integrate CandidateFilterPanel and DataTable<CandidateRow>
    - Columns: Tên, Email, Số điện thoại, Kỹ năng (max 5 badges + "+N"), Độ tin cậy (%), Trạng thái (colored badge), Ngày tạo (dd/MM/yyyy)
    - Pagination controls (10, 20, 50 page sizes, default 20), sorted by created_at desc
    - Skeleton loading (5+ rows), empty state "Chưa có ứng viên nào", error state with retry
    - Row click/Enter navigates to `/recruitment/{id}`
    - Responsive: card layout below 768px
    - Semantic table markup with aria-label "Danh sách ứng viên"
    - Keyboard-accessible row actions
    - aria-live region for data refresh announcements
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.7, 3.9, 10.1, 10.2, 10.3, 10.4, 11.1, 11.6, 11.8_

  - [x] 7.2 Create Candidate Detail page at `frontend/src/app/(dashboard)/recruitment/[id]/page.tsx`
    - Breadcrumb: Tuyển dụng > [Candidate Name]
    - Display full candidate info: name, email, phone, status badge, confidence score with progress bar, created date
    - Integrate CVSections, DocumentList, CandidateActions, and all action dialogs
    - Handle action success: close dialog, success toast, refresh data
    - Handle 409: error toast "Không thể thực hiện hành động này với trạng thái hiện tại", close dialog
    - Handle 5xx/network: error toast, keep dialog open with data preserved
    - Skeleton loading, 404 "Không tìm thấy ứng viên" with back link, 5xx error with retry
    - Disable mutation buttons during action in progress
    - aria-live regions for action results and errors
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 5.1, 5.7, 5.8, 5.9, 5.10, 5.11, 10.1, 10.4, 10.5, 10.6, 10.7, 10.8, 11.5, 11.6, 11.7_

  - [x] 7.3 Create CV Review Queue page at `frontend/src/app/(dashboard)/recruitment/review/page.tsx`
    - Fetch from `GET /api/recruitment/cv-review` with pagination
    - Display ReviewItem list with pagination controls (10, 20, 50, default 20), sorted by created_at desc
    - Handle correction submission: success toast, remove item from list
    - Handle retry parse: loading indicator (60s max), refresh item data
    - Handle dismiss: confirmation dialog, DELETE request, remove item on 204
    - Handle 404: error toast, remove stale item
    - Handle 422: inline field errors
    - Empty state: "Không có CV nào cần xem xét" with checkmark icon
    - Skeleton loading cards
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 10.1, 10.5, 10.6, 10.7_

  - [x] 7.4 Create Metrics Dashboard page at `frontend/src/app/(dashboard)/recruitment/metrics/page.tsx`
    - Page header: "Số liệu Pipeline" title, "Thống kê xử lý CV trong 24 giờ qua" subtitle
    - Fetch from `GET /api/recruitment/metrics`
    - Display 4 MetricCards in responsive grid (1 col <640px, 2 cols 640–1023px, 4 cols ≥1024px)
    - Auto-refresh every 30 seconds while page visible
    - Manual refresh button with loading indicator (10s timeout)
    - Skeleton loading cards, error state "Không thể tải số liệu" with retry
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 7.9, 10.1, 10.4_

- [x] 8. Integrate navigation and routing
  - [x] 8.1 Update sidebar navigation in `frontend/src/components/app-sidebar.tsx`
    - Add "Tuyển dụng" item with UserSearch icon and href "/recruitment"
    - Position immediately after "Gmail" entry in navItems
    - Active state when route starts with "/recruitment"
    - Collapsed: icon-only with tooltip; Expanded: icon + text
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 8.2 Update navigation config in `frontend/src/lib/navigation.ts`
    - Add recruitment entry with href "/recruitment" and label "Tuyển dụng"
    - _Requirements: 9.5_

  - [x] 8.3 Update breadcrumbs in `frontend/src/components/breadcrumbs.tsx`
    - Add labelMap entries: "recruitment" → "Tuyển dụng", "review" → "Xem xét CV", "metrics" → "Số liệu"
    - Handle dynamic `[id]` segment showing candidate name with "..." placeholder while loading
    - _Requirements: 9.3, 9.4_

  - [x] 8.4 Update command bar in `frontend/src/components/command-bar.tsx`
    - Add searchable items: "Xem xét CV" → `/recruitment/review`, "Số liệu Pipeline" → `/recruitment/metrics`
    - _Requirements: 9.6_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses TypeScript throughout, following existing project patterns (shadcn/ui, TailwindCSS, Next.js App Router)
- All Vietnamese labels and messages match the requirements exactly
- The API client follows the existing `gmail.ts` pattern with `handleResponse<T>` and `ApiError`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.3", "2.5"] },
    { "id": 2, "tasks": ["2.2", "2.4", "2.6", "4.1", "4.3", "4.5"] },
    { "id": 3, "tasks": ["4.2", "4.4", "5.1", "5.2", "5.3"] },
    { "id": 4, "tasks": ["5.4", "5.5"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3", "7.4"] },
    { "id": 6, "tasks": ["8.1", "8.2", "8.3", "8.4"] }
  ]
}
```
