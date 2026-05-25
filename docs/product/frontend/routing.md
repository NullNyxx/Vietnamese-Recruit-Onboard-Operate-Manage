# Frontend Routing

## Route Overview

Vroom HR uses **Next.js 14 App Router** with route groups for separating admin and employee self-service (ESS) views.

## Route Groups

```
app/
├── (dashboard)/       # Admin routes - / prefix
│   └── layout.tsx     # Dashboard layout with sidebar
├── (employee)/        # ESS routes - /employee prefix
│   └── layout.tsx     # ESS layout
└── login/             # Auth routes
```

## All Routes

### Root & Dashboard

| URL      | File                       | Description              |
| -------- | -------------------------- | ------------------------ |
| `/`      | `app/(dashboard)/page.tsx` | Admin dashboard overview |
| `/login` | `app/login/page.tsx`       | Google OAuth login       |

### Admin - Employees

| URL                         | File                                                | Description                  |
| --------------------------- | --------------------------------------------------- | ---------------------------- |
| `/employees`                | `app/(dashboard)/employees/page.tsx`                | Employee list with DataTable |
| `/employees/new`            | `app/(dashboard)/employees/new/page.tsx`            | Create employee form         |
| `/employees/[id]`           | `app/(dashboard)/employees/[id]/page.tsx`           | Employee detail/edit         |
| `/employees/[id]/documents` | `app/(dashboard)/employees/[id]/documents/page.tsx` | Employee documents           |

### Admin - Attendance

| URL                   | File                                          | Description        |
| --------------------- | --------------------------------------------- | ------------------ |
| `/attendance`         | `app/(dashboard)/attendance/page.tsx`         | Attendance records |
| `/attendance/checkin` | `app/(dashboard)/attendance/checkin/page.tsx` | Manual check-in    |

### Admin - Leave

| URL               | File                                      | Description              |
| ----------------- | ----------------------------------------- | ------------------------ |
| `/leave`          | `app/(dashboard)/leave/page.tsx`          | Leave requests list      |
| `/leave/types`    | `app/(dashboard)/leave/types/page.tsx`    | Leave type configuration |
| `/leave/balances` | `app/(dashboard)/leave/balances/page.tsx` | Leave balance management |

### Admin - Payroll

| URL                 | File                                        | Description            |
| ------------------- | ------------------------------------------- | ---------------------- |
| `/payroll`          | `app/(dashboard)/payroll/page.tsx`          | Payroll overview       |
| `/payroll/periods`  | `app/(dashboard)/payroll/periods/page.tsx`  | Payroll period config  |
| `/payroll/payslips` | `app/(dashboard)/payroll/payslips/page.tsx` | Generate/view payslips |
| `/payroll/configs`  | `app/(dashboard)/payroll/configs/page.tsx`  | Salary configuration   |

### Admin - Recruitment

| URL                            | File                                                   | Description          |
| ------------------------------ | ------------------------------------------------------ | -------------------- |
| `/recruitment`                 | `app/(dashboard)/recruitment/page.tsx`                 | Recruitment overview |
| `/recruitment/candidates`      | `app/(dashboard)/recruitment/candidates/page.tsx`      | Candidate list       |
| `/recruitment/candidates/[id]` | `app/(dashboard)/recruitment/candidates/[id]/page.tsx` | Candidate detail     |
| `/recruitment/jobs`            | `app/(dashboard)/recruitment/jobs/page.tsx`            | Job postings         |

### Admin - Gmail

| URL      | File                             | Description          |
| -------- | -------------------------------- | -------------------- |
| `/gmail` | `app/(dashboard)/gmail/page.tsx` | Gmail integration UI |

### Admin - Settings

| URL                     | File                                            | Description           |
| ----------------------- | ----------------------------------------------- | --------------------- |
| `/settings`             | `app/(dashboard)/settings/page.tsx`             | Settings overview     |
| `/settings/departments` | `app/(dashboard)/settings/departments/page.tsx` | Department management |
| `/settings/positions`   | `app/(dashboard)/settings/positions/page.tsx`   | Position management   |
| `/settings/schedules`   | `app/(dashboard)/settings/schedules/page.tsx`   | Work schedule config  |
| `/settings/leave-types` | `app/(dashboard)/settings/leave-types/page.tsx` | Leave type config     |

### Admin - System

| URL                 | File                                        | Description         |
| ------------------- | ------------------------------------------- | ------------------- |
| `/admin/whitelist`  | `app/(dashboard)/admin/whitelist/page.tsx`  | Email whitelist     |
| `/admin/oauth`      | `app/(dashboard)/admin/oauth/page.tsx`      | OAuth configuration |
| `/admin/audit-logs` | `app/(dashboard)/admin/audit-logs/page.tsx` | Audit log viewer    |

### Employee Self-Service (ESS)

| URL                      | File                                            | Description          |
| ------------------------ | ----------------------------------------------- | -------------------- |
| `/employee/dashboard`    | `app/(employee)/employee/dashboard/page.tsx`    | ESS dashboard        |
| `/employee/attendance`   | `app/(employee)/employee/attendance/page.tsx`   | Check-in/out         |
| `/employee/leave`        | `app/(employee)/employee/leave/page.tsx`        | My leave requests    |
| `/employee/leave/new`    | `app/(employee)/employee/leave/new/page.tsx`    | New leave request    |
| `/employee/overtime`     | `app/(employee)/employee/overtime/page.tsx`     | My overtime requests |
| `/employee/overtime/new` | `app/(employee)/employee/overtime/new/page.tsx` | New overtime request |
| `/employee/schedule`     | `app/(employee)/employee/schedule/page.tsx`     | My work schedule     |
| `/employee/profile`      | `app/(employee)/employee/profile/page.tsx`      | My profile           |
| `/employee/documents`    | `app/(employee)/employee/documents/page.tsx`    | My documents         |

## Navigation Components

### Sidebar (Admin)

**File:** `src/components/app-sidebar.tsx`

Navigation items defined in `src/lib/navigation.ts`:

```typescript
export const navigation = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Employees",
    href: "/employees",
    icon: Users,
  },
  // ...
];
```

### ESS Sidebar

**File:** `src/components/employee-sidebar.tsx`

Navigation items defined in `src/lib/employee-navigation.ts`:

```typescript
export const employeeNavigation = [
  {
    title: "Dashboard",
    href: "/employee/dashboard",
    icon: LayoutDashboard,
  },
  // ...
];
```

## Route Protection

### Middleware

**File:** `src/middleware.ts`

The middleware protects routes based on authentication and role:

1. **Unauthenticated** → Redirect to `/login`
2. **Authenticated, no role** → Show access denied
3. **Admin role** → Access `/` routes
4. **Employee role** → Access `/employee/*` routes

```typescript
// Middleware logic (simplified)
if (!token) {
  return Response.redirect(new URL("/login", request.url));
}

const role = token.role;
if (req.nextUrl.pathname.startsWith("/employee") && role !== "employee") {
  return new Response("Forbidden", { status: 403 });
}
if (!req.nextUrl.pathname.startsWith("/employee") && role !== "admin") {
  return new Response("Forbidden", { status: 403 });
}
```

## Dynamic Routes

### Employee Detail

```typescript
// app/(dashboard)/employees/[id]/page.tsx
export default function EmployeeDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  // Fetch employee by id
}
```

### Candidate Detail

```typescript
// app/(dashboard)/recruitment/candidates/[id]/page.tsx
export default function CandidatePage({ params }: { params: { id: string } }) {
  const { id } = params;
  // Fetch candidate by id
}
```

## Query Parameters

### Common Patterns

| Parameter | Usage            | Example                          |
| --------- | ---------------- | -------------------------------- |
| `page`    | Pagination       | `/employees?page=2`              |
| `limit`   | Page size        | `/employees?limit=20`            |
| `search`  | Search query     | `/employees?search=john`         |
| `status`  | Filter by status | `/leave?status=pending`          |
| `month`   | Month filter     | `/employee/attendance?month=5`   |
| `year`    | Year filter      | `/employee/attendance?year=2025` |

## Programmatic Navigation

```typescript
import { useRouter } from "next/navigation";

const router = useRouter();

// Navigate to a route
router.push("/employees");

// Replace current route (no back)
router.replace("/employees");

// Refresh the current route
router.refresh();

// Go back
router.back();
```

## Link Component

```typescript
import Link from "next/link";

// Basic link
<Link href="/employees">Employees</Link>

// With query params
<Link href={`/employees?status=${status}`}>Filter</Link>

// Active link styling
<Link
  href="/employees"
  className={pathname === "/employees" ? "text-primary" : ""}
>
  Employees
</Link>
```

## Nested Routes

### Example: Employee Tabs

```
/employees/[id]/
├── page.tsx              # Overview tab
├── documents/
│   └── page.tsx          # Documents tab
└── edit/
    └── page.tsx          # Edit tab
```

## Error Handling

### 404 Page

Next.js automatically handles 404 for non-existent routes.

### Custom Error Boundaries

```typescript
// app/error.tsx
"use client";

export default function Error({ reset }) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  );
}
```

### Loading States

```typescript
// app/employees/loading.tsx
export default function Loading() {
  return <div>Loading employees...</div>;
}
```

## Redirects

### Server-Side Redirect

```typescript
// In a server component or route handler
import { redirect } from "next/navigation";

if (!isAuthenticated) {
  redirect("/login");
}
```

### Conditional Redirect

```typescript
// In a component
useEffect(() => {
  if (!user) {
    router.push("/login");
  }
}, [user]);
```

## API Routes vs Pages

| Purpose       | Use                            |
| ------------- | ------------------------------ |
| UI Pages      | Next.js App Router (`app/`)    |
| API Endpoints | Not used (Backend handles API) |

> **Note:** This project doesn't use Next.js API routes (`app/api/`). All API calls go to the FastAPI backend at `/api/v1/*`.
