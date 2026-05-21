"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { AuditLog, AuditActionType } from "@/lib/api/admin";
import { validateDateRange } from "@/lib/utils/format";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuditLogTableProps {
  logs: AuditLog[];
  total: number;
  page: number;
  pageSize: number;
  actionTypeFilter: string;
  startDate: string;
  endDate: string;
  loading?: boolean;
  onPageChange: (page: number) => void;
  onActionTypeChange: (actionType: string) => void;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ACTION_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "whitelist_add", label: "Thêm whitelist" },
  { value: "whitelist_remove", label: "Xóa whitelist" },
  { value: "oauth_update", label: "Cập nhật OAuth" },
  { value: "role_change", label: "Thay đổi vai trò" },
];

function getActionBadgeVariant(
  actionType: AuditActionType
): "default" | "secondary" | "destructive" | "outline" {
  switch (actionType) {
    case "whitelist_add":
      return "default";
    case "whitelist_remove":
      return "destructive";
    case "oauth_update":
      return "secondary";
    case "role_change":
      return "outline";
    default:
      return "secondary";
  }
}

function getActionLabel(actionType: AuditActionType): string {
  switch (actionType) {
    case "whitelist_add":
      return "Thêm whitelist";
    case "whitelist_remove":
      return "Xóa whitelist";
    case "oauth_update":
      return "Cập nhật OAuth";
    case "role_change":
      return "Thay đổi vai trò";
    default:
      return actionType;
  }
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("vi-VN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDetails(details: Record<string, unknown>): string {
  const entries = Object.entries(details);
  if (entries.length === 0) return "—";
  return entries
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AuditLogTable({
  logs,
  total,
  page,
  pageSize,
  actionTypeFilter,
  startDate,
  endDate,
  loading = false,
  onPageChange,
  onActionTypeChange,
  onStartDateChange,
  onEndDateChange,
}: AuditLogTableProps) {
  const totalPages = Math.ceil(total / pageSize);

  // Date range validation
  const dateRangeInvalid =
    startDate !== "" && endDate !== "" && !validateDateRange(startDate, endDate);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-end gap-4">
        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">
            Loại hành động
          </label>
          <Select value={actionTypeFilter} onValueChange={onActionTypeChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Tất cả" />
            </SelectTrigger>
            <SelectContent>
              {ACTION_TYPE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">
            Từ ngày
          </label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="w-[160px]"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">
            Đến ngày
          </label>
          <Input
            type="date"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
            className="w-[160px]"
          />
        </div>
      </div>

      {/* Date range validation error */}
      {dateRangeInvalid && (
        <p className="text-sm text-destructive">
          Ngày kết thúc phải sau ngày bắt đầu
        </p>
      )}

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Thời gian</TableHead>
              <TableHead>Admin</TableHead>
              <TableHead>Hành động</TableHead>
              <TableHead>Chi tiết</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody aria-live="polite">
            {loading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8">
                  Đang tải...
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                  Không có bản ghi nào
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatTimestamp(log.created_at)}
                  </TableCell>
                  <TableCell>{log.admin_email}</TableCell>
                  <TableCell>
                    <Badge variant={getActionBadgeVariant(log.action_type)}>
                      {getActionLabel(log.action_type)}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate" title={formatDetails(log.details)}>
                    {formatDetails(log.details)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Trang {page} / {totalPages || 1} (Tổng: {total} bản ghi)
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-11 min-w-[44px] sm:h-8 sm:min-w-0"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || loading}
          >
            <ChevronLeft className="h-4 w-4" />
            Trước
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-11 min-w-[44px] sm:h-8 sm:min-w-0"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
          >
            Sau
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
