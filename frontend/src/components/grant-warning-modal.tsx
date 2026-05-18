"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";

interface GrantWarningModalProps {
  gmailGrantValid: boolean;
  calendarGrantValid: boolean;
  onDismiss: () => void;
}

export function GrantWarningModal({
  gmailGrantValid,
  calendarGrantValid,
  onDismiss,
}: GrantWarningModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const reauthorizeRef = useRef<HTMLButtonElement>(null);

  const shouldShow = !gmailGrantValid || !calendarGrantValid;

  useEffect(() => {
    if (shouldShow && reauthorizeRef.current) {
      reauthorizeRef.current.focus();
    }
  }, [shouldShow]);

  useEffect(() => {
    if (!shouldShow) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onDismiss();
      }

      // Trap focus within the modal
      if (e.key === "Tab" && dialogRef.current) {
        const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [shouldShow, onDismiss]);

  if (!shouldShow) {
    return null;
  }

  const handleReauthorize = () => {
    window.location.href = "/api/auth/login";
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="grant-warning-title"
      aria-describedby="grant-warning-description"
    >
      <div
        ref={dialogRef}
        className="w-full max-w-md rounded-lg border border-border bg-white p-6 shadow-xl"
      >
        <div className="flex items-center gap-2 mb-4">
          <span className="text-2xl" aria-hidden="true">⚠️</span>
          <h2
            id="grant-warning-title"
            className="text-lg font-semibold text-foreground"
          >
            Incomplete Permissions
          </h2>
        </div>

        <p
          id="grant-warning-description"
          className="mb-4 text-sm text-muted-foreground"
        >
          You haven&apos;t granted access to:
        </p>

        <ul className="mb-6 space-y-2">
          {!gmailGrantValid && (
            <li className="flex items-center gap-2 text-sm text-foreground">
              <span className="text-muted-foreground" aria-hidden="true">☐</span>
              <span>Gmail (required for Inbox)</span>
            </li>
          )}
          {!calendarGrantValid && (
            <li className="flex items-center gap-2 text-sm text-foreground">
              <span className="text-muted-foreground" aria-hidden="true">☐</span>
              <span>Calendar (required for Interview scheduling)</span>
            </li>
          )}
        </ul>

        <div className="flex justify-end gap-3">
          <Button
            ref={reauthorizeRef}
            onClick={handleReauthorize}
            aria-label="Re-authorize Google permissions"
          >
            Re-authorize
          </Button>
          <Button
            variant="outline"
            onClick={onDismiss}
            aria-label="Skip re-authorization for now"
          >
            Skip for now
          </Button>
        </div>
      </div>
    </div>
  );
}
