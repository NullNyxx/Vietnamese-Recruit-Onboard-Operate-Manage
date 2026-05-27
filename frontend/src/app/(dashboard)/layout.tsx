"use client";

import { useState, useEffect } from "react";
import { Search, Bell, Sparkles } from "lucide-react";

import { AppSidebar } from "@/components/app-sidebar";
import { MobileNav } from "@/components/mobile-nav";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { CommandBar } from "@/components/command-bar";
import { NavigationProgress } from "@/components/navigation-progress";
import { PageTransition } from "@/components/page-transition";
import { Button } from "@/components/ui/button";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-[#08090a]">
      {/* Navigation progress bar */}
      <NavigationProgress />

      {/* Background subtle grid */}
      <div
        className="fixed inset-0 -z-10 opacity-[0.012]"
        aria-hidden="true"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Sidebar — persistent, never re-renders on navigation */}
      <div className="hidden md:block shrink-0">
        <AppSidebar />
      </div>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header — persistent across navigations */}
        <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-white/[0.06] bg-[#08090a]/90 px-4 lg:px-6 backdrop-blur-xl">
          <MobileNav />
          <Breadcrumbs />
          <div className="flex-1" />

          {/* AI Assistant indicator */}
          <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 backdrop-blur-sm">
            <Sparkles className="h-3 w-3 text-[#e4f222]" />
            <span className="text-[10px] font-medium text-[#8a8f98]">
              AI Ready
            </span>
          </div>

          {/* Search */}
          <Button
            variant="outline"
            size="sm"
            className="hidden gap-2 border-white/[0.06] bg-white/[0.02] text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#f7f8f8] hover:border-white/[0.1] sm:flex backdrop-blur-sm"
            onClick={() => setCommandOpen(true)}
            aria-label="Tìm kiếm (⌘K)"
          >
            <Search className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-[11px]">Search...</span>
            <kbd className="pointer-events-none ml-2 hidden h-5 select-none items-center gap-1 rounded border border-white/[0.06] bg-white/[0.03] px-1.5 font-mono text-[10px] font-medium text-[#62666d] sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>

          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="relative h-8 w-8 text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#f7f8f8]"
            aria-label="Thông báo"
          >
            <Bell className="h-4 w-4" aria-hidden="true" />
            <span className="absolute right-1.5 top-1.5 flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#e4f222] opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-[#e4f222]" />
            </span>
          </Button>
        </header>

        {/* Main content — only this area transitions */}
        <main className="relative flex-1 overflow-y-auto p-5 lg:p-8 has-[.gmail-fullbleed]:p-0 has-[.gmail-fullbleed]:overflow-hidden">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>

      <CommandBar open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
