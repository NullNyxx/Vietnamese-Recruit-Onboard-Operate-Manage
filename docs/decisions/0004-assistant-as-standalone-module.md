# 0004 AI Assistant as a Standalone Orchestration Module

Date: 2026-05-30

## Status

Accepted

## Context

The HR AI Assistant (tool-calling, per ADR-0003) needs data from multiple
business modules — recruitment (candidates, CVs, interviews) and employee
(onboarding progress). It must decide where to live in the backend module
layout.

## Decision

Create a standalone `assistant/` module following the standard structure
(`api/application/domain/infrastructure/container.py`). It owns conversation
handling, the tool-calling loop, and the LLM client. Its tools call into the
services of other modules (recruitment, employee/onboarding); it holds no
business logic of its own.

Dependency direction is one-way: `assistant/` depends on other modules'
services, but no module depends on `assistant/`.

## Alternatives Considered

1. **Put it inside `recruitment/`.** Rejected: the assistant also reads
   onboarding data, which would force recruitment to depend on employee, and it
   bloats the recruitment module with an unrelated concern.
2. **A shared `ai/` module merging existing AI automation and the assistant.**
   Deferred: would require moving the working CV/email automation out of
   recruitment — unnecessary risk now.

## Consequences

Positive:

- Clean, one-way dependencies; business modules stay unaware of the assistant.
- A clearly demarcated "AI module" that is easy to point to at defense.

Tradeoffs:

- One more module to wire.
- Requires discipline to keep business logic out of the assistant (it
  orchestrates and calls services, it does not reimplement them).
