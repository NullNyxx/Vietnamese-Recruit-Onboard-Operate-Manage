"use client";

import * as React from "react";
import { ArrowLeft, Reply, ChevronDown, ChevronUp } from "lucide-react";
import type { EmailMessage, MessageBodyResponse } from "@/lib/api/types";
import { ApiError } from "@/lib/api/types";
import { getMessageBody } from "@/lib/api/gmail";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EmailDetailProps {
  email: EmailMessage | null;
  onBack: () => void;
  onReply: (email: EmailMessage) => void;
}

// ---------------------------------------------------------------------------
// Date Formatting (dd/MM/yyyy HH:mm)
// ---------------------------------------------------------------------------

function formatDetailDate(isoDate: string): string {
  const date = new Date(isoDate);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${day}/${month}/${year} ${hours}:${minutes}`;
}

// ---------------------------------------------------------------------------
// Skeleton Loading State
// ---------------------------------------------------------------------------

function EmailDetailSkeleton() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-pulse space-y-3 w-full max-w-md px-6">
        <div className="h-4 w-3/4 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-4 w-full rounded bg-gray-100 dark:bg-gray-600" />
        <div className="h-4 w-5/6 rounded bg-gray-100 dark:bg-gray-600" />
        <div className="h-4 w-2/3 rounded bg-gray-100 dark:bg-gray-600" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EmailDetail({ email, onBack, onReply }: EmailDetailProps) {
  const [body, setBody] = React.useState<MessageBodyResponse | null>(null);
  const [bodyLoading, setBodyLoading] = React.useState(false);
  const [bodyError, setBodyError] = React.useState<string | null>(null);
  const [headerExpanded, setHeaderExpanded] = React.useState(false);

  // Fetch email body when email changes
  React.useEffect(() => {
    if (!email) {
      setBody(null);
      setBodyError(null);
      return;
    }

    let cancelled = false;

    async function fetchBody() {
      setBodyLoading(true);
      setBodyError(null);
      setBody(null);

      try {
        const response = await getMessageBody(email!.gmail_message_id);
        if (!cancelled) {
          setBody(response);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && err.statusCode === 502) {
            setBodyError("Không thể tải nội dung email. Vui lòng thử lại.");
          } else {
            setBodyError("Đã xảy ra lỗi khi tải nội dung email.");
          }
        }
      } finally {
        if (!cancelled) {
          setBodyLoading(false);
        }
      }
    }

    fetchBody();

    return () => {
      cancelled = true;
    };
  }, [email]);

  // Collapse header when switching emails
  React.useEffect(() => {
    setHeaderExpanded(false);
  }, [email?.id]);

  // Retry handler for 502 errors
  function handleRetry() {
    if (!email) return;

    setBodyLoading(true);
    setBodyError(null);
    setBody(null);

    getMessageBody(email.gmail_message_id)
      .then((response) => {
        setBody(response);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.statusCode === 502) {
          setBodyError("Không thể tải nội dung email. Vui lòng thử lại.");
        } else {
          setBodyError("Đã xảy ra lỗi khi tải nội dung email.");
        }
      })
      .finally(() => {
        setBodyLoading(false);
      });
  }

  // No email selected
  if (!email) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Chọn một email để xem nội dung
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Compact header: subject + sender + actions */}
      <div className="shrink-0 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        {/* Row 1: Back (mobile) + Subject + Reply */}
        <div className="flex items-start gap-3">
          <button
            type="button"
            onClick={onBack}
            className="mt-0.5 shrink-0 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 lg:hidden"
            aria-label="Quay lại"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 leading-tight">
              {email.subject}
            </h2>

            {/* Row 2: Sender info (compact) */}
            <div className="mt-1 flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {email.sender_name}
              </span>
              <span className="text-gray-400 dark:text-gray-500">·</span>
              <span className="text-gray-500 dark:text-gray-400 text-xs">
                {formatDetailDate(email.received_at)}
              </span>

              {/* Expand/collapse details */}
              <button
                type="button"
                onClick={() => setHeaderExpanded(!headerExpanded)}
                className="ml-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                aria-label={headerExpanded ? "Thu gọn chi tiết" : "Xem chi tiết"}
              >
                {headerExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
            </div>

            {/* Expanded details */}
            {headerExpanded && (
              <div className="mt-2 space-y-0.5 text-xs text-gray-500 dark:text-gray-400">
                <div>
                  <span className="text-gray-600 dark:text-gray-300">Từ: </span>
                  {email.sender_name} &lt;{email.sender_email}&gt;
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-300">Đến: </span>
                  {email.recipient_emails.join(", ")}
                </div>
                {email.cc_emails.length > 0 && (
                  <div>
                    <span className="text-gray-600 dark:text-gray-300">CC: </span>
                    {email.cc_emails.join(", ")}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Reply button */}
          <button
            type="button"
            onClick={() => onReply(email)}
            className="shrink-0 flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            <Reply className="h-4 w-4" />
            <span className="hidden sm:inline">Trả lời</span>
          </button>
        </div>
      </div>

      {/* Email body — takes all remaining space */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {bodyLoading && <EmailDetailSkeleton />}

        {bodyError && (
          <div className="flex flex-col items-center justify-center gap-3 p-8 text-center h-full">
            <p className="text-sm text-red-600 dark:text-red-400">{bodyError}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Thử lại
            </button>
          </div>
        )}

        {!bodyLoading && !bodyError && body && (
          <>
            {body.html ? (
              <iframe
                srcDoc={body.html}
                sandbox=""
                title="Nội dung email"
                className="h-full w-full border-0"
              />
            ) : body.plain_text ? (
              <div className="p-5">
                <pre className="whitespace-pre-wrap break-words text-sm text-gray-800 dark:text-gray-200 font-sans leading-relaxed">
                  {body.plain_text}
                </pre>
              </div>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                  Không có nội dung email
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
