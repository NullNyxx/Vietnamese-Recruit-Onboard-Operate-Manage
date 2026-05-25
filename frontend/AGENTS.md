# Frontend Agent Instructions

## Stack

- Next.js 14 (App Router), TypeScript 5.6, React 18
- Tailwind CSS 3.4, shadcn/ui (Radix UI primitives)
- react-hook-form + zod validation
- lucide-react icons, sonner toasts, cmdk command palette
- date-fns, next-themes (dark mode)
- pnpm package manager
- Vitest + fast-check (property-based testing)

## Project Structure

```
src/
├── app/
│   ├── (dashboard)/     # Admin routes (employees, attendance, payroll, recruitment, settings)
│   ├── (employee)/      # Employee self-service routes
│   ├── login/           # Login page
│   └── layout.tsx       # Root layout
├── components/
│   ├── ui/              # shadcn/ui base components (DO NOT EDIT manually)
│   └── *.tsx            # App-specific components (sidebar, data-table, etc.)
├── hooks/               # Custom hooks (use-current-user, use-sidebar, use-debounce)
└── lib/
    ├── api/             # API client functions (one file per module)
    ├── navigation.ts    # Sidebar nav config
    └── utils.ts         # cn() helper, formatters
```

## Key Rules

1. **App Router:** Use `app/` directory with layouts, pages, loading, error boundaries
2. **Server Components by default:** Only add `"use client"` when needed (interactivity, hooks)
3. **API calls:** Use `lib/api/<module>.ts` — fetch from `/api/...` (proxied to backend)
4. **Forms:** Always use react-hook-form + zod schema validation
5. **UI components:** Use shadcn/ui. Run `pnpm dlx shadcn@latest add <component>` for new ones
6. **Styling:** Tailwind only. No CSS modules, no styled-components
7. **Icons:** lucide-react only. No other icon libraries
8. **Toasts:** Use sonner (`toast.success()`, `toast.error()`)
9. **Dark mode:** All components must work in both light and dark mode
10. **No Bearer tokens:** Auth is cookie-based. API calls don't need Authorization headers

## Commands

```bash
pnpm dev          # Dev server (port 3000)
pnpm build        # Production build
pnpm lint         # ESLint
pnpm test         # Vitest (single run)
pnpm test:watch   # Vitest (watch mode)
```

## API Client Pattern

```typescript
// lib/api/payroll.ts
const API_BASE = "/api/payroll";

export async function getPayrollPeriods() {
  const res = await fetch(`${API_BASE}/periods`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch periods");
  return res.json();
}
```

## Page Pattern

```typescript
// app/(dashboard)/payroll/page.tsx
"use client";

import { useEffect, useState } from "react";
import { getPayrollPeriods } from "@/lib/api/payroll";

export default function PayrollPage() {
  // ...
}
```

## Existing Pages

| Route        | Description                                 |
| ------------ | ------------------------------------------- |
| /login       | Google OAuth login                          |
| /employees   | Employee list + CRUD                        |
| /attendance  | Check-in/out dashboard                      |
| /leave       | Leave management                            |
| /payroll     | Payroll periods & payslips                  |
| /recruitment | Candidate pipeline                          |
| /gmail       | Email integration                           |
| /settings    | Departments, positions, holidays, schedules |
| /admin       | Whitelist, OAuth config, roles, audit       |
