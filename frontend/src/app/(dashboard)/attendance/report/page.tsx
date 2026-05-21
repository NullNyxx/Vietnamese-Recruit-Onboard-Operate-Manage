"use client";

import { useState } from "react";
import { FileDown, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { attendanceApi } from "@/lib/api";
import type { MonthlyReport } from "@/lib/api/attendance";

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
  late: "Muộn",
  early_leave: "Về sớm",
  absent: "Vắng",
  on_leave: "Nghỉ phép",
  holiday: "Ngày lễ",
};

export default function AttendanceReportPage() {
  const [employeeId, setEmployeeId] = useState("");
  const [year, setYear] = useState("2026");
  const [month, setMonth] = useState("5");
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchReport() {
    if (!employeeId.trim()) {
      setError("Vui lòng nhập Employee ID");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const data = await attendanceApi.getMonthlyReport(
        employeeId.trim(),
        parseInt(year),
        parseInt(month)
      );
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi khi tải báo cáo");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  function handleExport() {
    if (!employeeId.trim()) return;
    const url = `/api/attendance/export?employee_id=${employeeId.trim()}&year=${year}&month=${month}&format=xlsx`;
    window.open(url, "_blank");
  }

  function formatTime(isoStr: string | null): string {
    if (!isoStr) return "—";
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Ho_Chi_Minh" });
    } catch {
      return "—";
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Báo Cáo Chấm Công</h1>
      </div>

      {/* Filter form */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-1 block">Employee ID</label>
              <Input
                placeholder="Nhập UUID nhân viên..."
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
              />
            </div>
            <div className="w-[120px]">
              <label className="text-sm font-medium mb-1 block">Năm</label>
              <Select value={year} onValueChange={setYear}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2025">2025</SelectItem>
                  <SelectItem value="2026">2026</SelectItem>
                  <SelectItem value="2027">2027</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-[120px]">
              <label className="text-sm font-medium mb-1 block">Tháng</label>
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 12 }, (_, i) => (
                    <SelectItem key={i + 1} value={String(i + 1)}>
                      Tháng {i + 1}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={fetchReport} disabled={loading}>
              <Search className="h-4 w-4 mr-2" />
              {loading ? "Đang tải..." : "Xem báo cáo"}
            </Button>
            {report && (
              <Button variant="outline" onClick={handleExport}>
                <FileDown className="h-4 w-4 mr-2" />
                Xuất Excel
              </Button>
            )}
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </CardContent>
      </Card>

      {/* Summary stats */}
      {report && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ngày có mặt
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-green-600">
                  {report.summary.present_days}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ngày muộn
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-yellow-600">
                  {report.summary.late_days}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ngày vắng
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-red-600">
                  {report.summary.absent_days}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ngày nghỉ phép
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-blue-600">
                  {report.summary.leave_days}
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Tổng giờ làm
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold">
                  {report.summary.total_work_hours}h
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Tổng giờ OT
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-2xl font-bold text-purple-600">
                  {report.summary.total_overtime_hours}h
                </span>
              </CardContent>
            </Card>
          </div>

          {/* Daily records table */}
          <Card>
            <CardHeader>
              <CardTitle>
                Chi tiết chấm công tháng {month}/{year}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {report.records.length === 0 ? (
                <p className="text-muted-foreground">Không có dữ liệu chấm công.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ngày</TableHead>
                      <TableHead>Check-in</TableHead>
                      <TableHead>Check-out</TableHead>
                      <TableHead>Giờ làm</TableHead>
                      <TableHead>OT</TableHead>
                      <TableHead>Trạng thái</TableHead>
                      <TableHead>Ghi chú</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.records.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell className="font-medium">
                          {new Date(record.work_date).toLocaleDateString("vi-VN")}
                        </TableCell>
                        <TableCell>{formatTime(record.check_in)}</TableCell>
                        <TableCell>{formatTime(record.check_out)}</TableCell>
                        <TableCell>
                          {record.work_hours != null ? `${record.work_hours}h` : "—"}
                        </TableCell>
                        <TableCell>
                          {record.overtime_hours > 0 ? `${record.overtime_hours}h` : "—"}
                        </TableCell>
                        <TableCell>
                          <Badge className={statusColors[record.status] || ""}>
                            {statusLabels[record.status] || record.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {record.note || "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
