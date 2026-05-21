"use client";

import { useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import type { UserRole } from "@/lib/api/admin";

export interface UserRoleSelectProps {
  userId: string;
  userName: string;
  userEmail: string;
  currentRole: UserRole;
  disabled?: boolean;
  onRoleChange: (userId: string, newRole: UserRole) => Promise<void>;
}

export default function UserRoleSelect({
  userId,
  userName,
  userEmail,
  currentRole,
  disabled = false,
  onRoleChange,
}: UserRoleSelectProps) {
  const [pendingRole, setPendingRole] = useState<UserRole | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleValueChange(value: string) {
    const newRole = value as UserRole;
    if (newRole === currentRole) return;
    setPendingRole(newRole);
  }

  async function handleConfirm() {
    if (!pendingRole) return;
    setIsSubmitting(true);
    try {
      await onRoleChange(userId, pendingRole);
    } finally {
      setIsSubmitting(false);
      setPendingRole(null);
    }
  }

  function handleCancel() {
    setPendingRole(null);
  }

  const roleLabel = pendingRole === "admin" ? "Admin" : "User";
  const actionDescription =
    pendingRole === "admin"
      ? `Bạn có chắc muốn nâng quyền "${userName}" (${userEmail}) lên Admin? Người dùng này sẽ có toàn quyền quản trị hệ thống.`
      : `Bạn có chắc muốn hạ quyền "${userName}" (${userEmail}) xuống User? Người dùng này sẽ mất quyền truy cập trang quản trị.`;

  return (
    <>
      <Select
        value={currentRole}
        onValueChange={handleValueChange}
        disabled={disabled || isSubmitting}
      >
        <SelectTrigger
          className="w-[110px] h-8 text-xs"
          aria-label={`Vai trò của ${userName}`}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="admin">Admin</SelectItem>
          <SelectItem value="user">User</SelectItem>
        </SelectContent>
      </Select>

      <AlertDialog open={pendingRole !== null} onOpenChange={(open) => !open && handleCancel()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận thay đổi vai trò</AlertDialogTitle>
            <AlertDialogDescription>{actionDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSubmitting}>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} disabled={isSubmitting}>
              {isSubmitting ? "Đang xử lý..." : `Đổi thành ${roleLabel}`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
