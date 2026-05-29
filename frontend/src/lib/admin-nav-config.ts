import {
  Users,
  Building2,
  Briefcase,
  FileText,
  Upload,
  UserSearch,
  BarChart3,
  FileSearch,
  Clock,
  Calendar,
  CalendarOff,
  Timer,
  PartyPopper,
  DollarSign,
  Settings,
  Gift,
  Receipt,
  UserCog,
  ListChecks,
  KeyRound,
  ScrollText,
  Mail,
} from "lucide-react";
import type { HeaderNavConfig } from "./header-nav-config";

export const adminNavConfig: HeaderNavConfig = {
  logo: { label: "Vroom", href: "/" },
  groups: [
    {
      id: "nhan-su",
      label: "Nhân sự",
      links: [
        { href: "/employees", label: "Danh sách NV", icon: Users },
        { href: "/settings/departments", label: "Phòng ban", icon: Building2 },
        { href: "/settings/positions", label: "Chức vụ", icon: Briefcase },
        { href: "/employee/documents", label: "Tài liệu", icon: FileText },
        { href: "/employees/import", label: "Import", icon: Upload },
      ],
      activeRoutes: [
        "/employees",
        "/settings/departments",
        "/settings/positions",
      ],
    },
    {
      id: "tuyen-dung",
      label: "Tuyển dụng",
      links: [
        { href: "/recruitment", label: "Pipeline", icon: UserSearch },
        { href: "/recruitment/candidates", label: "Ứng viên", icon: Users },
        { href: "/recruitment/metrics", label: "Metrics", icon: BarChart3 },
        { href: "/recruitment/review", label: "Review", icon: FileSearch },
      ],
      activeRoutes: ["/recruitment"],
    },
    {
      id: "cham-cong",
      label: "Chấm công",
      links: [
        { href: "/attendance/checkin", label: "Check-in", icon: Clock },
        { href: "/attendance/schedules", label: "Lịch làm", icon: Calendar },
        { href: "/attendance/leave", label: "Nghỉ phép", icon: CalendarOff },
        { href: "/attendance/overtime", label: "Tăng ca", icon: Timer },
        { href: "/attendance/holidays", label: "Ngày lễ", icon: PartyPopper },
      ],
      activeRoutes: ["/attendance"],
    },
    {
      id: "luong",
      label: "Lương",
      links: [
        { href: "/payroll", label: "Bảng lương", icon: DollarSign },
        { href: "/payroll/config", label: "Cấu hình", icon: Settings },
        { href: "/payroll/allowances", label: "Phụ cấp", icon: Gift },
        { href: "/payroll/tax", label: "Thuế", icon: Receipt },
      ],
      activeRoutes: ["/payroll"],
    },
    {
      id: "he-thong",
      label: "Hệ thống",
      links: [
        { href: "/admin/users", label: "Users", icon: UserCog },
        { href: "/admin/whitelist", label: "Whitelist", icon: ListChecks },
        { href: "/admin/oauth", label: "OAuth", icon: KeyRound },
        { href: "/admin/audit-logs", label: "Audit logs", icon: ScrollText },
        { href: "/gmail", label: "Gmail", icon: Mail },
      ],
      activeRoutes: ["/admin", "/gmail"],
    },
  ],
};
