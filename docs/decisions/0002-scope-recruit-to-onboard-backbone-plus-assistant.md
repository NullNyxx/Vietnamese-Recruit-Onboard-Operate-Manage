# 0002 Scope to the Recruit-to-Onboard Backbone Plus AI Assistant

Date: 2026-05-30

## Status

Accepted

## Context

The `policy-engine-integration` spec defines 12 requirements (attendance,
leave, overtime, notifications, approvals, violations, background jobs,
self-service). For a graduation thesis with a fixed deadline, building all of it
risks an incoherent, half-finished system — the symptom the team was already
experiencing ("losing control" over a sprawling codebase).

Investigation of the existing code shows the team's real intended backbone — the
recruit-to-onboard flow that gives the project its name — is already largely
built in the recruitment module:

- Email intent classification (cv/partner/event/internal/other) — built.
- CV parsing (OCR → LLM → auto-created Candidate with confidence score) — built.
- Candidate pipeline state machine (new → reviewing → interview_scheduled →
  accepted/rejected/archived) — built.
- Schedule interview, send email to candidate — built.
- `accept` already emits a domain event "for downstream modules (onboarding)".
- An ARQ task queue already exists in recruitment.

The only missing link is **onboarding**: the "accepted" event has no consumer,
and there is no onboarding module. This flow does not touch the Policy Engine at
all (it has nothing to do with attendance/leave/overtime rules).

## Decision

Make the **recruit-to-onboard** flow the single backbone of the project:

Email → AI classify → CV parse → Candidate list → HR review →
schedule interview → accept → congratulations email → onboarding → Employee.

- Complete and connect what already exists; build only the missing onboarding
  link (consume the "accepted" event → onboard candidate → create Employee).
- Build the AI Assistant (read + draft, human-in-the-loop) on top of this flow.
- Freeze/shelve the Policy Engine and the entire `policy-engine-integration`
  spec — they are not part of this backbone.

## Alternatives Considered

1. **Leave management as the backbone.** Rejected: it depends on the frozen
   Policy Engine and is not what the team actually wants to demo.
2. **Full HR core (all 12 integration requirements).** Rejected: highest effort,
   the direct cause of the loss-of-control problem.

## Consequences

Positive:

- The backbone is mostly built already; remaining work is completion + wiring,
  not greenfield building. This directly restores the team's sense of control.
- One coherent, demoable story aligned with the project's name (Recruit-Onboard).
- The Policy Engine's lack of consumers stops being a problem — it is shelved,
  not integrated.

Tradeoffs:

- The Policy Engine and most of `policy-engine-integration` become dead/frozen
  code, not showcased work.
- Operate/Manage (attendance, leave, payroll) are out of scope for now.

## Follow-Up

- Define the onboarding boundary: when does a Candidate become an Employee, and
  what steps does onboarding consist of?
- Decide what to do with the frozen Policy Engine code (keep dormant vs remove).
