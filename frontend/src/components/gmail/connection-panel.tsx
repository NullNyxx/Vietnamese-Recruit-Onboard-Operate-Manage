"use client";

import * as React from "react";
import { Loader2, Mail, AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/api/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ConnectionPanelProps {
  status: ConnectionStatus | null;
  email: string | null;
  loading: boolean;
  error: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onRetry: () => void;
  connectLoading: boolean;
  disconnectLoading: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConnectionPanel({
  status,
  email,
  loading,
  error,
  onConnect,
  onDisconnect,
  onRetry,
  connectLoading,
  disconnectLoading,
}: ConnectionPanelProps) {
  // Initial loading state (fetching status)
  if (loading && status === null) {
    return (
      <div className="flex items-center justify-center rounded-lg border bg-white p-6">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">
          Đang kiểm tra kết nối...
        </span>
      </div>
    );
  }

  // Error state (API call failed)
  if (error && status === null) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-red-500" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">
              Không thể kiểm tra trạng thái kết nối
            </p>
            <p className="mt-1 text-sm text-red-600">{error}</p>
          </div>
          <button
            onClick={onRetry}
            className="shrink-0 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-200"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  // Connected state
  if (status === "connected") {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                <span className="text-sm font-medium text-green-800">
                  Đã kết nối
                </span>
              </div>
              {email && (
                <p className="mt-0.5 text-sm text-green-700">{email}</p>
              )}
            </div>
          </div>
          <button
            onClick={onDisconnect}
            disabled={disconnectLoading}
            className={cn(
              "inline-flex items-center gap-2 rounded-md border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50",
              disconnectLoading && "cursor-not-allowed opacity-60"
            )}
          >
            {disconnectLoading && (
              <Loader2 className="h-4 w-4 animate-spin" />
            )}
            Ngắt kết nối
          </button>
        </div>
      </div>
    );
  }

  // Token expired state
  if (status === "token_expired") {
    return (
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-yellow-100">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-yellow-800">
                Phiên kết nối đã hết hạn
              </p>
              <p className="mt-0.5 text-sm text-yellow-700">
                Vui lòng kết nối lại để tiếp tục sử dụng Gmail.
              </p>
            </div>
          </div>
          <button
            onClick={onConnect}
            disabled={connectLoading}
            className={cn(
              "inline-flex items-center gap-2 rounded-md bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-yellow-700",
              connectLoading && "cursor-not-allowed opacity-60"
            )}
          >
            {connectLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            Kết nối lại
          </button>
        </div>
      </div>
    );
  }

  // Disconnected state (default)
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
          <Mail className="h-6 w-6 text-gray-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-800">
            Chưa kết nối Gmail
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Kết nối tài khoản Gmail để đọc và gửi email trực tiếp từ Vroom HR.
          </p>
        </div>
        <button
          onClick={onConnect}
          disabled={connectLoading}
          className={cn(
            "inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700",
            connectLoading && "cursor-not-allowed opacity-60"
          )}
        >
          {connectLoading && <Loader2 className="h-4 w-4 animate-spin" />}
          Kết nối Gmail
        </button>
      </div>
    </div>
  );
}
