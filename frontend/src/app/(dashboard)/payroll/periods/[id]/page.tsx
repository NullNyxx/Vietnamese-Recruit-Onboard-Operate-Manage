"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ChevronLeft,
  Calculator,
  CheckCircle,
  XCircle,
  Send,
} from "lucide-react";

import {
  getPayrollPeriod,
  getPeriodEmployees,
  calculatePayroll,
  confirmPayrollPeriod,
  markPayrollPaid,
  sendPayslips,
} from "@/lib/api/payroll";
import type { PayrollPeriod, EmployeeWithPayslip } from "@/lib/api/payroll";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function PayrollPeriodDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useCurrentUser();

  const [period, setPeriod] = useState<PayrollPeriod | null>(null);
  const [employees, setEmployees] = useState<EmployeeWithPayslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!id) return;
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      const [periodData, employeesData] = await Promise.all([
        getPayrollPeriod(id!),
        getPeriodEmployees(id!),
      ]);
      setPeriod(periodData);
      setEmployees(employeesData);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleCalculate = async () => {
    if (!id) return;
    setProcessing(true);
    try {
      await calculatePayroll(id);
      await loadData();
    } catch (error) {
      console.error(error);
    } finally {
      setProcessing(false);
    }
  };

  const handleConfirm = async () => {
    if (!id || !user) return;
    setProcessing(true);
    try {
      await confirmPayrollPeriod(id, user.id);
      await loadData();
    } catch (error) {
      console.error(error);
    } finally {
      setProcessing(false);
    }
  };

  const handleMarkPaid = async () => {
    if (!id) return;
    setProcessing(true);
    try {
      await markPayrollPaid(id);
      await loadData();
    } catch (error) {
      console.error(error);
    } finally {
      setProcessing(false);
    }
  };

  const handleSendPayslips = async () => {
    if (!id) return;
    setProcessing(true);
    try {
      await sendPayslips(id);
      await loadData();
    } catch (error) {
      console.error(error);
    } finally {
      setProcessing(false);
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

  if (loading || !period) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">Đang tải...</p>
      </div>
    );
  }

  const canCalculate = period.status === "draft";
  const canConfirm =
    period.status === "draft" || period.status === "calculating";
  const canMarkPaid = period.status === "confirmed";
  const canSendPayslips =
    period.status === "confirmed" || period.status === "paid";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/payroll/periods">
              <ChevronLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Kỳ lương {period.month}/{period.year}
            </h1>
            <p className="text-muted-foreground">Chi tiết bảng lương</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge(period.status)}
          {canCalculate && (
            <Button onClick={handleCalculate} disabled={processing}>
              <Calculator className="mr-2 h-4 w-4" />
              Tính lương
            </Button>
          )}
          {canConfirm && (
            <Button onClick={handleConfirm} disabled={processing}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Xác nhận
            </Button>
          )}
          {canMarkPaid && (
            <Button onClick={handleMarkPaid} disabled={processing}>
              <XCircle className="mr-2 h-4 w-4" />
              Đánh dấu đã chi trả
            </Button>
          )}
          {canSendPayslips && (
            <Button
              variant="outline"
              onClick={handleSendPayslips}
              disabled={processing}
            >
              <Send className="mr-2 h-4 w-4" />
              G?i phi?u l??ng
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tổng gross</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {formatCurrency(period.total_gross)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tổng thuế</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {formatCurrency(period.total_tax)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tổng BH</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {formatCurrency(period.total_insurance)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tổng net</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-green-600">
              {formatCurrency(period.total_net)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Danh sách nhân viên ({employees.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {employees.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Chưa có dữ liệu. Hãy tính lương trước.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Mã NV</TableHead>
                  <TableHead>Họ tên</TableHead>
                  <TableHead>Phòng ban</TableHead>
                  <TableHead>Chức vụ</TableHead>
                  <TableHead className="text-right">Lương gross</TableHead>
                  <TableHead className="text-right">Phụ cấp</TableHead>
                  <TableHead className="text-right">OT</TableHead>
                  <TableHead className="text-right">Thuế</TableHead>
                  <TableHead className="text-right">BH</TableHead>
                  <TableHead className="text-right">Lương net</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {employees.map((emp) => (
                  <TableRow key={emp.employee_id}>
                    <TableCell className="font-medium">
                      {emp.employee_code}
                    </TableCell>
                    <TableCell>{emp.full_name}</TableCell>
                    <TableCell>{emp.department_name || "-"}</TableCell>
                    <TableCell>{emp.position_name || "-"}</TableCell>
                    <TableCell className="text-right">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.gross_salary)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.total_allowances)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.total_ot_amount)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.income_tax)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.insurance_premium)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right font-medium text-green-600">
                      {emp.payslip
                        ? formatCurrency(emp.payslip.net_salary)
                        : "-"}
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
