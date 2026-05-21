"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield } from "lucide-react";

import { useCurrentUser } from "@/hooks/use-current-user";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && user.role !== "admin") {
      router.replace("/");
    }
  }, [user, loading, router]);

  // Show loading state while checking role
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Shield className="h-8 w-8 animate-pulse" aria-hidden="true" />
          <p className="text-sm">Đang kiểm tra quyền truy cập...</p>
        </div>
      </div>
    );
  }

  // If not admin, show nothing while redirecting
  if (!user || user.role !== "admin") {
    return null;
  }

  return <>{children}</>;
}
