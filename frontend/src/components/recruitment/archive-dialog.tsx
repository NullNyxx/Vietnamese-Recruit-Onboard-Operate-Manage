"use client";

import { Loader2, AlertTriangle } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export interface ArchiveDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  loading?: boolean;
}

export function ArchiveDialog({
  open,
  onOpenChange,
  onConfirm,
  loading = false,
}: ArchiveDialogProps) {
  function handleOpenChange(nextOpen: boolean) {
    if (!loading) {
      onOpenChange(nextOpen);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Lưu trữ ứng viên</DialogTitle>
          <DialogDescription>
            Bạn có chắc chắn muốn lưu trữ ứng viên này?
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-start gap-3 rounded-md border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-900 dark:bg-yellow-950">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-yellow-600 dark:text-yellow-400" />
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Ứng viên sẽ được chuyển sang trạng thái lưu trữ. Bạn có thể khôi
            phục ứng viên sau nếu cần.
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Hủy
          </Button>
          <Button variant="secondary" onClick={onConfirm} disabled={loading}>
            {loading && <Loader2 className="animate-spin" />}
            Lưu trữ
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
