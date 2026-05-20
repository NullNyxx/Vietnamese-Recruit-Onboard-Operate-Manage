/**
 * Gmail UI utility functions
 * - Date formatting (Vietnamese locale)
 * - File size formatting
 * - Label category extraction and color mapping
 */

// ---------------------------------------------------------------------------
// Label Colors
// ---------------------------------------------------------------------------

export const LABEL_COLORS: Record<string, { bg: string; text: string }> = {
  processed: { bg: "bg-gray-100", text: "text-gray-700" },
  recruitment: { bg: "bg-blue-100", text: "text-blue-700" },
  interview: { bg: "bg-orange-100", text: "text-orange-700" },
  onboarding: { bg: "bg-green-100", text: "text-green-700" },
};

// ---------------------------------------------------------------------------
// Label Category
// ---------------------------------------------------------------------------

/**
 * Extract category from a VroomHR label ID.
 * E.g. "VroomHR/recruitment" → "recruitment"
 * Returns null if the label doesn't match the VroomHR pattern.
 */
export function getLabelCategory(labelId: string): string | null {
  const match = labelId.match(/^VroomHR\/(.+)$/);
  return match ? match[1] : null;
}

// ---------------------------------------------------------------------------
// Relative Date Formatting (Vietnamese)
// ---------------------------------------------------------------------------

/**
 * Format an ISO date string as a Vietnamese relative date.
 *
 * Rules:
 * - < 1 minute  → "Vừa xong"
 * - < 60 minutes → "X phút trước"
 * - < 24 hours  → "X giờ trước"
 * - yesterday   → "Hôm qua"
 * - < 7 days    → "X ngày trước"
 * - otherwise   → dd/MM/yyyy
 */
export function formatRelativeDate(isoDate: string, now?: Date): string {
  const date = new Date(isoDate);
  const currentTime = now ?? new Date();
  const diffMs = currentTime.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return "Vừa xong";
  if (diffMinutes < 60) return `${diffMinutes} phút trước`;
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffDays === 1) return "Hôm qua";
  if (diffDays < 7) return `${diffDays} ngày trước`;

  // Format as dd/MM/yyyy
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

// ---------------------------------------------------------------------------
// File Size Formatting
// ---------------------------------------------------------------------------

/**
 * Format a file size in bytes to a human-readable string.
 * - < 1024 bytes → "X B"
 * - < 1 MB → "X.X KB"
 * - >= 1 MB → "X.X MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
