"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

const labelMap: Record<string, string> = {
  "": "Trang chủ",
  employees: "Nhân viên",
  settings: "Cài đặt",
  departments: "Phòng ban",
  positions: "Chức vụ",
  gmail: "Gmail",
  new: "Thêm mới",
  recruitment: "Tuyển dụng",
  review: "Xem xét CV",
  metrics: "Số liệu",
};

interface BreadcrumbItem {
  label: string;
  href: string;
}

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  const items: BreadcrumbItem[] = [
    { label: "Trang chủ", href: "/" },
  ];

  segments.forEach((segment, index) => {
    const href = "/" + segments.slice(0, index + 1).join("/");
    let label: string;

    if (labelMap[segment]) {
      label = labelMap[segment];
    } else if (index > 0 && segments[index - 1] === "recruitment") {
      // Dynamic [id] segment under /recruitment — show placeholder
      label = "...";
    } else {
      label = segment;
    }

    items.push({ label, href });
  });

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <span key={item.href} className="flex items-center gap-1">
            {index > 0 && (
              <ChevronRight
                className="h-3.5 w-3.5 text-muted-foreground"
                aria-hidden="true"
              />
            )}
            {isLast ? (
              <span className="text-foreground font-medium">{item.label}</span>
            ) : (
              <Link
                href={item.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
