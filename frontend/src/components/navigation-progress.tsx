"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

/**
 * Thin progress bar at the top of the page during navigation.
 * Similar to Linear/GitHub's navigation indicator.
 * Only shows if navigation takes > 100ms (avoids flash for instant navigations).
 */
export function NavigationProgress() {
  const pathname = usePathname();
  const [isNavigating, setIsNavigating] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Reset on route change (navigation complete)
    setIsNavigating(false);
    setProgress(0);
  }, [pathname]);

  useEffect(() => {
    // Listen for navigation start via Next.js router events
    // We use a MutationObserver on the body to detect loading states
    let timeout: NodeJS.Timeout;
    let interval: NodeJS.Timeout;

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest("a");
      if (!anchor) return;

      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("http") || href.startsWith("#")) return;
      if (href === pathname) return;

      // Start progress after 100ms delay (skip for instant navigations)
      timeout = setTimeout(() => {
        setIsNavigating(true);
        setProgress(20);

        // Simulate progress
        interval = setInterval(() => {
          setProgress((prev) => {
            if (prev >= 90) {
              clearInterval(interval);
              return 90;
            }
            return prev + Math.random() * 15;
          });
        }, 200);
      }, 100);
    };

    document.addEventListener("click", handleClick);

    return () => {
      document.removeEventListener("click", handleClick);
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, [pathname]);

  if (!isNavigating) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] h-[2px]">
      <div
        className="h-full bg-[#e4f222] transition-[width] duration-200 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
