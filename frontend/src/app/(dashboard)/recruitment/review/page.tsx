"use client";

import * as React from "react";
import { CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  listReviewQueue,
  submitCorrection,
  retryParse,
  dismissReview,
  getCVPresignedUrl,
} from "@/lib/api/recruitment";
import type {
  CVReviewItem,
  CVReviewListResponse,
  ParsedCVInput,
} from "@/lib/api/recruitment";
import { ApiError } from "@/lib/api/types";
import { ReviewItem } from "@/components/recruitment/review-item";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;
const DEFAULT_PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// Skeleton Loading Component
// ---------------------------------------------------------------------------

function ReviewSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border bg-card p-4 space-y-3"
        >
          <div className="flex items-center gap-3">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty State Component
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
      <p className="text-lg font-medium text-muted-foreground">
        Không có CV nào cần xem xét
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error State Component
// ---------------------------------------------------------------------------

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <p className="text-lg font-medium text-muted-foreground mb-4">
        Không thể tải danh sách
      </p>
      <Button variant="outline" onClick={onRetry}>
        <RefreshCw className="h-4 w-4 mr-2" />
        Thử lại
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pagination Component
// ---------------------------------------------------------------------------

function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 pt-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>Hiển thị</span>
        <Select
          value={String(pageSize)}
          onValueChange={(val) => onPageSizeChange(Number(val))}
        >
          <SelectTrigger className="h-8 w-[70px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span>mục / trang</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          Trang {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Trước
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Sau
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function CVReviewPage() {
  const [data, setData] = React.useState<CVReviewListResponse | null>(null);
  const [items, setItems] = React.useState<CVReviewItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(DEFAULT_PAGE_SIZE);

  // --- Fetch review queue ---
  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await listReviewQueue({ page, page_size: pageSize });
      setData(response);
      setItems(response.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  // --- Handlers ---

  const handlePageChange = React.useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = React.useCallback((newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  }, []);

  const handleSubmitCorrection = React.useCallback(
    async (cvDocumentId: string, correctionData: ParsedCVInput) => {
      try {
        await submitCorrection(cvDocumentId, correctionData);
        toast.success("Đã cập nhật CV thành công");
        // Remove item from list
        setItems((prev) => prev.filter((item) => item.id !== cvDocumentId));
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.statusCode === 404) {
            toast.error("CV không tồn tại hoặc đã bị xóa");
            setItems((prev) =>
              prev.filter((item) => item.id !== cvDocumentId)
            );
            return;
          }
          if (err.statusCode === 422) {
            // Re-throw so ReviewItem can capture validation errors
            throw err;
          }
          toast.error(err.message || "Đã xảy ra lỗi. Vui lòng thử lại.");
        } else {
          toast.error("Đã xảy ra lỗi. Vui lòng thử lại.");
        }
        throw err;
      }
    },
    []
  );

  const handleRetryParse = React.useCallback(
    async (cvDocumentId: string) => {
      try {
        const updatedItem = await retryParse(cvDocumentId);
        // Refresh item data in the list
        setItems((prev) =>
          prev.map((item) => (item.id === cvDocumentId ? updatedItem : item))
        );
        toast.success("Đã phân tích lại CV thành công");
      } catch (err) {
        if (err instanceof ApiError && err.statusCode === 404) {
          toast.error("CV không tồn tại hoặc đã bị xóa");
          setItems((prev) =>
            prev.filter((item) => item.id !== cvDocumentId)
          );
          return;
        }
        toast.error(
          err instanceof ApiError
            ? err.message
            : "Đã xảy ra lỗi. Vui lòng thử lại."
        );
      }
    },
    []
  );

  const handleDismiss = React.useCallback(async (cvDocumentId: string) => {
    try {
      await dismissReview(cvDocumentId);
      // Remove item from list on 204 success
      setItems((prev) => prev.filter((item) => item.id !== cvDocumentId));
      toast.success("Đã bỏ qua CV");
    } catch (err) {
      if (err instanceof ApiError && err.statusCode === 404) {
        toast.error("CV không tồn tại hoặc đã bị xóa");
        setItems((prev) =>
          prev.filter((item) => item.id !== cvDocumentId)
        );
        return;
      }
      toast.error(
        err instanceof ApiError
          ? err.message
          : "Đã xảy ra lỗi. Vui lòng thử lại."
      );
    }
  }, []);

  const handleViewOriginal = React.useCallback(
    async (cvDocumentId: string) => {
      // Find the item to get candidate_id
      const item = items.find((i) => i.id === cvDocumentId);
      if (!item || !item.candidate_id) {
        toast.error("Không thể mở CV gốc. Thiếu thông tin ứng viên.");
        return;
      }
      try {
        const response = await getCVPresignedUrl(item.candidate_id, cvDocumentId);
        window.open(response.presigned_url, "_blank");
      } catch {
        toast.error("Không thể tải tài liệu. Vui lòng thử lại.");
      }
    },
    [items]
  );

  // --- Render ---

  const total = data?.total ?? 0;

  return (
    <div className="space-y-6 p-6">
      {/* Page header */}
      <div>
        <h1 className="font-heading text-2xl font-bold">Xem xét CV</h1>
        <p className="text-sm text-muted-foreground">
          Xem xét và chỉnh sửa CV được phân tích tự động
        </p>
      </div>

      {/* Content */}
      {loading ? (
        <ReviewSkeleton />
      ) : error ? (
        <ErrorState onRetry={fetchData} />
      ) : items.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {/* Review items list */}
          <div className="space-y-4" aria-live="polite">
            {items.map((item) => (
              <ReviewItem
                key={item.id}
                item={item}
                onSubmitCorrection={handleSubmitCorrection}
                onRetryParse={handleRetryParse}
                onDismiss={handleDismiss}
                onViewOriginal={handleViewOriginal}
              />
            ))}
          </div>

          {/* Pagination */}
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </>
      )}
    </div>
  );
}
