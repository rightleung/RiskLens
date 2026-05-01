# Codex Prompt: Build Multi-Plan Roadmap

You are the planning session.

There may be multiple implementation plans.
Build an execution roadmap.

Do not implement code.

## Inputs

Plans under:

docs/plans/*.md

## Review Requirements

For each plan, identify:

1. Goal
2. Scope
3. Target files / systems
4. Risk level
5. Dependencies
6. Conflicts
7. Overlaps
8. Recommended order
9. Whether the plan should be split, merged, or rewritten

## Output Format

# Plan Roadmap

## Plans Reviewed

| Plan | Goal | Scope | Risk |
|---|---|---|---|

## Dependencies

| Plan | Depends On | Reason |
|---|---|---|

## Overlaps

| Plans | Overlap | Recommendation |
|---|---|---|

## Conflicts

| Plans | Conflict | Resolution |
|---|---|---|

## Recommended Execution Order

1. docs/plans/<first>.md
   - Why first:
   - Claude audit command:
   - Claude implement command:
   - Claude handoff command:

2. docs/plans/<second>.md
   - Why next:
   - Claude audit command:
   - Claude implement command:
   - Claude handoff command:

## Plans To Split Or Rewrite
- none, or list

## Validation Strategy
Explain when to send handoff back to Codex for validation.

## Immediate Next Step
Give exactly one next step.
