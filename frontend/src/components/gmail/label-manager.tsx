"use client";

import * as React from "react";
import { X } from "lucide-react";
import { getLabelCategory, LABEL_COLORS } from "./utils";
import { removeLabel } from "@/lib/api/gmail";
import { useToast } from "./toast-provider";
import { cn } from "@/lib/utils";

interface LabelManagerProps {
  messageId: string;
  labelIds: string[];
  onLabelsChange: (newLabelIds: string[]) => void;
}

export function LabelManager({
  messageId,
  labelIds,
  onLabelsChange,
}: LabelManagerProps) {
  const { addToast } = useToast();

  // Filter to only VroomHR labels
  const vroomLabels = labelIds.filter(
    (id) => getLabelCategory(id) !== null
  );

  const handleRemove = async (labelId: string) => {
    const category = getLabelCategory(labelId);
    if (!category) return;

    // Optimistic UI: remove badge immediately
    const newLabelIds = labelIds.filter((id) => id !== labelId);
    onLabelsChange(newLabelIds);

    try {
      await removeLabel(messageId, category);
    } catch {
      // Restore badge on failure
      onLabelsChange(labelIds);
      addToast("Không thể gỡ nhãn. Vui lòng thử lại.", "error");
    }
  };

  if (vroomLabels.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {vroomLabels.map((labelId) => {
        const category = getLabelCategory(labelId)!;
        const colors = LABEL_COLORS[category] ?? {
          bg: "bg-gray-100",
          text: "text-gray-700",
        };

        return (
          <span
            key={labelId}
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
              colors.bg,
              colors.text
            )}
          >
            {category}
            <button
              type="button"
              onClick={() => handleRemove(labelId)}
              className="ml-0.5 inline-flex items-center rounded-full p-0.5 hover:bg-black/10 transition-colors"
              aria-label={`Gỡ nhãn ${category}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        );
      })}
    </div>
  );
}
