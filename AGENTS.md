# Agent Operating Guide

This repository is in Harness v0. There is no product implementation yet.

The current job of agents is to preserve and grow the collaboration harness
before writing application code. Do not scaffold application source folders,
platform shells, package scripts, CI, or tests unless a later story explicitly
moves the project into implementation.

## Source Of Truth

Read in this order:

1. `README.md` for project status.
2. `harness-experimental/docs/HARNESS.md` for the human-agent operating model.
3. `harness-experimental/docs/FEATURE_INTAKE.md` before turning any prompt into work.
4. `harness-experimental/specs/` for spec collaboration workspace (project and feature specs).
5. `harness-experimental/docs/product/` for current product contracts.
6. `harness-experimental/docs/ARCHITECTURE.md` before proposing implementation shape.
7. `harness-experimental/docs/stories/` for story packets and backlog.
8. `harness-experimental/docs/TEST_MATRIX.md` for proof status.
9. `harness-experimental/docs/decisions/` for why important choices were made.

## Spec Workflow

Specs live in `harness-experimental/specs/` and follow a discussion-first workflow:

- `harness-experimental/specs/project/`: project-level spec. Human describes the project idea, agent
  asks questions and proposes, both iterate until agreement. Agent then writes
  the final spec and runs Feature Intake to decompose it.
- `harness-experimental/specs/features/`: feature-level specs. Same discussion workflow per feature.
  Agent does not implement until the spec status reaches `Agreed`.

Each directory contains a `README.md` with the template and detailed workflow.
After a spec is written and decomposed, product docs, story packets, and
decisions become the living contract that agents update as the system evolves.

## Task Loop

For every task:

1. Classify the request with `harness-experimental/docs/FEATURE_INTAKE.md`.
2. Identify whether the input is a new spec, spec slice, change request, new
   initiative, maintenance request, or harness improvement.
3. Locate the affected product docs and story files.
4. Check `harness-experimental/docs/TEST_MATRIX.md` for existing proof and gaps.
5. Work only inside the selected lane: tiny, normal, or high-risk.
6. Before finishing, ask:
   - Did product truth change?
   - Did validation expectations change?
   - Did architecture rules change?
   - Did we discover a repeated failure pattern?
   - Did the next agent need a clearer instruction?
7. Update routine harness files directly, or add a proposal to
   `harness-experimental/docs/HARNESS_BACKLOG.md` when the change is structural.

## Harness Change Policy

Agents may update directly:

- Story status and evidence.
- `harness-experimental/docs/TEST_MATRIX.md` rows.
- Links from story packets to product docs.
- Validation notes and reports.
- Small clarifications tied to the current task.

Agents should ask for human confirmation before:

- Changing architecture direction.
- Removing validation requirements.
- Changing the source-of-truth hierarchy.
- Changing risk classification rules.
- Replacing the feature workflow.

## Done Definition

A task is done only when:

- The requested change is completed or the blocker is documented.
- Relevant docs, stories, and test matrix entries remain current.
- Validation commands were run when they exist.
- Missing harness capabilities were added to `harness-experimental/docs/HARNESS_BACKLOG.md`.
- The final response says what changed and what was not attempted.
