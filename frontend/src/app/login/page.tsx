"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

// ─── Animated Pulse Dot ─────────────────────────────────────────────────────
function PulseDot({ color, delay = "0s" }: { color: string; delay?: string }) {
  return (
    <span className="relative flex h-2 w-2">
      <span
        className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
        style={{
          backgroundColor: color,
          animationDelay: delay,
          animationDuration: "2s",
        }}
      />
      <span
        className="relative inline-flex h-2 w-2 rounded-full"
        style={{ backgroundColor: color }}
      />
    </span>
  );
}

// ─── AI Agent Activity Card ─────────────────────────────────────────────────
function AgentActivityCard({
  agent,
  action,
  status,
  time,
  color,
}: {
  agent: string;
  action: string;
  status: "active" | "completed" | "processing";
  time: string;
  color: string;
}) {
  const statusMap = {
    active: { label: "Đang hoạt động", dot: "#e4f222" },
    completed: { label: "Hoàn thành", dot: "#27a644" },
    processing: { label: "Đang xử lý", dot: "#02b8cc" },
  };

  return (
    <div className="group relative overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-sm transition-all hover:border-white/[0.1] hover:bg-white/[0.04]">
      {/* Subtle glow */}
      <div
        className="absolute -right-4 -top-4 h-16 w-16 rounded-full opacity-20 blur-xl"
        style={{ backgroundColor: color }}
      />
      <div className="relative flex items-start justify-between">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <PulseDot color={statusMap[status].dot} />
            <span className="text-[11px] font-medium uppercase tracking-wider text-[#8a8f98]">
              {agent}
            </span>
          </div>
          <p className="text-[13px] text-[#d0d6e0]">{action}</p>
        </div>
        <span className="text-[11px] text-[#62666d]">{time}</span>
      </div>
    </div>
  );
}

// ─── AI Insight Metric ──────────────────────────────────────────────────────
function InsightMetric({
  label,
  value,
  trend,
  color,
}: {
  label: string;
  value: string;
  trend?: string;
  color: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 backdrop-blur-sm">
      <div
        className="absolute -bottom-2 -left-2 h-12 w-12 rounded-full opacity-10 blur-lg"
        style={{ backgroundColor: color }}
      />
      <div className="relative space-y-2">
        <p className="text-[11px] font-medium uppercase tracking-wider text-[#62666d]">
          {label}
        </p>
        <p className="text-[20px] font-semibold tracking-tight text-[#f7f8f8]">
          {value}
        </p>
        {trend && <p className="text-[11px] text-[#27a644]">{trend}</p>}
      </div>
    </div>
  );
}

// ─── Workflow Node ───────────────────────────────────────────────────────────
function WorkflowNode({
  label,
  active,
  completed,
}: {
  label: string;
  active?: boolean;
  completed?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full border text-[10px] font-bold ${
          completed
            ? "border-[#27a644] bg-[#27a644]/20 text-[#27a644]"
            : active
              ? "border-[#e4f222] bg-[#e4f222]/10 text-[#e4f222] shadow-[0_0_12px_rgba(228,242,34,0.3)]"
              : "border-[#323334] bg-transparent text-[#62666d]"
        }`}
      >
        {completed ? "✓" : active ? "●" : "○"}
      </div>
      <span
        className={`text-[12px] ${
          completed
            ? "text-[#27a644]"
            : active
              ? "text-[#e4f222]"
              : "text-[#62666d]"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

// ─── Google Icon ────────────────────────────────────────────────────────────
function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

// ─── Main Login Page ────────────────────────────────────────────────────────
export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogin = () => {
    setLoading(true);
    window.location.href = "/api/auth/login";
  };

  return (
    <div className="relative flex min-h-screen bg-[#08090a] overflow-hidden">
      {/* ─── Background Effects ─────────────────────────────────────────── */}
      <div className="absolute inset-0 -z-10" aria-hidden="true">
        {/* Cinematic gradient mesh */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 80% 60% at 70% 40%, rgba(228, 242, 34, 0.04) 0%, transparent 50%),
              radial-gradient(ellipse 60% 80% at 20% 80%, rgba(94, 106, 210, 0.05) 0%, transparent 50%),
              radial-gradient(ellipse 50% 50% at 80% 80%, rgba(2, 184, 204, 0.03) 0%, transparent 50%),
              radial-gradient(ellipse 40% 40% at 50% 20%, rgba(139, 92, 246, 0.03) 0%, transparent 50%)
            `,
          }}
        />
        {/* Grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }}
        />
      </div>

      {/* ─── Left Panel: AI Platform Showcase ───────────────────────────── */}
      <div
        className={`hidden lg:flex lg:w-[58%] flex-col justify-between p-10 xl:p-14 transition-all duration-700 ${
          mounted ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4"
        }`}
      >
        {/* Top: Logo + Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-[#e4f222]">
              <span className="text-[15px] font-bold text-[#08090a]">V</span>
              {/* Glow ring */}
              <div className="absolute inset-0 rounded-lg shadow-[0_0_20px_rgba(228,242,34,0.3)]" />
            </div>
            <div>
              <span className="text-[15px] font-semibold tracking-tight text-[#f7f8f8]">
                Vroom HR
              </span>
              <span className="ml-2 rounded-full border border-[#e4f222]/30 bg-[#e4f222]/10 px-2 py-0.5 text-[10px] font-medium text-[#e4f222]">
                AI-Powered
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 backdrop-blur-sm">
            <PulseDot color="#27a644" />
            <span className="text-[11px] text-[#8a8f98]">System Online</span>
          </div>
        </div>

        {/* Center: Hero + AI Visualization */}
        <div className="space-y-10 max-w-[580px]">
          {/* Hero text */}
          <div className="space-y-4">
            <h1 className="text-[36px] xl:text-[42px] font-semibold leading-[1.1] tracking-[-0.5px] text-[#f7f8f8]">
              AI Workforce
              <br />
              <span className="bg-gradient-to-r from-[#e4f222] via-[#e4f222] to-[#02b8cc] bg-clip-text text-transparent">
                Operating System
              </span>
            </h1>
            <p className="text-[15px] leading-relaxed text-[#8a8f98] max-w-[460px]">
              Nền tảng vận hành nhân sự tích hợp AI Agent. Tự động hóa tuyển
              dụng, onboarding, quản lý nhân sự — một hệ thống thông minh cho
              toàn bộ workforce operations.
            </p>
          </div>

          {/* AI Workflow Visualization */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-gradient-to-r from-[#e4f222]/40 to-transparent" />
              <span className="text-[10px] font-medium uppercase tracking-widest text-[#62666d]">
                AI Workflow Pipeline
              </span>
              <div className="h-px flex-1 bg-gradient-to-l from-[#02b8cc]/40 to-transparent" />
            </div>
            <div className="flex items-center gap-3 overflow-hidden">
              <WorkflowNode label="CV Parsing" completed />
              <div className="h-px w-6 bg-[#27a644]" />
              <WorkflowNode label="AI Screening" completed />
              <div className="h-px w-6 bg-[#27a644]" />
              <WorkflowNode label="Auto Schedule" active />
              <div className="h-px w-6 bg-[#323334]" />
              <WorkflowNode label="Onboarding" />
              <div className="h-px w-6 bg-[#323334]" />
              <WorkflowNode label="Analytics" />
            </div>
          </div>

          {/* AI Insights Grid */}
          <div className="grid grid-cols-3 gap-3">
            <InsightMetric
              label="AI Processed"
              value="1,247"
              trend="+23% this week"
              color="#e4f222"
            />
            <InsightMetric
              label="Auto Tasks"
              value="89%"
              trend="Automation rate"
              color="#02b8cc"
            />
            <InsightMetric
              label="Time Saved"
              value="142h"
              trend="This month"
              color="#8b5cf6"
            />
          </div>

          {/* Agent Activity Stream */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium uppercase tracking-wider text-[#62666d]">
                Agent Activity
              </span>
              <div className="h-px flex-1 bg-[#23252a]" />
            </div>
            <div className="space-y-2">
              <AgentActivityCard
                agent="Recruitment Agent"
                action="Đang phân tích 3 CV mới từ LinkedIn"
                status="active"
                time="Vừa xong"
                color="#e4f222"
              />
              <AgentActivityCard
                agent="Document Agent"
                action="Hoàn thành phân loại 12 tài liệu nhân viên mới"
                status="completed"
                time="2 phút trước"
                color="#27a644"
              />
              <AgentActivityCard
                agent="Analytics Agent"
                action="Generating workforce insights report cho Q2/2026"
                status="processing"
                time="5 phút trước"
                color="#02b8cc"
              />
            </div>
          </div>
        </div>

        {/* Bottom: Trust indicators */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <svg
              className="h-4 w-4 text-[#62666d]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
              />
            </svg>
            <span className="text-[11px] text-[#62666d]">
              Enterprise Security
            </span>
          </div>
          <div className="flex items-center gap-2">
            <svg
              className="h-4 w-4 text-[#62666d]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
              />
            </svg>
            <span className="text-[11px] text-[#62666d]">
              AI-Native Platform
            </span>
          </div>
          <div className="flex items-center gap-2">
            <svg
              className="h-4 w-4 text-[#62666d]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"
              />
            </svg>
            <span className="text-[11px] text-[#62666d]">
              Vietnam Compliance
            </span>
          </div>
        </div>
      </div>

      {/* ─── Right Panel: Login ──────────────────────────────────────────── */}
      <div
        className={`flex w-full lg:w-[42%] items-center justify-center p-6 sm:p-8 transition-all duration-700 delay-200 ${
          mounted ? "opacity-100 translate-x-0" : "opacity-0 translate-x-4"
        }`}
      >
        <div className="w-full max-w-[400px] space-y-8">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e4f222]">
              <span className="text-[15px] font-bold text-[#08090a]">V</span>
            </div>
            <div>
              <span className="text-[15px] font-semibold text-[#f7f8f8]">
                Vroom HR
              </span>
              <span className="ml-2 rounded-full border border-[#e4f222]/30 bg-[#e4f222]/10 px-2 py-0.5 text-[10px] font-medium text-[#e4f222]">
                AI-Powered
              </span>
            </div>
          </div>

          {/* Login header */}
          <div className="space-y-2">
            <h2 className="text-[24px] font-semibold tracking-[-0.3px] text-[#f7f8f8]">
              Đăng nhập vào Workspace
            </h2>
            <p className="text-[14px] text-[#8a8f98]">
              Truy cập AI Workforce Operating System của tổ chức
            </p>
          </div>

          {/* Login card */}
          <div className="relative overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 backdrop-blur-sm">
            {/* Card glow */}
            <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[#e4f222]/5 blur-2xl" />
            <div className="absolute -bottom-10 -left-10 h-32 w-32 rounded-full bg-[#5e6ad2]/5 blur-2xl" />

            <div className="relative space-y-6">
              {/* Google OAuth Button — Primary */}
              <button
                onClick={handleLogin}
                disabled={loading}
                className="group relative flex w-full items-center justify-center gap-3 overflow-hidden rounded-lg bg-[#e4f222] px-4 py-3.5 text-[14px] font-semibold text-[#08090a] transition-all hover:shadow-[0_0_24px_rgba(228,242,34,0.3)] focus:outline-none focus:ring-2 focus:ring-[#e4f222]/50 focus:ring-offset-2 focus:ring-offset-[#08090a] disabled:opacity-60 disabled:cursor-not-allowed"
                aria-label="Đăng nhập bằng Google"
              >
                {/* Hover shimmer */}
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <GoogleIcon />
                )}
                <span className="relative">
                  {loading ? "Đang kết nối..." : "Đăng nhập bằng Google"}
                </span>
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-white/[0.06]" />
                <span className="text-[11px] text-[#62666d]">hoặc</span>
                <div className="h-px flex-1 bg-white/[0.06]" />
              </div>

              {/* Email/Password form */}
              <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                <div className="space-y-1.5">
                  <label
                    htmlFor="email"
                    className="text-[12px] font-medium text-[#8a8f98]"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    placeholder="name@company.com"
                    className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-[14px] text-[#f7f8f8] placeholder:text-[#62666d] transition-all focus:border-[#e4f222]/50 focus:outline-none focus:ring-1 focus:ring-[#e4f222]/20 focus:bg-white/[0.05]"
                    disabled
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="password"
                      className="text-[12px] font-medium text-[#8a8f98]"
                    >
                      Mật khẩu
                    </label>
                    <button
                      type="button"
                      className="text-[11px] text-[#8a8f98] hover:text-[#e4f222] transition-colors"
                      disabled
                    >
                      Quên mật khẩu?
                    </button>
                  </div>
                  <input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-[14px] text-[#f7f8f8] placeholder:text-[#62666d] transition-all focus:border-[#e4f222]/50 focus:outline-none focus:ring-1 focus:ring-[#e4f222]/20 focus:bg-white/[0.05]"
                    disabled
                  />
                </div>

                {/* Remember me */}
                <div className="flex items-center gap-2">
                  <input
                    id="remember"
                    type="checkbox"
                    className="h-3.5 w-3.5 rounded border-white/[0.1] bg-white/[0.03]"
                    disabled
                  />
                  <label
                    htmlFor="remember"
                    className="text-[12px] text-[#8a8f98]"
                  >
                    Ghi nhớ phiên đăng nhập
                  </label>
                </div>

                {/* Email login button */}
                <button
                  type="submit"
                  disabled
                  className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-[13px] font-medium text-[#62666d] cursor-not-allowed transition-colors"
                >
                  Đăng nhập bằng Email
                </button>
              </form>

              {/* Note */}
              <p className="text-center text-[11px] text-[#62666d] leading-relaxed">
                Hiện tại hỗ trợ Google Workspace. Email/Password sẽ available
                trong phiên bản tiếp theo.
              </p>
            </div>
          </div>

          {/* Bottom trust */}
          <div className="space-y-4">
            <p className="text-center text-[11px] text-[#62666d] leading-relaxed">
              Đăng nhập đồng nghĩa bạn đồng ý với{" "}
              <span className="text-[#8a8f98] hover:text-[#e4f222] cursor-pointer transition-colors">
                Điều khoản sử dụng
              </span>{" "}
              và{" "}
              <span className="text-[#8a8f98] hover:text-[#e4f222] cursor-pointer transition-colors">
                Chính sách bảo mật
              </span>
            </p>

            {/* AI-powered indicator */}
            <div className="flex items-center justify-center gap-2">
              <div className="flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5">
                <svg
                  className="h-3.5 w-3.5 text-[#e4f222]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
                  />
                </svg>
                <span className="text-[10px] font-medium text-[#8a8f98]">
                  Powered by AI Agents
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
