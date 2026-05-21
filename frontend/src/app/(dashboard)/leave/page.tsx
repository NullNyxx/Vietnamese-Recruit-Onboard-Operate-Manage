"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { CalendarPlus, CheckCircle, XCircle, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { leaveApi, employeesApi } from "@/lib/api";
import type { LeaveRequest } from "@/lib/api/leave";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

const statusLabels: Record<string, string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  rejected: "Từ chối",
  cancelled: "Đã hủy",
};

export default function LeavePage() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [employeeMap, setEmployeeMap] = useState<Record<string, string>>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [data, empRes] = await Promise.all([
        leaveApi.listRequests({ page: 1, page_size: 50 }),
        employeesApi.listEmployees({ page: 1, page_size: 100 }),
      ]);
      setRequests(data.items);
      setTotal(data.total);

      const map: Record<string, string> = {};
      for (const emp of empRes.items) {
        map[emp.id] = `${emp.full_name} (${emp.employee_code})`;
      }
      setEmployeeMap(map);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }

  async function fetchRequests() {
    try {
      const data = await leaveApi.listRequests({ page: 1, page_size: 50 });
      setRequests(data.items);
      setTotal(data.total);
    } catch {
      // Handle error silently
    }
  }

  async function handleApprove(id: string) {
    try {
      await leaveApi.approveRequest(id);
      fetchRequests();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi khi duyệt");
    }
  }

  async function handleReject(id: string) {
    const reason = prompt("Lý do từ chối (tùy chọn):");
    try {
      await leaveApi.rejectRequest(id, reason || undefined);
      fetchRequests();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi khi từ chối");
    }
  }
  const pendingCount = requests.filter((r) => r.status === "pending").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Quản lý Nghỉ phép</h1>
        <Button asChild>
          <Link href="/leave/request">
            <CalendarPlus className="h-4 w-4 mr-2" />
            Tạo đơn nghỉ
          </Link>
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Chờ duyệt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-yellow-500" />
              <span className="text-2xl font-bold">{pendingCount}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tổng đơn
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{total}</span>
          </CardContent>
        </Card>
      </div>

      {/* Requests table */}
      <Card>
        <CardHeader>
          <CardTitle>Danh sách đơn nghỉ phép</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : requests.length === 0 ? (
            <p className="text-muted-foreground">Chưa có đơn nghỉ phép nào.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nhân viên</TableHead>
                  <TableHead>Từ ngày</TableHead>
                  <TableHead>Đến ngày</TableHead>
                  <TableHead>Số ngày</TableHead>
                  <TableHead>Lý do</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell className="font-medium">
                      {employeeMap[req.employee_id] || req.employee_id.slice(0, 8)}
                    </TableCell>
                    <TableCell>{req.start_date}</TableCell>
                    <TableCell>{req.end_date}</TableCell>
                    <TableCell>{req.total_days}</TableCell>
                    <TableCell>{req.reason || "—"}</TableCell>
                    <TableCell>
                      <Badge className={statusColors[req.status] || ""}>
                        {statusLabels[req.status] || req.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {req.status === "pending" && (
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleApprove(req.id)}
                            title="Duyệt"
                          >
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleReject(req.id)}
                            title="Từ chối"
                          >
                            <XCircle className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
