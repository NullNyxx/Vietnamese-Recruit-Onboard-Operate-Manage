# Frontend Documentation

Vroom HR Frontend - Next.js 14 Application for HR Management.

## Overview

| Property        | Value                   |
| --------------- | ----------------------- |
| Framework       | Next.js 14 (App Router) |
| Language        | TypeScript 5.6+         |
| Package Manager | pnpm                    |
| UI Library      | shadcn/ui + Radix UI    |
| Styling         | Tailwind CSS            |
| State           | React hooks + Context   |
| Testing         | Vitest + fast-check     |
| Linting         | ESLint                  |

## Quick Commands

```bash
# Development
pnpm dev

# Build production
pnpm build

# Run tests
pnpm test

# Lint
pnpm lint
```

## Documentation Index

| Document                                  | Description                           |
| ----------------------------------------- | ------------------------------------- |
| [Architecture](./architecture.md)         | Folder structure, module organization |
| [Routing](./routing.md)                   | Route structure, URL patterns         |
| [Components](./components.md)             | UI components, shadcn/ui usage        |
| [API Client](./api-client.md)             | API patterns, error handling          |
| [State Management](./state-management.md) | State approach, hooks                 |

## Tech Stack Details

### Dependencies

**Core:**

- `next@14.2.15` - React framework with App Router
- `react@18.3.1` - UI library
- `react-dom@18.3.1` - React DOM renderer

**UI:**

- `shadcn@4.7.0` - Component collection
- `@radix-ui/*` - Headless UI primitives
- `lucide-react@0.447.0` - Icons
- `tailwindcss@3.4.13` - CSS framework
- `class-variance-authority` - Component variants
- `tailwind-merge` - Tailwind class merging
- `clsx` - Conditional classes

**Forms & Validation:**

- `react-hook-form@7.76.0` - Form management
- `@hookform/resolvers@5.2.2` - Zod integration
- `zod@4.4.3` - Schema validation

**Date Handling:**

- `date-fns@4.2.1` - Date utilities
- `react-day-picker@10.0.1` - Date picker

**Feedback:**

- `sonner@2.0.7` - Toast notifications

**Testing:**

- `vitest@4.1.6` - Test runner
- `fast-check@4.8.0` - Property-based testing

## Project Structure

```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── (dashboard)/       # Admin dashboard routes
│   ├── (employee)/        # Employee self-service routes
│   ├── login/             # Login page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/                # shadcn/ui components
│   ├── admin/             # Admin-specific components
│   └── ...
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities
│   ├── api/               # API clients
│   └── utils/             # Helper functions
└── middleware.ts          # Route protection
```

## Key Conventions

1. **Client Components**: Use `"use client"` directive for interactive components
2. **API Calls**: Use functions from `src/lib/api/`
3. **UI Components**: Use shadcn/ui from `@/components/ui/`
4. **Icons**: Use lucide-react
5. **Forms**: Use react-hook-form + zod
6. **Notifications**: Use sonner toast functions
7. **Routing**: Use Next.js App Router (NOT pages directory)
8. **TypeScript**: Strict mode enabled

## Development Workflow

1. Create component in appropriate folder under `src/components/`
2. Use shadcn/ui for base components: `npx shadcn@latest add <component>`
3. Create API function in `src/lib/api/<module>.ts`
4. Use server components by default, add `"use client"` only when needed
5. Test with `pnpm test`

## Related Documentation

- [Tech Stack](../tech-stack.md) - Full tech stack details
- [API Documentation](../api-documentation.md) - Backend API reference
- [Rate Limiting](../rate-limiting.md) - API rate limits
