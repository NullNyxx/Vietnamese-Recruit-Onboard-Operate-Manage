"use client";

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

export interface AcceptDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  loading?: boolean;
}

export function AcceptDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
}: AcceptDialogProps) {
  function handleOpenChange(nextOpen: boolean) {
    if (!loading) {
      onOpenChange(nextOpen);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Chấp nhận ứng viên</DialogTitle>
          <DialogDescription>
            Bạn có chắc chắn muốn chấp nhận ứng viên này?
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Hủy
          </Button>
          <Button onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="animate-spin" />}
            Chấp nhận
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
