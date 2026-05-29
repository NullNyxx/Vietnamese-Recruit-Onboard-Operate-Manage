"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

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
    <div className="relative flex min-h-screen items-center justify-center bg-[#F7F5F2] overflow-hidden">
      {/* ─── Login Panel ─────────────────────────────────────────────────── */}
      <div
        className={`flex w-full items-center justify-center p-6 sm:p-8 transition-all duration-700 ${
          mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
        }`}
      >
        <div className="w-full max-w-[400px] space-y-8">
          {/* Logo */}
          <div className="flex items-center justify-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#B8422E]">
              <span className="text-[15px] font-bold text-white">V</span>
            </div>
            <span className="text-[15px] font-semibold text-[#1A1C1E]">
              Vroom HR
            </span>
          </div>

          {/* Login header */}
          <div className="space-y-2 text-center">
            <h2 className="text-[24px] font-semibold tracking-[-0.3px] text-[#1A1C1E]">
              Đăng nhập vào Workspace
            </h2>
            <p className="text-[14px] text-[#6C7278]">
              Truy cập hệ thống quản lý nhân sự của tổ chức
            </p>
          </div>

          {/* Login card */}
          <div className="rounded-lg border border-[#6C7278]/20 bg-white p-6">
            <div className="space-y-6">
              {/* Google OAuth Button — Primary */}
              <button
                onClick={handleLogin}
                disabled={loading}
                className="flex w-full items-center justify-center gap-3 rounded-lg bg-[#B8422E] px-4 py-3.5 text-[14px] font-semibold text-white transition-colors hover:bg-[#9C3726] focus:outline-none focus:ring-2 focus:ring-[#B8422E]/50 focus:ring-offset-2 focus:ring-offset-[#F7F5F2] disabled:opacity-60 disabled:cursor-not-allowed"
                aria-label="Đăng nhập bằng Google"
              >
                {loading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <GoogleIcon />
                )}
                <span>
                  {loading ? "Đang kết nối..." : "Đăng nhập bằng Google"}
                </span>
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-[#6C7278]/20" />
                <span className="text-[11px] text-[#6C7278]">hoặc</span>
                <div className="h-px flex-1 bg-[#6C7278]/20" />
              </div>

              {/* Email/Password form */}
              <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
                <div className="space-y-1.5">
                  <label
                    htmlFor="email"
                    className="text-[12px] font-medium text-[#6C7278]"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    placeholder="name@company.com"
                    className="w-full rounded-lg border border-[#6C7278]/20 bg-white px-4 py-3 text-[14px] text-[#1A1C1E] placeholder:text-[#6C7278]/60 transition-colors focus:border-[#B8422E]/50 focus:outline-none focus:ring-1 focus:ring-[#B8422E]/20"
                    disabled
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="password"
                      className="text-[12px] font-medium text-[#6C7278]"
                    >
                      Mật khẩu
                    </label>
                    <button
                      type="button"
                      className="text-[11px] text-[#6C7278] hover:text-[#B8422E] transition-colors"
                      disabled
                    >
                      Quên mật khẩu?
                    </button>
                  </div>
                  <input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="w-full rounded-lg border border-[#6C7278]/20 bg-white px-4 py-3 text-[14px] text-[#1A1C1E] placeholder:text-[#6C7278]/60 transition-colors focus:border-[#B8422E]/50 focus:outline-none focus:ring-1 focus:ring-[#B8422E]/20"
                    disabled
                  />
                </div>

                {/* Remember me */}
                <div className="flex items-center gap-2">
                  <input
                    id="remember"
                    type="checkbox"
                    className="h-3.5 w-3.5 rounded border-[#6C7278]/20 bg-white"
                    disabled
                  />
                  <label
                    htmlFor="remember"
                    className="text-[12px] text-[#6C7278]"
                  >
                    Ghi nhớ phiên đăng nhập
                  </label>
                </div>

                {/* Email login button */}
                <button
                  type="submit"
                  disabled
                  className="w-full rounded-lg border border-[#6C7278]/20 bg-[#F7F5F2] px-4 py-3 text-[13px] font-medium text-[#6C7278] cursor-not-allowed transition-colors"
                >
                  Đăng nhập bằng Email
                </button>
              </form>

              {/* Note */}
              <p className="text-center text-[11px] text-[#6C7278] leading-relaxed">
                Hiện tại hỗ trợ Google Workspace. Email/Password sẽ available
                trong phiên bản tiếp theo.
              </p>
            </div>
          </div>

          {/* Bottom trust */}
          <p className="text-center text-[11px] text-[#6C7278] leading-relaxed">
            Đăng nhập đồng nghĩa bạn đồng ý với{" "}
            <span className="text-[#1A1C1E] hover:text-[#B8422E] cursor-pointer transition-colors">
              Điều khoản sử dụng
            </span>{" "}
            và{" "}
            <span className="text-[#1A1C1E] hover:text-[#B8422E] cursor-pointer transition-colors">
              Chính sách bảo mật
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
