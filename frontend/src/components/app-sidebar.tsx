"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, LogOut, Sparkles } from "lucide-react";

import { useSidebar } from "@/hooks/use-sidebar";
import { useCurrentUser } from "@/hooks/use-current-user";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { navItems, adminNavSection } from "@/lib/navigation";

interface AppSidebarProps {
  className?: string;
}

export function AppSidebar({ className }: AppSidebarProps) {
  const { collapsed, toggle } = useSidebar();
  const pathname = usePathname();
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  };

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex h-screen flex-col border-r border-white/[0.06] bg-[#0f1011]/80 backdrop-blur-xl transition-[width] duration-200 ease-out overflow-hidden shrink-0",
          collapsed ? "w-[60px]" : "w-[240px]",
          className,
        )}
      >
        {/* Logo section */}
        <div className="flex h-14 items-center gap-3 px-4 border-b border-white/[0.04]">
          <div className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#e4f222]">
            <span className="text-[12px] font-bold text-[#08090a]">V</span>
            <div className="absolute inset-0 rounded-md shadow-[0_0_12px_rgba(228,242,34,0.2)]" />
          </div>
          {!collapsed && (
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-semibold tracking-tight text-[#f7f8f8]">
                Vroom
              </span>
              <span className="rounded-full bg-[#e4f222]/10 px-1.5 py-0.5 text-[9px] font-medium text-[#e4f222]">
                AI
              </span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav
          className="flex-1 space-y-0.5 px-2 py-3 overflow-y-auto"
          aria-label="Điều hướng chính"
        >
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            const linkContent = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all",
                  isActive
                    ? "bg-[#e4f222]/10 text-[#e4f222] shadow-[inset_0_0_0_1px_rgba(228,242,34,0.15)]"
                    : "text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]",
                  collapsed && "justify-center px-2",
                )}
              >
                <item.icon
                  className="h-[18px] w-[18px] shrink-0"
                  aria-hidden="true"
                />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent
                    side="right"
                    className="bg-[#161718] text-[#f7f8f8] border-white/[0.06]"
                  >
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.href}>{linkContent}</div>;
          })}

          {/* Admin section */}
          {isAdmin && (
            <>
              <div className="my-3 h-px bg-white/[0.04]" />
              {!collapsed && (
                <div className="flex items-center gap-2 px-3 py-1.5">
                  <adminNavSection.icon
                    className="h-3.5 w-3.5 text-[#62666d]"
                    aria-hidden="true"
                  />
                  <span className="text-[10px] font-medium uppercase tracking-widest text-[#62666d]">
                    {adminNavSection.title}
                  </span>
                </div>
              )}
              {adminNavSection.items.map((item) => {
                const isActive = pathname.startsWith(item.href);

                const linkContent = (
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-all",
                      isActive
                        ? "bg-[#e4f222]/10 text-[#e4f222] shadow-[inset_0_0_0_1px_rgba(228,242,34,0.15)]"
                        : "text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]",
                      collapsed && "justify-center px-2",
                    )}
                  >
                    <item.icon
                      className="h-[18px] w-[18px] shrink-0"
                      aria-hidden="true"
                    />
                    {!collapsed && <span>{item.label}</span>}
                  </Link>
                );

                if (collapsed) {
                  return (
                    <Tooltip key={item.href}>
                      <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                      <TooltipContent
                        side="right"
                        className="bg-[#161718] text-[#f7f8f8] border-white/[0.06]"
                      >
                        {item.label}
                      </TooltipContent>
                    </Tooltip>
                  );
                }

                return <div key={item.href}>{linkContent}</div>;
              })}
            </>
          )}
        </nav>

        {/* Bottom section */}
        <div
          className={cn(
            "mt-auto border-t border-white/[0.04] py-3 space-y-1",
            collapsed ? "px-1" : "px-2",
          )}
        >
          {/* AI Status */}
          {!collapsed && (
            <div className="mx-2 mb-3 flex items-center gap-2 rounded-lg bg-[#e4f222]/5 border border-[#e4f222]/10 px-3 py-2">
              <Sparkles className="h-3.5 w-3.5 text-[#e4f222]" />
              <div className="flex-1">
                <p className="text-[11px] font-medium text-[#e4f222]">
                  AI Agents
                </p>
                <p className="text-[10px] text-[#8a8f98]">3 active, 1 idle</p>
              </div>
            </div>
          )}

          {/* User info */}
          {!collapsed && user && (
            <div className="px-3 py-1.5">
              <p className="text-[12px] font-medium text-[#d0d6e0] truncate">
                {user.email?.split("@")[0]}
              </p>
              <p className="text-[10px] text-[#62666d] truncate">
                {user.email}
              </p>
            </div>
          )}

          {/* Toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={toggle}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-[#8a8f98] transition-all hover:bg-white/[0.04] hover:text-[#d0d6e0]",
                  collapsed ? "mx-auto justify-center px-2 w-full" : "w-full",
                )}
                aria-label={collapsed ? "Mở rộng" : "Thu gọn"}
              >
                {collapsed ? (
                  <ChevronRight
                    className="h-[18px] w-[18px]"
                    aria-hidden="true"
                  />
                ) : (
                  <>
                    <ChevronLeft
                      className="h-[18px] w-[18px]"
                      aria-hidden="true"
                    />
                    <span>Thu gọn</span>
                  </>
                )}
              </button>
            </TooltipTrigger>
            {collapsed && (
              <TooltipContent
                side="right"
                className="bg-[#161718] text-[#f7f8f8] border-white/[0.06]"
              >
                Mở rộng
              </TooltipContent>
            )}
          </Tooltip>

          {/* Logout */}
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={handleLogout}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-[#8a8f98] transition-all hover:bg-white/[0.04] hover:text-[#eb5757]",
                  collapsed ? "mx-auto justify-center px-2 w-full" : "w-full",
                )}
                aria-label="Đăng xuất"
              >
                <LogOut className="h-[18px] w-[18px]" aria-hidden="true" />
                {!collapsed && <span>Đăng xuất</span>}
              </button>
            </TooltipTrigger>
            {collapsed && (
              <TooltipContent
                side="right"
                className="bg-[#161718] text-[#f7f8f8] border-white/[0.06]"
              >
                Đăng xuất
              </TooltipContent>
            )}
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}
