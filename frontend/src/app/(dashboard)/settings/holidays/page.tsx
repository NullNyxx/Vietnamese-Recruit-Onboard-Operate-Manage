"use client";

import { useState, useEffect } from "react";
import { Plus, Trash2, Calendar } from "lucide-react";

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
import type { Holiday } from "@/lib/api/attendance";

export default function HolidaysPage() {
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [loading, setLoading] = useState(true);
  const [year, setYear] = useState("2026");

  // Form state
  const [newName, setNewName] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newRecurring, setNewRecurring] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchHolidays();
  }, [year]);

  async function fetchHolidays() {
    setLoading(true);
    try {
      const data = await attendanceApi.listHolidays(parseInt(year));
      setHolidays(data);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!newName.trim() || !newDate) return;
    setSubmitting(true);
    try {
      await attendanceApi.createHoliday({
        holiday_date: newDate,
        name: newName.trim(),
        is_recurring: newRecurring,
      });
      setNewName("");
      setNewDate("");
      setNewRecurring(false);
      fetchHolidays();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi khi tạo ngày lễ");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Bạn có chắc muốn xóa ngày lễ này?")) return;
    try {
      await attendanceApi.deleteHoliday(id);
      fetchHolidays();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Lỗi khi xóa");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Quản Lý Ngày Lễ</h1>
        <div className="w-[120px]">
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
      </div>

      {/* Add holiday form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Thêm ngày lễ mới</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-1 block">Tên ngày lễ</label>
              <Input
                placeholder="VD: Tết Nguyên Đán"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="w-[180px]">
              <label className="text-sm font-medium mb-1 block">Ngày</label>
              <Input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="recurring"
                checked={newRecurring}
                onChange={(e) => setNewRecurring(e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="recurring" className="text-sm">
                Lặp hàng năm
              </label>
            </div>
            <Button onClick={handleCreate} disabled={submitting || !newName || !newDate}>
              <Plus className="h-4 w-4 mr-2" />
              {submitting ? "Đang tạo..." : "Thêm"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Holidays list */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Danh sách ngày lễ năm {year}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Đang tải...</p>
          ) : holidays.length === 0 ? (
            <p className="text-muted-foreground">Chưa có ngày lễ nào cho năm {year}.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ngày</TableHead>
                  <TableHead>Tên ngày lễ</TableHead>
                  <TableHead>Lặp hàng năm</TableHead>
                  <TableHead className="w-[80px]">Hành động</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holidays.map((holiday) => (
                  <TableRow key={holiday.id}>
                    <TableCell className="font-medium">
                      {new Date(holiday.holiday_date).toLocaleDateString("vi-VN")}
                    </TableCell>
                    <TableCell>{holiday.name}</TableCell>
                    <TableCell>
                      {holiday.is_recurring ? (
                        <Badge className="bg-blue-100 text-blue-800">Có</Badge>
                      ) : (
                        <Badge variant="outline">Không</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(holiday.id)}
                        title="Xóa"
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
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
