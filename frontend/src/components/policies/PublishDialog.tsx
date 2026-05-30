"use client";

import { useCallback, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { publishPolicy, type PolicyVersion } from "@/lib/api/policies";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PublishChangeSummary {
  added: number;
  modified: number;
  disabled: number;
}

interface PublishDialogProps {
  changeSummary: PublishChangeSummary;
  disabled?: boolean;
  onPublished?: (version: PolicyVersion) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Confirmation dialog showing added/modified/disabled rule counts.
 * Handles publish failure with error notification and retry.
 */
export function PublishDialog({
  changeSummary,
  disabled = false,
  onPublished,
}: PublishDialogProps) {
  const [open, setOpen] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [effectiveDate, setEffectiveDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [summary, setSummary] = useState("");

  const totalChanges =
    changeSummary.added + changeSummary.modified + changeSummary.disabled;

  const handlePublish = useCallback(async () => {
    setIsPublishing(true);
    try {
      const changeSummaryText =
        summary.trim() ||
        `Thêm ${changeSummary.added}, sửa ${changeSummary.modified}, tắt ${changeSummary.disabled} quy định`;

      const version = await publishPolicy({
        effective_date: effectiveDate,
        change_summary: changeSummaryText,
      });

      toast.success("Xuất bản thành công", {
        description: `Phiên bản ${version.version_number} đã được tạo`,
      });

      onPublished?.(version);
      setOpen(false);
      setSummary("");
    } catch {
      toast.error("Xuất bản thất bại", {
        description: "Đã xảy ra lỗi. Vui lòng thử lại.",
        action: {
          label: "Thử lại",
          onClick: () => handlePublish(),
        },
      });
    } finally {
      setIsPublishing(false);
    }
  }, [effectiveDate, summary, changeSummary, onPublished]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={disabled || totalChanges === 0}>
          <Upload className="h-4 w-4 mr-2" aria-hidden="true" />
          Xuất bản thay đổi
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Xuất bản chính sách</DialogTitle>
          <DialogDescription>
            Xác nhận xuất bản các thay đổi chính sách. Phiên bản mới sẽ được
            tạo.
          </DialogDescription>
        </DialogHeader>

        {/* Change summary */}
        <div className="space-y-3">
          <div className="rounded-md bg-muted p-4 space-y-2">
            <p className="text-sm font-medium">Tóm tắt thay đổi</p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md bg-green-50 p-2">
                <p className="text-lg font-bold text-green-700">
                  {changeSummary.added}
                </p>
                <p className="text-xs text-muted-foreground">Thêm mới</p>
              </div>
              <div className="rounded-md bg-amber-50 p-2">
                <p className="text-lg font-bold text-amber-700">
                  {changeSummary.modified}
                </p>
                <p className="text-xs text-muted-foreground">Đã sửa</p>
              </div>
              <div className="rounded-md bg-gray-100 p-2">
                <p className="text-lg font-bold text-gray-700">
                  {changeSummary.disabled}
                </p>
                <p className="text-xs text-muted-foreground">Đã tắt</p>
              </div>
            </div>
          </div>

          {/* Effective date */}
          <div className="space-y-1.5">
            <Label htmlFor="effective-date">Ngày hiệu lực</Label>
            <Input
              id="effective-date"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              disabled={isPublishing}
            />
          </div>

          {/* Change summary text */}
          <div className="space-y-1.5">
            <Label htmlFor="change-summary">Ghi chú (tùy chọn)</Label>
            <Input
              id="change-summary"
              placeholder="Mô tả ngắn về thay đổi..."
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              disabled={isPublishing}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isPublishing}
          >
            Hủy
          </Button>
          <Button onClick={handlePublish} disabled={isPublishing}>
            {isPublishing && (
              <Loader2
                className="h-4 w-4 mr-2 animate-spin"
                aria-hidden="true"
              />
            )}
            Xác nhận xuất bản
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
