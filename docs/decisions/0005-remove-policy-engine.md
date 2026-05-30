# 0005 Remove the Policy Engine and Its Specs

Date: 2026-05-30

## Status

Accepted

## Context

ADR-0001 (self-hosted, single-company) and ADR-0002 (recruit-to-onboard
backbone) left the Policy Engine outside the project's purpose. Its follow-ups
asked whether to keep it dormant or remove it. The team chose removal: the
multi-tenant rule engine serves no consumer in the recruit-to-onboard backbone,
exposed live API routes and a UI page that no longer fit the product, and its
presence was a direct contributor to the "loss of control" over the codebase.

Investigation confirmed the Policy Engine was self-contained: it was wired into
`main.py` and depended on `identity`, but no business module depended on it.
Removal therefore carried near-zero risk to the backbone.

## Decision

Delete the Policy Engine entirely:

- Backend module `backend/src/modules/policy/` and `backend/tests/modules/policy/`.
- Alembic migrations `028_create_policy_tables.py` and
  `029_seed_policy_templates.py` (they were the last two revisions; head reverts
  to `027`). The dev database was downgraded to `027` first to drop the tables.
- Frontend: `lib/api/policies.ts`, `app/(dashboard)/policies/`,
  `components/policies/`, and the `/policies` nav entry.
- Specs `.kiro/specs/company-policy-engine/` and
  `.kiro/specs/policy-engine-integration/`.
- Policy router/handler registrations in `main.py`.

## Alternatives Considered

1. **Freeze in place (disconnect routers, keep code).** Rejected: leaves unused
   code in the running system and does not fully restore control. (This was the
   option ADR-0001/0002 left open; the team overrode it in favor of removal.)

## Consequences

Positive:

- The running system contains only what serves the recruit-to-onboard backbone.
- Migration head is a clean `027`; new self-hosted installs never create policy
  tables.
- Backend lint passes; 965 tests pass (the 8 failures are pre-existing
  env-sensitive tests deselected in CI, unrelated to this change).

Tradeoffs:

- The tested multi-tenant rule engine work is gone from the tree (recoverable
  only via git history).

## Follow-Up

- None. Supersedes the "dormant vs remove" follow-ups in ADR-0001 and ADR-0002.
