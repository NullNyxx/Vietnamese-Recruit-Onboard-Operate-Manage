"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, Download } from "lucide-react";

import { getEmployeePayslips, getPayslipPdf } from "@/lib/api/payroll";
import type { Payslip } from "@/lib/api/payroll";
import { useCurrentUser } from "@/hooks/use-current-user";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function EmployeePayslipsPage() {
  const { user } = useCurrentUser();
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPayslip] = useState<Payslip | null>(null);

  useEffect(() => {
    if (!user?.employee_id) return;
    loadPayslips();
  }, [user?.employee_id]);

  const loadPayslips = () => {
    if (!user?.employee_id) return;
    getEmployeePayslips(user.employee_id)
      .then(setPayslips)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleDownloadPdf = async (payslipId: string) => {
    try {
      const blob = await getPayslipPdf(payslipId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `payslip_${payslipId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error(error);
    }
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(value);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-muted-foreground">Đang tải...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/payroll">
            <ChevronLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Phiếu lương của tôi
          </h1>
          <p className="text-muted-foreground">Lịch sử nhận lương</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lịch sử phiếu lương ({payslips.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {payslips.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              Chưa có phiếu lương nào.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kỳ lương</TableHead>
                  <TableHead className="text-right">Lương gross</TableHead>
                  <TableHead className="text-right">Phụ cấp</TableHead>
                  <TableHead className="text-right">OT</TableHead>
                  <TableHead className="text-right">Thuế TNCN</TableHead>
                  <TableHead className="text-right">BHXH/BHYT</TableHead>
                  <TableHead className="text-right">Lương net</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payslips.map((payslip) => (
                  <TableRow key={payslip.id}>
                    <TableCell className="font-medium">
                      {payslip.period_id ? (
                        <Link
                          href={`/payroll/periods/${payslip.period_id}`}
                          className="text-primary hover:underline"
                        >
                          Xem kỳ
                        </Link>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(payslip.gross_salary)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(payslip.total_allowances)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(payslip.total_ot_amount)}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      -{formatCurrency(payslip.income_tax)}
                    </TableCell>
                    <TableCell className="text-right text-red-600">
                      -{formatCurrency(payslip.insurance_premium)}
                    </TableCell>
                    <TableCell className="text-right font-medium text-green-600">
                      {formatCurrency(payslip.net_salary)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownloadPdf(payslip.id)}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        PDF
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {selectedPayslip && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Chi tiết phiếu lương</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="font-medium mb-2">Thu nhập</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Lương gross:</span>
                    <span>{formatCurrency(selectedPayslip.gross_salary)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Phụ cấp:</span>
                    <span>
                      {formatCurrency(selectedPayslip.total_allowances)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tiền OT:</span>
                    <span>
                      {formatCurrency(selectedPayslip.total_ot_amount)}
                    </span>
                  </div>
                  <div className="flex justify-between font-medium border-t pt-2">
                    <span>Tổng thu nhập:</span>
                    <span>{formatCurrency(selectedPayslip.gross_income)}</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-2">Khấu trừ</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Giảm trừ cá nhân:
                    </span>
                    <span>
                      -{formatCurrency(selectedPayslip.personal_deduction)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Giảm trừ NPT:</span>
                    <span>
                      -{formatCurrency(selectedPayslip.dependent_deduction)}
                    </span>
                  </div>
                  <div className="flex justify-between text-red-600">
                    <span>Thuế TNCN:</span>
                    <span>-{formatCurrency(selectedPayslip.income_tax)}</span>
                  </div>
                  <div className="flex justify-between text-red-600">
                    <span>BHXH/BHYT/BHTN:</span>
                    <span>
                      -{formatCurrency(selectedPayslip.insurance_premium)}
                    </span>
                  </div>
                  <div className="flex justify-between font-medium border-t pt-2">
                    <span>Tổng khấu trừ:</span>
                    <span>
                      -
                      {formatCurrency(
                        selectedPayslip.income_tax +
                          selectedPayslip.insurance_premium,
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-6 p-4 bg-green-50 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="text-lg font-medium">Lương thực nhận</span>
                <span className="text-2xl font-bold text-green-600">
                  {formatCurrency(selectedPayslip.net_salary)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
