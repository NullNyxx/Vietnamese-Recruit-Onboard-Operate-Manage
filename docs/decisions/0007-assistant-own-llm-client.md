# 0007 Assistant Has Its Own LLM Client (Not Recruitment's Adapter)

Date: 2026-05-30

## Status

Accepted

## Context

Recruitment already has an `LLMAdapter` (`recruitment/infrastructure/`) that
talks to the OpenAI-compatible endpoint for email intent classification and CV
parsing. The new `assistant/` module also needs to call the LLM. A reader might
assume the two should share one client.

They serve different jobs: the recruitment adapter runs fixed-prompt pipelines
returning intent/ParsedCV and does not do tool-calling; the assistant needs a
tool-calling loop (pass tool definitions, handle `tool_calls`, iterate).
Reusing the recruitment adapter would also force `assistant/` to import
`recruitment/infrastructure/`, breaking the one-way module boundary set in
ADR-0004 (the assistant calls other modules' services, not their internals).

## Decision

Give `assistant/` its own LLM client in `assistant/infrastructure/`, built for
tool-calling. The two clients share only configuration (endpoint URL, API key,
model name) via environment variables — not code.

## Alternatives Considered

1. **Reuse `recruitment.LLMAdapter`.** Rejected: it lacks tool-calling and
   reusing it creates a cross-module infrastructure dependency.
2. **Extract a shared `shared/llm/` module.** Deferred: would require moving
   working recruitment code for only two consumers; revisit if a third appears.

## Consequences

Positive:

- Clean module boundaries (ADR-0004 preserved).
- Each client stays focused on its own use case.

Tradeoffs:

- Two LLM clients exist. This is intentional — do not "deduplicate" them into a
  cross-module dependency without revisiting alternative 2.
- Minor duplication in `AsyncOpenAI` setup.
