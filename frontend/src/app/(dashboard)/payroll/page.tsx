"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Wallet, TrendingUp, TrendingDown, Calendar, Plus } from "lucide-react";

import { getPayrollPeriods } from "@/lib/api/payroll";
import type { PayrollPeriod } from "@/lib/api/payroll";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function PayrollDashboardPage() {
  const [periods, setPeriods] = useState<PayrollPeriod[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPayrollPeriods()
      .then(setPeriods)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const currentPeriod = periods.find((p) => p.status === "draft" || p.status === "calculating");
  const confirmedPeriods = periods.filter((p) => p.status === "confirmed");
  const paidPeriods = periods.filter((p) => p.status === "paid");

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(value);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
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
    return <Badge variant={variants[status] || "outline"}>{labels[status] || status}</Badge>;
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
          <h1 className="text-2xl font-bold tracking-tight">Lương & Thưởng</h1>
          <p className="text-muted-foreground">Quản lý bảng lương và phiếu lương</p>
        </div>
        <Button asChild>
          <Link href="/payroll/periods">
            <Plus className="mr-2 h-4 w-4" />
            Tạo kỳ lương
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tổng số kỳ lương</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{periods.length}</div>
            <p className="text-xs text-muted-foreground">
              {periods.length > 0
                ? `Tháng ${periods[0].month}/${periods[0].year} - ${periods[periods.length - 1].month}/${periods[periods.length - 1].year}`
                : "Chưa có dữ liệu"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Kỳ lương hiện tại</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {currentPeriod ? `${currentPeriod.month}/${currentPeriod.year}` : "-"}
            </div>
            <p className="text-xs text-muted-foreground">
              {currentPeriod ? getStatusBadge(currentPeriod.status) : "Không có kỳ nháp"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Đã duyệt</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{confirmedPeriods.length}</div>
            <p className="text-xs text-muted-foreground">
              {confirmedPeriods.length > 0
                ? `Tổng: ${formatCurrency(confirmedPeriods.reduce((sum, p) => sum + p.total_net, 0))}`
                : "Chưa có"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Đã chi trả</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{paidPeriods.length}</div>
            <p className="text-xs text-muted-foreground">
              {paidPeriods.length > 0
                ? `Tổng: ${formatCurrency(paidPeriods.reduce((sum, p) => sum + p.total_net, 0))}`
                : "Chưa có"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Danh sách kỳ lương gần đây</CardTitle>
        </CardHeader>
        <CardContent>
          {periods.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Chưa có kỳ lương nào. Hãy tạo kỳ lương đầu tiên.
            </p>
          ) : (
            <div className="space-y-4">
              {periods.slice(0, 6).map((period) => (
                <div
                  key={period.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <Calendar className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">Tháng {period.month}/{period.year}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatCurrency(period.total_gross)} (gross)
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-medium">{formatCurrency(period.total_net)}</p>
                      <p className="text-xs text-muted-foreground">net</p>
                    </div>
                    {getStatusBadge(period.status)}
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/payroll/periods/${period.id}`}>Xem</Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {periods.length > 6 && (
            <div className="mt-4 text-center">
              <Button variant="ghost" asChild>
                <Link href="/payroll/periods">Xem tất cả ({periods.length})</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}