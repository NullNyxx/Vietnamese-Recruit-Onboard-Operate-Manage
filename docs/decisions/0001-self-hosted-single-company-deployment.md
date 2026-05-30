# 0001 Self-Hosted, Single-Company Deployment Model

Date: 2026-05-30

## Status

Accepted

## Context

Vroom HR is an open-source HR platform intended to be self-hosted: each company
downloads the source and runs its own instance on its own infrastructure. The
isolation boundary between companies is therefore the deployment itself — one
running instance serves exactly one company.

This conflicts with how the Policy Engine module was already built. The Policy
Engine implements data-level multi-tenancy: a `tenant_id` column on every table
(`policy_rules`, `policy_versions`, `policy_audit_logs`), per-tenant versioning,
and tenant-scoped queries — a design that assumes many companies share one
database (a SaaS model). In a self-hosted single-company deployment that
machinery is dead weight: `tenant_id` only ever holds one value, and the
isolation logic guards against a situation that cannot occur.

## Decision

Adopt the self-hosted, single-company deployment model. One deployment = one
company.

- `Organization` becomes a singleton record holding company-level settings
  (name, tax code, timezone, holidays), not a data-isolation root.
- `tenant_id` in the Policy Engine is treated as a frozen implementation detail
  (a constant), not a live multi-tenancy concept. It may be removed later, but
  removal is not required for correctness.
- The system targets two roles: HR (admin) and Employee.

## Alternatives Considered

1. **SaaS multi-tenant (keep `tenant_id` as a live key).** One hosted instance
   serves many companies with data-level isolation. Rejected: incompatible with
   "open-source, self-hosted per company" — a self-hosted instance would carry
   multi-tenant machinery that can never serve a second tenant, and giving each
   company the full multi-tenant codebase to host their single company is
   contradictory.

## Consequences

Positive:

- The system collapses to the simple two-role vision (HR + Employee).
- No `tenant_id` data migration is needed; the column is frozen, not reworked.
- Easier to explain and demo: no "why isolate tenants when there is one company?"
  confusion.

Tradeoffs:

- The multi-tenancy work already built into the Policy Engine no longer serves
  the product purpose. It is retained as frozen code rather than showcased.
- Loses "multi-tenancy" as a technical talking point for the thesis defense.

## Follow-Up

- Decide whether to freeze `tenant_id` to a constant or remove it from the
  Policy Engine entirely (separate, lower-stakes decision).
- Re-evaluate the `policy-engine-integration` spec, which currently assumes a
  multi-company Organization model.
