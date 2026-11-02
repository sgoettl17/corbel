---
name: daily-log-summary
description: Summarizes a Procore project's daily construction report logs over a date range (weather, manpower, delays, notes). Use when the user asks what happened on site or wants a weekly field recap.
---

# Daily log summary

Read-only. Follow the working method in the `procore-domain-guide` skill.

1. Identify the project and the date range. Default to the last 7 days if none is given and say so.
2. Call `corbel_describe_endpoint` for `RestV10ProjectsProjectIdDailyConstructionReportLogsGet`, then `corbel_get` it with `start_date` and `end_date` and `all_pages: true`.
3. For other log types (accidents, manpower, deliveries, notes), use `corbel_search_endpoints` with `daily logs <type>` and the same project and dates.
4. Summarize by day, then overall:
   - Weather impact and any delay.
   - Work performed and headcount trends.
   - Safety incidents, visitors, deliveries, inspections.
   - Open issues the logs raise.
5. Quote only short phrases from log text; do not paste full entries. Note any days with no log.

Daily logs may be restricted for some users. If the call returns 403, say so rather than guessing.
