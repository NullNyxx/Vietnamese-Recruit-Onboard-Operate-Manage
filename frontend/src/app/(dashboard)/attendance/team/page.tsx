"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { Badge } from "@/components/ui/badge";
import { attendanceApi, employeesApi } from "@/lib/api";
import type { Employee } from "@/lib/api/types";

const statusOptions = [
  { value: "present", label: "Có mặt" },
  { value: "late", label: "Đi muộn" },
  { value: "early_leave", label: "Về sớm" },
  { value: "absent", label: "Vắng mặt" },
  { value: "on_leave", label: "Nghỉ phép" },
];

export default function AttendanceTeamPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [workDate, setWorkDate] = useState(new Date().toISOString().split("T")[0]);
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [status, setStatus] = useState("present");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadEmployees() {
      try {
        const res = await employeesApi.listEmployees({ page: 1, page_size: 100 });
        setEmployees(res.items);
      } catch {
        // Handle silently
      }
    }
    loadEmployees();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedEmployee || !workDate || !status) {
      alert("Vui lòng chọn nhân viên, ngày và trạng thái");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const checkInDt = checkIn ? `${workDate}T${checkIn}:00+07:00` : undefined;
      const checkOutDt = checkOut ? `${workDate}T${checkOut}:00+07:00` : undefined;

      await attendanceApi.manualRecord({
        employee_id: selectedEmployee,
        work_date: workDate,
        check_in: checkInDt,
        check_out: checkOutDt,
        status,
        note: note || undefined,
      });

      setMessage("✅ Đã lưu chấm công thành công!");
      setCheckIn("");
      setCheckOut("");
      setNote("");
    } catch (err) {
      setMessage(`❌ ${err instanceof Error ? err.message : "Lỗi"}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Nhập chấm công thủ công</h1>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Ghi nhận chấm công</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Nhân viên *</Label>
              <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
                <SelectTrigger>
                  <SelectValue placeholder="Chọn nhân viên" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map((emp) => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name} ({emp.employee_code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Ngày *</Label>
                <Input
                  type="date"
                  value={workDate}
                  onChange={(e) => setWorkDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Trạng thái *</Label>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statusOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Giờ vào</Label>
                <Input
                  type="time"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  placeholder="08:00"
                />
              </div>
              <div className="space-y-2">
                <Label>Giờ ra</Label>
                <Input
                  type="time"
                  value={checkOut}
                  onChange={(e) => setCheckOut(e.target.value)}
                  placeholder="17:00"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Ghi chú</Label>
              <Input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ghi chú (tùy chọn)"
              />
            </div>

            {message && (
              <p className={message.startsWith("✅") ? "text-green-600" : "text-red-600"}>
                {message}
              </p>
            )}

            <Button type="submit" disabled={loading}>
              {loading ? "Đang lưu..." : "Lưu chấm công"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
