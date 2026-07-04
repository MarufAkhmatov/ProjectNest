# ProjectNest — Metric & Methodology Reference (for Temur)

This document defines every metric ProjectNest computes. Temur must answer
methodology questions from these definitions.

## Portfolio structure
- An **epic** is a project. Regular tasks and sub-tasks belong to an epic via the
  "epic link". Only Epic, Task and New Feature issue types are counted; Sub-task,
  Blocker, Story, Bug and workflow artefact types are excluded at ingest.
- Two portfolios are tracked together: **PMD** and **PMO**.

## Project Health (0–100)
A composite score per epic. It blends, with weights:
- delivery speed (TTM) and lead time (faster = higher),
- number of active blockers (more = lower),
- overdue sub-tasks (more = lower),
- dependency load,
- status aging (how long the epic has sat in one status),
- delivery progress (% of child work done).

Bands: **Healthy ≥ 70**, **Watch 50–69**, **Critical < 50**.
IMPORTANT: The "%" shown in the Top Projects panel is the HEALTH score, **not**
completion. A project can be 99 % healthy and still be in progress.

## Time-to-Market (TTM)
- **TTM = Discovery + Delivery**, measured from the real status changelog.
  - Discovery = time from creation until active delivery starts.
  - Delivery = time in active delivery statuses until Done.
- **Lead Time** = created → resolved (calendar days).
- Without a status-history (changelog) export, Discovery/Delivery are approximate
  and Lead Time may collapse; Total TTM (Created→Resolved) stays exact.

## Flow efficiency
active (value-adding) time ÷ total lead time, as a %. Low flow efficiency means
work spends most of its life waiting or in rework, not being actively delivered.

## Delivery Flow (Created vs Resolved)
Per period (month/quarter/year): how many issues were created vs resolved.
Ratio = resolved ÷ created. Backlog delta = created − resolved (positive = backlog
is growing).

## Risk register & rollup
- **At Risk** = open projects with Critical or Warning health.
- **Critical** = health below 50.
- **Delayed** = open projects that have overdue child tasks.
- **Overdue tasks** = open tasks past their due date.
- **Blocked** = issues with an active "is blocked by" dependency.
- **In progress** = open epics in In Progress / Testing / Pilot.

## PM Leaderboard
Ranks project managers by completed projects, then completed tasks, then time
spent. PM is taken STRICTLY from the custom "PM" field — never the assignee.

## New-Epic Quality (Temur alert)
Flags recently created PMD epics that are unclear or incomplete: placeholder/junk
titles, missing or link-only descriptions, or unfilled required fields (PM,
customer division, due date, scoring, project type). Severity high/med/low; a
0–100 quality score. "Don't cry wolf": flag only when there is a real high/med
problem or at least two low ones. Temur then drafts a professional, ready-to-send
message the PM forwards to the epic's author.

## Data pipeline
- Daily Jira exports: CSV "all fields" (rich), HTML "Excel/Printable" (display
  names), History XLSX (status changelog → exact TTM).
- Ingest order: PMD CSV (replace) → PMO CSV (merge) → HTML (fill-only merge,
  never overwrites rich CSV data) → History XLSX (enrich).
