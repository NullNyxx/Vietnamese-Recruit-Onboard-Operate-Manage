"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Minus, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getVersionDiff,
  type PolicyDiffResponse,
  type RuleDiffEntry,
} from "@/lib/api/policies";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VersionDiffProps {
  versionA: number;
  versionB: number;
  onBack?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Diff view between two versions showing added, removed, modified, and
 * unchanged rules.
 */
export function VersionDiff({ versionA, versionB, onBack }: VersionDiffProps) {
  const [diff, setDiff] = useState<PolicyDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDiff = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getVersionDiff(versionA, versionB);
      setDiff(data);
    } catch {
      toast.error("Không thể tải so sánh phiên bản");
    } finally {
      setLoading(false);
    }
  }, [versionA, versionB]);

  useEffect(() => {
    fetchDiff();
  }, [fetchDiff]);

  if (loading) {
    return <VersionDiffSkeleton />;
  }

  if (!diff) {
    return (
      <div className="flex flex-col items-center justify-center rounded-md border p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Không thể tải dữ liệu so sánh
        </p>
        {onBack && (
          <Button variant="outline" className="mt-4" onClick={onBack}>
            Quay lại
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            aria-label="Quay lại lịch sử"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
        )}
        <h3 className="text-sm font-medium">
          So sánh phiên bản {diff.version_a} → {diff.version_b}
        </h3>
      </div>

      {/* Summary badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-0">
          <Plus className="h-3 w-3 mr-1" aria-hidden="true" />
          {diff.rules_added.length} thêm
        </Badge>
        <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 border-0">
          <Pencil className="h-3 w-3 mr-1" aria-hidden="true" />
          {diff.rules_modified.length} sửa
        </Badge>
        <Badge className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-0">
          <Minus className="h-3 w-3 mr-1" aria-hidden="true" />
          {diff.rules_removed.length} xóa
        </Badge>
        <Badge variant="outline">{diff.rules_unchanged.length} không đổi</Badge>
      </div>

      {/* Diff sections */}
      <div className="space-y-3">
        {diff.rules_added.length > 0 && (
          <DiffSection
            title="Quy định thêm mới"
            entries={diff.rules_added}
            variant="added"
          />
        )}

        {diff.rules_modified.length > 0 && (
          <DiffSection
            title="Quy định đã sửa"
            entries={diff.rules_modified}
            variant="modified"
          />
        )}

        {diff.rules_removed.length > 0 && (
          <DiffSection
            title="Quy định đã xóa"
            entries={diff.rules_removed}
            variant="removed"
          />
        )}

        {diff.rules_unchanged.length > 0 && (
          <DiffSection
            title="Quy định không đổi"
            entries={diff.rules_unchanged}
            variant="unchanged"
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type DiffVariant = "added" | "modified" | "removed" | "unchanged";

const variantStyles: Record<DiffVariant, string> = {
  added: "border-l-green-500 bg-green-50/50 dark:bg-green-900/10",
  modified: "border-l-amber-500 bg-amber-50/50 dark:bg-amber-900/10",
  removed: "border-l-red-500 bg-red-50/50 dark:bg-red-900/10",
  unchanged: "border-l-gray-300 bg-gray-50/50 dark:bg-gray-800/30",
};

function DiffSection({
  title,
  entries,
  variant,
}: {
  title: string;
  entries: RuleDiffEntry[];
  variant: DiffVariant;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {title}
      </p>
      <div className="rounded-md border divide-y">
        {entries.map((entry) => (
          <div
            key={entry.rule_id}
            className={`px-4 py-2.5 border-l-4 ${variantStyles[variant]}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{entry.name}</span>
              <span className="text-xs text-muted-foreground font-mono">
                {entry.rule_id}
              </span>
            </div>
            {entry.details && (
              <div className="mt-1 text-xs text-muted-foreground">
                {Object.entries(entry.details).map(([key, value]) => (
                  <span key={key} className="mr-3">
                    <span className="font-medium">{key}:</span>{" "}
                    {JSON.stringify(value)}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function VersionDiffSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-6 w-48" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-20" />
      </div>
      <div className="rounded-md border divide-y">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={`diff-skeleton-${i}`} className="px-4 py-2.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-24 mt-1" />
          </div>
        ))}
      </div>
    </div>
  );
}
