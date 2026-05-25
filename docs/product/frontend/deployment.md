# Deployment

## Overview

This document covers deployment options and configurations for Vroom HR frontend, including local development, Docker, and cloud platforms.

## Deployment Options

| Platform       | Complexity | Best For                            |
| -------------- | ---------- | ----------------------------------- |
| Vercel         | Low        | Serverless, auto-deploy             |
| Docker         | Medium     | Self-hosted, custom infra           |
| Docker Compose | Low        | Local development, small production |
| Custom Server  | High       | Full control, enterprise            |

## Local Development

### Prerequisites

```bash
# Install pnpm
npm install -g pnpm

# Install dependencies
cd frontend
pnpm install
```

### Development Server

```bash
pnpm dev
```

Server runs at `http://localhost:3000`

### Environment Variables

Create `.env.local`:

```bash
# .env.local
INTERNAL_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Docker Local Development

```bash
# Using docker-compose
docker compose up frontend

# Or build and run manually
docker build -t vroom-hr-frontend .
docker run -p 3000:3000 \
  -e INTERNAL_API_URL=http://host.docker.internal:8000 \
  vroom-hr-frontend
```

## Docker Deployment

### Dockerfile

**File:** `frontend/Dockerfile`

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
ARG INTERNAL_API_URL
ENV INTERNAL_API_URL=$INTERNAL_API_URL
RUN corepack enable pnpm && pnpm build

# Stage 3: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### Enable Standalone Output

**File:** `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/gmail/:path*",
        destination: `${apiUrl}/api/gmail/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

### Build Docker Image

```bash
# Build image
docker build \
  --build-arg INTERNAL_API_URL=http://backend:8000 \
  -t vroom-hr-frontend:latest \
  ./frontend

# Run container
docker run -d \
  -p 3000:3000 \
  -e INTERNAL_API_URL=http://backend:8000 \
  --name vroom-hr-frontend \
  vroom-hr-frontend:latest
```

### Docker Compose

**File:** `docker-compose.yml` (root)

```yaml
version: "3.8"

services:
  frontend:
    build:
      context: ./frontend
      args:
        INTERNAL_API_URL: http://backend:8000
    ports:
      - "3000:3000"
    environment:
      - INTERNAL_API_URL=http://backend:8000
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - vroom-network

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/vroomhr
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    networks:
      - vroom-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: vroomhr
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - vroom-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - vroom-network

volumes:
  postgres_data:
  redis_data:

networks:
  vroom-network:
    driver: bridge
```

### Run with Docker Compose

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f frontend

# Stop services
docker compose down
```

## Vercel Deployment

### Quick Deploy

```bash
# Install Vercel CLI
pnpm add -g vercel

# Deploy
vercel
```

### Configuration

**File:** `vercel.json` (optional)

```json
{
  "buildCommand": "pnpm build",
  "installCommand": "pnpm install",
  "framework": "nextjs"
}
```

### Environment Variables

Configure in Vercel Dashboard → Settings → Environment Variables:

| Variable              | Value                             | Environments        |
| --------------------- | --------------------------------- | ------------------- |
| `INTERNAL_API_URL`    | `https://api.vroomhr.com`         | Production, Preview |
| `NEXT_PUBLIC_API_URL` | `https://api.vroomhr.com`         | Production, Preview |
| `INTERNAL_API_URL`    | `https://staging-api.vroomhr.com` | Development         |

### Git Integration

1. Connect GitHub repository in Vercel
2. Configure project settings:
   - Framework: Next.js
   - Build Command: `pnpm build`
   - Output Directory: `.next`

3. Deploy automatically on push to `main` (production) and `develop` (preview)

### Vercel Analytics

Enabled by default on Vercel deployments.

### Vercel Edge Functions

For API routes, Vercel automatically deploys as Edge Functions.

## Environment Configuration

### Environment Variables

| Variable              | Required | Description     | Example                   |
| --------------------- | -------- | --------------- | ------------------------- |
| `INTERNAL_API_URL`    | Yes      | Backend API URL | `http://backend:8000`     |
| `NEXT_PUBLIC_API_URL` | Yes      | Public API URL  | `https://api.vroomhr.com` |
| `NEXT_PUBLIC_APP_URL` | No       | Frontend URL    | `https://vroomhr.com`     |

### Environment-Specific Config

```javascript
// next.config.js
const nextConfig = {
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

## Production Checklist

### Pre-Deployment

- [ ] Run `pnpm build` successfully
- [ ] Run `pnpm lint` - no errors
- [ ] Run `pnpm tsc --noEmit` - no errors
- [ ] All tests passing (`pnpm test`)
- [ ] Environment variables configured
- [ ] API endpoints accessible

### Security

- [ ] No secrets in code
- [ ] Environment variables use secrets manager
- [ ] HTTPS enabled
- [ ] Security headers configured

### Performance

- [ ] Images optimized (`next/image`)
- [ ] Fonts optimized (`next/font`)
- [ ] Bundle size reasonable (< 500KB initial JS)

## Security Headers

Add to `next.config.js`:

```javascript
const nextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

## Monitoring

### Vercel

- Dashboard → Analytics
- Real-time monitoring
- Performance metrics

### Error Tracking

Optional: Add Sentry

```bash
pnpm add @sentry/nextjs
```

```javascript
// sentry.client.config.js
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
});
```

## Troubleshooting

### Common Issues

| Issue             | Cause                  | Solution                               |
| ----------------- | ---------------------- | -------------------------------------- |
| 500 Error         | API URL misconfigured  | Check `INTERNAL_API_URL`               |
| 404 on API routes | Rewrite not configured | Check `next.config.js` rewrites        |
| Slow load         | Large bundle           | Analyze with `ANALYZE=true pnpm build` |
| CORS errors       | API not accessible     | Check backend is running               |

### Debug Build

```bash
# Build with bundle analysis
ANALYZE=true pnpm build

# Check output in .next/analyze
```

### Health Check

```bash
# Local
curl http://localhost:3000

# Production
curl https://vroomhr.com
```

## Commands Reference

### Development

```bash
pnpm dev              # Start dev server
pnpm build            # Production build
pnpm start            # Start production server
```

### Docker

```bash
docker build -t vroom-hr-frontend .    # Build image
docker run -p 3000:3000 vroom-hr-frontend  # Run container
docker compose up -d                   # Run with compose
```

### Deployment

```bash
vercel                    # Deploy to preview
vercel --prod             # Deploy to production
vercel --env-file .env.production  # With env file
```

## Related

- [CI/CD](./ci-cd.md) - Pipeline workflows
- [Testing](./testing.md) - Test configuration
- [Performance](./performance.md) - Optimization tips
