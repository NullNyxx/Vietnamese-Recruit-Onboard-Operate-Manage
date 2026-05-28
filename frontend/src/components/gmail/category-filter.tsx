"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { EmailMessage } from "@/lib/api/types";
import { CATEGORY_META, CATEGORY_GROUPS } from "./utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface CategoryFilterProps {
  emails: EmailMessage[];
  selectedCategory: string | null;
  onCategoryChange: (category: string | null) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CategoryFilter({
  emails,
  selectedCategory,
  onCategoryChange,
}: CategoryFilterProps) {
  // Count emails per category
  const categoryCounts = React.useMemo(() => {
    const counts: Record<string, number> = {};
    for (const email of emails) {
      const cat = email.category || "uncategorized";
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [emails]);

  // Get categories that have emails (for display)
  const activeCategories = React.useMemo(() => {
    const cats = new Set<string>();
    for (const email of emails) {
      cats.add(email.category || "uncategorized");
    }
    return cats;
  }, [emails]);

  const totalCount = emails.length;

  return (
    <div className="flex flex-col gap-1 px-2 py-2">
      {/* All emails button */}
      <button
        type="button"
        onClick={() => onCategoryChange(null)}
        className={cn(
          "flex items-center justify-between rounded-md px-3 py-1.5 text-sm transition-colors",
          selectedCategory === null
            ? "bg-white/[0.08] text-[#f7f8f8] font-medium"
            : "text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#c8cad0]",
        )}
      >
        <span className="flex items-center gap-2">
          <span>📬</span>
          <span>Tất cả</span>
        </span>
        <span
          className={cn(
            "min-w-[20px] rounded-full px-1.5 py-0.5 text-center text-xs",
            selectedCategory === null
              ? "bg-white/[0.12] text-[#f7f8f8]"
              : "bg-white/[0.06] text-[#62666d]",
          )}
        >
          {totalCount}
        </span>
      </button>

      {/* Category groups */}
      {CATEGORY_GROUPS.map((group) => {
        // Only show group if it has categories with emails
        const groupCategories = group.categories.filter((cat) =>
          activeCategories.has(cat),
        );
        if (groupCategories.length === 0) return null;

        return (
          <div key={group.label} className="mt-2">
            <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#62666d]">
              {group.label}
            </p>
            {groupCategories.map((category) => {
              const meta = CATEGORY_META[category];
              const count = categoryCounts[category] || 0;
              if (!meta || count === 0) return null;

              return (
                <button
                  key={category}
                  type="button"
                  onClick={() =>
                    onCategoryChange(
                      selectedCategory === category ? null : category,
                    )
                  }
                  className={cn(
                    "flex w-full items-center justify-between rounded-md px-3 py-1.5 text-sm transition-colors",
                    selectedCategory === category
                      ? "bg-white/[0.08] text-[#f7f8f8] font-medium"
                      : "text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#c8cad0]",
                  )}
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="shrink-0">{meta.icon}</span>
                    <span className="truncate">{meta.label}</span>
                  </span>
                  <span
                    className={cn(
                      "min-w-[20px] shrink-0 rounded-full px-1.5 py-0.5 text-center text-xs",
                      selectedCategory === category
                        ? "bg-white/[0.12] text-[#f7f8f8]"
                        : "bg-white/[0.06] text-[#62666d]",
                    )}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
