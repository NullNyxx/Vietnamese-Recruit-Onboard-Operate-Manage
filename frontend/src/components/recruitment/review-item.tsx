"use client";

import * as React from "react";
import { ChevronDown, Eye, RefreshCw, X, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import type {
  CVReviewItem,
  ParsedCVInput,
  ValidationError,
} from "@/lib/api/recruitment";
import { CorrectionForm } from "./correction-form";
import { CVSections } from "./cv-sections";
import { ConfidenceScore } from "./confidence-score";
import { formatDate } from "@/lib/recruitment-utils";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Processing status labels (Vietnamese)
// ---------------------------------------------------------------------------

const PROCESSING_STATUS_LABELS: Record<string, string> = {
  pending: "Đang chờ",
  ocr_processing: "Đang OCR",
  llm_parsing: "Đang phân tích",
  completed: "Hoàn thành",
  needs_review: "Cần xem xét",
  failed: "Thất bại",
  skipped: "Đã bỏ qua",
  dismissed: "Đã loại bỏ",
  upload_failed: "Tải lên thất bại",
  permanently_failed: "Thất bại vĩnh viễn",
};

const PROCESSING_STATUS_COLORS: Record<string, string> = {
  needs_review:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  completed:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  pending: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ReviewItemProps {
  item: CVReviewItem;
  onSubmitCorrection: (
    cvDocumentId: string,
    data: ParsedCVInput
  ) => Promise<void>;
  onRetryParse: (cvDocumentId: string) => Promise<void>;
  onDismiss: (cvDocumentId: string) => Promise<void>;
  onViewOriginal: (cvDocumentId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReviewItem({
  item,
  onSubmitCorrection,
  onRetryParse,
  onDismiss,
  onViewOriginal,
}: ReviewItemProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [retryLoading, setRetryLoading] = React.useState(false);
  const [dismissLoading, setDismissLoading] = React.useState(false);
  const [correctionLoading, setCorrectionLoading] = React.useState(false);
  const [showDismissDialog, setShowDismissDialog] = React.useState(false);
  const [serverErrors, setServerErrors] = React.useState<
    ValidationError[] | null
  >(null);

  const candidateName =
    item.parsed_cv_data?.name || "Không rõ tên";
  const statusLabel =
    PROCESSING_STATUS_LABELS[item.processing_status] ?? item.processing_status;
  const statusColor =
    PROCESSING_STATUS_COLORS[item.processing_status] ??
    "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";

  // --- Handlers ---

  async function handleRetryParse() {
    setRetryLoading(true);
    const timeoutId = setTimeout(() => {
      setRetryLoading(false);
    }, 60_000);

    try {
      await onRetryParse(item.id);
    } finally {
      clearTimeout(timeoutId);
      setRetryLoading(false);
    }
  }

  async function handleDismiss() {
    setDismissLoading(true);
    try {
      await onDismiss(item.id);
    } finally {
      setDismissLoading(false);
      setShowDismissDialog(false);
    }
  }

  async function handleSubmitCorrection(data: ParsedCVInput) {
    setCorrectionLoading(true);
    setServerErrors(null);
    try {
      await onSubmitCorrection(item.id, data);
    } catch (err: unknown) {
      // If the parent throws with validation errors, capture them
      if (
        err &&
        typeof err === "object" &&
        "body" in err &&
        (err as { body?: { errors?: ValidationError[] } }).body?.errors
      ) {
        setServerErrors(
          (err as { body: { errors: ValidationError[] } }).body.errors
        );
      }
      throw err;
    } finally {
      setCorrectionLoading(false);
    }
  }

  return (
    <>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
          {/* Header (clickable to expand/collapse) */}
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 p-4 text-left hover:bg-muted/50 transition-colors rounded-t-lg"
              aria-expanded={isOpen}
            >
              <div className="flex flex-1 flex-wrap items-center gap-3 min-w-0">
                {/* Candidate name */}
                <span className="font-medium truncate">{candidateName}</span>

                {/* Filename */}
                <span className="text-sm text-muted-foreground truncate">
                  {item.original_filename}
                </span>

                {/* Processing status badge */}
                <Badge className={statusColor}>{statusLabel}</Badge>

                {/* Confidence score */}
                {item.confidence_score !== null && (
                  <ConfidenceScore score={item.confidence_score} />
                )}

                {/* Date */}
                <span className="text-sm text-muted-foreground">
                  {formatDate(item.created_at)}
                </span>
              </div>

              {/* Expand/collapse chevron */}
              <ChevronDown
                className={cn(
                  "h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200",
                  isOpen && "rotate-180"
                )}
              />
            </button>
          </CollapsibleTrigger>

          {/* Detail panel (expanded) */}
          <CollapsibleContent>
            <div className="border-t p-4 space-y-6">
              {/* Action buttons */}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onViewOriginal(item.id)}
                >
                  <Eye className="h-4 w-4 mr-1" />
                  Xem CV gốc
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetryParse}
                  disabled={retryLoading}
                >
                  {retryLoading ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-1" />
                  )}
                  Thử lại phân tích
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDismissDialog(true)}
                  disabled={dismissLoading}
                >
                  {dismissLoading ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <X className="h-4 w-4 mr-1" />
                  )}
                  Bỏ qua
                </Button>
              </div>

              {/* Content: Original parsed data + Correction form */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Left: Read-only original parsed data */}
                <div>
                  <h4 className="text-sm font-semibold mb-3">
                    Dữ liệu phân tích gốc
                  </h4>
                  <div className="rounded-md border p-4 bg-muted/30">
                    <CVSections
                      summary={item.parsed_cv_data?.summary}
                      skills={item.parsed_cv_data?.skills ?? []}
                      experience={item.parsed_cv_data?.experience ?? []}
                      education={item.parsed_cv_data?.education ?? []}
                    />
                  </div>
                </div>

                {/* Right: Editable correction form */}
                <div>
                  <h4 className="text-sm font-semibold mb-3">
                    Chỉnh sửa dữ liệu
                  </h4>
                  <CorrectionForm
                    initialData={item.parsed_cv_data}
                    onSubmit={handleSubmitCorrection}
                    loading={correctionLoading}
                    serverErrors={serverErrors}
                  />
                </div>
              </div>
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>

      {/* Dismiss confirmation dialog */}
      <AlertDialog open={showDismissDialog} onOpenChange={setShowDismissDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận bỏ qua</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn bỏ qua CV &quot;{item.original_filename}
              &quot;? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={dismissLoading}>
              Hủy
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDismiss}
              disabled={dismissLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {dismissLoading && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              Bỏ qua
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
