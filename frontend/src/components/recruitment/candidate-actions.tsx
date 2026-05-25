"use client";

import { useState } from "react";
import { Calendar, Mail, XCircle, CheckCircle, Archive } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  getValidActions,
  STATUS_LABELS,
  type CandidateStatus,
} from "@/lib/recruitment-utils";

/** Action types that correspond to state transitions + email (non-transition). */
export type ActionType = "schedule" | "email" | "reject" | "accept" | "archive";

export interface CandidateActionsProps {
  status: CandidateStatus;
  onScheduleInterview?: () => void;
  onSendEmail?: () => void;
  onReject?: () => void;
  onAccept?: () => void;
  onArchive?: () => void;
  /** When true, all action buttons are disabled (e.g., during a mutation). */
  disabled?: boolean;
}

/**
 * Maps action types to the target status they transition to.
 * "email" is not a state transition so it's excluded.
 */
const ACTION_TARGET_STATUS: Record<
  Exclude<ActionType, "email">,
  CandidateStatus
> = {
  schedule: "interview_scheduled",
  reject: "rejected",
  accept: "accepted",
  archive: "archived",
};

/** Vietnamese labels for each action button. */
const ACTION_LABELS: Record<ActionType, string> = {
  schedule: "Lên lịch PV",
  email: "Gửi email",
  reject: "Từ chối",
  accept: "Chấp nhận",
  archive: "Lưu trữ",
};

/** Icons for each action button. */
const ACTION_ICONS: Record<
  ActionType,
  React.ComponentType<{ className?: string }>
> = {
  schedule: Calendar,
  email: Mail,
  reject: XCircle,
  accept: CheckCircle,
  archive: Archive,
};

/** Button variants for each action type. */
const ACTION_VARIANTS: Record<
  ActionType,
  "default" | "destructive" | "outline" | "secondary" | "ghost"
> = {
  schedule: "default",
  email: "outline",
  reject: "destructive",
  accept: "default",
  archive: "secondary",
};

/**
 * Renders action buttons for a candidate based on their current status.
 * Valid transitions are enabled; invalid transitions are shown at 50% opacity
 * with a tooltip explaining why they're disabled.
 * "Gửi email" is always shown regardless of status.
 */
export function CandidateActions({
  status,
  onScheduleInterview,
  onSendEmail,
  onReject,
  onAccept,
  onArchive,
  disabled = false,
}: CandidateActionsProps) {
  const [, setDialogOpen] = useState<Record<ActionType, boolean>>({
    schedule: false,
    email: false,
    reject: false,
    accept: false,
    archive: false,
  });

  const validTargetStatuses = getValidActions(status);

  /** Check if a transition action is valid for the current status. */
  function isActionValid(action: Exclude<ActionType, "email">): boolean {
    const targetStatus = ACTION_TARGET_STATUS[action];
    return validTargetStatuses.includes(targetStatus);
  }

  /** Open a specific action dialog. */
  function openDialog(action: ActionType) {
    setDialogOpen((prev) => ({ ...prev, [action]: true }));
  }

  /** Handle button click: open dialog and invoke callback. */
  function handleAction(action: ActionType) {
    openDialog(action);
    switch (action) {
      case "schedule":
        onScheduleInterview?.();
        break;
      case "email":
        onSendEmail?.();
        break;
      case "reject":
        onReject?.();
        break;
      case "accept":
        onAccept?.();
        break;
      case "archive":
        onArchive?.();
        break;
    }
  }

  /** All transition actions (excluding email). */
  const transitionActions: Exclude<ActionType, "email">[] = [
    "schedule",
    "reject",
    "accept",
    "archive",
  ];

  return (
    <TooltipProvider>
      <div className="flex flex-wrap gap-2">
        {/* Transition action buttons */}
        {transitionActions.map((action) => {
          const Icon = ACTION_ICONS[action];
          const valid = isActionValid(action);
          const label = ACTION_LABELS[action];
          const variant = ACTION_VARIANTS[action];

          if (valid) {
            return (
              <Button
                key={action}
                variant={variant}
                size="sm"
                onClick={() => handleAction(action)}
                disabled={disabled}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Button>
            );
          }

          // Invalid transition: disabled with 50% opacity and tooltip
          return (
            <Tooltip key={action}>
              <TooltipTrigger asChild>
                <span className="inline-flex">
                  <Button
                    variant={variant}
                    size="sm"
                    disabled
                    className="opacity-50"
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  Không thể chuyển từ &quot;{STATUS_LABELS[status]}&quot; sang
                  &quot;{STATUS_LABELS[ACTION_TARGET_STATUS[action]]}&quot;
                </p>
              </TooltipContent>
            </Tooltip>
          );
        })}

        {/* "Gửi email" button — always shown regardless of status */}
        <Button
          variant={ACTION_VARIANTS.email}
          size="sm"
          onClick={() => handleAction("email")}
          disabled={disabled}
        >
          <Mail className="h-4 w-4" />
          {ACTION_LABELS.email}
        </Button>
      </div>
    </TooltipProvider>
  );
}

/** Expose dialog state helpers for parent components to use. */
export { type CandidateActionsProps as CandidateActionsComponentProps };
