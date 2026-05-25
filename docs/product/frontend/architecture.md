# Frontend Architecture

## Folder Structure

```
frontend/src/
├── app/                    # Next.js App Router
│   ├── (dashboard)/       # Admin role routes
│   │   ├── admin/         # Admin management
│   │   ├── attendance/    # Attendance management
│   │   ├── employees/     # Employee CRUD
│   │   ├── gmail/         # Gmail integration
│   │   ├── leave/         # Leave management
│   │   ├── payroll/       # Payroll management
│   │   ├── recruitment/   # Recruitment management
│   │   ├── settings/      # System settings
│   │   ├── layout.tsx     # Dashboard layout with sidebar
│   │   └── page.tsx       # Dashboard home
│   ├── (employee)/        # Employee self-service routes
│   │   ├── employee/      # ESS pages
│   │   │   ├── dashboard/ # ESS dashboard
│   │   │   ├── attendance/# Check-in/out
│   │   │   ├── leave/     # Leave requests
│   │   │   ├── overtime/  # Overtime requests
│   │   │   ├── schedule/  # Work schedule
│   │   │   ├── profile/   # Profile management
│   │   │   └── documents/ # Document download
│   │   └── layout.tsx     # ESS layout
│   ├── login/             # Login page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global Tailwind + custom styles
├── components/
│   ├── ui/                # shadcn/ui components (Button, Card, etc.)
│   ├── admin/             # Admin-specific components
│   │   ├── audit-log-table.tsx
│   │   ├── oauth-config-form.tsx
│   │   ├── user-role-select.tsx
│   │   ├── whitelist-add-form.tsx
│   │   └── whitelist-table.tsx
│   ├── gmail/             # Gmail UI components
│   ├── recruitment/       # Recruitment UI components
│   ├── app-sidebar.tsx    # Dashboard sidebar
│   ├── breadcrumbs.tsx    # Breadcrumb navigation
│   ├── command-bar.tsx    # Command palette (Ctrl+K)
│   ├── data-table.tsx     # Reusable data table
│   ├── employee-form.tsx  # Employee create/edit form
│   ├── employee-sidebar.tsx
│   ├── employee-mobile-nav.tsx
│   ├── grant-warning-modal.tsx
│   ├── mobile-nav.tsx
│   ├── page-transition.tsx
│   ├── providers.tsx      # Context providers (theme, etc.)
│   ├── stat-card.tsx      # Statistics card
│   └── theme-toggle.tsx   # Dark/light mode toggle
├── hooks/                 # Custom React hooks
│   ├── use-current-user.ts
│   ├── use-debounce.ts
│   └── use-sidebar.ts
└── lib/
    ├── api/               # API client functions
    │   ├── index.ts       # Exports all API modules
    │   ├── types.ts       # Shared TypeScript types
    │   ├── admin.ts       # Admin endpoints
    │   ├── attendance.ts  # Attendance endpoints
    │   ├── departments.ts # Department endpoints
    │   ├── employees.ts   # Employee endpoints
    │   ├── ess.ts         # ESS endpoints
    │   ├── gmail.ts       # Gmail endpoints
    │   ├── leave.ts       # Leave endpoints
    │   ├── payroll.ts     # Payroll endpoints
    │   ├── positions.ts   # Position endpoints
    │   └── recruitment.ts # Recruitment endpoints
    ├── utils.ts           # Utility functions (cn, formatters)
    ├── navigation.ts      # Navigation config
    └── employee-navigation.ts
```

## Route Structure

### Admin Routes (Role: admin)

| URL                       | Page            | Description             |
| ------------------------- | --------------- | ----------------------- |
| `/`                       | Dashboard       | Overview stats          |
| `/employees`              | Employee List   | Employee CRUD           |
| `/employees/new`          | Create Employee | Add new employee        |
| `/employees/[id]`         | Employee Detail | View/edit employee      |
| `/attendance`             | Attendance      | Check-in/out management |
| `/leave`                  | Leave Requests  | Approve/reject leave    |
| `/leave/types`            | Leave Types     | Configure leave types   |
| `/payroll`                | Payroll         | Salary management       |
| `/payroll/periods`        | Payroll Periods | Configure periods       |
| `/recruitment`            | Recruitment     | Candidate pipeline      |
| `/recruitment/candidates` | Candidates      | Manage candidates       |
| `/gmail`                  | Gmail           | Gmail integration       |
| `/settings/departments`   | Departments     | Manage departments      |
| `/settings/positions`     | Positions       | Manage positions        |
| `/settings/schedules`     | Schedules       | Work schedules          |
| `/settings/leave-types`   | Leave Types     | Leave configuration     |
| `/admin/whitelist`        | Whitelist       | Email whitelist         |
| `/admin/oauth`            | OAuth Config    | OAuth settings          |
| `/admin/audit-logs`       | Audit Logs      | System logs             |

### Employee Self-Service Routes (Role: employee)

| URL                      | Page         | Description          |
| ------------------------ | ------------ | -------------------- |
| `/employee/dashboard`    | Dashboard    | Today's status       |
| `/employee/attendance`   | Attendance   | Check-in/out         |
| `/employee/leave`        | My Leaves    | Leave requests       |
| `/employee/leave/new`    | New Leave    | Submit leave request |
| `/employee/overtime`     | Overtime     | Overtime requests    |
| `/employee/overtime/new` | New Overtime | Submit overtime      |
| `/employee/schedule`     | Schedule     | Work schedule        |
| `/employee/profile`      | Profile      | Update profile       |
| `/employee/documents`    | Documents    | Download documents   |

### Auth Routes

| URL      | Page  | Description        |
| -------- | ----- | ------------------ |
| `/login` | Login | Google OAuth login |

## Component Patterns

### Client Component ("use client")

```typescript
"use client";

import { useState, useEffect } from "react";
// ... hooks and imports

export function ComponentName() {
  const [state, setState] = useState<Type>();

  // ... component logic

  return <div>...</div>;
}
```

### Server Component (Default)

```typescript
// Server component by default (no "use client")
import { fetchData } from "@/lib/api";

export default async function Page() {
  const data = await fetchData();

  return <div>{data.name}</div>;
}
```

### Using shadcn/ui Components

```typescript
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
```

### Data Table Pattern

```typescript
import { DataTable } from "@/components/data-table";
import { columns } from "./columns";

export function EmployeeTable({ data }) {
  return <DataTable columns={columns} data={data} />;
}
```

## API Client Pattern

Each module has its own API file in `src/lib/api/`:

```typescript
// src/lib/api/employees.ts
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface Employee {
  id: string;
  email: string;
  full_name: string;
  // ...
}

export async function getEmployees(): Promise<Employee[]> {
  const res = await fetch("/api/v1/employees");
  return handleResponse<Employee[]>(res);
}

export async function getEmployee(id: string): Promise<Employee> {
  const res = await fetch(`/api/v1/employees/${id}`);
  return handleResponse<Employee>(res);
}

export async function createEmployee(
  data: CreateEmployeeData,
): Promise<Employee> {
  const res = await fetch("/api/v1/employees", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return handleResponse<Employee>(res);
}
```

## State Management

### Local State with useState

```typescript
const [employees, setEmployees] = useState<Employee[]>([]);
const [loading, setLoading] = useState(false);
```

### Derived State

```typescript
const activeEmployees = employees.filter((e) => e.is_active);
```

### Async Data with useEffect

```typescript
useEffect(() => {
  async function load() {
    const data = await getEmployees();
    setEmployees(data);
  }
  load();
}, []);
```

### Custom Hooks

```typescript
// src/hooks/use-debounce.ts
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

## Styling with Tailwind

### Basic Classes

```tsx
<div className="flex items-center justify-between p-4 space-x-4">
  <h1 className="text-2xl font-bold">Title</h1>
  <Button variant="default" size="sm">
    Action
  </Button>
</div>
```

### Responsive

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* ... */}
</div>
```

### Dark Mode

```tsx
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
  {/* ... */}
</div>
```

### Using cn() Utility

```tsx
import { cn } from "@/lib/utils";

<div className={cn(
  "base-class",
  condition && "conditional-class",
  className
)}>
```

## Error Handling

### API Errors

```typescript
import { toast } from "sonner";

try {
  const data = await getEmployees();
} catch (error) {
  toast.error("Failed to load employees");
}
```

### Form Validation

```typescript
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const schema = z.object({
  email: z.string().email("Invalid email"),
  full_name: z.string().min(2, "Name too short"),
});

const form = useForm({
  resolver: zodResolver(schema),
});
```

## File Naming Conventions

| Type       | Convention                    | Example                  |
| ---------- | ----------------------------- | ------------------------ |
| Pages      | `page.tsx`                    | `employees/page.tsx`     |
| Layouts    | `layout.tsx`                  | `(dashboard)/layout.tsx` |
| Components | `kebab-case.tsx`              | `data-table.tsx`         |
| API files  | `kebab-case.ts`               | `employees.ts`           |
| Hooks      | `kebab-case.ts`               | `use-debounce.ts`        |
| Utils      | `kebab-case.ts`               | `utils.ts`               |
| Types      | `kebab-case.ts` or `types.ts` | `api/types.ts`           |

## Import Aliases

The project uses `@/` alias for `src/`:

```typescript
import { Button } from "@/components/ui/button";
import { getEmployees } from "@/lib/api/employees";
import { useDebounce } from "@/hooks/use-debounce";
```

## Testing

### Unit Tests with Vitest

```typescript
import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });
});
```

### Run Tests

```bash
pnpm test           # Run all tests
pnpm test:watch    # Watch mode
```

## Linting

```bash
pnpm lint          # Run ESLint
```

## Build

```bash
pnpm build         # Production build
pnpm dev           # Development server
```
