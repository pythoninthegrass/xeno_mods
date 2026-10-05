---
id: TASK-002
title: Decide IModLifecycle vs IContentPackLifecycle
status: To Do
assignee: []
created_date: '2026-10-05 04:10'
labels: []
dependencies:
  - TASK-001
priority: low
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
IModLifecycle is marked obsolete in game 7.27.11 (renamed to Common.Content.Lifecycle.IContentPackLifecycle, old implementations still work via default interface method bridges). Decide whether to migrate now or only if loading fails.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Decision recorded in the task notes
- [ ] #2 Lifecycle class uses the chosen interface and the build has no CS0618 warnings if migrated
<!-- AC:END -->
