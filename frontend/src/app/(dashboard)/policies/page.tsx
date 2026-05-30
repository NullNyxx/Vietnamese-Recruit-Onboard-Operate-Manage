"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  Clock,
  CalendarDays,
  AlertTriangle,
  Timer,
  History,
} from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

import {
  listRules,
  type PolicyDomain,
  type PolicyRule,
  type PolicyRulesGrouped,
} from "@/lib/api/policies";
import { PolicyRuleList } from "@/components/policies/PolicyRuleList";
import {
  PublishDialog,
  type PublishChangeSummary,
} from "@/components/policies/PublishDialog";
import { VersionHistory } from "@/components/policies/VersionHistory";
import { VersionDiff } from "@/components/policies/VersionDiff";

// ---------------------------------------------------------------------------
// Domain Tab Configuration
// ---------------------------------------------------------------------------

const DOMAIN_TABS: {
  value: PolicyDomain;
  label: string;
  icon: React.ElementType;
}[] = [
  { value: "attendance", label: "Chấm công", icon: Clock },
  { value: "leave", label: "Nghỉ phép", icon: CalendarDays },
  { value: "overtime", label: "Tăng ca", icon: Timer },
  { value: "disciplinary", label: "Kỷ luật", icon: AlertTriangle },
];

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function PoliciesPage() {
  const [rulesGrouped, setRulesGrouped] = useState<PolicyRulesGrouped | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<PolicyDomain>("attendance");
  const [hasValidationErrors, setHasValidationErrors] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [diffVersions, setDiffVersions] = useState<{
    a: number;
    b: number;
  } | null>(null);
  const [versionRefresh, setVersionRefresh] = useState(0);

  const fetchRules = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listRules();
      setRulesGrouped(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách chính sách";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleRetry = useCallback(() => {
    fetchRules();
  }, [fetchRules]);

  const handleRuleUpdated = useCallback(
    (updatedRule: PolicyRule) => {
      if (!rulesGrouped) return;
      setRulesGrouped({
        ...rulesGrouped,
        [updatedRule.domain]: rulesGrouped[updatedRule.domain].map((r) =>
          r.id === updatedRule.id ? updatedRule : r,
        ),
      });
    },
    [rulesGrouped],
  );

  const handleRuleToggled = useCallback(
    (rule: PolicyRule, enabled: boolean) => {
      if (!rulesGrouped) return;
      setRulesGrouped({
        ...rulesGrouped,
        [rule.domain]: rulesGrouped[rule.domain].map((r) =>
          r.id === rule.id ? { ...r, enabled } : r,
        ),
      });
    },
    [rulesGrouped],
  );

  const handlePublished = useCallback(() => {
    setVersionRefresh((v) => v + 1);
    fetchRules();
  }, [fetchRules]);

  const handleRollback = useCallback(() => {
    setVersionRefresh((v) => v + 1);
    fetchRules();
  }, [fetchRules]);

  const handleViewDiff = useCallback((a: number, b: number) => {
    setDiffVersions({ a, b });
  }, []);

  // Compute change summary for publish dialog
  const changeSummary: PublishChangeSummary = {
    added: 0,
    modified: 0,
    disabled: 0,
  };
  if (rulesGrouped) {
    for (const domain of Object.values(rulesGrouped)) {
      for (const rule of domain) {
        if (rule.is_custom) changeSummary.added++;
        else if (!rule.enabled) changeSummary.disabled++;
        else if (rule.template_rule_id) changeSummary.modified++;
      }
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-primary" aria-hidden="true" />
            <h1 className="font-heading text-2xl font-bold">
              Chính sách công ty
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Quản lý và cấu hình các quy định nội bộ theo từng lĩnh vực
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setShowHistory(!showHistory);
              setDiffVersions(null);
            }}
            className="gap-1"
          >
            <History className="h-4 w-4" aria-hidden="true" />
            {showHistory ? "Ẩn lịch sử" : "Lịch sử"}
          </Button>
          <PublishDialog
            changeSummary={changeSummary}
            disabled={hasValidationErrors}
            onPublished={handlePublished}
          />
        </div>
      </div>

      {/* Validation warning */}
      {hasValidationErrors && (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3">
          <p className="text-sm text-destructive">
            Có lỗi xác thực. Vui lòng sửa trước khi xuất bản.
          </p>
        </div>
      )}

      {/* Version History Panel */}
      {showHistory && !diffVersions && (
        <div className="rounded-md border p-4 space-y-3">
          <h2 className="text-sm font-medium">Lịch sử phiên bản</h2>
          <VersionHistory
            onViewDiff={handleViewDiff}
            onRollback={handleRollback}
            refreshTrigger={versionRefresh}
          />
        </div>
      )}

      {/* Version Diff View */}
      {diffVersions && (
        <div className="rounded-md border p-4">
          <VersionDiff
            versionA={diffVersions.a}
            versionB={diffVersions.b}
            onBack={() => setDiffVersions(null)}
          />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center rounded-md border p-12 text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={handleRetry} variant="outline">
            Thử lại
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading && <PolicyPageSkeleton />}

      {/* Domain Tabs */}
      {!loading && !error && (
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as PolicyDomain)}
          className="w-full"
        >
          <TabsList aria-label="Lĩnh vực chính sách">
            {DOMAIN_TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                  className="gap-2"
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span>{tab.label}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {DOMAIN_TABS.map((tab) => (
            <TabsContent key={tab.value} value={tab.value}>
              <PolicyRuleList
                rules={rulesGrouped?.[tab.value] ?? []}
                loading={loading}
                onRuleUpdated={handleRuleUpdated}
                onRuleToggled={handleRuleToggled}
                onValidationChange={setHasValidationErrors}
              />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PolicyPageSkeleton() {
  return (
    <div className="space-y-4">
      {/* Tab skeleton */}
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={`tab-skeleton-${i}`} className="h-10 w-28" />
        ))}
      </div>
      {/* Content skeleton */}
      <div className="rounded-md border divide-y">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={`rule-skeleton-${i}`}
            className="flex items-center justify-between px-4 py-3"
          >
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-72" />
            </div>
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}
