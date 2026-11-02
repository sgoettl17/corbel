---
name: project-health
description: Builds a one-page health snapshot of a Procore project from RFIs, submittals, change events and punch items. Use when the user asks how a project is doing or wants a status rollup.
---

# Project health snapshot

Read-only. Follow the working method in the `procore-domain-guide` skill.

1. Identify the project ID (see that skill).
2. Fetch, one call each, with `all_pages: true` and `max_pages` of 3 unless the user wants more:
   - RFIs: `RestV10ProjectsProjectIdRfisGet`
   - Submittals: `RestV10ProjectsProjectIdSubmittalsGet`
   - Change events: `RestV10ChangeEventsGet` (query `project_id`)
   - Punch items: `RestV10PunchItemsGet` (query `project_id`)
3. If a call fails with 403 or 404, mark that area "not available to these credentials" and continue.
4. Produce a table with one row per area: total fetched, open, overdue or late, oldest open item. Follow it with three to five bullet points on the biggest risks.
5. Say which areas were truncated by the page cap.

Keep it to one screen. Offer to drill into any area with the matching skill rather than dumping detail.
