# 0006 Assistant Safety: Read-Tools Execute, Draft-Tools Only Propose

Date: 2026-05-30

## Status

Accepted

## Context

The HR AI Assistant (ADR-0003, ADR-0004) is human-in-the-loop: it may read data
and draft actions, but must never write to the database on its own. The existing
recruitment/employee services expose both safe reads (list/get candidates,
employees, review queue) and sensitive writes (accept/reject candidate, schedule
interview, send email, promote). The question is how to expose writes to the LLM
without ever letting the LLM actually perform one.

## Decision

Give the LLM exactly two kinds of tools, and no write-capable tool:

- **Read-Tool**: executes a real read via existing services, returns live data.
- **Draft-Tool**: does NOT execute. It returns a structured Draft Action
  (action type + parameters + human-readable preview). HR reviews it; on
  confirm, the frontend calls the existing real write endpoint directly — never
  the LLM.

The safety boundary is structural: the LLM is physically incapable of writing,
because no tool in its toolset performs a write. There is no "remember to set a
flag" convention to get wrong.

## Alternatives Considered

1. **Single write-tool guarded by a dry-run flag.** Rejected: safety depends on
   always setting the flag; one missed flag lets the LLM commit a real write.
2. **No actions at all (text-only chatbot).** Rejected: removes the
   automation/assistant value the project wants.

## Consequences

Positive:

- Human-in-the-loop is enforced by architecture, not discipline.
- Reuses existing write endpoints for the confirm step; no duplicate write paths.
- Aligns with the project's parse-first / explicit-boundary philosophy.

Tradeoffs:

- Two tool families to define and maintain.
- Each Draft Action type must be mapped to a real confirm endpoint in the UI.

## Follow-Up

- Define the initial Read-Tool and Draft-Tool sets.
- Define the Draft Action wire format and how the frontend maps it to a confirm
  endpoint.
