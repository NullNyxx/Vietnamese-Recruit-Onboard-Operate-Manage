"use client";

import * as React from "react";
import { Clock, CheckCircle, XCircle, Layers, RefreshCw, Loader2, AlertCircle } from "lucide-react";

import { getMetrics } from "@/lib/api/recruitment";
import type { MetricsResponse } from "@/lib/api/recruitment";
import { MetricCard } from "@/components/recruitment/metric-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const AUTO_REFRESH_INTERVAL_MS = 30_000;
const MANUAL_REFRESH_TIMEOUT_MS = 10_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatProcessingTime(ms: number): string {
  return (ms / 1000).toFixed(1) + "s";
}

function formatPercentage(ratio: number): string {
  return (ratio * 100).toFixed(1) + "%";
}

function formatQueueDepth(count: number): string {
  return String(Math.round(count));
}

// ---------------------------------------------------------------------------
// Skeleton Loading State
// ---------------------------------------------------------------------------

function MetricsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="flex items-center gap-4 p-6">
            <Skeleton className="h-12 w-12 rounded-lg shrink-0" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-7 w-16" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error State
// ---------------------------------------------------------------------------

function MetricsError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-4">
      <AlertCircle className="h-12 w-12 text-muted-foreground" />
      <p className="text-muted-foreground text-sm">Không thể tải số liệu</p>
      <Button variant="outline" onClick={onRetry}>
        Thử lại
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function MetricsDashboardPage() {
  const [metrics, setMetrics] = React.useState<MetricsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(false);
  const [refreshing, setRefreshing] = React.useState(false);

  // Fetch metrics data
  const fetchMetrics = React.useCallback(async () => {
    try {
      const data = await getMetrics();
      setMetrics(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  // Initial fetch on mount
  const loadMetrics = React.useCallback(async () => {
    setLoading(true);
    setError(false);
    await fetchMetrics();
    setLoading(false);
  }, [fetchMetrics]);

  React.useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  // Auto-refresh every 30 seconds while page is visible
  React.useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;

    function startInterval() {
      if (intervalId) return;
      intervalId = setInterval(() => {
        fetchMetrics();
      }, AUTO_REFRESH_INTERVAL_MS);
    }

    function stopInterval() {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        // Fetch immediately when becoming visible, then restart interval
        fetchMetrics();
        startInterval();
      } else {
        stopInterval();
      }
    }

    // Start interval if page is currently visible
    if (document.visibilityState === "visible") {
      startInterval();
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopInterval();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchMetrics]);

  // Manual refresh with 10s timeout
  const handleManualRefresh = React.useCallback(async () => {
    setRefreshing(true);

    const timeoutId = setTimeout(() => {
      setRefreshing(false);
    }, MANUAL_REFRESH_TIMEOUT_MS);

    try {
      await fetchMetrics();
    } finally {
      clearTimeout(timeoutId);
      setRefreshing(false);
    }
  }, [fetchMetrics]);

  // Retry after error (shows skeleton)
  const handleRetry = React.useCallback(() => {
    loadMetrics();
  }, [loadMetrics]);

  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Số liệu Pipeline</h1>
          <p className="text-muted-foreground text-sm">
            Thống kê xử lý CV trong 24 giờ qua
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleManualRefresh}
          disabled={refreshing || loading}
          aria-label="Làm mới"
        >
          {refreshing ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-2" />
          )}
          Làm mới
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <MetricsSkeleton />
      ) : error ? (
        <MetricsError onRetry={handleRetry} />
      ) : metrics ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Thời gian xử lý TB"
            value={formatProcessingTime(metrics.average_processing_time_ms)}
            icon={Clock}
            type="processing_time"
            rawValue={metrics.average_processing_time_ms}
          />
          <MetricCard
            label="Tỷ lệ thành công"
            value={formatPercentage(metrics.success_rate)}
            icon={CheckCircle}
            type="success_rate"
            rawValue={metrics.success_rate}
          />
          <MetricCard
            label="Tỷ lệ thất bại"
            value={formatPercentage(metrics.failure_rate)}
            icon={XCircle}
            type="failure_rate"
            rawValue={metrics.failure_rate}
          />
          <MetricCard
            label="Hàng đợi"
            value={formatQueueDepth(metrics.queue_depth)}
            icon={Layers}
            type="queue_depth"
            rawValue={metrics.queue_depth}
          />
        </div>
      ) : null}
    </div>
  );
}
