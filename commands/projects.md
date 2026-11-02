---
description: List Procore projects for the configured company, optionally filtered by name or status
argument-hint: [name or status]
---

List the Procore projects for the configured company using `RestV10ProjectsGet` through `corbel_get`. The `company_id` query parameter is required; use the configured company ID, or ask the user if it is unknown.

If $ARGUMENTS is not empty, treat it as a project name (`filters[name]`) or status (`filters[by_status]`) filter, confirming parameter names with `corbel_describe_endpoint` first. Show project ID, name, status and city in a table, with the number of results and whether more pages exist.
