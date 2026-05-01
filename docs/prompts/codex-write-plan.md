# Codex Prompt: Write Implementation Plan

You are the planning session.

Inspect the repository and write a structured implementation plan.
Do not implement code.

The plan must be executable by Claude Code.

## Requirements

1. Inspect relevant files before writing the plan.
2. Identify concrete files, functions, classes, API routes, models, tests, and configuration entries where possible.
3. Separate implementation changes from tests.
4. Preserve existing public APIs unless the task explicitly requires changing them.
5. Avoid broad refactors unless explicitly justified.
6. Include assumptions Claude Code must verify before implementation.
7. Include risks and non-goals.
8. Include acceptance criteria.
9. Include suggested execution batches.
10. Make the plan suitable for Claude Code's /user:implement-plan.

## Output Format

# <Topic> Plan

## Summary
Explain the goal, root cause, and intended outcome.

## Key Changes
- Change group 1:
  - Files / symbols:
  - Behavior change:
  - Scope boundary:
- Change group 2:
  - Files / symbols:
  - Behavior change:
  - Scope boundary:

## Test Plan
- Unit tests:
- Integration / API tests:
- Regression tests:
- Negative tests:
- Edge-case tests:

## Acceptance Criteria
- ...

## Assumptions
- ...

## Risks / Non-Goals

### Risks
- ...

### Non-Goals
- ...

## Suggested Execution Batches
Batch 1:
Batch 2:
Batch 3:
Batch 4:

## Execution Contract
This plan is intended to be executed by Claude Code.
Claude Code should validate repository fit first, then implement only the listed changes.
Any mismatch between this plan and the current codebase should be reported before implementation.
