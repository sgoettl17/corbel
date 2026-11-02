---
name: rfi-triage
description: Summarizes a Procore project's RFIs by status, who holds the ball, and what is overdue, then proposes follow-ups. Use when the user asks about open, late or stalled RFIs.
---

# RFI triage

Read-only. Follow the working method in the `procore-domain-guide` skill.

1. Identify the project. If the user gave a name, list projects with `RestV10ProjectsGet` (query `company_id`) and match it; ask if several match.
2. Call `corbel_describe_endpoint` for `RestV10ProjectsProjectIdRfisGet` to confirm the `filters[...]` names, then `corbel_get` it with `all_pages: true` and a small `max_pages`.
3. For a narrower view, pass `filters[status]` and, for lateness, `filters[overdue]` as described by the endpoint.
4. Report:
   - Counts by status.
   - Overdue RFIs, oldest first, each with number, subject, who has the ball in court, and days overdue.
   - RFIs with no recent update (use `updated_at`).
   - Up to five suggested follow-ups, each naming the person to chase.
5. State how many RFIs you fetched and whether more exist. Do not claim completeness if pagination was capped.

Do not create or edit RFIs or send reminders from this skill.
