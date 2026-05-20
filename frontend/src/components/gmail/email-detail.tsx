"use client";

import * as React from "react";
import { ArrowLeft, Reply } from "lucide-react";
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
    <div className="animate-pulse p-6">
      {/* Metadata skeleton */}
      <div className="mb-6 space-y-3">
        <div className="h-6 w-3/4 rounded bg-gray-200" />
        <div className="h-4 w-1/2 rounded bg-gray-200" />
        <div className="h-4 w-1/3 rounded bg-gray-200" />
        <div className="h-4 w-1/4 rounded bg-gray-100" />
      </div>
      {/* Body skeleton */}
      <div className="space-y-2">
        <div className="h-4 w-full rounded bg-gray-100" />
        <div className="h-4 w-full rounded bg-gray-100" />
        <div className="h-4 w-5/6 rounded bg-gray-100" />
        <div className="h-4 w-4/6 rounded bg-gray-100" />
        <div className="h-4 w-full rounded bg-gray-100" />
        <div className="h-4 w-3/4 rounded bg-gray-100" />
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
        <p className="text-sm text-gray-500">
          Chọn một email để xem nội dung
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar: Back button (mobile) + Reply button */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 lg:hidden"
          aria-label="Quay lại"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Quay lại</span>
        </button>

        <button
          type="button"
          onClick={() => onReply(email)}
          className="ml-auto flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          <Reply className="h-4 w-4" />
          <span>Trả lời</span>
        </button>
      </div>

      {/* Email metadata header */}
      <div className="border-b px-6 py-4">
        {/* Subject */}
        <h2 className="text-lg font-semibold text-gray-900">
          {email.subject}
        </h2>

        {/* Sender */}
        <div className="mt-2 text-sm text-gray-700">
          <span className="font-medium">{email.sender_name}</span>
          <span className="ml-1 text-gray-500">
            &lt;{email.sender_email}&gt;
          </span>
        </div>

        {/* Recipients */}
        <div className="mt-1 text-sm text-gray-600">
          <span className="font-medium">Đến: </span>
          <span>{email.recipient_emails.join(", ")}</span>
        </div>

        {/* CC (if present) */}
        {email.cc_emails.length > 0 && (
          <div className="mt-1 text-sm text-gray-600">
            <span className="font-medium">CC: </span>
            <span>{email.cc_emails.join(", ")}</span>
          </div>
        )}

        {/* Date */}
        <div className="mt-1 text-sm text-gray-500">
          {formatDetailDate(email.received_at)}
        </div>
      </div>

      {/* Email body */}
      <div className="flex-1 overflow-y-auto">
        {bodyLoading && <EmailDetailSkeleton />}

        {bodyError && (
          <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
            <p className="text-sm text-red-600">{bodyError}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Thử lại
            </button>
          </div>
        )}

        {!bodyLoading && !bodyError && body && (
          <div className="p-6">
            {body.html ? (
              <iframe
                srcDoc={body.html}
                sandbox=""
                title="Nội dung email"
                className="w-full border-0"
                style={{ minHeight: "300px" }}
                onLoad={(e) => {
                  // Auto-resize iframe to fit content
                  const iframe = e.currentTarget;
                  try {
                    const height =
                      iframe.contentDocument?.documentElement?.scrollHeight;
                    if (height) {
                      iframe.style.height = `${height}px`;
                    }
                  } catch {
                    // Cross-origin restrictions may prevent access
                  }
                }}
              />
            ) : body.plain_text ? (
              <pre className="whitespace-pre-wrap break-words text-sm text-gray-800 font-sans">
                {body.plain_text}
              </pre>
            ) : (
              <p className="text-sm text-gray-500 italic">
                Không có nội dung email
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
