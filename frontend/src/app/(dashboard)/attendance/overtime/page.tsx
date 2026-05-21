"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { attendanceApi, employeesApi } from "@/lib/api";
import type { OvertimeRequest } from "@/lib/api/attendance";
import type { Employee } from "@/lib/api/types";

const statusLabels: Record<string, string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  rejected: "Từ chối",
};

export default function OvertimePage() {
  const [requests, setRequests] = useState<OvertimeRequest[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [employeeId, setEmployeeId] = useState("");
  const [workDate, setWorkDate] = useState("");
  const [hours, setHours] = useState("2");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [otRes, empRes] = await Promise.all([
        attendanceApi.listOvertimeRequests({ page: 1, page_size: 50 }),
        employeesApi.listEmployees({ page: 1, page_size: 100 }),
      ]);
      setRequests(otRes.items);
      setEmployees(empRes.items);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!employeeId || !workDate || !reason) {
      alert("Vui lòng điền đầy đủ thông tin");
      return;
    }
    setSubmitting(true);
    try {
      await attendanceApi.createOvertimeRequest({
        employee_id: employeeId,
        work_date: workDate,
        planned_hours: parseFloat(hours),
        reason,
      });
      setReason("");
      setWorkDate("");
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(id: string) {
    try {
      await attendanceApi.approveOvertime(id);
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi");
    }
  }

  async function handleReject(id: string) {
    try {
      await attendanceApi.rejectOvertime(id);
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Quản lý Overtime</h1>

      {/* Create OT form */}
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Đăng ký OT</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nhân viên *</Label>
                <Select value={employeeId} onValueChange={setEmployeeId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Chọn NV" />
                  </SelectTrigger>
                  <SelectContent>
                    {employees.map((emp) => (
                      <SelectItem key={emp.id} value={emp.id}>
                        {emp.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Ngày OT *</Label>
                <Input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Số giờ (max 4h)</Label>
                <Input
                  type="number"
                  min="0.5"
                  max="4"
                  step="0.5"
                  value={hours}
                  onChange={(e) => setHours(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Lý do *</Label>
                <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Lý do OT" />
              </div>
            </div>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Đang tạo..." : "Đăng ký OT"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* OT requests list */}
      <Card>
        <CardHeader>
          <CardTitle>Danh sách OT</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nhân viên</TableHead>
                  <TableHead>Ngày</TableHead>
                  <TableHead>Số giờ</TableHead>
                  <TableHead>Lý do</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map((req) => (
                  <TableRow key={req.id}>
                    <TableCell>{req.employee_id.slice(0, 8)}...</TableCell>
                    <TableCell>{req.work_date}</TableCell>
                    <TableCell>{req.planned_hours}h</TableCell>
                    <TableCell>{req.reason}</TableCell>
                    <TableCell>
                      <Badge variant={req.status === "approved" ? "default" : "secondary"}>
                        {statusLabels[req.status] || req.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {req.status === "pending" && (
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => handleApprove(req.id)}>
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleReject(req.id)}>
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
