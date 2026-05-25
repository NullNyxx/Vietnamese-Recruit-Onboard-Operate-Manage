# Accessibility (WCAG)

## Overview

Vroom HR follows **WCAG 2.1 AA** guidelines to ensure the application is usable by everyone, including people with disabilities.

## WCAG Principles

| Principle          | Description                                           |
| ------------------ | ----------------------------------------------------- |
| **Perceivable**    | Information must be presentable to users              |
| **Operable**       | User interface must be operable                       |
| **Understandable** | UI must be understandable                             |
| **Robust**         | Content must be robust enough for various user agents |

## Color Accessibility

### Contrast Ratios

All text meets WCAG AA contrast requirements:

| Level | Normal Text | Large Text |
| ----- | ----------- | ---------- |
| AA    | 4.5:1       | 3:1        |
| AAA   | 7:1         | 4.5:1      |

### Semantic Colors Used

The design system uses semantic color tokens that meet contrast requirements:

```tsx
// ✅ Good - Semantic colors (meets contrast)
<p className="text-foreground">Normal text</p>
<p className="text-muted-foreground">Secondary text</p>

// ❌ Bad - Hardcoded colors (may fail contrast)
<p className="text-gray-400">Secondary text</p>
```

### Don't Rely on Color Alone

```tsx
// ❌ Bad - Color-only status
<span className="text-green-500">Active</span>

// ✅ Good - Color + text/icon
<span className="text-green-600">
  <CheckCircle className="inline w-4 h-4 mr-1" />
  Active
</span>

// ✅ Good - Color + pattern
<span className="bg-green-100 text-green-800 rounded px-2 py-1">
  Active
</span>
```

## Keyboard Navigation

### Focus Indicators

All interactive elements must have visible focus states:

```tsx
// ✅ Good - Visible focus (shadcn/ui default)
<Button>Action</Button>

// ✅ Good - Explicit focus styles
<button className="focus-visible:ring-2 focus-visible:ring-offset-2">
  Action
</button>

// ❌ Bad - No visible focus
<button className="focus:outline-none">
  Action
</button>
```

### Tab Order

Ensure logical tab order:

```tsx
// ✅ Good - Logical order
<form>
  <Label htmlFor="first">First Name</Label>
  <Input id="first" />

  <Label htmlFor="last">Last Name</Label>
  <Input id="last" />

  <Button>Submit</Button>
</form>
```

### Skip Links

Add skip navigation for keyboard users:

```tsx
// app/layout.tsx
export default function Layout({ children }) {
  return (
    <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-background">
      Skip to main content
    </a>
    <main id="main-content">
      {children}
    </main>
  );
}
```

### Keyboard Shortcuts

```tsx
// Command bar (Ctrl+K)
<CommandBar keyboardShortcut="k" />

// Ensure shortcuts have accessible alternatives
<button
  onClick={handleDelete}
  aria-label="Delete employee"
  // Don't rely solely on keyboard shortcuts
>
  <Trash2 />
</button>
```

## Screen Reader Support

### ARIA Labels

```tsx
// ✅ Good - Descriptive labels
<Button aria-label="Create new employee">
  <Plus />
</Button>

<Input
  aria-label="Search employees"
  placeholder="Search..."
/>

// ✅ Good - Hidden labels for icon-only buttons
<IconButton aria-label="Close dialog">
  <X />
</IconButton>
```

### ARIA Descriptions

```tsx
// For additional context
<Input
  aria-describedby="email-hint"
  id="email"
/>
<p id="email-hint" className="text-sm text-muted-foreground">
  We'll never share your email.
</p>
```

### Live Regions

```tsx
// Announce dynamic content changes
<div aria-live="polite" className="sr-only">
  {message}
</div>

// For errors
<form aria-invalid="true">
  <Input aria-invalid="true" aria-describedby="name-error" />
  <span id="name-error" className="text-destructive text-sm" role="alert">
    Name is required
  </span>
</form>
```

### Semantic HTML

```tsx
// ✅ Good - Semantic elements
<header>
  <nav>
    <ul>
      <li><a href="/">Home</a></li>
    </ul>
  </nav>
</header>

<main>
  <article>
    <h1>Title</h1>
    <p>Content</p>
  </article>
</main>

<footer>
  <p>Copyright</p>
</footer>

// ❌ Bad - Non-semantic
<div>
  <div>
    <div>Home</div>
  </div>
</div>
```

## Forms

### Label Association

```tsx
// ✅ Good - Proper label association
<Label htmlFor="email">Email</Label>
<Input id="email" type="email" />

// ✅ Good - Wrapper pattern
<Label>
  <Input />
  Email
</Label>

// ❌ Bad - No label
<Input placeholder="Enter email" />
```

### Error Handling

```tsx
// ✅ Good - Clear error messages
<form>
  <div className="space-y-2">
    <Label htmlFor="email">Email</Label>
    <Input id="email" aria-invalid="true" aria-describedby="email-error" />
    <span id="email-error" className="text-sm text-destructive" role="alert">
      Please enter a valid email address
    </span>
  </div>
</form>
```

### Required Fields

```tsx
// ✅ Good - Clear required indication
<Label htmlFor="name">
  Name <span className="text-destructive">*</span>
</Label>

// ✅ Good - ARIA required
<Input aria-required="true" />
```

### Form Instructions

```tsx
// ✅ Good - Clear instructions
<fieldset>
  <legend className="text-sm font-medium mb-2">
    How would you like to be contacted?
  </legend>
  <RadioGroup>
    <div className="flex items-center space-x-2">
      <RadioGroupItem value="email" id="email" />
      <Label htmlFor="email">Email</Label>
    </div>
  </RadioGroup>
</fieldset>
```

## Images & Media

### Alt Text

```tsx
import Image from "next/image";

// ✅ Good - Descriptive alt text
<Image
  src="/employee-photo.jpg"
  alt="John Doe, Software Engineer"
/>

// ✅ Good - Empty alt for decorative images
<Image src="/decoration.svg" alt="" />

// ❌ Bad - Missing or unhelpful alt
<Image src="/photo.jpg" alt="photo" />
```

### Video & Audio

```tsx
// ✅ Good - Captions and transcripts
<video controls aria-label="Employee training video">
  <track kind="captions" src="/captions.vtt" />
  Your browser doesn't support video.
</video>
```

## Focus Management

### Modal Focus

```tsx
import { Dialog, DialogContent } from "@/components/ui/dialog";

function Modal({ open, onClose }) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        {/* Focus automatically trapped in Dialog */}
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
        </DialogHeader>
        <p>Are you sure?</p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button>Confirm</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Focus Restoration

```tsx
function DetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();

  // After saving, focus returns to trigger element
  useEffect(() => {
    const trigger = document.activeElement;
    // After navigation, focus management kicks in
    return () => {
      (trigger as HTMLElement)?.focus();
    };
  }, []);

  return <div>Detail content</div>;
}
```

### List Navigation

```tsx
// ✅ Good - Arrow key navigation for lists
import { Command } from "cmdk";

<Command>
  <CommandInput placeholder="Search..." />
  <CommandList>
    <CommandGroup>
      <CommandItem>Option 1</CommandItem>
      <CommandItem>Option 2</CommandItem>
    </CommandGroup>
  </CommandList>
</Command>;
```

## Typography & Layout

### Text Scaling

```tsx
// ✅ Good - Supports browser zoom
<div className="max-w-prose">
  <p>Content scales with browser text size</p>
</div>

// ❌ Bad - Fixed pixel sizes that break zoom
<p style={{ fontSize: "16px" }}>Content</p>
```

### Touch Targets

Minimum touch target size: 44x44 pixels:

```tsx
// ✅ Good - Adequate touch target
<Button className="h-11 px-4">
  Action
</Button>

// ✅ Good - Icon button
<IconButton className="w-11 h-11">
  <Icon />
</IconButton>

// ❌ Bad - Too small
<button className="h-6 w-6">X</button>
```

### Spacing

```tsx
// ✅ Good - Sufficient spacing between elements
<div className="space-y-4">
  <Input />
  <Input />
  <Button />
</div>

// ✅ Good - Focus visible spacing
<Input className="focus-visible:ring-2 focus-visible:ring-offset-2" />
```

## Color Blindness

Design doesn't rely on color alone:

```tsx
// ✅ Good - Multiple indicators
<span className="status-active">
  <CheckCircle className="w-4 h-4 text-green-600" />
  <span>Active</span>
</span>

// ✅ Good - Pattern + color
<div className="bg-green-100 border-l-4 border-green-600">
  Approved
</div>

// ❌ Bad - Color only
<span className="text-green-600">Active</span>
```

## Motor Disabilities

### No Time Limits

```tsx
// ✅ Good - No time limits on forms
<form>{/* User can take as long as needed */}</form>

// If there is a timeout, warn user
// ❌ Bad - Auto-logout without warning
```

### Single Switch Access

Ensure all functionality works with single input:

```tsx
// ✅ Good - Works with keyboard only
<Button>Save</Button>
<Input />
<Select />

// ❌ Bad - Requires mouse-specific actions
<div onMouseOver={handleHover}>Content</div>
```

## Cognitive Accessibility

### Clear Navigation

```tsx
// ✅ Good - Consistent, predictable navigation
<nav>
  <Link href="/employees">Employees</Link>
  <Link href="/attendance">Attendance</Link>
</nav>
```

### Error Recovery

```tsx
// ✅ Good - Clear error messages with recovery steps
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Error saving employee</AlertTitle>
  <AlertDescription>
    Please check the following:
    <ul className="list-disc pl-4 mt-2">
      <li>Email must be unique</li>
      <li>Department must be selected</li>
    </ul>
  </AlertDescription>
</Alert>
```

### Progress Indicators

```tsx
// ✅ Good - Clear loading states
{
  isLoading && (
    <div role="status" aria-live="polite">
      <Spinner /> Loading employees...
    </div>
  );
}
```

## Testing Accessibility

### Automated Testing

```bash
# ESLint jsx-a11y plugin
pnpm lint

# Axe Core
npx @axe-core/cli http://localhost:3000
```

### Manual Testing Checklist

- [ ] Tab through all interactive elements
- [ ] Verify focus indicators visible
- [ ] Test with screen reader (NVDA, VoiceOver)
- [ ] Check color contrast
- [ ] Verify all images have alt text
- [ ] Test keyboard navigation
- [ ] Check form error messages
- [ ] Test at 200% zoom

### Browser Extensions

| Tool                    | Description             |
| ----------------------- | ----------------------- |
| axe DevTools            | Automated a11y testing  |
| WAVE                    | Visual a11y checker     |
| Color Contrast Analyzer | Check contrast ratios   |
| NVDA                    | Screen reader (Windows) |
| VoiceOver               | Screen reader (Mac)     |

## Common Patterns

### Data Table Accessibility

```tsx
<Table>
  <TableCaption>
    Employee list showing name, department, and status
  </TableCaption>
  <TableHeader>
    <TableRow>
      <TableHead scope="col">Name</TableHead>
      <TableHead scope="col">Department</TableHead>
      <TableHead scope="col">Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {employees.map((emp) => (
      <TableRow key={emp.id}>
        <TableCell>{emp.name}</TableCell>
        <TableCell>{emp.department}</TableCell>
        <TableCell>{emp.status}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### Dialog/Modal Accessibility

```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>This action cannot be undone.</DialogDescription>
    </DialogHeader>
    {/* Content */}
  </DialogContent>
</Dialog>
```

### Dropdown Accessibility

```tsx
<Select value={value} onValueChange={setValue}>
  <SelectTrigger aria-label="Select department">
    <SelectValue placeholder="Select department" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="engineering">Engineering</SelectItem>
    <SelectItem value="design">Design</SelectItem>
  </SelectContent>
</Select>
```

### Tabs Accessibility

```tsx
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="details">Details</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">...</TabsContent>
  <TabsContent value="details">...</TabsContent>
</Tabs>
```

## Quick Reference

### Must Have

| Requirement      | Implementation                 |
| ---------------- | ------------------------------ |
| Focus indicators | `focus-visible:ring-*`         |
| Form labels      | `<Label htmlFor="...">`        |
| Alt text         | `alt="description"`            |
| Error messages   | `role="alert"`                 |
| Semantic HTML    | `<main>`, `<nav>`, `<article>` |

### Should Have

| Requirement       | Implementation             |
| ----------------- | -------------------------- |
| Skip link         | `<a href="#main">Skip</a>` |
| ARIA descriptions | `aria-describedby`         |
| Required fields   | `aria-required`            |
| Touch targets     | Minimum 44x44px            |

### Nice to Have

| Feature                     | Implementation           |
| --------------------------- | ------------------------ |
| Reduced motion              | `prefers-reduced-motion` |
| High contrast               | CSS custom properties    |
| Screen reader announcements | `aria-live`              |

## Commands

```bash
# Run accessibility audit
npx axe http://localhost:3000

# Test with screen reader
# On Mac: Cmd + F5 (VoiceOver)
# On Windows: Insert + N (NVDA)

# Check color contrast
# Use browser dev tools or Color Contrast Analyzer
```

## Related Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [Axe Core](https://www.deque.com/axe/)
