# Codex Prompt: Validate Claude Code Implementation

You are the original planning/review session.

Validate Claude Code's implementation against the original plan and the handoff file.

## Inputs

1. Original plan:
   - docs/plans/<topic>.md

2. Claude Code handoff:
   - docs/plans/<topic>_fix.md

3. Current diff or repository state, if available.

## Review Requirements

Check:

1. Whether every Key Change was implemented.
2. Whether the implementation stayed within scope.
3. Whether public API behavior changed unexpectedly.
4. Whether tests match the Test Plan.
5. Whether deviations are acceptable.
6. Whether there are unhandled risks or missing edge cases.
7. Whether any implementation detail contradicts the original assumptions.
8. Whether the handoff provides enough evidence.

## Verdict

Return exactly one:

- Accepted
- Needs fixes
- Blocked

## Output Format

# Validation Result

## Verdict
Accepted / Needs fixes / Blocked

## Required Fixes
Only include required fixes. Group by severity.

### Critical
- none, or list

### High
- none, or list

### Medium
- none, or list

### Low
- none, or list

## Scope / Deviation Review
- ...

## Test Coverage Review
- ...

## Claude Code Fix Prompt

Paste this into Claude Code:

/user:fix-external-review
Original plan: docs/plans/<topic>.md

External review:
<required fixes here>
