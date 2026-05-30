"use client";

import { useCallback, useState } from "react";
import { Pencil, Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  updateRule,
  type PolicyRule,
  type RuleCondition,
} from "@/lib/api/policies";

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

export interface ValidationError {
  field: string;
  message: string;
}

/**
 * Validates a rule value based on its condition type.
 * Returns null if valid, or a ValidationError if invalid.
 */
function validateRuleValue(
  value: string,
  condition: RuleCondition,
): ValidationError | null {
  if (value.trim() === "") {
    return { field: "value", message: "Giá trị không được để trống" };
  }

  // Numeric validation for threshold/comparison operators
  const numericOperators = [
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal",
    "between",
  ];

  if (numericOperators.includes(condition.operator)) {
    const num = Number(value);
    if (isNaN(num)) {
      return { field: "value", message: "Giá trị phải là số" };
    }
    if (num < 0) {
      return { field: "value", message: "Giá trị không được âm" };
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface PolicyRuleEditorProps {
  rule: PolicyRule;
  templateDefault?: unknown;
  onSaved?: (rule: PolicyRule) => void;
  onError?: (error: string) => void;
  onValidationChange?: (ruleId: string, hasError: boolean) => void;
}

/**
 * Inline editing component with visual marker for overridden values.
 * Shows the current value and allows editing with validation.
 */
export function PolicyRuleEditor({
  rule,
  templateDefault,
  onSaved,
  onError,
  onValidationChange,
}: PolicyRuleEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(
    formatConditionValue(rule.rule_condition.value),
  );
  const [validationError, setValidationError] =
    useState<ValidationError | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isOverridden =
    templateDefault !== undefined &&
    JSON.stringify(rule.rule_condition.value) !==
      JSON.stringify(templateDefault);

  const handleStartEdit = useCallback(() => {
    setIsEditing(true);
    setEditValue(formatConditionValue(rule.rule_condition.value));
    setValidationError(null);
  }, [rule.rule_condition.value]);

  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditValue(formatConditionValue(rule.rule_condition.value));
    setValidationError(null);
    onValidationChange?.(rule.rule_id, false);
  }, [rule.rule_condition.value, rule.rule_id, onValidationChange]);

  const handleValueChange = useCallback(
    (newValue: string) => {
      setEditValue(newValue);
      const error = validateRuleValue(newValue, rule.rule_condition);
      setValidationError(error);
      onValidationChange?.(rule.rule_id, error !== null);
    },
    [rule.rule_condition, rule.rule_id, onValidationChange],
  );

  const handleSave = useCallback(async () => {
    const error = validateRuleValue(editValue, rule.rule_condition);
    if (error) {
      setValidationError(error);
      onValidationChange?.(rule.rule_id, true);
      return;
    }

    setIsSaving(true);
    try {
      const parsedValue = parseConditionValue(editValue, rule.rule_condition);
      const updatedCondition: RuleCondition = {
        ...rule.rule_condition,
        value: parsedValue,
      };
      await updateRule(rule.rule_id, { rule_condition: updatedCondition });
      setIsEditing(false);
      setValidationError(null);
      onValidationChange?.(rule.rule_id, false);
      onSaved?.({ ...rule, rule_condition: updatedCondition });
    } catch {
      onError?.("Không thể lưu thay đổi");
    } finally {
      setIsSaving(false);
    }
  }, [editValue, rule, onSaved, onError, onValidationChange]);

  return (
    <div className="flex items-center gap-2">
      {!isEditing ? (
        <>
          <span className="text-sm font-mono">
            {formatConditionValue(rule.rule_condition.value)}
          </span>

          {isOverridden && (
            <Badge
              variant="outline"
              className="border-amber-500 text-amber-600 dark:text-amber-400 text-xs"
            >
              Đã thay đổi
            </Badge>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={handleStartEdit}
            aria-label={`Chỉnh sửa ${rule.name}`}
          >
            <Pencil className="h-3.5 w-3.5" />
          </Button>

          {isOverridden && templateDefault !== undefined && (
            <span className="text-xs text-muted-foreground">
              (Mặc định: {formatConditionValue(templateDefault)})
            </span>
          )}
        </>
      ) : (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1">
            <Input
              value={editValue}
              onChange={(e) => handleValueChange(e.target.value)}
              className={`h-8 w-32 text-sm font-mono ${
                validationError
                  ? "border-destructive focus-visible:ring-destructive"
                  : ""
              }`}
              disabled={isSaving}
              aria-label={`Giá trị mới cho ${rule.name}`}
              aria-invalid={validationError !== null}
              aria-describedby={
                validationError ? `error-${rule.rule_id}` : undefined
              }
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") handleCancel();
              }}
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-green-600"
              onClick={handleSave}
              disabled={isSaving || validationError !== null}
              aria-label="Lưu"
            >
              <Check className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-muted-foreground"
              onClick={handleCancel}
              disabled={isSaving}
              aria-label="Hủy"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
          {validationError && (
            <p
              id={`error-${rule.rule_id}`}
              className="text-xs text-destructive"
              role="alert"
            >
              {validationError.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatConditionValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function parseConditionValue(input: string, condition: RuleCondition): unknown {
  const numericOperators = [
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal",
  ];

  if (numericOperators.includes(condition.operator)) {
    return Number(input);
  }

  if (condition.operator === "between") {
    // Try to parse as JSON array [min, max]
    try {
      const parsed = JSON.parse(input);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      // Fall through to return as string
    }
    return Number(input);
  }

  if (
    condition.operator === "in_list" ||
    condition.operator === "not_in_list"
  ) {
    try {
      return JSON.parse(input);
    } catch {
      return input.split(",").map((s) => s.trim());
    }
  }

  if (condition.operator === "is_null") {
    return null;
  }

  // For equals/not_equals, try number first
  const num = Number(input);
  if (!isNaN(num) && input.trim() !== "") return num;

  return input;
}

// Export validation helper for use in parent components
export { validateRuleValue };
