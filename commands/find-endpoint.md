---
description: Search the Procore API for endpoints matching a topic and explain the best match
argument-hint: <topic, e.g. "submittal approvers">
---

Use `corbel_search_endpoints` to find Procore endpoints for: $ARGUMENTS

Show up to five candidates as a table of operation_id, method, path and summary. Then call `corbel_describe_endpoint` on the best match and explain its path parameters, query filters and (for writes) required body fields. Do not call Procore data endpoints.
