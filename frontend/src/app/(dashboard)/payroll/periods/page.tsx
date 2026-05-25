"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Calendar, ChevronLeft } from "lucide-react";

import { getPayrollPeriods, createPayrollPeriod } from "@/lib/api/payroll";
import type { PayrollPeriod } from "@/lib/api/payroll";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function PayrollPeriodsPage() {
  const [periods, setPeriods] = useState<PayrollPeriod[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newMonth, setNewMonth] = useState(new Date().getMonth() + 1);
  const [newYear, setNewYear] = useState(new Date().getFullYear());

  useEffect(() => {
    loadPeriods();
  }, []);

  const loadPeriods = () => {
    getPayrollPeriods()
      .then(setPeriods)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleCreatePeriod = async () => {
    try {
      await createPayrollPeriod({ month: newMonth, year: newYear });
      setShowCreateDialog(false);
      loadPeriods();
    } catch (error) {
      console.error(error);
    }
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(value);

  const getStatusBadge = (status: string) => {
    const variants: Record<
      string,
      "default" | "secondary" | "destructive" | "outline"
    > = {
      draft: "secondary",
      calculating: "outline",
      confirmed: "default",
      paid: "destructive",
    };
    const labels: Record<string, string> = {
      draft: "Nháp",
      calculating: "Đang tính",
      confirmed: "Đã duyệt",
      paid: "Đã chi trả",
    };
    return (
      <Badge variant={variants[status] || "outline"}>
        {labels[status] || status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">Đang tải...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/payroll">
                <ChevronLeft className="h-5 w-5" />
              </Link>
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Danh sách kỳ lương
              </h1>
              <p className="text-muted-foreground">Quản lý các kỳ tính lương</p>
            </div>
          </div>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Tạo kỳ lương
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tất cả kỳ lương ({periods.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {periods.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Chưa có kỳ lương nào.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kỳ</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="text-right">Tổng gross</TableHead>
                  <TableHead className="text-right">Tổng thuế</TableHead>
                  <TableHead className="text-right">Tổng BH</TableHead>
                  <TableHead className="text-right">Tổng net</TableHead>
                  <TableHead>Ngày xác nhận</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {periods.map((period) => (
                  <TableRow key={period.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        {period.month}/{period.year}
                      </div>
                    </TableCell>
                    <TableCell>{getStatusBadge(period.status)}</TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(period.total_gross)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(period.total_tax)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(period.total_insurance)}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(period.total_net)}
                    </TableCell>
                    <TableCell>
                      {period.confirmed_at
                        ? new Date(period.confirmed_at).toLocaleDateString(
                            "vi-VN",
                          )
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/payroll/periods/${period.id}`}>
                          Xem chi tiết
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tạo kỳ lương mới</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="month">Tháng</Label>
                <Input
                  id="month"
                  type="number"
                  min={1}
                  max={12}
                  value={newMonth}
                  onChange={(e) => setNewMonth(parseInt(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="year">Năm</Label>
                <Input
                  id="year"
                  type="number"
                  min={2020}
                  max={2100}
                  value={newYear}
                  onChange={(e) => setNewYear(parseInt(e.target.value))}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
            >
              Hủy
            </Button>
            <Button onClick={handleCreatePeriod}>Tạo</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
