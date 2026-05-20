"use client";

import * as React from "react";
import { X, Send, Loader2 } from "lucide-react";
import type { EmailMessage, SendEmailRequest } from "@/lib/api/types";
import { ApiError } from "@/lib/api/types";
import { sendEmail } from "@/lib/api/gmail";
import { useToast } from "./toast-provider";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ComposeDialogProps {
  open: boolean;
  onClose: () => void;
  replyTo: EmailMessage | null;
}

// ---------------------------------------------------------------------------
// Email Validation
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email.trim());
}

function parseEmails(value: string): string[] {
  return value
    .split(",")
    .map((e) => e.trim())
    .filter((e) => e.length > 0);
}

function hasAtLeastOneValidEmail(value: string): boolean {
  const emails = parseEmails(value);
  return emails.length > 0 && emails.some(isValidEmail);
}

// ---------------------------------------------------------------------------
// Reply Subject Helper
// ---------------------------------------------------------------------------

function getReplySubject(subject: string): string {
  if (subject.startsWith("Re: ")) {
    return subject;
  }
  return `Re: ${subject}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ComposeDialog({ open, onClose, replyTo }: ComposeDialogProps) {
  const { addToast } = useToast();

  // Form state
  const [to, setTo] = React.useState("");
  const [cc, setCc] = React.useState("");
  const [subject, setSubject] = React.useState("");
  const [body, setBody] = React.useState("");
  const [sending, setSending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Initialize form when dialog opens or replyTo changes
  React.useEffect(() => {
    if (open) {
      if (replyTo) {
        setTo(replyTo.sender_email);
        setSubject(getReplySubject(replyTo.subject));
        setBody("");
      } else {
        setTo("");
        setSubject("");
        setBody("");
      }
      setCc("");
      setError(null);
    }
  }, [open, replyTo]);

  // Prevent body scroll when dialog is open
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Close on Escape key
  React.useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Validation
  const isToValid = hasAtLeastOneValidEmail(to);
  const isSubjectValid = subject.trim().length > 0;
  const canSend = isToValid && isSubjectValid && !sending;

  // Send handler
  async function handleSend() {
    if (!canSend) return;

    setSending(true);
    setError(null);

    const toEmails = parseEmails(to).filter(isValidEmail);
    const ccEmails = parseEmails(cc).filter(isValidEmail);

    const request: SendEmailRequest = {
      to: toEmails,
      subject: subject.trim(),
      body_text: body,
    };

    if (ccEmails.length > 0) {
      request.cc = ccEmails;
    }

    if (replyTo) {
      request.reply_to_message_id = replyTo.gmail_message_id;
    }

    try {
      await sendEmail(request);
      addToast("Email đã được gửi thành công!", "success");
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Không thể gửi email. Vui lòng thử lại.");
      }
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;

  const title = replyTo ? "Trả lời" : "Soạn email mới";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative z-10 flex max-h-[90vh] w-full flex-col rounded-lg bg-white shadow-xl sm:max-w-[640px]">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
            aria-label="Đóng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {/* To field */}
          <div>
            <label
              htmlFor="compose-to"
              className="block text-sm font-medium text-gray-700"
            >
              Đến <span className="text-red-500">*</span>
            </label>
            <input
              id="compose-to"
              type="text"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="email@example.com, email2@example.com"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* CC field */}
          <div>
            <label
              htmlFor="compose-cc"
              className="block text-sm font-medium text-gray-700"
            >
              CC
            </label>
            <input
              id="compose-cc"
              type="text"
              value={cc}
              onChange={(e) => setCc(e.target.value)}
              placeholder="email@example.com"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Subject field */}
          <div>
            <label
              htmlFor="compose-subject"
              className="block text-sm font-medium text-gray-700"
            >
              Tiêu đề <span className="text-red-500">*</span>
            </label>
            <input
              id="compose-subject"
              type="text"
              value={subject}
              onChange={(e) =>
                setSubject(e.target.value.slice(0, 500))
              }
              maxLength={500}
              placeholder="Tiêu đề email"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-400">
              {subject.length}/500
            </p>
          </div>

          {/* Body field */}
          <div>
            <label
              htmlFor="compose-body"
              className="block text-sm font-medium text-gray-700"
            >
              Nội dung
            </label>
            <textarea
              id="compose-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              placeholder="Nhập nội dung email..."
              className="mt-1 block w-full resize-y rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Quoted original in reply mode */}
          {replyTo && replyTo.snippet && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Email gốc:
              </p>
              <blockquote className="border-l-4 border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600 italic">
                {replyTo.snippet}
              </blockquote>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span>Gửi</span>
          </button>
        </div>
      </div>
    </div>
  );
}
