# Performance Optimization

## Overview

This document covers performance best practices for Vroom HR frontend, focusing on Next.js 14 optimization techniques.

## Core Web Vitals

Vroom HR targets these Core Web Vitals:

| Metric                         | Target  | Impact           |
| ------------------------------ | ------- | ---------------- |
| LCP (Largest Contentful Paint) | < 2.5s  | Page load speed  |
| FID (First Input Delay)        | < 100ms | Interactivity    |
| CLS (Cumulative Layout Shift)  | < 0.1   | Visual stability |

## Next.js Optimizations

### Server Components (Default)

Use server components by default — they reduce JavaScript sent to client:

```typescript
// ✅ Good - Server Component (default)
export default async function EmployeesPage() {
  const employees = await getEmployees(); // Runs on server
  return <EmployeeList employees={employees} />;
}

// Only add "use client" when needed
"use client";
export function EmployeeSearch() {
  // Client-side interactivity
}
```

### When to Use Client Components

Add `"use client"` only when you need:

- `useState`, `useEffect`, `useRef`
- Event handlers (onClick, onChange)
- Browser-only APIs
- Custom hooks that use above

```typescript
// ❌ Bad - Unnecessary client component
"use client";

export function EmployeeList({ employees }) {
  return <ul>{employees.map(e => <li key={e.id}>{e.name}</li>)}</ul>;
}

// ✅ Good - Server Component
export default function EmployeeList({ employees }) {
  return <ul>{employees.map(e => <li key={e.id}>{e.name}</li>)}</ul>;
}
```

## Image Optimization

### Using next/image

```typescript
import Image from "next/image";

export function EmployeeAvatar({ src, name }) {
  return (
    <Image
      src={src}
      alt={name}
      width={40}
      height={40}
      className="rounded-full"
    />
  );
}
```

### Best Practices

```typescript
// ✅ Good - Proper sizing
<Image
  src={avatar}
  alt="Employee"
  width={48}
  height={48}
  sizes="48px"
/>

// ✅ Good - Lazy loading (default)
<Image src={largeImage} loading="lazy" />

// ✅ Good - Priority for above-fold
<Image src={heroImage} priority />

// ❌ Bad - No dimensions (causes layout shift)
<Image src={image} />
```

### Responsive Images

```typescript
<Image
  src={avatar}
  alt="Employee"
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
/>
```

## Font Optimization

### Using next/font

Fonts are automatically optimized in Next.js:

```typescript
// src/app/layout.tsx
import { Plus_Jakarta_Sans, DM_Sans } from "next/font/google";

const heading = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap", // Prevents FOIT
});

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export default function Layout({ children }) {
  return (
    <html className={`${heading.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

### Display Options

| Option     | Behavior                                      |
| ---------- | --------------------------------------------- |
| `swap`     | Show fallback, swap when loaded (recommended) |
| `block`    | Hide text until font loads (FOIT)             |
| `fallback` | Show fallback, never swap                     |
| `optional` | Browser decides                               |

## Code Splitting

### Dynamic Imports

```typescript
import dynamic from "next/dynamic";

// ✅ Good - Lazy load heavy components
const DataChart = dynamic(() => import("@/components/DataChart"), {
  loading: () => <Skeleton />,
  ssr: false, // Only load on client
});

// ✅ Good - Conditional client components
const DatePicker = dynamic(
  () => import("@/components/ui/date-picker"),
  { ssr: false }
);
```

### When to Use Dynamic Imports

- Heavy UI libraries (charts, maps)
- Components below the fold
- Client-only components (using browser APIs)
- Modals, dialogs (load when opened)

```typescript
// ❌ Bad - Unnecessary dynamic import
const Button = dynamic(() => import("@/components/ui/button"));

// ✅ Good - Direct import for small components
import { Button } from "@/components/ui/button";
```

## Data Fetching

### Server-Side Fetching

```typescript
// ✅ Good - Server component fetch
async function Page() {
  const data = await fetch("https://api.example.com/data", {
    cache: "no-store", // Dynamic
    // or
    cache: "force-cache", // Static (default)
    next: { revalidate: 60 }, // ISR: revalidate every 60s
  });

  return <Content data={data} />;
}
```

### Client-Side Fetching

```typescript
"use client";

import { useEffect, useState } from "react";

function EmployeeList() {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchEmployees() {
      try {
        const res = await fetch("/api/v1/employees");
        const data = await res.json();
        if (!cancelled) setEmployees(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchEmployees();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Skeleton />;

  return <List items={employees} />;
}
```

### SWR for Caching

Consider using SWR for client-side data with caching:

```typescript
"use client";

import useSWR from "swr";

const fetcher = (url) => fetch(url).then((res) => res.json());

function EmployeeList() {
  const { data, error, isLoading } = useSWR(
    "/api/v1/employees",
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    }
  );

  if (isLoading) return <Skeleton />;
  if (error) return <Error />;

  return <List items={data} />;
}
```

## Memoization

### useMemo

```typescript
// ✅ Good - Expensive computation
const filteredEmployees = useMemo(() => {
  return employees.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase()),
  );
}, [employees, search]);

// ❌ Bad - Unnecessary memoization
const doubled = useMemo(() => count * 2, [count]);
```

### useCallback

```typescript
// ✅ Good - Stable function reference for dependencies
const handleClick = useCallback((id: string) => {
  router.push(`/employees/${id}`);
}, [router]);

// ✅ Good - Pass to child component
<ChildComponent onAction={handleClick} />
```

### React.memo

```typescript
// For pure presentational components
const EmployeeRow = memo(function EmployeeRow({ employee }) {
  return <tr>{employee.name}</tr>;
});

// ✅ Good - Prevents re-render when props don't change
const list = [/* same reference */];
<EmployeeRow employee={list[0]} />
```

## Bundle Size

### Analyzing Bundle

```bash
# Analyze bundle size
pnpm build
# or
pnpm analyze  # If @next/bundle-analyzer is configured
```

### Reducing Bundle Size

```typescript
// ❌ Bad - Import entire library
import _ from "lodash";
const filtered = _.filter(items, condition);

// ✅ Good - Import specific function
import filter from "lodash/filter";
const filtered = filter(items, condition);

// ✅ Better - Use native methods
const filtered = items.filter(condition);
```

### Tree Shaking

Ensure packages support tree shaking:

```json
// package.json
{
  "sideEffects": false
}
```

All imports must use ESM syntax for tree shaking.

## Caching Strategies

### Static vs Dynamic

| Data Type      | Strategy           | Example                |
| -------------- | ------------------ | ---------------------- |
| Reference data | Static (cache)     | Departments, positions |
| User data      | Dynamic (no-store) | Employee profile       |
| Semi-static    | ISR (revalidate)   | Leave types            |

```typescript
// Static - Cache indefinitely
const depts = await fetch("/api/departments", {
  cache: "force-cache",
});

// Dynamic - No cache
const profile = await fetch("/api/v1/ess/profile", {
  cache: "no-store",
});

// ISR - Revalidate every hour
const leaveTypes = await fetch("/api/leave/types", {
  next: { revalidate: 3600 },
});
```

### Route Cache

```typescript
// Force static generation
export const dynamic = "force-static";

// Force dynamic
export const dynamic = "force-dynamic";

// ISR with specific interval
export const revalidate = 60;
```

## Rendering Optimization

### Virtualization

For long lists, use virtualization:

```typescript
import { useVirtualizer } from "@tanstack/react-virtual";

function VirtualList({ items }) {
  const parentRef = useRef(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35,
  });

  return (
    <div ref={parentRef} className="h-[500px] overflow-auto">
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: "absolute",
              top: virtualItem.start,
              height: virtualItem.size,
            }}
          >
            {items[virtualItem.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Debouncing

```typescript
import { useDebounce } from "@/hooks/use-debounce";

function SearchInput() {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    // API call only fires when user stops typing
    search(debouncedQuery);
  }, [debouncedQuery]);

  return <Input value={query} onChange={(e) => setQuery(e.target.value)} />;
}
```

## Performance Monitoring

### Core Web Vitals in Analytics

```typescript
// next.config.js
module.exports = {
  analytics: {
    vercel: {
      // Vercel Analytics
    },
  },
};
```

### Custom Performance Tracking

```typescript
// Track component mount time
function Component() {
  useEffect(() => {
    const metric = performance.getEntriesByName("component-mount")[0];
    console.log("Component render time:", metric?.duration);
  }, []);

  return <div>Content</div>;
}
```

### LCP Optimization Checklist

1. ✅ Use `priority` prop on hero image
2. ✅ Preload critical fonts
3. ✅ Inline critical CSS
4. ✅ Use server components
5. ✅ Minimize main thread work

### FID Optimization Checklist

1. ✅ Keep JS bundle small
2. ✅ Defer non-critical JS
3. ✅ Use server components
4. ✅ Break up long tasks

### CLS Optimization Checklist

1. ✅ Set image dimensions
2. ✅ Reserve space for dynamic content
3. ✅ Use font-display: swap
4. ✅ Avoid layout shifts from ads

## Build & Deployment

### Production Build

```bash
# Build for production
pnpm build

# Analyze bundle
ANALYZE=true pnpm build
```

### Environment Variables

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.vroomhr.com
```

### Caching Headers

In `next.config.js`:

```javascript
module.exports = {
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
};
```

## Testing Performance

### Lighthouse CI

```bash
# Run Lighthouse
npx lhci autorun

# Or via GitHub Actions
- name: Lighthouse CI
  uses: treosh/lighthouse-ci-action@v9
```

### Web Vitals Testing

```typescript
// vitest/setup.ts
import { expect, vi } from "vitest";

// Mock web vitals
vi.mock("web-vitals", () => ({
  onCLS: vi.fn(),
  onFID: vi.fn(),
  onLCP: vi.fn(),
}));
```

## Common Pitfalls

### 1. Large Client Bundles

**Problem:** Too much JavaScript on client

**Solution:** Use server components, dynamic imports

### 2. Unnecessary Re-renders

**Problem:** Components re-render unnecessarily

**Solution:** Use memo, useCallback properly

### 3. Large Images

**Problem:** Images not optimized

**Solution:** Use next/image with proper sizes

### 4. Blocking JS

**Problem:** JS blocks rendering

**Solution:** Defer scripts, use server components

### 5. Unoptimized Fonts

**Problem:** FOUT/FOIT

**Solution:** Use next/font with display: swap

## Quick Reference

| Optimization      | Impact     | Effort |
| ----------------- | ---------- | ------ |
| Server Components | High       | Low    |
| next/image        | High       | Low    |
| next/font         | Medium     | Low    |
| Dynamic Imports   | Medium     | Medium |
| Memoization       | Low-Medium | Medium |
| Virtualization    | High       | High   |

## Commands

```bash
# Development
pnpm dev

# Production build
pnpm build

# Analyze bundle
ANALYZE=true pnpm build

# Lighthouse CI
npx lhci autorun
```
