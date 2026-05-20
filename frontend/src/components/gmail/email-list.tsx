"use client";

import * as React from "react";
import { Paperclip } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EmailMessage } from "@/lib/api/types";
import { formatRelativeDate, getLabelCategory, LABEL_COLORS } from "./utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EmailListProps {
  emails: EmailMessage[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  connected: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Truncate a snippet to a maximum of 100 characters, appending "..." if longer.
 */
function truncateSnippet(snippet: string): string {
  if (snippet.length <= 100) return snippet;
  return snippet.slice(0, 100) + "...";
}

// ---------------------------------------------------------------------------
// Skeleton Loading State
// ---------------------------------------------------------------------------

function EmailListSkeleton() {
  return (
    <div className="flex flex-col gap-1 p-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-lg border bg-white p-4"
        >
          <div className="flex items-center justify-between">
            <div className="h-4 w-32 rounded bg-gray-200" />
            <div className="h-3 w-16 rounded bg-gray-200" />
          </div>
          <div className="mt-2 h-4 w-48 rounded bg-gray-200" />
          <div className="mt-2 h-3 w-full rounded bg-gray-100" />
          <div className="mt-2 flex gap-1">
            <div className="h-5 w-16 rounded bg-gray-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EmailList({
  emails,
  selectedId,
  loading,
  onSelect,
  connected,
}: EmailListProps) {
  // Hide when not connected
  if (!connected) {
    return null;
  }

  // Loading state
  if (loading) {
    return <EmailListSkeleton />;
  }

  // Sort emails by received_at descending (newest first)
  const sortedEmails = [...emails].sort(
    (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime()
  );

  // Empty state
  if (sortedEmails.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <p className="text-sm text-gray-500">Không có email nào</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 overflow-y-auto p-2">
      {sortedEmails.map((email) => {
        const isSelected = email.id === selectedId;

        // Extract VroomHR label categories
        const labelCategories = email.label_ids
          .map(getLabelCategory)
          .filter((cat): cat is string => cat !== null && cat in LABEL_COLORS);

        return (
          <button
            key={email.id}
            type="button"
            onClick={() => onSelect(email.id)}
            className={cn(
              "w-full rounded-lg border p-3 text-left transition-colors hover:bg-gray-50",
              isSelected
                ? "border-blue-300 bg-blue-50"
                : "border-gray-200 bg-white"
            )}
          >
            {/* Header: sender + date */}
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <span className="truncate text-sm font-medium text-gray-900">
                  {email.sender_name}
                </span>
                <span className="ml-1 truncate text-xs text-gray-500">
                  &lt;{email.sender_email}&gt;
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {email.has_attachments && (
                  <Paperclip className="h-3.5 w-3.5 text-gray-400" />
                )}
                <span className="text-xs text-gray-500">
                  {formatRelativeDate(email.received_at)}
                </span>
              </div>
            </div>

            {/* Subject */}
            <p className="mt-1 truncate text-sm font-medium text-gray-800">
              {email.subject}
            </p>

            {/* Snippet */}
            <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
              {truncateSnippet(email.snippet)}
            </p>

            {/* Label badges */}
            {labelCategories.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {labelCategories.map((category) => {
                  const colors = LABEL_COLORS[category];
                  return (
                    <span
                      key={category}
                      className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                        colors.bg,
                        colors.text
                      )}
                    >
                      {category}
                    </span>
                  );
                })}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
