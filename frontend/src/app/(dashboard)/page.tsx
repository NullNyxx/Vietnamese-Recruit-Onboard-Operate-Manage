"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Users,
  Building2,
  Briefcase,
  UserPlus,
  FileText,
  ArrowUpRight,
  Zap,
  Brain,
  TrendingUp,
  Activity,
  Sparkles,
  Bot,
  Target,
  Mail,
} from "lucide-react";

import { employeesApi, departmentsApi, positionsApi } from "@/lib/api";
import { useCurrentUser } from "@/hooks/use-current-user";

// ─── Types ──────────────────────────────────────────────────────────────────
interface DashboardStats {
  employees: number;
  departments: number;
  positions: number;
  activeToday: number;
}

// ─── Pulse Dot ──────────────────────────────────────────────────────────────
function PulseDot({ color }: { color: string }) {
  return (
    <span className="relative flex h-2 w-2">
      <span
        className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
        style={{ backgroundColor: color, animationDuration: "2s" }}
      />
      <span
        className="relative inline-flex h-2 w-2 rounded-full"
        style={{ backgroundColor: color }}
      />
    </span>
  );
}

// ─── AI Stat Card ───────────────────────────────────────────────────────────
function AIStatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  loading,
  glowColor,
}: {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
  loading?: boolean;
  glowColor: string;
}) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 backdrop-blur-sm transition-all hover:border-white/[0.1] hover:bg-white/[0.04]">
      {/* Glow effect */}
      <div
        className="absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-0 blur-2xl transition-opacity group-hover:opacity-100"
        style={{ backgroundColor: glowColor }}
      />
      <div className="relative flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-[#62666d]">
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-16 animate-pulse rounded-md bg-white/[0.05]" />
          ) : (
            <p className="text-[28px] font-semibold tracking-[-0.5px] text-[#f7f8f8]">
              {value}
            </p>
          )}
          {subtitle && <p className="text-[11px] text-[#8a8f98]">{subtitle}</p>}
        </div>
        <div
          className="flex h-10 w-10 items-center justify-center rounded-lg"
          style={{ backgroundColor: `${color}15` }}
        >
          <Icon className="h-5 w-5" style={{ color }} aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

// ─── AI Agent Card ──────────────────────────────────────────────────────────
function AgentCard({
  name,
  status,
  lastAction,
  metric,
  color,
}: {
  name: string;
  status: "active" | "idle" | "processing";
  lastAction: string;
  metric: string;
  color: string;
}) {
  const statusConfig = {
    active: { label: "Active", dotColor: "#27a644" },
    idle: { label: "Idle", dotColor: "#8a8f98" },
    processing: { label: "Processing", dotColor: "#e4f222" },
  };

  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-sm transition-all hover:border-white/[0.1] hover:bg-white/[0.04]">
      <div
        className="absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-10 blur-xl"
        style={{ backgroundColor: color }}
      />
      <div className="relative space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="flex h-7 w-7 items-center justify-center rounded-md"
              style={{ backgroundColor: `${color}20` }}
            >
              <Bot className="h-3.5 w-3.5" style={{ color }} />
            </div>
            <span className="text-[13px] font-medium text-[#f7f8f8]">
              {name}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <PulseDot color={statusConfig[status].dotColor} />
            <span className="text-[10px] text-[#8a8f98]">
              {statusConfig[status].label}
            </span>
          </div>
        </div>
        <p className="text-[12px] text-[#8a8f98] leading-relaxed">
          {lastAction}
        </p>
        <div className="flex items-center gap-1.5 rounded-md bg-white/[0.03] px-2.5 py-1.5">
          <Zap className="h-3 w-3 text-[#e4f222]" />
          <span className="text-[11px] text-[#d0d6e0]">{metric}</span>
        </div>
      </div>
    </div>
  );
}

// ─── Quick Action ───────────────────────────────────────────────────────────
function QuickAction({
  title,
  description,
  href,
  icon: Icon,
  color,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3.5 transition-all hover:border-white/[0.1] hover:bg-white/[0.04]"
    >
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
        style={{ backgroundColor: `${color}12` }}
      >
        <Icon
          className="h-4 w-4 transition-colors"
          style={{ color }}
          aria-hidden="true"
        />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-[13px] font-medium text-[#f7f8f8]">{title}</h3>
        <p className="text-[11px] text-[#62666d]">{description}</p>
      </div>
      <ArrowUpRight className="h-3.5 w-3.5 text-[#62666d] opacity-0 group-hover:opacity-100 transition-opacity" />
    </Link>
  );
}

// ─── Activity Item ──────────────────────────────────────────────────────────
function ActivityItem({
  icon: Icon,
  title,
  time,
  color,
}: {
  icon: React.ElementType;
  title: string;
  time: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md"
        style={{ backgroundColor: `${color}12` }}
      >
        <Icon className="h-3.5 w-3.5" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] text-[#d0d6e0] truncate">{title}</p>
      </div>
      <span className="text-[10px] text-[#62666d] shrink-0">{time}</span>
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    employees: 0,
    departments: 0,
    positions: 0,
    activeToday: 0,
  });
  const [loading, setLoading] = useState(true);
  const { user } = useCurrentUser();

  useEffect(() => {
    async function fetchStats() {
      try {
        const [employeesRes, departments, positions] = await Promise.all([
          employeesApi.listEmployees({ page: 1, page_size: 1 }),
          departmentsApi.listDepartments(),
          positionsApi.listPositions(),
        ]);
        setStats({
          employees: employeesRes.total,
          departments: departments.length,
          positions: positions.length,
          activeToday: 0,
        });
      } catch {
        // Keep defaults
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Chào buổi sáng";
    if (hour < 18) return "Chào buổi chiều";
    return "Chào buổi tối";
  };

  return (
    <div className="space-y-8 max-w-[1440px]">
      {/* ─── Welcome + AI Status ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-[24px] font-semibold tracking-[-0.3px] text-[#f7f8f8]">
            {greeting()}
            {user?.email ? `, ${user.email.split("@")[0]}` : ""}
          </h1>
          <p className="text-[14px] text-[#8a8f98]">
            AI Workforce Operating System — tổng quan hoạt động hôm nay
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 backdrop-blur-sm">
            <PulseDot color="#27a644" />
            <span className="text-[11px] text-[#8a8f98]">3 Agents Active</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 backdrop-blur-sm">
            <Sparkles className="h-3 w-3 text-[#e4f222]" />
            <span className="text-[11px] text-[#8a8f98]">AI Online</span>
          </div>
        </div>
      </div>

      {/* ─── Stats Grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <AIStatCard
          title="Nhân viên"
          value={stats.employees}
          subtitle="Active workforce"
          icon={Users}
          color="#e4f222"
          glowColor="#e4f222"
          loading={loading}
        />
        <AIStatCard
          title="Phòng ban"
          value={stats.departments}
          subtitle="Organizational units"
          icon={Building2}
          color="#5e6ad2"
          glowColor="#5e6ad2"
          loading={loading}
        />
        <AIStatCard
          title="Chức vụ"
          value={stats.positions}
          subtitle="Role definitions"
          icon={Briefcase}
          color="#02b8cc"
          glowColor="#02b8cc"
          loading={loading}
        />
        <AIStatCard
          title="AI Tasks Today"
          value="24"
          subtitle="Automated operations"
          icon={Brain}
          color="#8b5cf6"
          glowColor="#8b5cf6"
          loading={false}
        />
      </div>

      {/* ─── AI Agents + Activity ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* AI Agents — 2 cols */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-[#e4f222]" />
              <h2 className="text-[15px] font-medium text-[#f7f8f8]">
                AI Agents
              </h2>
            </div>
            <span className="text-[11px] text-[#62666d]">Realtime status</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <AgentCard
              name="Recruitment Agent"
              status="active"
              lastAction="Đang phân tích CV và matching với JD cho vị trí Senior Developer"
              metric="47 CVs processed today"
              color="#e4f222"
            />
            <AgentCard
              name="Document Agent"
              status="processing"
              lastAction="Đang phân loại và index tài liệu nhân viên mới upload"
              metric="156 docs indexed"
              color="#27a644"
            />
            <AgentCard
              name="Analytics Agent"
              status="active"
              lastAction="Monitoring workforce metrics, generating weekly report"
              metric="Real-time insights"
              color="#02b8cc"
            />
            <AgentCard
              name="Onboarding Agent"
              status="idle"
              lastAction="Hoàn thành onboarding flow cho 2 nhân viên mới tuần trước"
              metric="Avg 2.3 days to complete"
              color="#8b5cf6"
            />
          </div>
        </div>

        {/* Activity Stream — 1 col */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-[#02b8cc]" />
              <h2 className="text-[15px] font-medium text-[#f7f8f8]">
                Live Activity
              </h2>
            </div>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-sm space-y-0.5">
            <ActivityItem
              icon={Brain}
              title="AI parsed 3 new CVs from email"
              time="2m ago"
              color="#e4f222"
            />
            <ActivityItem
              icon={Users}
              title="Nguyễn Văn A profile updated"
              time="1h ago"
              color="#02b8cc"
            />
            <ActivityItem
              icon={Briefcase}
              title="Position updated: Senior Developer"
              time="2h ago"
              color="#8b5cf6"
            />
            <ActivityItem
              icon={TrendingUp}
              title="Workforce analytics report generated"
              time="3h ago"
              color="#27a644"
            />
            <ActivityItem
              icon={UserPlus}
              title="New employee onboarded: Lê Văn C"
              time="Yesterday"
              color="#e4f222"
            />
            <ActivityItem
              icon={Target}
              title="Recruitment pipeline updated"
              time="Yesterday"
              color="#5e6ad2"
            />
            <div className="pt-3 mt-2 border-t border-white/[0.04]">
              <Link
                href="#"
                className="flex items-center justify-center gap-1 text-[11px] text-[#8a8f98] hover:text-[#e4f222] transition-colors"
              >
                <span>View all activity</span>
                <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Quick Actions + AI Insights ─────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quick Actions */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-[#e4f222]" />
            <h2 className="text-[15px] font-medium text-[#f7f8f8]">
              Quick Actions
            </h2>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <QuickAction
              title="Thêm nhân viên"
              description="Create new record"
              href="/employees/new"
              icon={UserPlus}
              color="#e4f222"
            />
            <QuickAction
              title="Import Excel"
              description="Bulk import"
              href="/employees/import"
              icon={FileText}
              color="#5e6ad2"
            />
            <QuickAction
              title="Tuyển dụng"
              description="AI-powered pipeline"
              href="/recruitment"
              icon={Target}
              color="#02b8cc"
            />
            <QuickAction
              title="Phòng ban"
              description="Organizational structure"
              href="/settings/departments"
              icon={Building2}
              color="#27a644"
            />
            <QuickAction
              title="Chức vụ"
              description="Role management"
              href="/settings/positions"
              icon={Briefcase}
              color="#8b5cf6"
            />
            <QuickAction
              title="Gmail"
              description="Email integration"
              href="/gmail"
              icon={Mail}
              color="#e4f222"
            />
          </div>
        </div>

        {/* AI Insights Panel */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#8b5cf6]" />
            <h2 className="text-[15px] font-medium text-[#f7f8f8]">
              AI Insights
            </h2>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-sm space-y-4">
            {/* Insight cards */}
            <div className="space-y-3">
              <div className="rounded-lg bg-[#e4f222]/5 border border-[#e4f222]/10 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Brain className="h-3 w-3 text-[#e4f222]" />
                  <span className="text-[11px] font-medium text-[#e4f222]">
                    Recommendation
                  </span>
                </div>
                <p className="text-[12px] text-[#d0d6e0] leading-relaxed">
                  3 ứng viên có match score &gt;85% cho vị trí Frontend
                  Developer. Xem ngay?
                </p>
              </div>

              <div className="rounded-lg bg-[#02b8cc]/5 border border-[#02b8cc]/10 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Activity className="h-3 w-3 text-[#02b8cc]" />
                  <span className="text-[11px] font-medium text-[#02b8cc]">
                    Pattern Detected
                  </span>
                </div>
                <p className="text-[12px] text-[#d0d6e0] leading-relaxed">
                  Phòng Engineering có tỷ lệ turnover cao hơn 40% so với trung
                  bình. Cần review hiring strategy.
                </p>
              </div>

              <div className="rounded-lg bg-[#8b5cf6]/5 border border-[#8b5cf6]/10 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="h-3 w-3 text-[#8b5cf6]" />
                  <span className="text-[11px] font-medium text-[#8b5cf6]">
                    Forecast
                  </span>
                </div>
                <p className="text-[12px] text-[#d0d6e0] leading-relaxed">
                  Dự báo chi phí nhân sự Q3 tăng 12% do hiring plan. Budget cần
                  điều chỉnh.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
