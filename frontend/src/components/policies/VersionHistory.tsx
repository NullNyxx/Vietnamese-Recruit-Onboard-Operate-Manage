"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  GitCompare,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listVersions,
  rollbackVersion,
  type PolicyVersion,
  type PolicyVersionListResponse,
} from "@/lib/api/policies";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VersionHistoryProps {
  onViewDiff?: (versionA: number, versionB: number) => void;
  onRollback?: (newVersion: PolicyVersion) => void;
  refreshTrigger?: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Paginated list (20/page) with version number, date, publisher, change count.
 * Supports diff view and rollback actions.
 */
export function VersionHistory({
  onViewDiff,
  onRollback,
  refreshTrigger,
}: VersionHistoryProps) {
  const [data, setData] = useState<PolicyVersionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [rollingBack, setRollingBack] = useState<number | null>(null);

  const fetchVersions = useCallback(async (page: number) => {
    setLoading(true);
    try {
      const response = await listVersions({ page, page_size: PAGE_SIZE });
      setData(response);
    } catch {
      toast.error("Không thể tải lịch sử phiên bản");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVersions(currentPage);
  }, [currentPage, fetchVersions, refreshTrigger]);

  const handleRollback = useCallback(
    async (versionNumber: number) => {
      setRollingBack(versionNumber);
      try {
        const newVersion = await rollbackVersion(versionNumber);
        toast.success("Khôi phục thành công", {
          description: `Đã tạo phiên bản ${newVersion.version_number} từ phiên bản ${versionNumber}`,
        });
        onRollback?.(newVersion);
        // Refresh the list
        fetchVersions(currentPage);
      } catch {
        toast.error("Khôi phục thất bại", {
          description: "Đã xảy ra lỗi. Vui lòng thử lại.",
        });
      } finally {
        setRollingBack(null);
      }
    },
    [currentPage, fetchVersions, onRollback],
  );

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  if (loading && !data) {
    return <VersionHistorySkeleton />;
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-md border p-8 text-center">
        <Clock
          className="h-10 w-10 text-muted-foreground mb-3"
          aria-hidden="true"
        />
        <p className="text-sm text-muted-foreground">
          Chưa có phiên bản nào được xuất bản
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="rounded-md border divide-y">
        {data.items.map((version, index) => (
          <VersionRow
            key={version.id}
            version={version}
            isLatest={currentPage === 1 && index === 0}
            isRollingBack={rollingBack === version.version_number}
            onViewDiff={onViewDiff}
            onRollback={handleRollback}
            previousVersion={
              index < data.items.length - 1
                ? data.items[index + 1].version_number
                : undefined
            }
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2">
          <p className="text-sm text-muted-foreground">
            Trang {currentPage} / {totalPages} ({data.total} phiên bản)
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1 || loading}
              aria-label="Trang trước"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages || loading}
              aria-label="Trang sau"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Row sub-component
// ---------------------------------------------------------------------------

function VersionRow({
  version,
  isLatest,
  isRollingBack,
  onViewDiff,
  onRollback,
  previousVersion,
}: {
  version: PolicyVersion;
  isLatest: boolean;
  isRollingBack: boolean;
  onViewDiff?: (versionA: number, versionB: number) => void;
  onRollback: (versionNumber: number) => void;
  previousVersion?: number;
}) {
  const totalChanges =
    version.rules_added + version.rules_modified + version.rules_removed;

  return (
    <div className="flex items-center justify-between px-4 py-3 gap-4">
      {/* Left: version info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            Phiên bản {version.version_number}
          </span>
          {isLatest && (
            <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/20 dark:text-green-300">
              Hiện tại
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-xs text-muted-foreground">
            {formatDate(version.published_at)}
          </span>
          <span className="text-xs text-muted-foreground">
            {version.published_by}
          </span>
          <span className="text-xs text-muted-foreground">
            {totalChanges} thay đổi
          </span>
        </div>
        {version.change_summary && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {version.change_summary}
          </p>
        )}
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {previousVersion && onViewDiff && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1"
            onClick={() => onViewDiff(previousVersion, version.version_number)}
            aria-label={`So sánh phiên bản ${previousVersion} và ${version.version_number}`}
          >
            <GitCompare className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-xs">So sánh</span>
          </Button>
        )}
        {!isLatest && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1 text-amber-600 hover:text-amber-700"
            onClick={() => onRollback(version.version_number)}
            disabled={isRollingBack}
            aria-label={`Khôi phục phiên bản ${version.version_number}`}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-xs">Khôi phục</span>
          </Button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function VersionHistorySkeleton() {
  return (
    <div className="rounded-md border divide-y">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={`version-skeleton-${i}`}
          className="flex items-center justify-between px-4 py-3"
        >
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-56" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(isoString: string): string {
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}
