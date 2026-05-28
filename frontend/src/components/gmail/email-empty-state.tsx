"use client";

import { Sparkles, Mail, RefreshCw } from "lucide-react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EmailEmptyStateProps {
  /** Whether emails are currently being synced */
  syncing?: boolean;
  /** Whether this is the first time (no emails ever synced) */
  isFirstSync?: boolean;
  /** Callback to trigger manual sync */
  onSync?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Empty state shown when there are no emails to display.
 * Provides context about the AI classification feature and
 * guides HR users on what to expect.
 */
export function EmailEmptyState({
  syncing = false,
  isFirstSync = false,
  onSync,
}: EmailEmptyStateProps) {
  if (syncing) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-8 text-center h-full">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-500/10">
          <RefreshCw className="h-7 w-7 text-blue-400 animate-spin" />
        </div>
        <div>
          <p className="text-sm font-medium text-[#c8cad0]">
            Đang đồng bộ email...
          </p>
          <p className="mt-1 text-xs text-[#62666d]">
            Hệ thống đang tải email từ Gmail và phân loại tự động
          </p>
        </div>
      </div>
    );
  }

  if (isFirstSync) {
    return (
      <div className="flex flex-col items-center justify-center gap-5 p-8 text-center h-full">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#e4f222]/20 to-[#e4f222]/5 border border-[#e4f222]/20">
          <Sparkles className="h-8 w-8 text-[#e4f222]" />
        </div>
        <div className="max-w-[280px]">
          <h3 className="text-base font-semibold text-[#f7f8f8]">
            AI Phân loại Email
          </h3>
          <p className="mt-2 text-sm text-[#8a8f98] leading-relaxed">
            Nhấn <strong className="text-[#c8cad0]">Đồng bộ</strong> để tải
            email. Hệ thống sẽ tự động phân loại thành các nhóm: Tuyển dụng,
            Nghỉ phép, Lương, Đối tác...
          </p>
        </div>
        <div className="flex flex-col items-center gap-3">
          {onSync && (
            <button
              type="button"
              onClick={onSync}
              className="inline-flex items-center gap-2 rounded-lg bg-[#e4f222] px-4 py-2.5 text-sm font-semibold text-[#08090a] hover:bg-[#d4e220] transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Đồng bộ email ngay
            </button>
          )}
          <p className="text-[10px] text-[#62666d]">
            Email 7 ngày gần nhất sẽ được tải về
          </p>
        </div>

        {/* Feature highlights */}
        <div className="mt-4 grid grid-cols-1 gap-2 w-full max-w-[280px]">
          <FeatureItem
            icon="📄"
            title="Tuyển dụng"
            desc="CV, ứng viên, headhunter"
          />
          <FeatureItem
            icon="🏖️"
            title="Nghỉ phép"
            desc="Đơn xin nghỉ, nghỉ ốm"
          />
          <FeatureItem
            icon="💰"
            title="Lương & Phúc lợi"
            desc="Payslip, thuế, thưởng"
          />
          <FeatureItem
            icon="🏢"
            title="Đối tác"
            desc="Vendor, báo giá, dịch vụ"
          />
        </div>
      </div>
    );
  }

  // Default: no emails match filter
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 text-center h-full">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/[0.04]">
        <Mail className="h-6 w-6 text-[#62666d]" />
      </div>
      <div>
        <p className="text-sm font-medium text-[#8a8f98]">Không có email nào</p>
        <p className="mt-1 text-xs text-[#62666d]">
          Thử chọn nhóm khác hoặc đồng bộ để tải email mới
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feature Item (for first-sync empty state)
// ---------------------------------------------------------------------------

function FeatureItem({
  icon,
  title,
  desc,
}: {
  icon: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] px-3 py-2">
      <span className="text-base">{icon}</span>
      <div className="text-left">
        <p className="text-[11px] font-medium text-[#c8cad0]">{title}</p>
        <p className="text-[10px] text-[#62666d]">{desc}</p>
      </div>
    </div>
  );
}
