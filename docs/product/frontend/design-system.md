# Design System

## Overview

Vroom HR uses a custom design system built on **Tailwind CSS** with **CSS variables** for theming. The system supports **dark mode** and follows **accessibility best practices**.

## Color Palette

### Primary Colors

| Token                | Light Mode         | Dark Mode          | Usage                     |
| -------------------- | ------------------ | ------------------ | ------------------------- |
| `primary`            | `hsl(168 65% 28%)` | `hsl(168 55% 45%)` | Main actions, CTAs, links |
| `primary-foreground` | `hsl(0 0% 98%)`    | `hsl(210 20% 8%)`  | Text on primary           |

**Usage:**

```tsx
<Button>Action</Button> {/* Uses primary by default */}
<a className="text-primary">Link</a>
```

### Accent Colors

| Token               | Light Mode        | Dark Mode         | Usage              |
| ------------------- | ----------------- | ----------------- | ------------------ |
| `accent`            | `hsl(35 90% 52%)` | `hsl(35 85% 55%)` | Highlights, badges |
| `accent-foreground` | `hsl(30 80% 10%)` | `hsl(30 80% 10%)` | Text on accent     |

### Neutral Colors

| Token              | Light Mode         | Dark Mode          | Usage                 |
| ------------------ | ------------------ | ------------------ | --------------------- |
| `background`       | `hsl(0 0% 99%)`    | `hsl(210 20% 8%)`  | Page background       |
| `foreground`       | `hsl(200 20% 12%)` | `hsl(180 5% 92%)`  | Main text             |
| `muted`            | `hsl(180 8% 95%)`  | `hsl(210 15% 16%)` | Secondary backgrounds |
| `muted-foreground` | `hsl(200 10% 45%)` | `hsl(200 8% 55%)`  | Secondary text        |
| `border`           | `hsl(180 10% 90%)` | `hsl(210 12% 20%)` | Borders, dividers     |
| `input`            | `hsl(180 10% 90%)` | `hsl(210 12% 20%)` | Input backgrounds     |

### Semantic Colors

| Token         | Light Mode         | Dark Mode          | Usage                  |
| ------------- | ------------------ | ------------------ | ---------------------- |
| `destructive` | `hsl(0 72% 51%)`   | `hsl(0 62% 50%)`   | Errors, delete actions |
| `secondary`   | `hsl(180 10% 94%)` | `hsl(210 15% 16%)` | Secondary actions      |

### Component-Specific Colors

| Token                            | Usage                         |
| -------------------------------- | ----------------------------- |
| `card` / `card-foreground`       | Card components               |
| `popover` / `popover-foreground` | Dropdowns, popovers           |
| `sidebar` / `sidebar-*`          | Dashboard sidebar             |
| `chart-1` through `chart-5`      | Charts and data visualization |

## Typography

### Font Families

| Variable         | Font                  | Weights            | Usage            |
| ---------------- | --------------------- | ------------------ | ---------------- |
| `--font-heading` | **Plus Jakarta Sans** | 500, 600, 700, 800 | Headings (h1-h6) |
| `--font-body`    | **DM Sans**           | 400, 500, 600      | Body text, UI    |

### Usage in Components

```tsx
// Using Tailwind
<h1 className="font-heading font-bold text-3xl">Heading</h1>
<p className="font-body text-base">Body text</p>
```

### Font Configuration

**File:** `src/app/layout.tsx`

```typescript
const heading = Plus_Jakarta_Sans({
  subsets: ["latin", "latin-ext"],
  variable: "--font-heading",
  weight: ["500", "600", "700", "800"],
});

const body = DM_Sans({
  subsets: ["latin", "latin-ext"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});
```

### Scale

| Class       | Size            | Line Height | Usage                  |
| ----------- | --------------- | ----------- | ---------------------- |
| `text-xs`   | 0.75rem (12px)  | 1rem        | Small labels, captions |
| `text-sm`   | 0.875rem (14px) | 1.25rem     | Secondary text, inputs |
| `text-base` | 1rem (16px)     | 1.5rem      | Body text              |
| `text-lg`   | 1.125rem (18px) | 1.75rem     | Lead text              |
| `text-xl`   | 1.25rem (20px)  | 1.75rem     | Section titles         |
| `text-2xl`  | 1.5rem (24px)   | 2rem        | Page titles            |
| `text-3xl`  | 1.875rem (30px) | 2.25rem     | Hero titles            |

## Spacing

### Spacing Scale

| Token         | Value          | Usage            |
| ------------- | -------------- | ---------------- |
| `p-1` / `m-1` | 0.25rem (4px)  | Tight spacing    |
| `p-2` / `m-2` | 0.5rem (8px)   | Compact elements |
| `p-3` / `m-3` | 0.75rem (12px) | Related elements |
| `p-4` / `m-4` | 1rem (16px)    | Default padding  |
| `p-6` / `m-6` | 1.5rem (24px)  | Section spacing  |
| `p-8` / `m-8` | 2rem (32px)    | Large gaps       |

### Common Patterns

```tsx
// Card padding
<Card className="p-6">

// Form field spacing
<div className="space-y-4">
  <Input />
  <Input />
</div>

// Section spacing
<section className="space-y-6">
  <h2>Title</h2>
  <Content />
</section>
```

## Border Radius

| Token          | Value           | Usage             |
| -------------- | --------------- | ----------------- |
| `rounded-sm`   | 0.375rem (6px)  | Small elements    |
| `rounded-md`   | 0.5rem (8px)    | Buttons, inputs   |
| `rounded-lg`   | 0.625rem (10px) | Cards             |
| `rounded-xl`   | 1rem (16px)     | Large containers  |
| `rounded-full` | 9999px          | Circular elements |

### Usage

```tsx
<Button className="rounded-md">Button</Button>
<Card className="rounded-lg">Card</Card>
<Avatar className="rounded-full">JD</Avatar>
```

## Shadows

| Token       | Value                               | Usage            |
| ----------- | ----------------------------------- | ---------------- |
| `shadow-sm` | `0 1px 2px rgb(0 0 0 / 0.05)`       | Subtle elevation |
| `shadow-md` | `0 4px 6px -1px rgb(0 0 0 / 0.1)`   | Cards, dropdowns |
| `shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.1)` | Modals, popovers |

### Usage

```tsx
<Card className="shadow-md">Elevated card</Card>
<DialogContent className="shadow-lg">Modal</DialogContent>
```

## Animations

### Built-in Animations

| Name                    | Effect                    | Duration |
| ----------------------- | ------------------------- | -------- |
| `animate-fade-in`       | Fade in + slight slide up | 200ms    |
| `animate-slide-up`      | Slide up from below       | 200ms    |
| `animate-slide-in-left` | Slide in from left        | 200ms    |
| `animate-scale-in`      | Scale up from 96%         | 150ms    |

### Usage

```tsx
import { cn } from "@/lib/utils";

<div className="animate-fade-in">
  Content fades in
</div>

<div className="animate-slide-up">
  Content slides up
</div>
```

### Stagger Animation

```tsx
<div className="stagger-children space-y-4">
  <div className="animate-slide-up">Item 1</div>
  <div className="animate-slide-up">Item 2</div>
  <div className="animate-slide-up">Item 3</div>
</div>
```

### Reduced Motion

The system automatically respects `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Responsive Design

### Breakpoints

| Breakpoint | Min Width | Usage         |
| ---------- | --------- | ------------- |
| `sm`       | 640px     | Small tablets |
| `md`       | 768px     | Tablets       |
| `lg`       | 1024px    | Laptops       |
| `xl`       | 1280px    | Desktops      |
| `2xl`      | 1536px    | Large screens |

### Common Patterns

```tsx
// Mobile-first: default is mobile, add breakpoints for larger
<div className="flex flex-col md:flex-row">
  {/* Stack on mobile, row on tablet+ */}
</div>

// Hide on mobile, show on desktop
<div className="hidden md:block">

// Show on mobile, hide on desktop
<div className="md:hidden">
```

## Dark Mode

### How It Works

- Toggle via `ThemeProvider` (next-themes)
- Uses CSS class `.dark` on `<html>` element
- All colors defined in CSS variables adapt automatically

### Usage

```tsx
// Using semantic color tokens (recommended)
<div className="bg-background text-foreground">
  Adapts to dark mode automatically
</div>

// Explicit dark mode
<div className="dark:bg-slate-900 dark:text-white">
  Always dark in dark mode
</div>
```

### Implementing Dark Mode

```tsx
// src/components/providers.tsx
"use client";

import { ThemeProvider } from "next-themes";

export function Providers({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}

// src/components/theme-toggle.tsx
("use client");

import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      Toggle
    </button>
  );
}
```

## Accessibility

### Focus States

All interactive elements have visible focus states:

```tsx
// Button focus (built into shadcn/ui)
<Button className="focus-visible:ring-2 focus-visible:ring-offset-2">
  Action
</Button>

// Input focus
<Input className="focus-visible:ring-2 focus-visible:ring-ring" />
```

### Screen Reader Support

```tsx
// Hidden label
<Label htmlFor="email" className="sr-only">Email</Label>

// ARIA attributes
<Button aria-label="Close dialog">
  <X />
</Button>

// Live regions for dynamic content
<div aria-live="polite" className="sr-only">
  {message}
</div>
```

### Color Contrast

All semantic colors meet WCAG AA standards:

- Primary on background: ✓
- Foreground on background: ✓
- Muted text on background: ✓

## Layout Patterns

### Page Layout (Dashboard)

```tsx
// app/(dashboard)/layout.tsx
<div className="flex min-h-screen">
  <Sidebar className="w-64" />
  <main className="flex-1 p-6">{children}</main>
</div>
```

### Card Grid

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  <Card>Content</Card>
  <Card>Content</Card>
</div>
```

### Form Layout

```tsx
<form className="space-y-4 max-w-md">
  <div className="space-y-2">
    <Label htmlFor="field">Label</Label>
    <Input id="field" />
  </div>
  <Button type="submit">Submit</Button>
</form>
```

### Table Layout

```tsx
<div className="rounded-md border">
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Column</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      <TableRow>
        <TableCell>Data</TableCell>
      </TableRow>
    </TableBody>
  </Table>
</div>
```

## Component Guidelines

### Button Priority

1. **Primary** — Main action (default variant)
2. **Secondary** — Alternative actions
3. **Ghost** — Tertiary actions, navigation
4. **Destructive** — Delete, cancel actions

```tsx
<Button variant="default">Primary Action</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Tertiary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
```

### Card Usage

```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Main content</CardContent>
  <CardFooter>Actions</CardFooter>
</Card>
```

### Input States

```tsx
// Default
<Input />

// With label
<div className="space-y-2">
  <Label>Email</Label>
  <Input type="email" placeholder="name@company.com" />
</div>

// Error state
<div className="space-y-2">
  <Label>Email</Label>
  <Input className="border-destructive" />
  <p className="text-sm text-destructive">Invalid email</p>
</div>

// Disabled
<Input disabled />
```

### Loading States

```tsx
// Button loading
<Button disabled>
  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
  Loading...
</Button>

// Skeleton
<Skeleton className="h-4 w-full" />
<Skeleton className="h-4 w-3/4" />

// Spinner only
<div className="flex items-center justify-center">
  <Loader2 className="h-8 w-8 animate-spin" />
</div>
```

## Best Practices

### 1. Use semantic colors

```tsx
// ✅ Good - adapts to dark mode
<div className="bg-background text-foreground">

// ❌ Bad - hardcoded colors
<div className="bg-white text-gray-900">
```

### 2. Use semantic text colors

```tsx
// ✅ Good
<p className="text-muted-foreground">Secondary text</p>

// ❌ Bad
<p className="text-gray-500">Secondary text</p>
```

### 3. Maintain consistent spacing

```tsx
// ✅ Good - consistent spacing scale
<div className="space-y-4">

// ❌ Bad - arbitrary values
<div className="space-y-5">
```

### 4. Use proper heading hierarchy

```tsx
// ✅ Good
<h1 className="text-2xl font-heading font-bold">Page Title</h1>
<h2 className="text-xl font-heading font-semibold">Section</h2>
<h3 className="text-lg font-heading font-medium">Subsection</h3>

// ❌ Bad - skipping levels
<h3>Page Title</h3>
```

### 5. Add proper focus states

```tsx
// ✅ Good - explicit focus styles
<Button className="focus-visible:ring-2 focus-visible:ring-ring">
  Action
</Button>

// For custom components
<button className="focus-visible:outline-none focus-visible:ring-2">
  Action
</button>
```

### 6. Use animations sparingly

```tsx
// ✅ Good - subtle, purposeful animations
<div className="animate-fade-in">

// ❌ Bad - excessive animations
<div className="animate-bounce animate-pulse animate-spin">
```

### 7. Test in both themes

Always verify your components look good in both light and dark mode:

```tsx
// Test these patterns:
<div className="bg-card text-card-foreground">
<div className="bg-muted text-muted-foreground">
<div className="border-input">
```
