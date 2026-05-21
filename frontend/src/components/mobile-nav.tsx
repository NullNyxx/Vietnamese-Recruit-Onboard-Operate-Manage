"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, LogOut } from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { navItems, adminNavSection } from "@/lib/navigation";
import { useCurrentUser } from "@/hooks/use-current-user";

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";

  const handleLogout = async () => {
    setOpen(false);
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon"
        className="min-h-[44px] min-w-[44px] md:hidden"
        onClick={() => setOpen(true)}
        aria-label="Mở menu điều hướng"
      >
        <Menu className="h-6 w-6" aria-hidden="true" />
      </Button>

      <SheetContent side="left" className="flex w-72 flex-col p-0">
        <SheetHeader className="px-4 pt-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-bold">
              V
            </div>
            <SheetTitle className="text-lg font-semibold">
              Vroom HR
            </SheetTitle>
          </div>
          <SheetDescription className="sr-only">
            Menu điều hướng chính
          </SheetDescription>
        </SheetHeader>

        <Separator className="mt-4" />

        {/* Navigation links */}
        <nav className="flex-1 space-y-1 px-2 py-4" aria-label="Điều hướng chính">
          {navItems.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-muted"
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {/* Admin navigation section — only visible to admin users */}
          {isAdmin && (
            <>
              <Separator className="my-3" />
              <div className="flex items-center gap-2 px-3 py-1">
                <adminNavSection.icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {adminNavSection.title}
                </span>
              </div>
              {adminNavSection.items.map((item) => {
                const isActive = pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "flex min-h-[44px] items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-muted"
                    )}
                  >
                    <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* Bottom section */}
        <div className="mt-auto px-2 pb-4">
          <Separator className="mb-4" />
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="min-h-[44px] w-full justify-start gap-3 text-sidebar-foreground hover:bg-muted"
            aria-label="Đăng xuất"
          >
            <LogOut className="h-5 w-5" aria-hidden="true" />
            <span>Đăng xuất</span>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
