"use client";

import * as React from "react";
import { FileText, Image, File, Loader2, Paperclip } from "lucide-react";
import type { AttachmentMetadata } from "@/lib/api/types";
import { ApiError } from "@/lib/api/types";
import { getAttachments } from "@/lib/api/gmail";
import { formatFileSize } from "@/components/gmail/utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface AttachmentViewerProps {
  messageId: string;
  hasAttachments: boolean;
}

// ---------------------------------------------------------------------------
// MIME Type Icon Mapping
// ---------------------------------------------------------------------------

function getMimeTypeIcon(mimeType: string) {
  if (mimeType === "application/pdf") {
    return <File className="h-5 w-5 text-red-500" />;
  }
  if (
    mimeType ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    mimeType === "application/msword"
  ) {
    return <FileText className="h-5 w-5 text-blue-500" />;
  }
  if (mimeType.startsWith("image/")) {
    // eslint-disable-next-line jsx-a11y/alt-text -- This is a Lucide icon component, not an <img> tag
    return <Image className="h-5 w-5 text-green-500" />;
  }
  return <File className="h-5 w-5 text-gray-500" />;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AttachmentViewer({
  messageId,
  hasAttachments,
}: AttachmentViewerProps) {
  const [attachments, setAttachments] = React.useState<AttachmentMetadata[]>(
    [],
  );
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch attachments when messageId changes and hasAttachments is true
  const fetchAttachments = React.useCallback(async () => {
    if (!hasAttachments) return;

    setLoading(true);
    setError(null);

    try {
      const response = await getAttachments(messageId);
      setAttachments(response.attachments);
    } catch (err) {
      if (err instanceof ApiError) {
        setError("Không thể tải danh sách tệp đính kèm. Vui lòng thử lại.");
      } else {
        setError("Đã xảy ra lỗi khi tải tệp đính kèm.");
      }
    } finally {
      setLoading(false);
    }
  }, [messageId, hasAttachments]);

  React.useEffect(() => {
    fetchAttachments();
  }, [fetchAttachments]);

  // Don't render anything if no attachments
  if (!hasAttachments) {
    return null;
  }

  // Loading state
  if (loading) {
    return (
      <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Đang tải tệp đính kèm...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex flex-col items-start gap-2">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button
            type="button"
            onClick={fetchAttachments}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  // No attachments found
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
      {/* Header */}
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
        <Paperclip className="h-4 w-4" />
        <span>Tệp đính kèm ({attachments.length})</span>
      </div>

      {/* Attachment list */}
      <div className="space-y-2">
        {attachments.map((attachment) => (
          <a
            key={attachment.attachment_id}
            href={`/api/gmail/messages/${messageId}/attachments/${attachment.attachment_id}/download`}
            download={attachment.filename}
            className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            {getMimeTypeIcon(attachment.mime_type)}
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                {attachment.filename}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatFileSize(attachment.size_bytes)}
              </p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
