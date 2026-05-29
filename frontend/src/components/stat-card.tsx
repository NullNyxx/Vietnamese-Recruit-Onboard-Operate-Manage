import type { LucideIcon } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  loading?: boolean;
}

export function StatCard({ title, value, icon: Icon, loading }: StatCardProps) {
  return (
    <div className="rounded-lg border border-[#6C7278]/20 bg-white p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="font-label text-xs uppercase tracking-[0.08em] text-[#6C7278]">
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-16 animate-pulse rounded-md bg-[#F7F5F2]" />
          ) : (
            <p className="font-heading text-2xl font-semibold text-[#1A1C1E]">
              {value}
            </p>
          )}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#F7F5F2]">
          <Icon className="h-5 w-5 text-[#6C7278]" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
