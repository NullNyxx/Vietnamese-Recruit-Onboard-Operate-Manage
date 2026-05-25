# Frontend Components

## Overview

Vroom HR uses **shadcn/ui** as the primary component library, built on top of **Radix UI** primitives. All UI components are in `src/components/ui/`.

## Adding New Components

```bash
cd frontend
npx shadcn@latest add button
```

This adds:

- `src/components/ui/button.tsx` - Component code
- Updates `src/components/ui/` exports

## Available shadcn/ui Components

| Component       | File                  | Usage                         |
| --------------- | --------------------- | ----------------------------- |
| Button          | `button.tsx`          | Primary actions, submit forms |
| Card            | `card.tsx`            | Content containers            |
| Input           | `input.tsx`           | Text input fields             |
| Label           | `label.tsx`           | Form labels                   |
| Textarea        | `textarea.tsx`        | Multi-line text input         |
| Select          | `select.tsx`          | Dropdown selection            |
| Checkbox        | `checkbox.tsx`        | Boolean checkboxes            |
| Switch          | `switch.tsx`          | Toggle switches               |
| Dialog          | `dialog.tsx`          | Modal dialogs                 |
| Dropdown Menu   | `dropdown-menu.tsx`   | Context menus                 |
| Tabs            | `tabs.tsx`            | Tabbed content                |
| Table           | `table.tsx`           | Data tables                   |
| Avatar          | `avatar.tsx`          | User avatars                  |
| Badge           | `badge.tsx`           | Status badges                 |
| Alert           | `alert.tsx`           | Alert messages                |
| Toast/Sonner    | -                     | Notifications (via sonner)    |
| Tooltip         | `tooltip.tsx`         | Hover tooltips                |
| Separator       | `separator.tsx`       | Visual dividers               |
| Slider          | `slider.tsx`          | Range sliders                 |
| Collapsible     | `collapsible.tsx`     | Collapsible sections          |
| Navigation Menu | `navigation-menu.tsx` | Navigation                    |

## Custom Components

### Data Table

**File:** `src/components/data-table.tsx`

Reusable table with sorting, pagination, and column configuration.

```typescript
import { DataTable } from "@/components/data-table";
import { columns } from "./columns";

<DataTable columns={columns} data={employees} />
```

### Stat Card

**File:** `src/components/stat-card.tsx`

Display statistics with icon, value, label, and optional trend.

```typescript
import { StatCard } from "@/components/stat-card";
import { Users } from "lucide-react";

<StatCard
  title="Total Employees"
  value="150"
  icon={Users}
  trend={{ value: 5, positive: true }}
/>
```

### Breadcrumbs

**File:** `src/components/breadcrumbs.tsx`

Navigation breadcrumbs.

```typescript
import { Breadcrumbs } from "@/components/breadcrumbs";

<Breadcrumbs
  items={[
    { label: "Employees", href: "/employees" },
    { label: "John Doe" },
  ]}
/>
```

### Theme Toggle

**File:** `src/components/theme-toggle.tsx`

Dark/light mode switcher.

```typescript
import { ThemeToggle } from "@/components/theme-toggle";

<ThemeToggle />
```

### Command Bar

**File:** `src/components/command-bar.tsx`

Command palette (Ctrl+K) for quick navigation.

```typescript
import { CommandBar } from "@/components/command-bar";

// Opens with Ctrl+K
<CommandBar />
```

### Employee Form

**File:** `src/components/employee-form.tsx`

Create/edit employee form with validation.

```typescript
import { EmployeeForm } from "@/components/employee-form";

<EmployeeForm onSubmit={handleSubmit} defaultValues={employee} />
```

### Page Transition

**File:** `src/components/page-transition.tsx`

Animated page transitions.

```typescript
import { PageTransition } from "@/components/page-transition";

<PageTransition>
  <YourContent />
</PageTransition>
```

## Admin Components

### Audit Log Table

**File:** `src/components/admin/audit-log-table.tsx`

Display audit logs with filtering.

```typescript
import { AuditLogTable } from "@/components/admin/audit-log-table";

<AuditLogTable logs={auditLogs} />
```

### OAuth Config Form

**File:** `src/components/admin/oauth-config-form.tsx`

Configure OAuth providers.

```typescript
import { OAuthConfigForm } from "@/components/admin/oauth-config-form";

<OAuthConfigForm config={oauthConfig} onSave={handleSave} />
```

### User Role Select

**File:** `src/components/admin/user-role-select.tsx`

Select user role dropdown.

```typescript
import { UserRoleSelect } from "@/components/admin/user-role-select";

<UserRoleSelect value={role} onChange={setRole} />
```

### Whitelist Table

**File:** `src/components/admin/whitelist-table.tsx`

Manage email whitelist.

```typescript
import { WhitelistTable } from "@/components/admin/whitelist-table";

<WhitelistTable entries={whitelist} onDelete={handleDelete} />
```

## Using Components

### Basic Button

```typescript
import { Button } from "@/components/ui/button";

<Button variant="default">Click me</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
<Button variant="ghost">Link</Button>
<Button variant="secondary">Secondary</Button>
```

### Button Sizes

```typescript
<Button size="default">Default</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon">Icon only</Button>
```

### Card Layout

```typescript
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    Content goes here
  </CardContent>
  <CardFooter>
    Footer actions
  </CardFooter>
</Card>
```

### Form Input

```typescript
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

<Label htmlFor="email">Email</Label>
<Input id="email" type="email" placeholder="john@example.com" />
```

### Dialog/Modal

```typescript
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger>Open</DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Title</DialogTitle>
    </DialogHeader>
    <YourForm />
  </DialogContent>
</Dialog>
```

### Select Dropdown

```typescript
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="1">Option 1</SelectItem>
    <SelectItem value="2">Option 2</SelectItem>
  </SelectContent>
</Select>
```

### Table

```typescript
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Email</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {data.map((item) => (
      <TableRow key={item.id}>
        <TableCell>{item.name}</TableCell>
        <TableCell>{item.email}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### Tabs

```typescript
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="details">Details</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">...</TabsContent>
  <TabsContent value="details">...</TabsContent>
</Tabs>
```

### Badge/Status

```typescript
import { Badge } from "@/components/ui/badge";

<Badge variant="default">Pending</Badge>
<Badge variant="secondary">Active</Badge>
<Badge variant="destructive">Rejected</Badge>
<Badge variant="outline">Info</Badge>
```

### Toast Notifications

```typescript
import { toast } from "sonner";

// Success
toast.success("Employee created successfully");

// Error
toast.error("Failed to create employee");

// Info
toast.info("Processing your request...");

// Warning
toast.warning("Please complete all fields");

// With action
toast.success("Employee created", {
  action: { label: "View", onClick: () => router.push("/employees") },
});
```

### Icons (Lucide React)

```typescript
import {
  Users,
  Plus,
  Pencil,
  Trash2,
  Search,
  Filter,
  Download,
  Upload,
  Check,
  X,
} from "lucide-react";

<Button>
  <Plus className="mr-2 h-4 w-4" />
  Add Employee
</Button>
```

## Styling with Tailwind

### Common Patterns

```typescript
// Flexbox
<div className="flex items-center justify-between">
  <div className="flex-1">...</div>
</div>

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

// Spacing
<div className="p-4 m-4 space-y-2">

// Typography
<h1 className="text-2xl font-bold">Title</h1>
<p className="text-sm text-muted-foreground">Description</p>

// Responsive
<div className="hidden md:block">

// Dark mode
<div className="bg-white dark:bg-gray-900">
```

### Using cn() Utility

```typescript
import { cn } from "@/lib/utils";

<div className={cn(
  "base-class",
  isActive && "active-class",
  className // allow override
)}>
```

## Creating New Components

### 1. Create component file

```typescript
// src/components/ui/new-component.tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface NewComponentProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary";
}

export function NewComponent({
  className,
  variant = "default",
  ...props
}: NewComponentProps) {
  return (
    <div
      className={cn(
        "base-styles",
        variant === "secondary" && "secondary-styles",
        className
      )}
      {...props}
    />
  );
}
```

### 2. Export from index

```typescript
// src/components/ui/index.ts
export * from "./new-component";
```

## Component Variants with cva

```typescript
import { cva } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-red-500 text-white hover:bg-red-600",
        outline: "border border-input hover:bg-accent",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export { buttonVariants };
```

## Responsive Design

### Mobile-First

```typescript
// Mobile first (default), then add breakpoints
<div className="flex flex-col md:flex-row">

// Hidden on mobile, visible on desktop
<div className="hidden md:block">

// Visible on mobile, hidden on desktop
<div className="md:hidden">
```

### Breakpoints

| Breakpoint | Min Width |
| ---------- | --------- |
| sm         | 640px     |
| md         | 768px     |
| lg         | 1024px    |
| xl         | 1280px    |
| 2xl        | 1536px    |

## Accessibility

### ARIA Attributes

```typescript
<Button
  aria-label="Close dialog"
  aria-describedby="dialog-description"
>
  <X />
</Button>
```

### Keyboard Navigation

- Use native `<button>` for actions
- Use `<a>` for links
- Add `tabIndex` for custom focusable elements

### Focus States

```typescript
<Button className="focus-visible:ring-2 focus-visible:ring-offset-2">
  Action
</Button>
```
