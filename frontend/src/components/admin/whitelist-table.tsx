"use client";

import { useState } from "react";
import { Trash2, FileText } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import type { WhitelistEntry } from "@/lib/api/admin";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WhitelistTableProps {
  entries: WhitelistEntry[];
  loading: boolean;
  onDelete: (id: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function WhitelistTable({
  entries,
  loading,
  onDelete,
}: WhitelistTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<WhitelistEntry | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleConfirmDelete = async () => {
    if (!deleteTarget?.id) return;
    setDeleting(true);
    try {
      await onDelete(deleteTarget.id);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("vi-VN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">Đang tải...</p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">
          Chưa có mục nào trong whitelist
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Giá trị</TableHead>
            <TableHead>Loại</TableHead>
            <TableHead>Nguồn</TableHead>
            <TableHead>Thêm bởi</TableHead>
            <TableHead>Ngày thêm</TableHead>
            <TableHead className="w-[80px]">Hành động</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry, index) => (
            <TableRow key={entry.id ?? `file-${index}`}>
              <TableCell className="font-medium">{entry.value}</TableCell>
              <TableCell>
                <Badge variant="secondary">
                  {entry.entry_type === "exact_email" ? "Email" : "Domain"}
                </Badge>
              </TableCell>
              <TableCell>
                {entry.source === "file" ? (
                  <Badge variant="outline" className="gap-1" aria-label="Nguồn: File">
                    <FileText className="h-3 w-3" aria-hidden="true" />
                    File
                  </Badge>
                ) : (
                  <Badge variant="default" aria-label="Nguồn: Database">Database</Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {entry.added_by_email || "—"}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(entry.created_at)}
              </TableCell>
              <TableCell>
                {!entry.is_readonly && entry.id ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-11 w-11 sm:h-8 sm:w-8 text-destructive hover:text-destructive"
                    onClick={() => setDeleteTarget(entry)}
                    aria-label={`Xóa ${entry.value}`}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    Chỉ đọc
                  </span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn xóa{" "}
              <span className="font-semibold">{deleteTarget?.value}</span> khỏi
              whitelist? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Hủy</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? "Đang xóa..." : "Xóa"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
