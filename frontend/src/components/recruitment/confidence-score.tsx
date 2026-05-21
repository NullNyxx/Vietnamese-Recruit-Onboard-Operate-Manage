import { cn } from "@/lib/utils";
import { formatConfidence } from "@/lib/recruitment-utils";

interface ConfidenceScoreProps {
  /** Decimal confidence score from 0 to 1 */
  score: number;
}

/**
 * Returns the Tailwind CSS color class for the progress bar based on the percentage.
 * - 0–49%: destructive (red)
 * - 50–74%: warning (yellow/amber)
 * - 75–100%: primary (green/blue)
 */
function getProgressColor(percentage: number): string {
  if (percentage < 50) {
    return "bg-destructive";
  }
  if (percentage < 75) {
    return "bg-yellow-500 dark:bg-yellow-400";
  }
  return "bg-primary";
}

/**
 * Displays a confidence score as a percentage text with a colored progress bar.
 * Color thresholds: 0–49% = destructive (red), 50–74% = warning (yellow/amber), 75–100% = primary (green/blue).
 * Includes an aria-label for screen reader accessibility.
 */
export function ConfidenceScore({ score }: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);
  const displayText = formatConfidence(score);
  const colorClass = getProgressColor(percentage);

  return (
    <div
      className="flex items-center gap-2"
      aria-label={`Độ tin cậy: ${percentage}%`}
    >
      <span className="text-sm font-medium tabular-nums">{displayText}</span>
      <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", colorClass)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
