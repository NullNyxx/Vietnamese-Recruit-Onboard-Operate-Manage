"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

interface PageTransitionProps {
  children: React.ReactNode;
}

/**
 * Smooth page transition with subtle fade + slide.
 * Uses CSS transitions for 60fps performance (no JS animation library).
 * Duration is kept very short (150ms) to feel instant, not sluggish.
 */
export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const [displayChildren, setDisplayChildren] = useState(children);
  const [transitionStage, setTransitionStage] = useState<"enter" | "idle">(
    "idle",
  );
  const prevPathname = useRef(pathname);

  useEffect(() => {
    if (pathname !== prevPathname.current) {
      prevPathname.current = pathname;
      setTransitionStage("enter");
      setDisplayChildren(children);

      // Reset to idle after animation completes
      const timer = setTimeout(() => {
        setTransitionStage("idle");
      }, 150);

      return () => clearTimeout(timer);
    } else {
      // Same route, just update children (e.g. data change)
      setDisplayChildren(children);
    }
  }, [pathname, children]);

  return (
    <div
      className={
        transitionStage === "enter"
          ? "animate-page-enter"
          : "opacity-100 translate-y-0"
      }
    >
      {displayChildren}
    </div>
  );
}
