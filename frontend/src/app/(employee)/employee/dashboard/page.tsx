"use client";

import { FileText, User, Sparkles } from "lucide-react";
import Link from "next/link";

export default function EmployeeDashboardPage() {
  return (
    <div className="space-y-8 max-w-[900px]">
      <div className="space-y-1">
        <h1 className="text-[24px] font-semibold tracking-[-0.3px] text-[#f7f8f8]">
          Tổng quan
        </h1>
        <p className="text-[14px] text-[#8a8f98]">
          Chào mừng bạn đến với Employee Self-Service Portal
        </p>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link
          href="/employee/profile"
          className="group flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all hover:border-white/[0.1] hover:bg-white/[0.04]"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e4f222]/10">
            <User className="h-5 w-5 text-[#e4f222]" />
          </div>
          <div>
            <h3 className="text-[14px] font-medium text-[#f7f8f8]">
              Hồ sơ cá nhân
            </h3>
            <p className="text-[12px] text-[#8a8f98]">
              Xem và cập nhật thông tin
            </p>
          </div>
        </Link>

        <Link
          href="/employee/documents"
          className="group flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all hover:border-white/[0.1] hover:bg-white/[0.04]"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#5e6ad2]/10">
            <FileText className="h-5 w-5 text-[#5e6ad2]" />
          </div>
          <div>
            <h3 className="text-[14px] font-medium text-[#f7f8f8]">Tài liệu</h3>
            <p className="text-[12px] text-[#8a8f98]">Kho tài liệu cá nhân</p>
          </div>
        </Link>
      </div>

      {/* AI Assistant hint */}
      <div className="rounded-xl border border-[#e4f222]/10 bg-[#e4f222]/5 p-5">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-[#e4f222]" />
          <div>
            <h3 className="text-[14px] font-medium text-[#e4f222]">
              AI Assistant
            </h3>
            <p className="text-[12px] text-[#8a8f98]">
              Các tính năng AI sẽ được tích hợp trong phiên bản tiếp theo — bao
              gồm smart notifications, document analysis, và personalized
              insights.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
