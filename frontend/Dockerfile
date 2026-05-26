FROM node:22-slim

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# Copy dependency files
COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/.npmrc* ./

# Install dependencies (--ignore-scripts is safe for this project)
RUN pnpm install --ignore-scripts

# Copy application code
COPY frontend/src/ ./src/
COPY frontend/public/ ./public/
COPY frontend/next.config.js ./
COPY frontend/next-env.d.ts ./
COPY frontend/tsconfig.json ./
COPY frontend/postcss.config.js ./
COPY frontend/tailwind.config.ts ./
COPY frontend/components.json ./
COPY frontend/.eslintrc.json ./
COPY frontend/pnpm-workspace.yaml ./

EXPOSE 3000

ENV HOSTNAME="0.0.0.0"
ENV INTERNAL_API_URL="http://backend:8000"

CMD ["pnpm", "dev"]
