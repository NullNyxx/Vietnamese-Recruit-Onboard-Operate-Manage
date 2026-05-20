"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types ---

export type ToastVariant = "success" | "error";

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  addToast: (message: string, variant: ToastVariant) => void;
  removeToast: (id: string) => void;
}

// --- Context ---

const ToastContext = React.createContext<ToastContextValue | null>(null);

// --- Hook ---

export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

// --- Toast Item ---

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "pointer-events-auto flex w-full max-w-sm items-center justify-between gap-2 rounded-md px-4 py-3 shadow-lg transition-all",
        toast.variant === "success" &&
          "bg-green-50 border border-green-200 text-green-800",
        toast.variant === "error" &&
          "bg-red-50 border border-red-200 text-red-800"
      )}
    >
      <p className="text-sm font-medium">{toast.message}</p>
      <button
        onClick={() => onDismiss(toast.id)}
        className={cn(
          "shrink-0 rounded-md p-1 transition-colors",
          toast.variant === "success" && "hover:bg-green-100",
          toast.variant === "error" && "hover:bg-red-100"
        )}
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// --- Provider ---

const MAX_VISIBLE_TOASTS = 3;
const SUCCESS_AUTO_DISMISS_MS = 5000;

let toastCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = React.useCallback(
    (message: string, variant: ToastVariant) => {
      const id = `toast-${++toastCounter}`;
      const newToast: Toast = { id, message, variant };

      setToasts((prev) => {
        const updated = [...prev, newToast];
        // Keep only the most recent MAX_VISIBLE_TOASTS
        if (updated.length > MAX_VISIBLE_TOASTS) {
          return updated.slice(updated.length - MAX_VISIBLE_TOASTS);
        }
        return updated;
      });

      // Auto-dismiss success toasts after 5 seconds
      if (variant === "success") {
        setTimeout(() => {
          removeToast(id);
        }, SUCCESS_AUTO_DISMISS_MS);
      }
    },
    [removeToast]
  );

  const contextValue = React.useMemo(
    () => ({ addToast, removeToast }),
    [addToast, removeToast]
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {/* Toast container - positioned top-right, stacked vertically */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="pointer-events-none fixed top-4 right-4 z-50 flex flex-col gap-2"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
