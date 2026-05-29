import {
  User,
  FileText,
  Edit,
  Clock,
  CalendarOff,
  Timer,
  History,
} from "lucide-react";
import type { HeaderNavConfig } from "./header-nav-config";

export const essNavConfig: HeaderNavConfig = {
  logo: { label: "Vroom ESS", href: "/employee/dashboard" },
  groups: [
    {
      id: "ho-so",
      label: "Hồ sơ",
      links: [
        { href: "/employee/profile", label: "Thông tin", icon: User },
        { href: "/employee/documents", label: "Tài liệu", icon: FileText },
        { href: "/employee/profile/update", label: "Cập nhật", icon: Edit },
      ],
      activeRoutes: ["/employee/profile", "/employee/documents"],
    },
    {
      id: "cham-cong-ess",
      label: "Chấm công",
      links: [
        {
          href: "/employee/attendance/checkin",
          label: "Check-in",
          icon: Clock,
        },
        {
          href: "/employee/attendance/leave",
          label: "Nghỉ phép",
          icon: CalendarOff,
        },
        {
          href: "/employee/attendance/overtime",
          label: "Tăng ca",
          icon: Timer,
        },
      ],
      activeRoutes: ["/employee/attendance"],
    },
    {
      id: "luong-ess",
      label: "Lương",
      links: [
        {
          href: "/employee/payroll/payslip",
          label: "Phiếu lương",
          icon: FileText,
        },
        { href: "/employee/payroll/history", label: "Lịch sử", icon: History },
      ],
      activeRoutes: ["/employee/payroll"],
    },
  ],
};
