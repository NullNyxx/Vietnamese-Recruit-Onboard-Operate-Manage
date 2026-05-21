"use client";

import { useState, useEffect } from "react";
import { Plus, Clock } from "lucide-react";

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
import { attendanceApi } from "@/lib/api";
import type { WorkSchedule } from "@/lib/api/attendance";

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<WorkSchedule[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formStart, setFormStart] = useState("08:00");
  const [formEnd, setFormEnd] = useState("17:00");
  const [formBreak, setFormBreak] = useState("60");
  const [formLateThreshold, setFormLateThreshold] = useState("15");
  const [formEarlyThreshold, setFormEarlyThreshold] = useState("15");
  const [formIsDefault, setFormIsDefault] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchSchedules();
  }, []);

  async function fetchSchedules() {
    setLoading(true);
    try {
      const data = await attendanceApi.listSchedules();
      setSchedules(data);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formName.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch("/api/schedules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formName.trim(),
          start_time: formStart,
          end_time: formEnd,
          break_minutes: parseInt(formBreak),
          late_threshold_minutes: parseInt(formLateThreshold),
          early_leave_threshold_minutes: parseInt(formEarlyThreshold),
          is_default: formIsDefault,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: { message: "Lỗi" } }));
        throw new Error(err.detail?.message || "Tạo ca thất bại");
      }
      // Reset form
      setFormName("");
      setFormStart("08:00");
      setFormEnd("17:00");
      setFormBreak("60");
      setFormLateThreshold("15");
      setFormEarlyThreshold("15");
      setFormIsDefault(false);
      setShowForm(false);
      fetchSchedules();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi khi tạo ca làm việc");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Quản Lý Ca Làm Việc</h1>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Thêm ca mới
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Tạo ca làm việc mới</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Tên ca</label>
                <Input
                  placeholder="VD: Ca hành chính"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Giờ bắt đầu</label>
                <Input
                  type="time"
                  value={formStart}
                  onChange={(e) => setFormStart(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Giờ kết thúc</label>
                <Input
                  type="time"
                  value={formEnd}
                  onChange={(e) => setFormEnd(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Nghỉ trưa (phút)</label>
                <Input
                  type="number"
                  value={formBreak}
                  onChange={(e) => setFormBreak(e.target.value)}
                  min="0"
                  max="120"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Ngưỡng muộn (phút)
                </label>
                <Input
                  type="number"
                  value={formLateThreshold}
                  onChange={(e) => setFormLateThreshold(e.target.value)}
                  min="0"
                  max="60"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  Ngưỡng về sớm (phút)
                </label>
                <Input
                  type="number"
                  value={formEarlyThreshold}
                  onChange={(e) => setFormEarlyThreshold(e.target.value)}
                  min="0"
                  max="60"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="isDefault"
                checked={formIsDefault}
                onChange={(e) => setFormIsDefault(e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="isDefault" className="text-sm">
                Đặt làm ca mặc định
              </label>
            </div>
            <div className="flex gap-2 mt-4">
              <Button onClick={handleCreate} disabled={submitting || !formName.trim()}>
                {submitting ? "Đang tạo..." : "Tạo ca"}
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Hủy
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Schedules list */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Danh sách ca làm việc
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : schedules.length === 0 ? (
            <p className="text-muted-foreground">Chưa có ca làm việc nào.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tên ca</TableHead>
                  <TableHead>Giờ bắt đầu</TableHead>
                  <TableHead>Giờ kết thúc</TableHead>
                  <TableHead>Nghỉ trưa</TableHead>
                  <TableHead>Ngưỡng muộn</TableHead>
                  <TableHead>Ngưỡng về sớm</TableHead>
                  <TableHead>Mặc định</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedules.map((schedule) => (
                  <TableRow key={schedule.id}>
                    <TableCell className="font-medium">{schedule.name}</TableCell>
                    <TableCell>{schedule.start_time}</TableCell>
                    <TableCell>{schedule.end_time}</TableCell>
                    <TableCell>{schedule.break_minutes} phút</TableCell>
                    <TableCell>{schedule.late_threshold_minutes} phút</TableCell>
                    <TableCell>{schedule.early_leave_threshold_minutes} phút</TableCell>
                    <TableCell>
                      {schedule.is_default ? (
                        <Badge className="bg-green-100 text-green-800">Mặc định</Badge>
                      ) : (
                        <Badge variant="outline">Không</Badge>
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
