import {
  LayoutDashboard,
  Users,
  Building2,
  Briefcase,
  Mail,
  UserSearch,
  Shield,
  ListChecks,
  KeyRound,
  UserCog,
  ScrollText,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { href: "/", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/employees", label: "Nhân viên", icon: Users },
  { href: "/settings/departments", label: "Phòng ban", icon: Building2 },
  { href: "/settings/positions", label: "Chức vụ", icon: Briefcase },
  { href: "/gmail", label: "Gmail", icon: Mail },
  { href: "/recruitment", label: "Tuyển dụng", icon: UserSearch },
];

export interface AdminNavSection {
  title: string;
  icon: LucideIcon;
  items: NavItem[];
}

export const adminNavSection: AdminNavSection = {
  title: "Quản trị",
  icon: Shield,
  items: [
    { href: "/admin/whitelist", label: "Whitelist", icon: ListChecks },
    { href: "/admin/oauth", label: "OAuth", icon: KeyRound },
    { href: "/admin/users", label: "Người dùng", icon: UserCog },
    { href: "/admin/audit-logs", label: "Nhật ký", icon: ScrollText },
  ],
};
