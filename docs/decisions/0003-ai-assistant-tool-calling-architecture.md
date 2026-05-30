# 0003 AI Assistant Uses Tool-Calling, Not RAG

Date: 2026-05-30

## Status

Accepted

## Context

The HR-facing AI Assistant needs to answer questions and draft actions using the
system's recruitment and onboarding data. Two common architectures exist:
tool-calling (the LLM invokes typed functions that query the database) and RAG
(documents are embedded into a vector store and retrieved by semantic search).

The backbone data (candidate pipeline status, counts, lookups by id, onboarding
progress) is overwhelmingly **structured**. Quantitative questions ("how many
candidates are awaiting interview?") demand exact answers from live data, which
RAG cannot reliably produce. The system already exposes an OpenAI-compatible LLM
endpoint and has service/repository layers the assistant can reuse.

## Decision

Build the AI Assistant on **tool-calling**:

- The LLM is given a set of read-only tools that wrap existing services
  (e.g. count candidates by status, get candidate, list pending interviews, get
  onboarding progress).
- "Draft" actions (e.g. compose an email) are tools that return content for HR
  to confirm — the assistant never writes to the database itself.
- RAG is not used now. Semantic search over CV content may be added later as a
  single additional tool if needed (the hybrid option).

## Alternatives Considered

1. **RAG.** Rejected for now: adds a vector store and embedding pipeline, and is
   weak at the quantitative/status questions that dominate HR usage.
2. **Hybrid (tool-calling + RAG for CV content search).** Deferred: introduce a
   semantic-search tool only when "find candidates by CV skill" is actually
   needed.

## Consequences

Positive:

- Answers come from live, exact database state.
- Reuses existing services; tools are thin wrappers.
- Tool-calling is the natural mechanism for human-in-the-loop drafting.

Tradeoffs:

- Free-text search over CV/document content is not supported until a semantic
  tool is added.
- Each new assistant capability requires defining a new tool.

## Follow-Up

- Decide where the assistant lives: a new `assistant` module vs extending an
  existing one.
- Define the initial tool set and how write-confirmation (human-in-the-loop) is
  represented in the API/UI.
