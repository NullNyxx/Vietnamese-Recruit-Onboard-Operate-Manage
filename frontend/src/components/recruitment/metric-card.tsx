import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { LucideIcon } from "lucide-react";

/**
 * Metric types that determine which color-coding threshold to apply.
 */
export type MetricType =
  | "success_rate"
  | "failure_rate"
  | "queue_depth"
  | "processing_time";

interface MetricCardProps {
  /** Descriptive label for the metric */
  label: string;
  /** Formatted display value (e.g. "85.2%", "3.4s", "12") */
  value: string;
  /** Lucide icon to display */
  icon: LucideIcon;
  /** Metric type used to determine color-coding threshold */
  type: MetricType;
  /** Raw numeric value used for threshold comparison */
  rawValue?: number;
  /** Whether the card is in a loading state */
  loading?: boolean;
}

/**
 * Returns the Tailwind color classes for the metric value based on type and threshold.
 *
 * Thresholds (from Requirements 7.7):
 * - success_rate > 0.80 → green (success)
 * - failure_rate > 0.20 → red (destructive)
 * - queue_depth > 50 → amber (warning)
 * - All others / below threshold → default foreground
 */
function getValueColorClass(type: MetricType, rawValue?: number): string {
  if (rawValue === undefined) return "";

  switch (type) {
    case "success_rate":
      return rawValue > 0.8
        ? "text-green-600 dark:text-green-400"
        : "";
    case "failure_rate":
      return rawValue > 0.2
        ? "text-red-600 dark:text-red-400"
        : "";
    case "queue_depth":
      return rawValue > 50
        ? "text-amber-600 dark:text-amber-400"
        : "";
    default:
      return "";
  }
}

/**
 * MetricCard displays a pipeline metric with an icon, label, and value.
 * Extends the StatCard pattern with conditional color coding based on
 * metric-specific thresholds.
 *
 * The value is rendered at 1.5× body text size (text-2xl = 1.5rem).
 */
export function MetricCard({
  label,
  value,
  icon: Icon,
  type,
  rawValue,
  loading,
}: MetricCardProps) {
  const valueColorClass = getValueColorClass(type, rawValue);

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-6">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-6 w-6 text-primary" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="h-7 w-16" />
          ) : (
            <p className={`text-2xl font-bold font-heading ${valueColorClass}`}>
              {value}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
