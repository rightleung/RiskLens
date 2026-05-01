# Plans Directory

This directory stores implementation plans and Claude Code handoff files.

## Naming

Original plans:

docs/plans/<topic>.md

Claude Code handoff files:

docs/plans/<topic>_fix.md

## Workflow

Codex writes plan
↓
Claude Code audits plan
↓
Claude Code implements plan
↓
Claude Code writes <topic>_fix.md
↓
Codex validates <topic>_fix.md
↓
Claude Code fixes required issues
↓
Codex re-validates until Accepted

## Claude Code Commands

/user:plan-roadmap docs/plans/*.md
/user:plan-audit docs/plans/<topic>.md
/user:implement-plan docs/plans/<topic>.md
/user:continue-plan docs/plans/<topic>.md
/user:prepare-plan-handoff docs/plans/<topic>.md
/user:fix-external-review
