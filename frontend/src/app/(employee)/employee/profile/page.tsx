"use client";

import { useState, useEffect } from "react";
import { User, Phone, MapPin, Shield, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useCurrentUser } from "@/hooks/use-current-user";

interface EmployeeData {
  id: string;
  employee_code: string;
  full_name: string;
  email: string;
  phone: string | null;
  date_of_birth: string | null;
  gender: string | null;
  address: string | null;
  department_id: string | null;
  position_id: string | null;
  start_date: string | null;
  contract_type: string | null;
  id_number: string | null;
  tax_code: string | null;
  is_active: boolean;
}

interface FormErrors {
  phone?: string;
  address?: string;
}

const PHONE_PATTERN = /^0\d{9}$/;

function validatePhone(value: string): string | undefined {
  if (!value) return undefined;
  if (!PHONE_PATTERN.test(value)) {
    return "Số điện thoại phải gồm 10 chữ số, bắt đầu bằng 0";
  }
  return undefined;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("vi-VN");
  } catch {
    return dateStr;
  }
}

function formatGender(gender: string | null): string {
  if (!gender) return "—";
  const map: Record<string, string> = {
    male: "Nam",
    female: "Nữ",
    other: "Khác",
  };
  return map[gender.toLowerCase()] || gender;
}

function formatContractType(type: string | null): string {
  if (!type) return "—";
  const map: Record<string, string> = {
    full_time: "Toàn thời gian",
    part_time: "Bán thời gian",
    contract: "Hợp đồng",
    intern: "Thực tập",
    probation: "Thử việc",
  };
  return map[type.toLowerCase()] || type;
}

function maskValue(value: string | null): string {
  if (!value) return "—";
  if (value.length <= 4) return "****";
  return "****" + value.slice(-4);
}

export default function EmployeeProfilePage() {
  const { user } = useCurrentUser();
  const [employee, setEmployee] = useState<EmployeeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (user?.employee_id) {
      fetchProfile(user.employee_id);
    } else if (user && !user.employee_id) {
      setLoading(false);
    }
  }, [user]);

  async function fetchProfile(employeeId: string) {
    setLoading(true);
    try {
      const res = await fetch(`/api/employees/${employeeId}`);
      if (!res.ok) {
        throw new Error(`Lỗi tải hồ sơ (${res.status})`);
      }
      const data: EmployeeData = await res.json();
      setEmployee(data);
      setPhone(data.phone || "");
      setAddress(data.address || "");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Không thể tải hồ sơ cá nhân",
      );
    } finally {
      setLoading(false);
    }
  }

  function handlePhoneChange(value: string) {
    setPhone(value);
    setIsDirty(true);
    const error = validatePhone(value);
    setErrors((prev) => ({ ...prev, phone: error }));
  }

  function handleAddressChange(value: string) {
    setAddress(value);
    setIsDirty(true);
    if (value.length > 500) {
      setErrors((prev) => ({
        ...prev,
        address: "Địa chỉ không được vượt quá 500 ký tự",
      }));
    } else {
      setErrors((prev) => ({ ...prev, address: undefined }));
    }
  }

  function hasValidationErrors(): boolean {
    return Object.values(errors).some((e) => e !== undefined);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!user?.employee_id) return;

    const phoneError = validatePhone(phone);
    if (phoneError) {
      setErrors((prev) => ({ ...prev, phone: phoneError }));
      return;
    }
    if (hasValidationErrors()) return;

    const payload: Record<string, string | null> = {};
    if (phone !== (employee?.phone || "")) payload.phone = phone || null;
    if (address !== (employee?.address || ""))
      payload.address = address || null;

    if (Object.keys(payload).length === 0) {
      toast.info("Không có thay đổi nào để cập nhật");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/api/employees/${user.employee_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Cập nhật thất bại (${res.status})`);
      }
      const updated: EmployeeData = await res.json();
      setEmployee(updated);
      setPhone(updated.phone || "");
      setAddress(updated.address || "");
      setIsDirty(false);
      toast.success("Cập nhật hồ sơ thành công");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Không thể cập nhật hồ sơ",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Hồ sơ cá nhân</h1>
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-40" />
              </CardHeader>
              <CardContent className="space-y-4">
                {Array.from({ length: 5 }).map((_, j) => (
                  <div key={j} className="space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-5 w-48" />
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Hồ sơ cá nhân</h1>
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              Chưa có hồ sơ nhân viên được liên kết với tài khoản của bạn.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Hồ sơ cá nhân</h1>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="h-5 w-5" />
              Thông tin cá nhân
            </CardTitle>
            <CardDescription>
              Thông tin cơ bản — liên hệ HR để thay đổi
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Họ và tên
                </dt>
                <dd className="text-sm mt-1">{employee.full_name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Email
                </dt>
                <dd className="text-sm mt-1">{employee.email}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Mã nhân viên
                </dt>
                <dd className="text-sm mt-1 font-mono">
                  {employee.employee_code}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Ngày sinh
                </dt>
                <dd className="text-sm mt-1">
                  {formatDate(employee.date_of_birth)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Giới tính
                </dt>
                <dd className="text-sm mt-1">
                  {formatGender(employee.gender)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Shield className="h-5 w-5" />
              Thông tin công việc
            </CardTitle>
            <CardDescription>Hợp đồng và thông tin bảo mật</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Ngày bắt đầu
                </dt>
                <dd className="text-sm mt-1">
                  {formatDate(employee.start_date)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Loại hợp đồng
                </dt>
                <dd className="text-sm mt-1">
                  {formatContractType(employee.contract_type)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Số CMND/CCCD
                </dt>
                <dd className="text-sm mt-1 font-mono">
                  {maskValue(employee.id_number)}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Mã số thuế
                </dt>
                <dd className="text-sm mt-1 font-mono">
                  {maskValue(employee.tax_code)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Phone className="h-5 w-5" />
            Thông tin liên hệ
          </CardTitle>
          <CardDescription>Cập nhật số điện thoại và địa chỉ</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="phone">
                  <Phone className="inline h-4 w-4 mr-1" />
                  Số điện thoại
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="0912345678"
                  value={phone}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  className={errors.phone ? "border-destructive" : ""}
                />
                {errors.phone && (
                  <p className="text-sm text-destructive">{errors.phone}</p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">
                <MapPin className="inline h-4 w-4 mr-1" />
                Địa chỉ
              </Label>
              <Input
                id="address"
                type="text"
                placeholder="123 Đường ABC, Quận 1, TP.HCM"
                value={address}
                onChange={(e) => handleAddressChange(e.target.value)}
                className={errors.address ? "border-destructive" : ""}
                maxLength={500}
              />
              {errors.address && (
                <p className="text-sm text-destructive">{errors.address}</p>
              )}
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={submitting || !isDirty || hasValidationErrors()}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Đang lưu...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Lưu thay đổi
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
