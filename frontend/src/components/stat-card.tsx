import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  loading?: boolean;
  trend?: string;
  color?: "lime" | "blue" | "cyan" | "green" | "violet";
}

export function StatCard({
  title,
  value,
  icon: Icon,
  loading,
  color = "lime",
}: StatCardProps) {
  const colorMap = {
    lime: "text-[#e4f222]",
    blue: "text-[#5e6ad2]",
    cyan: "text-[#02b8cc]",
    green: "text-[#27a644]",
    violet: "text-[#8b5cf6]",
  };

  const bgColorMap = {
    lime: "bg-[#e4f222]/10",
    blue: "bg-[#5e6ad2]/10",
    cyan: "bg-[#02b8cc]/10",
    green: "bg-[#27a644]/10",
    violet: "bg-[#8b5cf6]/10",
  };

  return (
    <div className="rounded-md border border-[#23252a] bg-[#0f1011] p-5 transition-colors hover:border-[#323334]">
      <div className="flex items-center gap-4">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-md ${bgColorMap[color]}`}
        >
          <Icon className={`h-5 w-5 ${colorMap[color]}`} aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <p className="text-[13px] text-[#8a8f98]">{title}</p>
          {loading ? (
            <div className="h-7 w-16 animate-pulse rounded bg-[#161718]" />
          ) : (
            <p className="text-[22px] font-semibold tracking-[-0.22px] text-[#f7f8f8]">
              {value}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
