"use client";

import * as React from "react";
import { PenSquare, Sparkles } from "lucide-react";

import type { ConnectionStatus, EmailMessage } from "@/lib/api/types";
import { ApiError } from "@/lib/api/types";
import * as gmailApi from "@/lib/api/gmail";

import { ToastProvider, useToast } from "@/components/gmail/toast-provider";
import { ConnectionPanel } from "@/components/gmail/connection-panel";
import { ConfirmDialog } from "@/components/gmail/confirm-dialog";
import { EmailList } from "@/components/gmail/email-list";
import { SyncIndicator } from "@/components/gmail/sync-indicator";
import { EmailDetail } from "@/components/gmail/email-detail";
import { ComposeDialog } from "@/components/gmail/compose-dialog";
import { AIClassificationBanner } from "@/components/gmail/ai-classification-banner";
import { EmailEmptyState } from "@/components/gmail/email-empty-state";

// ---------------------------------------------------------------------------
// Inner page component (needs ToastProvider context)
// ---------------------------------------------------------------------------

function GmailPageContent() {
  const { addToast } = useToast();

  // --- Connection state ---
  const [connectionStatus, setConnectionStatus] =
    React.useState<ConnectionStatus | null>(null);
  const [connectedEmail, setConnectedEmail] = React.useState<string | null>(
    null,
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
    null,
  );

  // --- Compose state ---
  const [composeOpen, setComposeOpen] = React.useState(false);
  const [replyToEmail, setReplyToEmail] = React.useState<EmailMessage | null>(
    null,
  );

  // --- Category filter state ---
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(
    null,
  );

  // --- Classification state ---
  const [classifying, setClassifying] = React.useState(false);
  const [classifyProgress, setClassifyProgress] = React.useState<string | null>(
    null,
  );

  // Derived: filtered emails by category
  const filteredEmails = React.useMemo(() => {
    if (selectedCategory === null) return emails;
    return emails.filter(
      (e) => (e.category || "uncategorized") === selectedCategory,
    );
  }, [emails, selectedCategory]);

  // Derived: selected email object
  const selectedEmail = React.useMemo(
    () => emails.find((e) => e.id === selectedEmailId) ?? null,
    [emails, selectedEmailId],
  );

  // --- Error handler (stable ref to avoid re-render loops) ---
  const handleApiErrorRef = React.useRef<(err: unknown) => void>(() => {});
  handleApiErrorRef.current = React.useCallback(
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
    [addToast],
  );

  const handleApiError = React.useCallback((err: unknown) => {
    handleApiErrorRef.current(err);
  }, []);

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
        err instanceof Error ? err.message : "Không thể kiểm tra trạng thái",
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
          body?.detail || "Không thể tải danh sách email",
        );
      }
      const data = await res.json();
      // Support both { items: [...] } and direct array response
      const emailList: EmailMessage[] = Array.isArray(data)
        ? data
        : (data.items ?? data.messages ?? []);
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

  // --- Classify handler ---
  const handleClassify = React.useCallback(async () => {
    setClassifying(true);
    setClassifyProgress("Đang chuẩn bị phân loại...");

    let totalClassified = 0;
    const totalToClassify = emails.filter(
      (e) => !e.category || e.category === "uncategorized",
    ).length;

    try {
      // Process in batches of 5 to avoid proxy timeout
      let remaining = totalToClassify;
      while (remaining > 0) {
        setClassifyProgress(
          `AI đang phân loại... (${totalClassified}/${totalToClassify})`,
        );

        const result = await gmailApi.classifyBatch(5);
        totalClassified += result.classified_count;
        remaining = result.remaining;

        // If nothing was classified in this batch, stop
        if (result.classified_count === 0) break;
      }

      setClassifyProgress(null);
      addToast(`AI đã phân loại ${totalClassified} email`, "success");
      await fetchEmails();
    } catch (err) {
      setClassifyProgress(null);
      if (totalClassified > 0) {
        addToast(
          `Đã phân loại ${totalClassified}/${totalToClassify} email (có lỗi)`,
          "error",
        );
        await fetchEmails();
      } else {
        handleApiError(err);
      }
    } finally {
      setClassifying(false);
    }
  }, [addToast, emails, fetchEmails, handleApiError]);

  // --- Determine if connected ---
  const isConnected = connectionStatus === "connected";

  return (
    <div className="gmail-fullbleed flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Hộp thư
          </h1>
          <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-[#e4f222]/10 px-2 py-0.5 text-[10px] font-semibold text-[#e4f222]">
            <Sparkles className="h-3 w-3" />
            AI phân loại
          </span>
        </div>
        {isConnected && (
          <div className="flex items-center gap-2">
            {/* Classify button in header — always visible when there are unclassified emails */}
            {emails.length > 0 &&
              emails.some(
                (e) => !e.category || e.category === "uncategorized",
              ) && (
                <button
                  type="button"
                  onClick={handleClassify}
                  disabled={classifying}
                  className="inline-flex items-center gap-1.5 rounded-md border border-[#e4f222]/30 bg-[#e4f222]/10 px-3 py-1.5 text-xs font-medium text-[#e4f222] hover:bg-[#e4f222]/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Sparkles
                    className={`h-3.5 w-3.5 ${classifying ? "animate-spin" : ""}`}
                  />
                  {classifying
                    ? "Đang phân loại..."
                    : `Phân loại (${emails.filter((e) => !e.category || e.category === "uncategorized").length})`}
                </button>
              )}
            <SyncIndicator
              onSyncComplete={handleSyncComplete}
              onConnectionLost={handleConnectionLost}
            />
          </div>
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
        <div className="flex flex-1 flex-col overflow-hidden relative min-h-0">
          {/* Classification progress overlay */}
          {classifying && classifyProgress && (
            <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#08090a]/80 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-4 rounded-xl border border-white/[0.08] bg-[#12141a] px-8 py-6 shadow-2xl">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#e4f222]/10">
                  <Sparkles className="h-6 w-6 text-[#e4f222] animate-pulse" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-[#f7f8f8]">
                    AI đang phân loại email
                  </p>
                  <p className="mt-1 text-xs text-[#8a8f98]">
                    {classifyProgress}
                  </p>
                </div>
                <div className="w-48 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <div className="h-full bg-[#e4f222] rounded-full animate-pulse w-2/3" />
                </div>
              </div>
            </div>
          )}
          {/* AI Classification Banner — always visible when connected */}
          <AIClassificationBanner
            emails={emails}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
            onClassify={handleClassify}
            classifying={classifying}
          />

          {/* Two-panel layout */}
          <div className="flex flex-1 min-h-0 overflow-hidden">
            {/* Left panel: Connection + Email List */}
            <div
              className={`flex flex-col border-r border-gray-200 dark:border-gray-700 ${
                selectedEmailId ? "hidden lg:flex" : "flex"
              } w-full lg:w-[380px] lg:shrink-0 h-full`}
            >
              {/* Connection status bar (compact) */}
              <div className="border-b border-gray-200 dark:border-gray-700 px-3 py-2">
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

              {/* Email list or empty state */}
              <div className="flex-1 overflow-y-auto">
                {!emailsLoading && filteredEmails.length === 0 ? (
                  <EmailEmptyState
                    isFirstSync={emails.length === 0}
                    onSync={() => {
                      const syncBtn = document.querySelector(
                        '[aria-label="Đồng bộ email"]',
                      ) as HTMLButtonElement | null;
                      syncBtn?.click();
                    }}
                  />
                ) : (
                  <EmailList
                    emails={filteredEmails}
                    selectedId={selectedEmailId}
                    loading={emailsLoading}
                    onSelect={handleEmailSelect}
                    connected={isConnected}
                  />
                )}
              </div>
            </div>

            {/* Right panel: Email Detail */}
            <div
              className={`flex flex-1 flex-col overflow-hidden h-full ${
                selectedEmailId ? "flex" : "hidden lg:flex"
              }`}
            >
              {selectedEmail ? (
                <div className="flex h-full flex-col overflow-hidden">
                  <EmailDetail
                    email={selectedEmail}
                    onBack={handleBack}
                    onReply={handleReply}
                  />
                </div>
              ) : (
                <div className="flex h-full items-center justify-center">
                  <div className="text-center">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Chọn một email để xem nội dung
                    </p>
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                      Email được AI phân loại tự động sau khi đồng bộ
                    </p>
                  </div>
                </div>
              )}
            </div>
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
