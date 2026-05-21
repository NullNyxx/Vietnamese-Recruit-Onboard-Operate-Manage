/**
 * Recruitment utilities: state machine transitions, Vietnamese labels,
 * status colors (dark mode), and formatting helpers.
 */

export type CandidateStatus =
  | "new"
  | "screening"
  | "interview_scheduled"
  | "interviewed"
  | "accepted"
  | "rejected"
  | "archived";

/**
 * Valid state machine transitions for candidate statuses.
 * Maps each status to the array of statuses it can transition to.
 */
export const VALID_TRANSITIONS: Record<CandidateStatus, CandidateStatus[]> = {
  new: ["screening", "interview_scheduled", "rejected", "archived"],
  screening: ["interview_scheduled", "accepted", "rejected", "archived"],
  interview_scheduled: ["interviewed", "accepted", "rejected", "archived"],
  interviewed: ["accepted", "rejected", "archived"],
  accepted: [],
  rejected: [],
  archived: [],
};

/**
 * Vietnamese labels for each candidate status.
 */
export const STATUS_LABELS: Record<CandidateStatus, string> = {
  new: "Mới",
  screening: "Đang sàng lọc",
  interview_scheduled: "Đã lên lịch PV",
  interviewed: "Đã phỏng vấn",
  accepted: "Đã chấp nhận",
  rejected: "Đã từ chối",
  archived: "Đã lưu trữ",
};

/**
 * Tailwind CSS classes for each candidate status with dark mode support.
 */
export const STATUS_COLORS: Record<CandidateStatus, string> = {
  new: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  screening:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  interview_scheduled:
    "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  interviewed:
    "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
  accepted:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
};

/**
 * Returns the list of valid next statuses for a given candidate status.
 */
export function getValidActions(status: CandidateStatus): CandidateStatus[] {
  return VALID_TRANSITIONS[status] ?? [];
}

/**
 * Converts a decimal confidence score (0–1) to a percentage string.
 * Example: 0.85 → "85%"
 */
export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Formats an ISO date string to dd/MM/yyyy format.
 * Example: "2024-03-15T10:30:00Z" → "15/03/2024"
 */
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}
