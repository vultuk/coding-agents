# Retrospective Template

Use this template to produce a complete retrospective post.
Replace placeholders with concrete incident details.

## Incident Summary

- **Title:** <incident title>
- **Date:** <YYYY-MM-DD>
- **Severity:** <P1/P2/etc>
- **Duration:** <start -> resolution>
- **Status:** Resolved

## Impact

- Describe customer, operational, and financial impact.
- Include scope (systems, symbols, accounts, services, regions).

## Detection

- Describe how the issue was detected.
- Include alert/log/symptom sources and first detection timestamp.

## Timeline (UTC)

| Time | Event |
|---|---|
| <hh:mm> | <first symptom observed> |
| <hh:mm> | <key investigation step> |
| <hh:mm> | <root cause confirmed> |
| <hh:mm> | <fix deployed> |
| <hh:mm> | <validation complete> |

## Investigation and Actions Taken

List concrete actions in order. Include:

- Logs and systems queried.
- Hypotheses considered and discarded.
- Commands/checks run.
- Decisions made during mitigation.

## Root Cause

- State the technical root cause precisely.
- Include triggering conditions and why safeguards did not prevent it.

## Fix Implemented

- Describe code/config/process changes made.
- Link issue/PR/commit references when available.

## Validation

- Describe verification steps performed.
- Include tests, dashboards, checks, and rollback confidence.

## What Went Well

- List actions that reduced impact or sped up resolution.

## What Could Be Better

- List gaps in detection, tooling, communication, or process.

## Follow-up Actions

| Action | Owner | Due Date | Status |
|---|---|---|---|
| <action item> | <team/person> | <YYYY-MM-DD> | <Open/In Progress/Done> |

## References

- Issue: #<id>
- PR: #<id>
- Commits: <hash list>
- Logs/Dashboards: <links or identifiers>
