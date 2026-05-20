# Kiro Powers Setup Guide

## Presets: backend, frontend

## Essential Powers (install these first)

### 1. Supabase
- URL: https://kiro.dev/powers/supabase
- Description: Backend-as-a-service with Postgres, auth, and real-time subscriptions
- How to install: Open Kiro IDE > Powers panel > Search "Supabase" > Click Install

### 2. Figma
- URL: https://kiro.dev/powers/figma
- Description: Design-to-code integration with Figma files
- How to install: Open Kiro IDE > Powers panel > Search "Figma" > Click Install

## Recommended Powers

### 3. Neon
- URL: https://kiro.dev/powers/neon
- Description: Serverless Postgres with branching and autoscaling
- How to install: Open Kiro IDE > Powers panel > Search "Neon" > Click Install

### 4. Postman
- URL: https://kiro.dev/powers/postman
- Description: API testing and collection management
- How to install: Open Kiro IDE > Powers panel > Search "Postman" > Click Install

### 5. Context7
- URL: https://kiro.dev/powers/context7
- Description: Up-to-date documentation lookup for libraries and frameworks
- How to install: Open Kiro IDE > Powers panel > Search "Context7" > Click Install

### 6. Netlify
- URL: https://kiro.dev/powers/netlify
- Description: Deploy React, Next.js, and modern web apps to global CDN
- How to install: Open Kiro IDE > Powers panel > Search "Netlify" > Click Install

## MCP Servers (auto-configured)

The following MCP servers have been configured in `.mcp.json`:

- **filesystem** (enabled)
- **git** (enabled)
- **fetch** (enabled)
- **postgres** (disabled, requires credentials)
- **docker** (disabled, requires credentials)
- **playwright** (enabled)

To enable disabled servers, set the required environment variables
and remove the `_disabled_` prefix from the server key in `.mcp.json`.
