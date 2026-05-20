"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// --- Types ---

export interface ConfirmDialogProps {
  /** Whether the dialog is visible */
  open: boolean;
  /** Callback when user confirms the action */
  onConfirm: () => void;
  /** Callback when user cancels (closes the dialog) */
  onCancel: () => void;
  /** Dialog title */
  title?: string;
  /** Dialog message / description */
  message?: string;
  /** Label for the confirm button */
  confirmLabel?: string;
  /** Label for the cancel button */
  cancelLabel?: string;
}

/**
 * Reusable confirmation dialog component.
 * Renders as a modal overlay with backdrop.
 *
 * Default text is Vietnamese for the Gmail disconnect use case:
 * - Title: "Ngắt kết nối Gmail"
 * - Message: "Bạn có chắc chắn muốn ngắt kết nối tài khoản Gmail?"
 * - Confirm: "Ngắt kết nối"
 * - Cancel: "Hủy"
 */
export function ConfirmDialog({
  open,
  onConfirm,
  onCancel,
  title = "Ngắt kết nối Gmail",
  message = "Bạn có chắc chắn muốn ngắt kết nối tài khoản Gmail?",
  confirmLabel = "Ngắt kết nối",
  cancelLabel = "Hủy",
}: ConfirmDialogProps) {
  // Close on Escape key
  React.useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onCancel();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-message"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Dialog panel */}
      <div
        className={cn(
          "relative z-10 w-full max-w-sm rounded-lg bg-white p-6 shadow-xl",
          "mx-4 sm:mx-0"
        )}
      >
        <h2
          id="confirm-dialog-title"
          className="text-lg font-semibold text-gray-900"
        >
          {title}
        </h2>

        <p
          id="confirm-dialog-message"
          className="mt-2 text-sm text-gray-600"
        >
          {message}
        </p>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className={cn(
              "rounded-md px-4 py-2 text-sm font-medium",
              "border border-gray-300 bg-white text-gray-700",
              "hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-300"
            )}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={cn(
              "rounded-md px-4 py-2 text-sm font-medium",
              "bg-red-600 text-white",
              "hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
