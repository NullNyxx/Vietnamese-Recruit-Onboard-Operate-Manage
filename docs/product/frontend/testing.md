# Testing

## Overview

Vroom HR uses **Vitest** as the testing framework with **fast-check** for property-based testing. Tests are co-located with source files using the `.test.ts` extension.

## Quick Commands

```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Run specific test file
pnpm test src/lib/utils.test.ts
```

## Test Configuration

**File:** `vitest.config.ts`

```typescript
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true, // Auto-import test globals (describe, it, expect)
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

## Test Structure

### File Organization

```
src/
├── lib/
│   ├── utils.ts
│   ├── utils.test.ts       # Unit tests
│   └── recruitment-utils.ts
│       └── recruitment-utils.test.ts
├── hooks/
│   ├── use-sidebar.ts
│   └── use-sidebar.test.ts
├── components/
│   └── gmail/
│       ├── utils.ts
│       └── utils.test.ts
└── middleware.ts
    └── middleware.test.ts
```

### Test File Patterns

| Pattern      | Usage             |
| ------------ | ----------------- |
| `*.test.ts`  | Unit tests        |
| `*.spec.ts`  | Integration tests |
| `__tests__/` | Test directories  |

## Test Examples

### Unit Tests

**File:** `src/lib/utils.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { formatDateVN, getInitials, validateDateRange } from "./utils";

describe("formatDateVN", () => {
  it("formats date in Vietnamese format", () => {
    const date = new Date("2025-05-25");
    expect(formatDateVN(date)).toBe("25/05/2025");
  });

  it("handles invalid date", () => {
    expect(formatDateVN(null)).toBe("");
  });
});

describe("getInitials", () => {
  it("generates initials from name", () => {
    expect(getInitials("Nguyen Van A")).toBe("NVA");
  });

  it("handles single name", () => {
    expect(getInitials("Trang")).toBe("T");
  });

  it("handles empty string", () => {
    expect(getInitials("")).toBe("");
  });
});
```

### Hook Tests

**File:** `src/hooks/use-sidebar.test.ts`

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSidebar } from "./use-sidebar";

// Mock window
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: mockLocalStorage });

describe("useSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with default open state", () => {
    mockLocalStorage.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebar());
    expect(result.current.isOpen).toBe(true);
  });

  it("toggles sidebar state", () => {
    const { result } = renderHook(() => useSidebar());

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isOpen).toBe(false);
  });
});
```

### Middleware Tests

**File:** `src/middleware.test.ts`

```typescript
import { describe, it, expect, vi } from "vitest";
import { middleware } from "./middleware";
import { NextRequest } from "next/server";

vi.mock("next/server", () => ({
  NextRequest: vi.fn(),
}));

describe("middleware", () => {
  it("redirects unauthenticated users to login", async () => {
    const request = new NextRequest("http://localhost:3000/");

    const result = await middleware(request);

    expect(result.status).toBe(307); // Redirect
    expect(result.headers.get("location")).toBe("/login");
  });
});
```

## Testing Utilities

### Testing Library for React

```bash
pnpm add -D @testing-library/react @testing-library/dom
```

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

describe("Component", () => {
  it("renders correctly", () => {
    render(<MyComponent />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("handles click", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);

    fireEvent.click(screen.getByRole("button"));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("shows loading state", async () => {
    render(<UserProfile userId="1" />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
  });
});
```

### Mocking

```typescript
import { vi, describe, it, expect } from "vitest";

// Mock functions
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("API", () => {
  it("fetches employees", async () => {
    mockFetch.mockResolvedValue({
      json: () => Promise.resolve([{ id: "1", name: "John" }]),
    });

    const employees = await getEmployees();

    expect(employees).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/employees");
  });
});

// Mock modules
vi.mock("@/lib/api/employees", () => ({
  getEmployees: vi.fn().mockResolvedValue([]),
}));

// Mock timers
describe("Debounce", () => {
  it("debounces function calls", async () => {
    vi.useFakeTimers();

    const fn = vi.fn();
    const debounced = debounce(fn, 300);

    debounced();
    debounced();
    debounced();

    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(300);

    expect(fn).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });
});
```

## Property-Based Testing with fast-check

```bash
pnpm add -D fast-check
```

```typescript
import { test, describe } from "vitest";
import { fc } from "fast-check";

describe("property-based tests", () => {
  test("sorting is idempotent", () => {
    fc.assert(
      fc.property(fc.array(fc.integer()), (arr) => {
        const sorted = [...arr].sort((a, b) => a - b);
        const reSorted = [...sorted].sort((a, b) => a - b);
        return sorted.every((v, i) => v === reSorted[i]);
      }),
    );
  });

  test("email validation", () => {
    fc.assert(
      fc.property(fc.emailAddress(), (email) => {
        return isValidEmail(email);
      }),
    );
  });
});
```

## Coverage

### Running Coverage

```bash
pnpm test:coverage
```

### Coverage Report

| Type    | Command                                          |
| ------- | ------------------------------------------------ |
| Console | `pnpm test:coverage`                             |
| HTML    | `pnpm test:coverage -- --coverage.reporter=html` |

### Coverage Thresholds

Add to `vitest.config.ts`:

```typescript
export default defineConfig({
  test: {
    coverage: {
      reporter: ["text", "json", "html"],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
```

### Coverage Report Structure

```
coverage/
├── lcov-report/
│   ├── index.html
│   └── src/
│       ├── lib/
│       └── hooks/
├── coverage-final.json
└── lcov.info
```

## Best Practices

### 1. Test Behavior, Not Implementation

```typescript
// ✅ Good - Test behavior
it("shows error when login fails", async () => {
  mockFetch.mockRejectedValue(new Error("Invalid credentials"));

  render(<LoginForm />);
  await fillAndSubmit();

  expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
});

// ❌ Bad - Test implementation details
it("calls login API", async () => {
  render(<LoginForm />);
  // ...
  expect(login).toHaveBeenCalled();
});
```

### 2. Use Descriptive Test Names

```typescript
// ✅ Good
it("should display validation error when email is invalid");

// ❌ Bad
it("test email");
```

### 3. Arrange-Act-Assert

```typescript
it("calculates total correctly", () => {
  // Arrange
  const cart = [{ price: 100 }, { price: 50 }];

  // Act
  const total = calculateTotal(cart);

  // Assert
  expect(total).toBe(150);
});
```

### 4. Keep Tests Independent

```typescript
// ✅ Good - Each test is independent
describe("formatDate", () => {
  it("formats valid date", () => {
    /* ... */
  });
  it("handles null", () => {
    /* ... */
  });
});

// ❌ Bad - Tests depend on each other
describe("formatDate", () => {
  it("first test", () => {
    // Sets global state
  });
  it("second test", () => {
    // Depends on first test
  });
});
```

### 5. Test Edge Cases

```typescript
describe("calculateAge", () => {
  it("calculates age correctly", () => {
    const birthDate = new Date("2000-01-01");
    expect(calculateAge(birthDate, new Date("2025-05-25"))).toBe(25);
  });

  it("handles birthday not yet passed", () => {
    const birthDate = new Date("2000-12-31");
    expect(calculateAge(birthDate, new Date("2025-05-25"))).toBe(24);
  });

  it("handles same day birthday", () => {
    const birthDate = new Date("2000-05-25");
    expect(calculateAge(birthDate, new Date("2025-05-25"))).toBe(25);
  });
});
```

### 6. Use beforeEach for Setup

```typescript
describe("EmployeeList", () => {
  let mockEmployees;

  beforeEach(() => {
    mockEmployees = [
      { id: "1", name: "John", department: "Engineering" },
      { id: "2", name: "Jane", department: "Design" },
    ];
  });

  it("renders employee list", () => {
    render(<EmployeeList employees={mockEmployees} />);
    expect(screen.getByText("John")).toBeInTheDocument();
  });

  it("filters by department", () => {
    render(<EmployeeList employees={mockEmployees} filter="Engineering" />);
    expect(screen.getByText("John")).toBeInTheDocument();
    expect(screen.queryByText("Jane")).not.toBeInTheDocument();
  });
});
```

### 7. Mock External Dependencies

```typescript
import { vi } from "vitest";

// Mock API calls
vi.mock("@/lib/api/employees", () => ({
  getEmployees: vi.fn(),
  createEmployee: vi.fn(),
}));

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: mockLocalStorage });

// Mock router
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));
```

### 8. Test Error Handling

```typescript
it("shows error toast on API failure", async () => {
  mockFetch.mockRejectedValue(new Error("Network error"));

  render(<EmployeeList />);
  await fireEvent.click(screen.getByText("Refresh"));

  expect(toast.error).toHaveBeenCalledWith("Failed to load employees");
});

it("handles empty state", () => {
  render(<EmployeeList employees={[]} />);
  expect(screen.getByText("No employees found")).toBeInTheDocument();
});
```

## CI Integration

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"
      - run: pnpm install
      - run: pnpm test
      - run: pnpm test:coverage
        with:
          files: ./coverage/lcov.info
```

## Commands Reference

| Command                                    | Description                |
| ------------------------------------------ | -------------------------- |
| `pnpm test`                                | Run all tests once         |
| `pnpm test:watch`                          | Run tests in watch mode    |
| `pnpm test:coverage`                       | Run with coverage report   |
| `pnpm test src/lib/utils.test.ts`          | Run specific file          |
| `pnpm test --grep "pattern"`               | Run tests matching pattern |
| `pnpm test --exclude "**/node_modules/**"` | Exclude patterns           |

## Related

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [fast-check](https://fast-check.dev/)
