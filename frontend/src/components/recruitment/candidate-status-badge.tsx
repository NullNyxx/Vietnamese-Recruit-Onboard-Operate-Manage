import { Badge } from "@/components/ui/badge";
import {
  STATUS_COLORS,
  STATUS_LABELS,
  type CandidateStatus,
} from "@/lib/recruitment-utils";

interface CandidateStatusBadgeProps {
  status: CandidateStatus;
}

/**
 * Displays a candidate's status as a colored badge with a Vietnamese text label.
 * Both color and text are always visible to meet accessibility requirements
 * (never relies on color alone to convey status information).
 */
export function CandidateStatusBadge({ status }: CandidateStatusBadgeProps) {
  return (
    <Badge className={STATUS_COLORS[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
