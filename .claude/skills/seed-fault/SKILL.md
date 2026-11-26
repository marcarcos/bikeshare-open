---
name: seed-fault
description: Seed one deliberate fault in src/ to test whether the hook and tests catch it. Use when asked to seed, plant, or inject a fault. Argument is a one-line description of the fault.
allowed-tools: Read, Edit, Bash(python -m pytest*), Bash(git diff*), Bash(git status*)
---

# Seed a fault

Fault to seed: $ARGUMENTS

Current state of the suite (must be green before seeding):
!`python -m pytest tests/ -q 2>&1 | tail -1`

Files changed right now:
!`git status --short`

## Steps

1. If the suite above is not all passing, or `git status` shows modified files under src/, STOP and say so. Do not seed on a dirty tree.
2. Read only the file in src/ that the fault concerns. Make the smallest edit that introduces exactly the fault described. One edit, no refactoring.
3. Never edit anything in tests/, data/, or .claude/. A fault the tests are changed to hide is not a seeded fault.
4. Run `python -m pytest tests/ -q` and show the last 5 lines verbatim.
5. Run `git diff src/` and show it verbatim.
6. Report in three lines:
   - CAUGHT BY: the failing test name(s), or NOTHING if the suite stayed green
   - HOOK: whether the PostToolUse hook printed a failure after your edit
   - GAP: if nothing caught it, one sentence on what test would

Do not fix the fault. The human commits it as the broken state, then asks for the fix separately.
