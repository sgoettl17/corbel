---
name: procore-domain-guide
description: Explains how Procore data is organized and how to use the Corbel tools correctly (companies, projects, API versions, filters, pagination, safe writes). Use before any Procore lookup, report or change.
---

# Procore domain guide

Use this with the Corbel MCP tools: `corbel_search_endpoints`, `corbel_describe_endpoint`, `corbel_get`, and (only when the user has enabled writes) `corbel_create`, `corbel_update`, `corbel_delete`.

## How Procore is organized

- A **company** owns **projects**. Most tools (RFIs, submittals, daily logs, drawings, punch list) live inside a project and need a `project_id`.
- Financial records (budget, commitments, prime contracts, change events) are also project-scoped, and some list endpoints take `project_id` as a **query** parameter rather than a path parameter. Always read the endpoint description.
- The configured company ID is sent automatically as the `Procore-Company-Id` header. Pass `company_id` to a tool only to override it.
- IDs are numeric. Names are not unique, so resolve a project name to an ID with a list call and confirm with the user if more than one matches.

## Working method

1. Find the endpoint: `corbel_search_endpoints` with a short keyword query and `method: "get"`.
2. Read its parameters: `corbel_describe_endpoint` with the `operation_id`. Do not guess parameter names; `filters[...]` names vary by endpoint.
3. Call it: `corbel_get` with `path_params` for `{placeholders}` and `query` for the rest.
4. Report what came back, including how many records you saw versus how many exist.

## API versions

Paths carry a version (`/rest/v1.0/...`, `/rest/v1.1/...`, `/rest/v2.0/...`). Several versions of one resource can exist. Prefer the endpoint that matches the user's need and has the fields you require; mention which version you used.

## Query conventions

- Lists use `page` and `per_page` (max 100). Use `all_pages: true` with a small `max_pages` for complete lists; the tool stops at 10 pages.
- Pass a filter key exactly as `corbel_describe_endpoint` lists it, e.g. `"filters[status]": "open"`. A nested object also works: `{"filters": {"status": "open"}}`. For names ending in `[]`, give a list value.
- Dates are ISO 8601 strings; ranges are usually `start..end`. Check the endpoint description.

## Starting points (verified against the bundled index)

| Need | operation_id |
| --- | --- |
| Companies the credentials can see | `RestV10CompaniesGet` |
| Projects for a company | `RestV10ProjectsGet` (query `company_id`, required) |
| RFIs on a project | `RestV10ProjectsProjectIdRfisGet` |
| Submittals on a project | `RestV10ProjectsProjectIdSubmittalsGet` |
| Daily construction report logs | `RestV10ProjectsProjectIdDailyConstructionReportLogsGet` |
| Change events | `RestV10ChangeEventsGet` (query `project_id`, required) |
| Punch items | `RestV10PunchItemsGet` (query `project_id`, required) |
| Prime contracts | `RestV10PrimeContractsGet` |
| Commitments | `RestV10CommitmentsGet` |
| Drawing areas | `RestV10ProjectsProjectIdDrawingAreasGet` |

## Safety rules

- Reads are the default. Never call a create, update or delete tool unless the user asked for that specific change.
- Before any write, state the endpoint, the project, and the exact fields you will send, and wait for the user to confirm. After it, report the result.
- Prefer the sandbox environment when testing writes.
- Results can contain people's names and contract amounts. Share only what the user needs and do not copy data into other tools unless asked.
- If a call returns 401, 403 or 404, report it plainly. Do not retry with other credentials or guess IDs.
