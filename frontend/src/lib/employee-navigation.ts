import { LayoutDashboard, User, FileText } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface EmployeeNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const employeeNavItems: EmployeeNavItem[] = [
  { href: "/employee/dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/employee/profile", label: "Hồ sơ", icon: User },
  { href: "/employee/documents", label: "Tài liệu", icon: FileText },
];
