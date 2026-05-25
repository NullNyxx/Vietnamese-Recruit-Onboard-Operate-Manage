"use client";

import { toast } from "sonner";

// --- Types (kept for backward compatibility) ---

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

// --- Hook (now uses global Sonner) ---

export function useToast(): ToastContextValue {
  const addToast = (message: string, variant: ToastVariant) => {
    if (variant === "success") {
      toast.success(message);
    } else {
      toast.error(message);
    }
  };

  const removeToast = () => {
    toast.dismiss();
  };

  return { addToast, removeToast };
}

// --- Provider (now a passthrough — Toaster is in root layout) ---

export function ToastProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
