FROM node:22-slim

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# Copy dependency files
COPY package.json pnpm-lock.yaml* .npmrc* ./

# Install dependencies (--ignore-scripts is safe for this project)
RUN pnpm install --ignore-scripts

# Copy application code
COPY . .

EXPOSE 3000

ENV HOSTNAME="0.0.0.0"
ENV INTERNAL_API_URL="http://backend:8000"

CMD ["pnpm", "dev"]
