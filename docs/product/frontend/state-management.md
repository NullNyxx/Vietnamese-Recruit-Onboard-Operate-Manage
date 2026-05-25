# State Management

## Overview

Vroom HR uses a simple, pragmatic approach to state management:

- **Local State**: `useState` for component-specific state
- **Derived State**: Computed from state in render
- **Server State**: Server components + `router.refresh()` for data mutations
- **Context**: For theme and global settings
- **Custom Hooks**: For reusable stateful logic

> **Note**: This project does NOT use Redux, Zustand, or Jotai. It relies on React's built-in primitives.

## Local State

### Basic useState

```typescript
import { useState } from "react";

function Component() {
  const [count, setCount] = useState(0);
  const [name, setName] = useState("");

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
      <input value={name} onChange={(e) => setName(e.target.value)} />
    </div>
  );
}
```

### State with Type

```typescript
interface Employee {
  id: string;
  name: string;
  email: string;
}

const [employees, setEmployees] = useState<Employee[]>([]);
const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
const [isLoading, setIsLoading] = useState(false);
```

### Functional Updates

```typescript
// When new state depends on previous state
setCount((prev) => prev + 1);

setEmployees((prev) => [...prev, newEmployee]);

setFormData((prev) => ({ ...prev, name: "New Name" }));
```

## Derived State

### Computed Values

```typescript
function EmployeeList({ employees }: { employees: Employee[] }) {
  // Derived state - no need for separate useState
  const activeEmployees = employees.filter((e) => e.is_active);
  const inactiveEmployees = employees.filter((e) => !e.is_active);
  const totalCount = employees.length;

  return (
    <div>
      <p>Total: {totalCount}</p>
      <p>Active: {activeEmployees.length}</p>
    </div>
  );
}
```

### Using useMemo

```typescript
import { useMemo } from "react";

function ExpensiveComponent({ items, filter }: Props) {
  // Only recalculate when items or filter changes
  const filteredItems = useMemo(() => {
    return items.filter((item) => item.name.includes(filter));
  }, [items, filter]);

  return <List items={filteredItems} />;
}
```

### Using useCallback

```typescript
import { useCallback } from "react";

function Component({ onDataLoaded }: Props) {
  const handleLoad = useCallback(async () => {
    const data = await fetchData();
    onDataLoaded(data);
  }, [onDataLoaded]);

  return <button onClick={handleLoad}>Load</button>;
}
```

## Server State

### Server Components (Default)

In Next.js App Router, components are server components by default:

```typescript
// app/employees/page.tsx (Server Component)
import { getEmployees } from "@/lib/api/employees";

export default async function EmployeesPage() {
  // This runs on the server
  const employees = await getEmployees();

  return <EmployeeList employees={employees} />;
}
```

### Refetching After Mutations

After creating/updating data, use `router.refresh()` to re-fetch server components:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

function CreateEmployeeForm() {
  const router = useRouter();

  async function handleSubmit(data: CreateEmployeeData) {
    try {
      await createEmployee(data);
      toast.success("Employee created");
      router.refresh(); // Re-fetch server components
      router.push("/employees");
    } catch (error) {
      toast.error("Failed to create employee");
    }
  }

  return <Form onSubmit={handleSubmit} />;
}
```

### Client-Side Fetching

When you need client-side fetching (user interactions, real-time):

```typescript
"use client";

import { useEffect, useState } from "react";
import { getEmployees } from "@/lib/api/employees";

function EmployeeSearch() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchEmployees() {
      setLoading(true);
      try {
        const data = await getEmployees();
        setEmployees(data);
      } finally {
        setLoading(false);
      }
    }

    // Debounce could be added here
    const timer = setTimeout(fetchEmployees, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      {loading ? <Skeleton /> : <List employees={employees} />}
    </div>
  );
}
```

## Context

### Theme Context

**File:** `src/components/providers.tsx`

```typescript
"use client";

import { ThemeProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

**Usage:**

```typescript
"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const { theme, setTheme } = useTheme();

  // Prevent hydration mismatch
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle Theme
    </button>
  );
}
```

### Creating Custom Context

```typescript
import { createContext, useContext, useState } from "react";

interface AppContextType {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <AppContext.Provider value={{ sidebarOpen, setSidebarOpen }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}
```

## Custom Hooks

### useDebounce

**File:** `src/hooks/use-debounce.ts`

```typescript
import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Usage
function SearchComponent() {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    // This only runs when user stops typing for 300ms
    search(debouncedQuery);
  }, [debouncedQuery]);

  return <input value={query} onChange={(e) => setQuery(e.target.value)} />;
}
```

### useSidebar

**File:** `src/hooks/use-sidebar.ts`

```typescript
import { useEffect, useState } from "react";

export function useSidebar() {
  const [isOpen, setIsOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check if mobile
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const toggle = () => setIsOpen((prev) => !prev);

  return { isOpen, setIsOpen, toggle, isMobile };
}
```

### useCurrentUser

**File:** `src/hooks/use-current-user.ts`

```typescript
import { useEffect, useState } from "react";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "employee";
}

export function useCurrentUser() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("/api/v1/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data);
        }
      } catch (error) {
        console.error("Failed to fetch user:", error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchUser();
  }, []);

  return { user, isLoading };
}
```

## Form State

### useState for Simple Forms

```typescript
function SimpleForm() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    console.log(formData);
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" value={formData.name} onChange={handleChange} />
      <input name="email" value={formData.email} onChange={handleChange} />
      <button type="submit">Submit</button>
    </form>
  );
}
```

### react-hook-form for Complex Forms

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  department_id: z.string().uuid("Invalid department"),
  position_id: z.string().uuid("Invalid position"),
  hire_date: z.string().date(),
});

type FormData = z.infer<typeof schema>;

function EmployeeForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    await createEmployee(data);
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <input {...register("full_name")} />
        {errors.full_name && <span>{errors.full_name.message}</span>}
      </div>

      <div>
        <input {...register("email")} />
        {errors.email && <span>{errors.email.message}</span>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create Employee"}
      </button>
    </form>
  );
}
```

## Managing Multiple Related State

### Grouping Related State

```typescript
// Instead of multiple useState
const [name, setName] = useState("");
const [email, setEmail] = useState("");
const [phone, setPhone] = useState("");

// Use object
const [formData, setFormData] = useState({
  name: "",
  email: "",
  phone: "",
});

function updateField(field: string, value: string) {
  setFormData((prev) => ({ ...prev, [field]: value }));
}
```

### State Machines (Simple)

For complex state transitions, use explicit states:

```typescript
type RequestStatus = "idle" | "loading" | "success" | "error";

function DataFetcher() {
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  async function fetch() {
    setStatus("loading");
    try {
      const result = await api.getData();
      setData(result);
      setStatus("success");
    } catch (e) {
      setError(e);
      setStatus("error");
    }
  }

  if (status === "loading") return <Spinner />;
  if (status === "error") return <Error error={error} />;
  if (status === "success") return <Data data={data} />;
  return <Button onClick={fetch}>Load Data</Button>;
}
```

## Optimistic Updates

### Update UI Immediately, Revert on Error

```typescript
function ApproveButton({ request, onApprove }) {
  const [pending, setPending] = useState(false);

  async function handleApprove() {
    const previousStatus = request.status;

    // Optimistic update
    request.status = "approved";

    setPending(true);
    try {
      await onApprove(request.id);
    } catch (error) {
      // Revert on error
      request.status = previousStatus;
      toast.error("Failed to approve");
    } finally {
      setPending(false);
    }
  }

  return (
    <Button onClick={handleApprove} disabled={pending}>
      {pending ? "Approving..." : "Approve"}
    </Button>
  );
}
```

## Best Practices

### 1. Keep state as local as possible

```typescript
// ❌ Bad - lifting state too high
function Parent() {
  const [count, setCount] = useState(0);
  return <Child count={count} onUpdate={setCount} />;
}

// ✅ Good - local state when possible
function Child() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

### 2. Use functional updates for dependent state

```typescript
// ❌ Bad
setCount(count + 1);

// ✅ Good
setCount((prev) => prev + 1);
```

### 3. Clean up effects

```typescript
useEffect(() => {
  const subscription = subscribe();
  return () => subscription.unsubscribe();
}, []);
```

### 4. Memoize expensive computations

```typescript
const filteredData = useMemo(() => data.filter((item) => item.active), [data]);
```

### 5. Use proper TypeScript types

```typescript
// ❌ Bad
const [data, setData] = useState(null);

// ✅ Good
const [data, setData] = useState<DataType | null>(null);
```

### 6. Prefer server components + router.refresh()

```typescript
// For data that changes infrequently or on navigation
// Use server component + router.refresh() after mutations

// Only use client-side fetching for:
// - Real-time data
// - User-triggered refreshes
// - Interactive filters/pagination
```

## When to Use What

| Scenario                   | Solution                              |
| -------------------------- | ------------------------------------- |
| Component-specific state   | `useState`                            |
| Computed from props        | Derived state (no useState)           |
| Expensive computation      | `useMemo`                             |
| Stable function reference  | `useCallback`                         |
| Theme, locale              | Context                               |
| Global app state           | Context (sparingly)                   |
| Server data                | Server component + `router.refresh()` |
| Real-time/interactive data | Client fetch with `useEffect`         |
| Reusable state logic       | Custom hook                           |
| Form state                 | `react-hook-form` + `zod`             |
