"use client";

import Link from "next/link";
import {
  Users,
  Building2,
  Briefcase,
  UserPlus,
  FileText,
  ArrowUpRight,
  Target,
  Mail,
} from "lucide-react";

import { useCurrentUser } from "@/hooks/use-current-user";
import { useDashboardStats } from "@/hooks/queries";
import { StatCard } from "@/components/stat-card";

// ─── Quick Action ───────────────────────────────────────────────────────────
function QuickAction({
  title,
  href,
  icon: Icon,
  variant = "default",
}: {
  title: string;
  href: string;
  icon: React.ElementType;
  variant?: "default" | "primary";
}) {
  const isPrimary = variant === "primary";

  return (
    <Link
      href={href}
      className={`group flex items-center gap-3 rounded-lg p-3.5 transition-colors ${
        isPrimary
          ? "bg-[#B8422E] text-white"
          : "border border-[#6C7278]/20 bg-white text-[#1A1C1E] hover:border-[#6C7278]/40"
      }`}
    >
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
          isPrimary ? "bg-white/20" : "bg-[#F7F5F2]"
        }`}
      >
        <Icon
          className={`h-4 w-4 ${isPrimary ? "text-white" : "text-[#6C7278]"}`}
          aria-hidden="true"
        />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-[13px] font-medium">{title}</h3>
      </div>
      <ArrowUpRight
        className={`h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity ${
          isPrimary ? "text-white/70" : "text-[#6C7278]"
        }`}
      />
    </Link>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: stats, isLoading: loading } = useDashboardStats();
  const { user } = useCurrentUser();

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Chào buổi sáng";
    if (hour < 18) return "Chào buổi chiều";
    return "Chào buổi tối";
  };

  return (
    <div className="space-y-8 max-w-[1440px] mx-auto overflow-x-hidden">
      {/* ─── Welcome ─────────────────────────────────────────────────────── */}
      <div>
        <h1 className="font-heading text-[24px] font-medium text-[#1A1C1E]">
          {greeting()}
          {user?.email ? `, ${user.email.split("@")[0]}` : ""}
        </h1>
        <p className="mt-1 font-sans text-base leading-[1.6] text-[#6C7278]">
          Tổng quan hoạt động hôm nay
        </p>
      </div>

      {/* ─── Stats Grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Nhân viên"
          value={stats?.employees ?? 0}
          icon={Users}
          loading={loading}
        />
        <StatCard
          title="Phòng ban"
          value={stats?.departments ?? 0}
          icon={Building2}
          loading={loading}
        />
        <StatCard
          title="Chức vụ"
          value={stats?.positions ?? 0}
          icon={Briefcase}
          loading={loading}
        />
      </div>

      {/* ─── Quick Actions ───────────────────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="font-heading text-lg font-medium text-[#1A1C1E]">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QuickAction
            title="Thêm nhân viên"
            href="/employees/new"
            icon={UserPlus}
            variant="primary"
          />
          <QuickAction
            title="Import Excel"
            href="/employees/import"
            icon={FileText}
          />
          <QuickAction title="Tuyển dụng" href="/recruitment" icon={Target} />
          <QuickAction
            title="Phòng ban"
            href="/settings/departments"
            icon={Building2}
          />
          <QuickAction
            title="Chức vụ"
            href="/settings/positions"
            icon={Briefcase}
          />
          <QuickAction title="Gmail" href="/gmail" icon={Mail} />
        </div>
      </div>
    </div>
  );
}
