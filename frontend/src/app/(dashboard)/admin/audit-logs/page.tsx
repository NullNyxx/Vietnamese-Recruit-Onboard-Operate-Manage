"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import AuditLogTable from "@/components/admin/audit-log-table";
import { getAuditLogs, type AuditLog, type AuditLogQueryParams } from "@/lib/api/admin";
import { validateDateRange } from "@/lib/utils/format";

const PAGE_SIZE = 20;

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actionTypeFilter, setActionTypeFilter] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    // Prevent API call if date range is invalid
    if (startDate && endDate && !validateDateRange(startDate, endDate)) {
      return;
    }

    setLoading(true);
    try {
      const params: AuditLogQueryParams = {
        page,
        page_size: PAGE_SIZE,
      };
      if (actionTypeFilter && actionTypeFilter !== "all") {
        params.action_type = actionTypeFilter;
      }
      if (startDate) {
        params.start_date = startDate;
      }
      if (endDate) {
        params.end_date = endDate;
      }

      const result = await getAuditLogs(params);
      setLogs(result.items);
      setTotal(result.total);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Không thể tải nhật ký";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [page, actionTypeFilter, startDate, endDate]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  function handleActionTypeChange(value: string) {
    setActionTypeFilter(value);
    setPage(1);
  }

  function handleStartDateChange(value: string) {
    setStartDate(value);
    setPage(1);
  }

  function handleEndDateChange(value: string) {
    setEndDate(value);
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold font-heading tracking-tight">
        Nhật ký hoạt động
      </h1>

      <AuditLogTable
        logs={logs}
        total={total}
        page={page}
        pageSize={PAGE_SIZE}
        actionTypeFilter={actionTypeFilter}
        startDate={startDate}
        endDate={endDate}
        loading={loading}
        onPageChange={setPage}
        onActionTypeChange={handleActionTypeChange}
        onStartDateChange={handleStartDateChange}
        onEndDateChange={handleEndDateChange}
      />
    </div>
  );
}
