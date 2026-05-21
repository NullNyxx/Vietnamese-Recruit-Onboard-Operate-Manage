"use client";

import { useState, useEffect, useCallback } from "react";
import { Users, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import UserRoleSelect from "@/components/admin/user-role-select";
import { listUsers, updateUserRole } from "@/lib/api/admin";
import type { AdminUser, UserRole } from "@/lib/api/admin";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể tải danh sách người dùng";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleRoleChange(userId: string, newRole: UserRole) {
    try {
      await updateUserRole(userId, newRole);
      toast.success("Đã cập nhật vai trò thành công");
      await fetchUsers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể cập nhật vai trò";
      toast.error(message);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
          <h1 className="text-2xl font-bold font-heading tracking-tight">
            Quản lý người dùng
          </h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchUsers}
          disabled={loading}
          aria-label="Làm mới danh sách"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          <span className="hidden sm:inline ml-2">Làm mới</span>
        </Button>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="hidden sm:table-cell w-[50px]">Avatar</TableHead>
              <TableHead>Tên</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Vai trò</TableHead>
              <TableHead>Trạng thái</TableHead>
              <TableHead className="hidden sm:table-cell">Đăng nhập lần cuối</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody aria-live="polite">
            {/* Loading state */}
            {loading && (
              <>
                {Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={`skeleton-${i}`}>
                    <TableCell className="hidden sm:table-cell">
                      <Skeleton className="h-8 w-8 rounded-full" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-32" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-48" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-8 w-[110px]" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-5 w-16" />
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <Skeleton className="h-4 w-36" />
                    </TableCell>
                  </TableRow>
                ))}
              </>
            )}

            {/* Empty state */}
            {!loading && !error && users.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center text-muted-foreground sm:hidden">
                  Không có người dùng nào
                </TableCell>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground hidden sm:table-cell">
                  Không có người dùng nào
                </TableCell>
              </TableRow>
            )}

            {/* Data rows */}
            {!loading &&
              users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="hidden sm:table-cell">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.avatar_url ?? undefined} alt={user.name} />
                      <AvatarFallback className="text-xs">
                        {getInitials(user.name)}
                      </AvatarFallback>
                    </Avatar>
                  </TableCell>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell className="text-muted-foreground">{user.email}</TableCell>
                  <TableCell>
                    <UserRoleSelect
                      userId={user.id}
                      userName={user.name}
                      userEmail={user.email}
                      currentRole={user.role}
                      onRoleChange={handleRoleChange}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_active ? "default" : "secondary"}>
                      {user.is_active ? "Hoạt động" : "Không hoạt động"}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                    {formatDate(user.last_login)}
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
