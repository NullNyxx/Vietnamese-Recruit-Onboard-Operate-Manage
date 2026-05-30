"use client";

import { useCallback, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { type PolicyRule } from "@/lib/api/policies";
import { PolicyRuleEditor } from "./PolicyRuleEditor";
import { PolicyRuleToggle } from "./PolicyRuleToggle";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 50;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PolicyRuleListProps {
  rules: PolicyRule[];
  templateDefaults?: Map<string, unknown>;
  loading?: boolean;
  onRuleUpdated?: (rule: PolicyRule) => void;
  onRuleToggled?: (rule: PolicyRule, enabled: boolean) => void;
  onValidationChange?: (hasErrors: boolean) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Paginated list (max 50/page) showing rule name, current value,
 * template default, and enabled status.
 */
export function PolicyRuleList({
  rules,
  templateDefaults,
  loading = false,
  onRuleUpdated,
  onRuleToggled,
  onValidationChange,
}: PolicyRuleListProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [, setValidationErrors] = useState<Set<string>>(new Set());

  const totalPages = Math.max(1, Math.ceil(rules.length / PAGE_SIZE));
  const paginatedRules = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return rules.slice(start, start + PAGE_SIZE);
  }, [rules, currentPage]);

  const handleValidationChange = useCallback(
    (ruleId: string, hasError: boolean) => {
      setValidationErrors((prev) => {
        const next = new Set(prev);
        if (hasError) {
          next.add(ruleId);
        } else {
          next.delete(ruleId);
        }
        onValidationChange?.(next.size > 0);
        return next;
      });
    },
    [onValidationChange],
  );

  const handlePageChange = useCallback(
    (page: number) => {
      setCurrentPage(Math.max(1, Math.min(page, totalPages)));
    },
    [totalPages],
  );

  if (loading) {
    return <PolicyRuleListSkeleton />;
  }

  if (rules.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-md border p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Không có quy định nào trong lĩnh vực này
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Rules list */}
      <div className="rounded-md border divide-y">
        {paginatedRules.map((rule) => (
          <PolicyRuleRow
            key={rule.id}
            rule={rule}
            templateDefault={templateDefaults?.get(rule.rule_id)}
            onRuleUpdated={onRuleUpdated}
            onRuleToggled={onRuleToggled}
            onValidationChange={handleValidationChange}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2">
          <p className="text-sm text-muted-foreground">
            Trang {currentPage} / {totalPages} ({rules.length} quy định)
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Trang trước"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
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

function PolicyRuleRow({
  rule,
  templateDefault,
  onRuleUpdated,
  onRuleToggled,
  onValidationChange,
}: {
  rule: PolicyRule;
  templateDefault?: unknown;
  onRuleUpdated?: (rule: PolicyRule) => void;
  onRuleToggled?: (rule: PolicyRule, enabled: boolean) => void;
  onValidationChange?: (ruleId: string, hasError: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 gap-4">
      {/* Left: name + description */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{rule.name}</span>
          {rule.is_custom && (
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
              Tùy chỉnh
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate mt-0.5">
          {rule.description}
        </p>
      </div>

      {/* Center: value editor */}
      <div className="flex-shrink-0">
        <PolicyRuleEditor
          rule={rule}
          templateDefault={templateDefault}
          onSaved={onRuleUpdated}
          onValidationChange={onValidationChange}
        />
      </div>

      {/* Right: toggle */}
      <div className="flex-shrink-0">
        <PolicyRuleToggle rule={rule} onToggled={onRuleToggled} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function PolicyRuleListSkeleton() {
  return (
    <div className="rounded-md border divide-y">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={`skeleton-${i}`}
          className="flex items-center justify-between px-4 py-3"
        >
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-72" />
          </div>
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-6 w-11 ml-4" />
        </div>
      ))}
    </div>
  );
}
