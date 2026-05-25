# CI/CD Pipeline

## Overview

This document covers the CI/CD workflows for Vroom HR frontend, covering GitHub Actions, testing, linting, and deployment.

## Current Structure

```
.github/
├── CODEOWNERS
└── workflows/           # GitHub Actions (to be added)
```

## GitHub Actions Workflows

### 1. Main CI Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run ESLint
        run: pnpm lint

      - name: TypeScript check
        run: pnpm tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run tests
        run: pnpm test

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: false
```

### 2. Build Workflow

Create `.github/workflows/build.yml`:

```yaml
name: Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
    types: [opened, synchronize]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build
        env:
          INTERNAL_API_URL: ${{ secrets.INTERNAL_API_URL }}

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: next-build
          path: .next
          retention-days: 7
```

### 3. Deploy Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build
        env:
          INTERNAL_API_URL: ${{ secrets.INTERNAL_API_URL }}
          NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}

      # Deploy to Vercel
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: "--prod"

      # Or deploy to Docker
      - name: Build and push Docker image
        if: false # Enable if using container registry
        run: |
          docker build -t vroom-hr-frontend:${{ github.sha }} .
          docker push registry.example.com/vroom-hr-frontend:${{ github.sha }}
```

### 4. Staging Deploy

Create `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy Staging

on:
  push:
    branches: [develop]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm build
        env:
          INTERNAL_API_URL: ${{ secrets.STAGING_API_URL }}

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID_STAGING }}
          vercel-args: "--prebuilt"
```

## Environment Configuration

### Environment Variables

| Variable              | Description                | Example                   |
| --------------------- | -------------------------- | ------------------------- |
| `INTERNAL_API_URL`    | Backend API URL (internal) | `http://backend:8000`     |
| `NEXT_PUBLIC_API_URL` | Backend API URL (public)   | `https://api.vroomhr.com` |
| `NEXT_PUBLIC_APP_URL` | Frontend URL               | `https://vroomhr.com`     |

### GitHub Secrets

Configure in **Settings → Secrets and variables → Actions**:

| Secret                      | Description            |
| --------------------------- | ---------------------- |
| `VERCEL_TOKEN`              | Vercel API token       |
| `VERCEL_ORG_ID`             | Vercel organization ID |
| `VERCEL_PROJECT_ID`         | Production project ID  |
| `VERCEL_PROJECT_ID_STAGING` | Staging project ID     |
| `INTERNAL_API_URL`          | Production API URL     |
| `NEXT_PUBLIC_API_URL`       | Production API URL     |
| `STAGING_API_URL`           | Staging API URL        |

## Deployment Options

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
pnpm add -g vercel

# Link project
vercel link

# Deploy
vercel --prod
```

**Auto-deploy:** Connect GitHub repository in Vercel dashboard.

### Option 2: Docker

**Dockerfile:**

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable pnpm && pnpm build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

**Update `next.config.js` for standalone output:**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // ... other config
};

module.exports = nextConfig;
```

**Build and run:**

```bash
docker build -t vroom-hr-frontend .
docker run -p 3000:3000 vroom-hr-frontend
```

### Option 3: Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - INTERNAL_API_URL=http://backend:8000
      - NEXT_PUBLIC_API_URL=https://api.vroomhr.com
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/vroomhr
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: vroomhr
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Branch Strategy

```
main ─────────────────────────────── production
  │
  └── develop ─────────────────────── staging
       │
       └── feature/xyz ────────────── preview PR
```

### Branch Rules

| Branch      | Environment | Auto-deploy     |
| ----------- | ----------- | --------------- |
| `main`      | Production  | ✅ Yes          |
| `develop`   | Staging     | ✅ Yes          |
| `feature/*` | Preview     | ❌ No (PR only) |
| `fix/*`     | Preview     | ❌ No (PR only) |

## Pull Request Checks

All PRs must pass:

- ✅ ESLint (no errors)
- ✅ TypeScript (no errors)
- ✅ Tests (all passing)
- ✅ Build (successful)

## Versioning

### Automatic Versioning

```yaml
# In package.json
{ "name": "vroom-hr-frontend", "version": "0.1.0" }
```

### Release Process

1. Create release branch from main
2. Update version in `package.json`
3. Create GitHub release with changelog
4. Tag: `v0.1.0`

## Monitoring

### Vercel Analytics

Enable in Vercel dashboard:

```javascript
// next.config.js
module.exports = {
  analytics: {
    vercel: {
      enabled: true,
    },
  },
};
```

### Error Tracking

```javascript
// Sentry example (optional)
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
});
```

## Quick Commands

```bash
# Local development
pnpm dev

# Production build
pnpm build

# Start production
pnpm start

# Lint
pnpm lint

# Type check
pnpm tsc --noEmit

# Test
pnpm test
```

## Troubleshooting

### Build Failures

1. Check Node version matches `package.json` (currently 20)
2. Clear `.next` cache: `rm -rf .next`
3. Clear node_modules: `rm -rf node_modules && pnpm install`

### Deployment Issues

| Issue            | Solution                        |
| ---------------- | ------------------------------- |
| 500 Error        | Check environment variables     |
| 404 on routes    | Check `next.config.js` rewrites |
| Slow performance | Enable Vercel Analytics         |

### CI Failures

| Issue         | Solution                |
| ------------- | ----------------------- |
| ESLint errors | Run `pnpm lint --fix`   |
| Type errors   | Run `pnpm tsc --noEmit` |
| Test failures | Run `pnpm test` locally |
