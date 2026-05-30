"use client";

import { useCallback, useState, useTransition } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { updateRule, type PolicyRule } from "@/lib/api/policies";

interface PolicyRuleToggleProps {
  rule: PolicyRule;
  onToggled?: (rule: PolicyRule, enabled: boolean) => void;
  onError?: (error: string) => void;
}

/**
 * Enabled/disabled toggle with optimistic UI update (< 1 second).
 * Reverts on server failure.
 */
export function PolicyRuleToggle({
  rule,
  onToggled,
  onError,
}: PolicyRuleToggleProps) {
  const [optimisticEnabled, setOptimisticEnabled] = useState(rule.enabled);
  const [isPending, startTransition] = useTransition();

  const handleToggle = useCallback(
    (checked: boolean) => {
      // Optimistic update — reflect immediately
      setOptimisticEnabled(checked);

      startTransition(async () => {
        try {
          await updateRule(rule.rule_id, { enabled: checked });
          onToggled?.(rule, checked);
        } catch {
          // Revert on failure
          setOptimisticEnabled(!checked);
          onError?.("Không thể cập nhật trạng thái quy định");
        }
      });
    },
    [rule, onToggled, onError],
  );

  return (
    <div className="flex items-center gap-2">
      <Switch
        id={`toggle-${rule.id}`}
        checked={optimisticEnabled}
        onCheckedChange={handleToggle}
        disabled={isPending}
        aria-label={
          optimisticEnabled
            ? `Tắt quy định ${rule.name}`
            : `Bật quy định ${rule.name}`
        }
      />
      <Label
        htmlFor={`toggle-${rule.id}`}
        className="text-xs text-muted-foreground cursor-pointer"
      >
        {optimisticEnabled ? "Bật" : "Tắt"}
      </Label>
    </div>
  );
}
