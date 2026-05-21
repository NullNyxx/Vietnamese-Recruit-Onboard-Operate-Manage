"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export interface RejectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => void;
  loading?: boolean;
}

export function RejectDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
}: RejectDialogProps) {
  const [reason, setReason] = React.useState("");
  const [touched, setTouched] = React.useState(false);

  const charCount = reason.length;
  const isValid = charCount >= 10 && charCount <= 500;
  const showError = touched && !isValid;

  function getErrorMessage(): string | null {
    if (!touched) return null;
    if (charCount === 0) return "Vui lòng nhập lý do từ chối";
    if (charCount < 10) return `Tối thiểu 10 ký tự (hiện tại: ${charCount})`;
    if (charCount > 500) return `Tối đa 500 ký tự (hiện tại: ${charCount})`;
    return null;
  }

  function handleConfirm() {
    setTouched(true);
    if (isValid) {
      onConfirm(reason);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen && !loading) {
      // Reset form state when closing (not on 5xx - parent controls open state)
      setReason("");
      setTouched(false);
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Từ chối ứng viên</DialogTitle>
          <DialogDescription>
            Vui lòng nhập lý do từ chối ứng viên này.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="reject-reason">Lý do từ chối</Label>
          <Textarea
            id="reject-reason"
            placeholder="Nhập lý do từ chối (10–500 ký tự)..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onBlur={() => setTouched(true)}
            maxLength={500}
            rows={4}
            aria-invalid={showError}
            aria-describedby={showError ? "reject-reason-error" : undefined}
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            {showError ? (
              <span
                id="reject-reason-error"
                className="text-destructive"
                role="alert"
              >
                {getErrorMessage()}
              </span>
            ) : (
              <span />
            )}
            <span>{charCount}/500</span>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Hủy
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={loading || !isValid}
          >
            {loading && <Loader2 className="animate-spin" />}
            Từ chối ứng viên
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
