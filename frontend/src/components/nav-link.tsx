"use client";

import { useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { prefetchRouteData } from "@/lib/prefetch";

interface NavLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
  prefetch?: boolean;
}

/**
 * Smart navigation link that prefetches both:
 * 1. Next.js route chunk (via router.prefetch)
 * 2. API data for the target route (via React Query)
 *
 * Triggers on pointer enter (hover) or focus for keyboard nav.
 */
export function NavLink({
  href,
  children,
  className,
  prefetch = true,
}: NavLinkProps) {
  const router = useRouter();
  const hasPrefetched = useRef(false);

  const handlePrefetch = useCallback(() => {
    if (!prefetch || hasPrefetched.current) return;
    hasPrefetched.current = true;

    // Prefetch the route JS chunk
    router.prefetch(href);
    // Prefetch the API data
    prefetchRouteData(href);
  }, [href, prefetch, router]);

  return (
    <Link
      href={href}
      className={className}
      onMouseEnter={handlePrefetch}
      onFocus={handlePrefetch}
      // Reset prefetch flag after leaving (allow re-prefetch after stale)
      onMouseLeave={() => {
        // Allow re-prefetch after 30s
        setTimeout(() => {
          hasPrefetched.current = false;
        }, 30 * 1000);
      }}
    >
      {children}
    </Link>
  );
}
