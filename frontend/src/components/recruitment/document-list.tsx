"use client";

import { useState } from "react";
import { FileText, ExternalLink, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  type CVDocument,
  getCVPresignedUrl,
} from "@/lib/api/recruitment";
import { formatDate } from "@/lib/recruitment-utils";

// ---------------------------------------------------------------------------
// Processing status Vietnamese labels
// ---------------------------------------------------------------------------

const PROCESSING_STATUS_LABELS: Record<string, string> = {
  pending: "Đang chờ",
  ocr_processing: "Đang OCR",
  llm_parsing: "Đang phân tích",
  completed: "Hoàn thành",
  needs_review: "Cần xem xét",
  failed: "Thất bại",
  skipped: "Bỏ qua",
  dismissed: "Đã loại",
  upload_failed: "Tải lên thất bại",
  permanently_failed: "Thất bại vĩnh viễn",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DocumentListProps {
  documents: CVDocument[];
  candidateId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Displays a list of CV documents with filename, upload date, processing status,
 * and a "Xem CV" button for documents that are completed or need review.
 * Fetches a presigned URL and opens the document in a new tab on click.
 */
export function DocumentList({ documents, candidateId }: DocumentListProps) {
  const [loadingDocId, setLoadingDocId] = useState<string | null>(null);

  const canView = (status: string) =>
    status === "completed" || status === "needs_review";

  const handleViewCV = async (documentId: string) => {
    setLoadingDocId(documentId);
    try {
      const response = await getCVPresignedUrl(candidateId, documentId);
      window.open(response.presigned_url, "_blank");
    } catch {
      toast.error("Không thể tải tài liệu. Vui lòng thử lại.");
    } finally {
      setLoadingDocId(null);
    }
  };

  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Chưa có tài liệu nào</p>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center justify-between rounded-md border p-3"
        >
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">
                {doc.original_filename}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDate(doc.uploaded_at)} &middot;{" "}
                {PROCESSING_STATUS_LABELS[doc.processing_status] ??
                  doc.processing_status}
              </p>
            </div>
          </div>

          {canView(doc.processing_status) && (
            <Button
              variant="outline"
              size="sm"
              disabled={loadingDocId === doc.id}
              onClick={() => handleViewCV(doc.id)}
            >
              {loadingDocId === doc.id ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1" />
              ) : (
                <ExternalLink className="h-4 w-4 mr-1" />
              )}
              Xem CV
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
