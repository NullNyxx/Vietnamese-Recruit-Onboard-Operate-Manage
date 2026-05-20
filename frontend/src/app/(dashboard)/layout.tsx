"use client";

import { useState, useEffect } from "react";
import { Search } from "lucide-react";

import { AppSidebar } from "@/components/app-sidebar";
import { MobileNav } from "@/components/mobile-nav";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { CommandBar } from "@/components/command-bar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [commandOpen, setCommandOpen] = useState(false);

  // Register ⌘K / Ctrl+K keyboard shortcut
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
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar — hidden on mobile, fixed height */}
      <div className="hidden md:block shrink-0">
        <AppSidebar />
      </div>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          {/* Mobile menu trigger */}
          <MobileNav />

          {/* Breadcrumbs */}
          <Breadcrumbs />

          {/* Spacer */}
          <div className="flex-1" />

          {/* Command bar trigger */}
          <Button
            variant="outline"
            size="sm"
            className="hidden gap-2 text-muted-foreground sm:flex"
            onClick={() => setCommandOpen(true)}
            aria-label="Tìm kiếm (⌘K)"
          >
            <Search className="h-4 w-4" aria-hidden="true" />
            <span className="text-xs">Tìm kiếm...</span>
            <kbd className="pointer-events-none ml-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>

          {/* Theme toggle */}
          <ThemeToggle />
        </header>

        {/* Main content */}
        <main className="relative flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 has-[.gmail-fullbleed]:p-0 has-[.gmail-fullbleed]:overflow-hidden">
          {children}
        </main>
      </div>

      {/* Command bar dialog */}
      <CommandBar open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
}
