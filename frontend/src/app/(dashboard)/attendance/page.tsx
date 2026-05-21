"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Clock, Users, Timer, CalendarDays } from "lucide-react";

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
import { attendanceApi, employeesApi } from "@/lib/api";
import type { AttendanceRecord } from "@/lib/api/attendance";
import type { Employee } from "@/lib/api/types";

const statusColors: Record<string, string> = {
  present: "bg-green-100 text-green-800",
  late: "bg-yellow-100 text-yellow-800",
  early_leave: "bg-orange-100 text-orange-800",
  absent: "bg-red-100 text-red-800",
  on_leave: "bg-blue-100 text-blue-800",
  holiday: "bg-purple-100 text-purple-800",
};

const statusLabels: Record<string, string> = {
  present: "Có mặt",
  late: "Đi muộn",
  early_leave: "Về sớm",
  absent: "Vắng mặt",
  on_leave: "Nghỉ phép",
  holiday: "Ngày lễ",
};

function formatTime(isoString: string | null): string {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh",
  });
}

export default function AttendancePage() {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [employeeMap, setEmployeeMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [data, empRes] = await Promise.all([
        attendanceApi.getTeamToday(),
        employeesApi.listEmployees({ page: 1, page_size: 100 }),
      ]);
      setRecords(data);

      // Build map: employee_id → "full_name (employee_code)"
      const map: Record<string, string> = {};
      for (const emp of empRes.items) {
        map[emp.id] = `${emp.full_name} (${emp.employee_code})`;
      }
      setEmployeeMap(map);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  }

  const presentCount = records.filter((r) =>
    ["present"].includes(r.status)
  ).length;
  const lateCount = records.filter((r) => r.status === "late").length;
  const earlyLeaveCount = records.filter((r) => r.status === "early_leave").length;
  const absentCount = records.filter((r) => r.status === "absent").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Chấm công</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/attendance/team">
              <Users className="h-4 w-4 mr-2" />
              Bảng chấm công
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/attendance/overtime">
              <Timer className="h-4 w-4 mr-2" />
              Overtime
            </Link>
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Có mặt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-green-500" />
              <span className="text-2xl font-bold">{presentCount}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Đi muộn
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold text-yellow-600">{lateCount}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Về sớm
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold text-orange-600">{earlyLeaveCount}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Vắng mặt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold text-red-600">{absentCount}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tổng records
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{records.length}</span>
          </CardContent>
        </Card>
      </div>

      {/* Today's records */}
      <Card>
        <CardHeader>
          <CardTitle>Chấm công hôm nay</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : records.length === 0 ? (
            <p className="text-muted-foreground">
              Chưa có dữ liệu chấm công hôm nay. Dùng nút &quot;Bảng chấm công&quot; để nhập thủ công.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nhân viên</TableHead>
                  <TableHead>Check-in</TableHead>
                  <TableHead>Check-out</TableHead>
                  <TableHead>Giờ làm</TableHead>
                  <TableHead>OT</TableHead>
                  <TableHead>Trạng thái</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((rec) => (
                  <TableRow key={rec.id}>
                    <TableCell className="font-medium">
                      {employeeMap[rec.employee_id] || rec.employee_id.slice(0, 8)}
                    </TableCell>
                    <TableCell>{formatTime(rec.check_in)}</TableCell>
                    <TableCell>{formatTime(rec.check_out)}</TableCell>
                    <TableCell>{rec.work_hours ?? "—"}</TableCell>
                    <TableCell>{rec.overtime_hours > 0 ? `${rec.overtime_hours}h` : "—"}</TableCell>
                    <TableCell>
                      <Badge className={statusColors[rec.status] || ""}>
                        {statusLabels[rec.status] || rec.status}
                      </Badge>
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
