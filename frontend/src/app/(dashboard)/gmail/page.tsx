"use client";

import * as React from "react";
import { PenSquare } from "lucide-react";

import type {
  ConnectionStatus,
  EmailMessage,
} from "@/lib/api/types";
import { ApiError } from "@/lib/api/types";
import * as gmailApi from "@/lib/api/gmail";

import { ToastProvider, useToast } from "@/components/gmail/toast-provider";
import { ConnectionPanel } from "@/components/gmail/connection-panel";
import { ConfirmDialog } from "@/components/gmail/confirm-dialog";
import { EmailList } from "@/components/gmail/email-list";
import { SyncIndicator } from "@/components/gmail/sync-indicator";
import { EmailDetail } from "@/components/gmail/email-detail";
import { LabelManager } from "@/components/gmail/label-manager";
import { AttachmentViewer } from "@/components/gmail/attachment-viewer";
import { ComposeDialog } from "@/components/gmail/compose-dialog";

// ---------------------------------------------------------------------------
// Inner page component (needs ToastProvider context)
// ---------------------------------------------------------------------------

function GmailPageContent() {
  const { addToast } = useToast();

  // --- Connection state ---
  const [connectionStatus, setConnectionStatus] =
    React.useState<ConnectionStatus | null>(null);
  const [connectedEmail, setConnectedEmail] = React.useState<string | null>(
    null
  );
  const [statusLoading, setStatusLoading] = React.useState(true);
  const [statusError, setStatusError] = React.useState<string | null>(null);
  const [connectLoading, setConnectLoading] = React.useState(false);
  const [disconnectLoading, setDisconnectLoading] = React.useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = React.useState(false);

  // --- Email list state ---
  const [emails, setEmails] = React.useState<EmailMessage[]>([]);
  const [emailsLoading, setEmailsLoading] = React.useState(false);

  // --- Selected email state ---
  const [selectedEmailId, setSelectedEmailId] = React.useState<string | null>(
    null
  );

  // --- Compose state ---
  const [composeOpen, setComposeOpen] = React.useState(false);
  const [replyToEmail, setReplyToEmail] = React.useState<EmailMessage | null>(
    null
  );

  // Derived: selected email object
  const selectedEmail = React.useMemo(
    () => emails.find((e) => e.id === selectedEmailId) ?? null,
    [emails, selectedEmailId]
  );

  // --- Error handler ---
  const handleApiError = React.useCallback(
    (err: unknown) => {
      if (err instanceof ApiError) {
        if (err.statusCode === 401) {
          window.location.href = "/login";
          return;
        }
        addToast(err.message, "error");
      } else {
        addToast("Không thể kết nối server. Vui lòng thử lại.", "error");
      }
    },
    [addToast]
  );

  // --- Fetch connection status ---
  const fetchStatus = React.useCallback(async () => {
    setStatusLoading(true);
    setStatusError(null);
    try {
      const res = await gmailApi.getStatus();
      setConnectionStatus(res.status);
      setConnectedEmail(res.email);
    } catch (err) {
      if (err instanceof ApiError && err.statusCode === 401) {
        window.location.href = "/login";
        return;
      }
      setStatusError(
        err instanceof Error ? err.message : "Không thể kiểm tra trạng thái"
      );
    } finally {
      setStatusLoading(false);
    }
  }, []);

  // --- Fetch emails from backend ---
  const fetchEmails = React.useCallback(async () => {
    setEmailsLoading(true);
    try {
      const res = await fetch("/api/gmail/messages");
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(
          res.status,
          "FETCH_ERROR",
          body?.detail || "Không thể tải danh sách email"
        );
      }
      const data = await res.json();
      // Support both { items: [...] } and direct array response
      const emailList: EmailMessage[] = Array.isArray(data)
        ? data
        : data.items ?? data.messages ?? [];
      setEmails(emailList);
    } catch (err) {
      handleApiError(err);
    } finally {
      setEmailsLoading(false);
    }
  }, [handleApiError]);

  // --- On mount: fetch status ---
  React.useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // --- When connected: fetch emails ---
  React.useEffect(() => {
    if (connectionStatus === "connected") {
      fetchEmails();
    } else {
      setEmails([]);
      setSelectedEmailId(null);
    }
  }, [connectionStatus, fetchEmails]);

  // --- Connect handler ---
  const handleConnect = React.useCallback(async () => {
    setConnectLoading(true);
    try {
      const res = await gmailApi.connect();
      if (res.redirect_url) {
        window.location.href = res.redirect_url;
      } else {
        // Already connected
        await fetchStatus();
      }
    } catch (err) {
      handleApiError(err);
    } finally {
      setConnectLoading(false);
    }
  }, [fetchStatus, handleApiError]);

  // --- Disconnect handlers ---
  const handleDisconnectClick = React.useCallback(() => {
    setDisconnectDialogOpen(true);
  }, []);

  const handleDisconnectConfirm = React.useCallback(async () => {
    setDisconnectDialogOpen(false);
    setDisconnectLoading(true);
    try {
      const res = await gmailApi.disconnect();
      setConnectionStatus(res.status);
      setConnectedEmail(res.email);
      addToast("Đã ngắt kết nối Gmail thành công.", "success");
    } catch (err) {
      handleApiError(err);
    } finally {
      setDisconnectLoading(false);
    }
  }, [addToast, handleApiError]);

  const handleDisconnectCancel = React.useCallback(() => {
    setDisconnectDialogOpen(false);
  }, []);

  // --- Sync complete handler ---
  const handleSyncComplete = React.useCallback(() => {
    fetchEmails();
  }, [fetchEmails]);

  // --- Connection lost handler (from SyncIndicator 409) ---
  const handleConnectionLost = React.useCallback(() => {
    fetchStatus();
  }, [fetchStatus]);

  // --- Email selection ---
  const handleEmailSelect = React.useCallback((id: string) => {
    setSelectedEmailId(id);
  }, []);

  // --- Back button (mobile) ---
  const handleBack = React.useCallback(() => {
    setSelectedEmailId(null);
  }, []);

  // --- Reply handler ---
  const handleReply = React.useCallback((email: EmailMessage) => {
    setReplyToEmail(email);
    setComposeOpen(true);
  }, []);

  // --- Compose handlers ---
  const handleComposeOpen = React.useCallback(() => {
    setReplyToEmail(null);
    setComposeOpen(true);
  }, []);

  const handleComposeClose = React.useCallback(() => {
    setComposeOpen(false);
    setReplyToEmail(null);
  }, []);

  // --- Label change handler ---
  const handleLabelsChange = React.useCallback(
    (newLabelIds: string[]) => {
      if (!selectedEmailId) return;
      setEmails((prev) =>
        prev.map((e) =>
          e.id === selectedEmailId ? { ...e, label_ids: newLabelIds } : e
        )
      );
    },
    [selectedEmailId]
  );

  // --- Determine if connected ---
  const isConnected = connectionStatus === "connected";

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3 sm:px-6">
        <h1 className="text-xl font-semibold text-gray-900">Gmail</h1>
        {isConnected && (
          <SyncIndicator
            onSyncComplete={handleSyncComplete}
            onConnectionLost={handleConnectionLost}
          />
        )}
      </div>

      {/* Connection Panel - always visible when not connected */}
      {!isConnected && (
        <div className="p-4 sm:p-6">
          <ConnectionPanel
            status={connectionStatus}
            email={connectedEmail}
            loading={statusLoading}
            error={statusError}
            onConnect={handleConnect}
            onDisconnect={handleDisconnectClick}
            onRetry={fetchStatus}
            connectLoading={connectLoading}
            disconnectLoading={disconnectLoading}
          />
        </div>
      )}

      {/* Main content area - only when connected */}
      {isConnected && (
        <div className="flex flex-1 overflow-hidden">
          {/* Desktop: two-panel layout */}
          {/* Mobile: single-panel (show list or detail) */}

          {/* Left panel: Email List */}
          <div
            className={`flex flex-col border-r ${
              selectedEmailId
                ? "hidden lg:flex"
                : "flex"
            } w-full lg:w-[380px] lg:shrink-0`}
          >
            {/* Connection status bar (compact, when connected) */}
            <div className="border-b px-3 py-2">
              <ConnectionPanel
                status={connectionStatus}
                email={connectedEmail}
                loading={statusLoading}
                error={statusError}
                onConnect={handleConnect}
                onDisconnect={handleDisconnectClick}
                onRetry={fetchStatus}
                connectLoading={connectLoading}
                disconnectLoading={disconnectLoading}
              />
            </div>

            {/* Email list */}
            <div className="flex-1 overflow-y-auto">
              <EmailList
                emails={emails}
                selectedId={selectedEmailId}
                loading={emailsLoading}
                onSelect={handleEmailSelect}
                connected={isConnected}
              />
            </div>
          </div>

          {/* Right panel: Email Detail */}
          <div
            className={`flex flex-1 flex-col overflow-hidden ${
              selectedEmailId
                ? "flex"
                : "hidden lg:flex"
            }`}
          >
            {selectedEmail ? (
              <div className="flex h-full flex-col overflow-hidden">
                <EmailDetail
                  email={selectedEmail}
                  onBack={handleBack}
                  onReply={handleReply}
                />

                {/* Label Manager */}
                {selectedEmail.label_ids.length > 0 && (
                  <div className="border-t px-6 py-3">
                    <LabelManager
                      messageId={selectedEmail.gmail_message_id}
                      labelIds={selectedEmail.label_ids}
                      onLabelsChange={handleLabelsChange}
                    />
                  </div>
                )}

                {/* Attachment Viewer */}
                <AttachmentViewer
                  messageId={selectedEmail.gmail_message_id}
                  hasAttachments={selectedEmail.has_attachments}
                />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-500">
                  Chọn một email để xem nội dung
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Compose Button */}
      {isConnected && (
        <button
          type="button"
          onClick={handleComposeOpen}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-medium text-white shadow-lg transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label="Soạn email mới"
        >
          <PenSquare className="h-5 w-5" />
          <span className="hidden sm:inline">Soạn email</span>
        </button>
      )}

      {/* Compose Dialog */}
      <ComposeDialog
        open={composeOpen}
        onClose={handleComposeClose}
        replyTo={replyToEmail}
      />

      {/* Disconnect Confirmation Dialog */}
      <ConfirmDialog
        open={disconnectDialogOpen}
        onConfirm={handleDisconnectConfirm}
        onCancel={handleDisconnectCancel}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export (wrapped with ToastProvider)
// ---------------------------------------------------------------------------

export default function GmailPage() {
  return (
    <ToastProvider>
      <GmailPageContent />
    </ToastProvider>
  );
}
