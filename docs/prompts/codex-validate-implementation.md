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

## Fix Instruction Requirements

If fixes are required, produce a complete code-level fix plan that Claude Code can execute in one pass.

Hard requirements:

1. Be specific enough for Claude Code to execute directly.
2. Identify exact files, functions, classes, models, routes, tests, or config entries to modify.
3. Explain what is missing, what should change, and why.
4. Clearly state what Claude Code did not implement, only partially implemented, or implemented incorrectly.
5. Do not give vague advice.
6. Do not merely say "improve tests", "fix validation", or "handle edge cases"; specify the exact expected behavior and test cases.
7. The fix plan must be complete enough to resolve the issue in one follow-up implementation pass.
8. The fix plan must include verification commands and acceptance conditions.
9. Save the required-fix plan as a Markdown file under docs/reviews/.
10. Use this filename pattern:
    - docs/reviews/<topic>_required_fixes.md
11. Treat the required-fix Markdown file as the source of truth for Claude Code's follow-up fix session.

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

## Code-Level Fix Plan

If the verdict is Needs fixes or Blocked, write a complete code-level fix plan.

For each required fix, include:

### Fix <N>: <short title>

- Severity:
- Related original plan item:
- Problem:
- Missing, partial, or incorrect implementation:
- Files to modify:
- Symbols to modify:
- Required behavior:
- Tests to add or update:
- Verification command:
- Acceptance condition:

## What Claude Code Did Not Finish

List exact missing, partial, incorrect, or unverifiable items.

## Scope / Deviation Review
- ...

## Test Coverage Review
- ...

## Required Fix Plan File

If fixes are required, create or instruct creation of:

docs/reviews/<topic>_required_fixes.md

The file must contain the full Code-Level Fix Plan above.

## Claude Code Fix Prompt

Paste this into Claude Code:

/user:fix-external-review
Original plan: docs/plans/<topic>.md

External review:
<required fixes here>

Required fix plan file:
docs/reviews/<topic>_required_fixes.md
