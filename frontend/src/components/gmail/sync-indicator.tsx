"use client";

import * as React from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

import { useToast } from "./toast-provider";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface SyncIndicatorProps {
  onSyncComplete: () => void;
  onConnectionLost: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SyncIndicator({
  onSyncComplete,
  onConnectionLost,
}: SyncIndicatorProps) {
  const { addToast } = useToast();
  const [syncing, setSyncing] = React.useState(false);
  const [cooldown, setCooldown] = React.useState(0);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(
    null
  );

  const cooldownRef = React.useRef<ReturnType<typeof setInterval> | null>(null);
  const successTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  // Cleanup timers on unmount
  React.useEffect(() => {
    return () => {
      if (cooldownRef.current) {
        clearInterval(cooldownRef.current);
      }
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current);
      }
    };
  }, []);

  function startCooldown(seconds: number) {
    setCooldown(seconds);

    if (cooldownRef.current) {
      clearInterval(cooldownRef.current);
    }

    cooldownRef.current = setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          if (cooldownRef.current) {
            clearInterval(cooldownRef.current);
            cooldownRef.current = null;
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  async function handleSync() {
    if (syncing || cooldown > 0) return;

    setSyncing(true);
    setSuccessMessage(null);

    try {
      // Make a raw fetch to access the Retry-After header on 429
      const res = await fetch("/api/gmail/sync", { method: "POST" });

      if (!res.ok) {
        if (res.status === 429) {
          // Parse Retry-After header or default to 60s
          const retryAfter = res.headers.get("Retry-After");
          const cooldownSeconds = retryAfter
            ? parseInt(retryAfter, 10) || 60
            : 60;
          startCooldown(cooldownSeconds);
          addToast(
            `Đồng bộ quá nhanh. Vui lòng đợi ${cooldownSeconds} giây.`,
            "error"
          );
          return;
        }

        if (res.status === 409) {
          onConnectionLost();
          addToast("Gmail chưa được kết nối. Vui lòng kết nối lại.", "error");
          return;
        }

        // Other errors
        const body = await res.json().catch(() => ({
          detail: res.statusText,
        }));
        const message =
          body?.detail ||
          body?.error?.message ||
          `Đồng bộ thất bại: ${res.status}`;
        addToast(message, "error");
        return;
      }

      const data = await res.json();
      const syncedCount = data.synced_count ?? 0;

      setSuccessMessage(`Đã đồng bộ ${syncedCount} email`);
      onSyncComplete();

      // Auto-dismiss success message after 3 seconds
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current);
      }
      successTimerRef.current = setTimeout(() => {
        setSuccessMessage(null);
        successTimerRef.current = null;
      }, 3000);
    } catch {
      addToast("Không thể kết nối server. Vui lòng thử lại.", "error");
    } finally {
      setSyncing(false);
    }
  }

  const isDisabled = syncing || cooldown > 0;

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleSync}
        disabled={isDisabled}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
          isDisabled
            ? "cursor-not-allowed border-gray-200 bg-gray-50 text-gray-400"
            : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
        )}
        aria-label="Đồng bộ email"
      >
        {syncing ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw
            className={cn("h-4 w-4", syncing && "animate-spin")}
          />
        )}
        {cooldown > 0 ? `Đợi ${cooldown}s` : "Đồng bộ"}
      </button>

      {successMessage && (
        <span className="text-sm text-green-600">{successMessage}</span>
      )}
    </div>
  );
}
