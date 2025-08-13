# File: /docs/filter_dsl.md | Version: 1.0 | Path: /docs/filter_dsl.md
# Task Search & Filter DSL (Phase-5)

This document explains the JSON payload your API accepts for advanced task filtering, including Tags `ANY/ALL`, custom fields, scoping (workspace/space/folder/list), sorting, and pagination.

## Endpoint
POST /api/tasks/search
Content-Type: application/json

## Payload shape (high-level)
{
"scope": {
"workspace_id": null,
"space_id": null,
"folder_id": null,
"list_id": null
},
"where": {
"op": "AND",
"filters": [
{ "field": "status", "operator": "in", "value": ["open", "in_progress"] },
{ "field": "due_date", "operator": "between", "value": ["2025-08-01", "2025-08-31"] }
]
},
"sort": [
{ "field": "created_at", "direction": "desc" }
],
"page": { "limit": 50, "offset": 0 }
}

**Notes**
- `where` supports nested groups (`filters` can contain groups with their own `op`).
- `op` is one of `AND` | `OR`.
- All date/time values are ISO-8601 (e.g., `2025-08-12T00:00:00Z` or `2025-08-12`).

## Supported fields (Task core)

| Field         | Type      | Common Operators                                                                             | Examples                                                                                     |
|---------------|-----------|----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `title`       | string    | `eq`, `neq`, `contains`, `startswith`, `endswith`                                            | `{"field":"title","operator":"contains","value":"invoice"}`                                  |
| `description` | string    | `contains`, `startswith`, `endswith`, `eq`, `neq`                                            | `{"field":"description","operator":"contains","value":"urgent"}`                             |
| `status`      | enum      | `eq`, `neq`, `in`, `nin`                                                                     | `{"field":"status","operator":"in","value":["open","in_progress"]}`                          |
| `priority`    | enum/int  | `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `in`, `nin`                                           | `{"field":"priority","operator":"lte","value":2}`                                            |
| `assignees`   | list[id]  | `in` (any-of), `nin` (none-of), `is_null`, `not_null`                                        | `{"field":"assignees","operator":"in","value":["user_123","user_456"]}`                      |
| `due_date`    | date/time | `eq`, `lt`, `lte`, `gt`, `gte`, `between`, `is_null`, `not_null`                             | `{"field":"due_date","operator":"between","value":["2025-08-01","2025-08-31"]}`              |
| `created_at`  | date/time | `lt`, `lte`, `gt`, `gte`, `between`                                                          | `{"field":"created_at","operator":"gte","value":"2025-08-01"}`                               |
| `updated_at`  | date/time | `lt`, `lte`, `gt`, `gte`, `between`                                                          |                                                                                              |
| `tags`        | tags      | `match` (see Tags ANY/ALL below)                                                             | see examples below                                                                           |
| `completed`   | boolean   | `eq`                                                                                         | `{"field":"completed","operator":"eq","value":false}`                                        |
| `archived`    | boolean   | `eq`                                                                                         |                                                                                              |
| `list_id`     | id        | `eq`, `in`                                                                                   |                                                                                              |

> Null checks use `is_null` / `not_null` with `"value": true` (value is ignored).

## Custom fields

Address custom fields using the pattern `custom.<key>` (the `<key>` is your field’s unique key or slug).

| Type       | Operators                                                                                         | Example                                                                                         |
|------------|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| string     | `eq`, `neq`, `contains`, `startswith`, `endswith`, `in`, `nin`, `is_null`, `not_null`             | `{"field":"custom.cf_project_code","operator":"contains","value":"PO-"}`                        |
| number     | `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `between`, `in`, `nin`, `is_null`, `not_null`              | `{"field":"custom.cf_cost","operator":"between","value":[1000,5000]}`                           |
| boolean    | `eq`, `is_null`, `not_null`                                                                        | `{"field":"custom.cf_billable","operator":"eq","value":true}`                                   |
| date/time  | `eq`, `lt`, `lte`, `gt`, `gte`, `between`, `is_null`, `not_null`                                  | `{"field":"custom.cf_go_live","operator":"lte","value":"2025-09-01"}`                           |
| enum/multi | `eq`, `neq`, `in`, `nin` (enum); multi-select uses `in`/`nin` as any-of / none-of semantics       | `{"field":"custom.cf_phase","operator":"in","value":["design","delivery"]}`                     |

## Tags: `ANY` vs `ALL`

Use `operator: "match"` with a value object:

{
"field": "tags",
"operator": "match",
"value": { "mode": "ANY", "tag_ids": ["tag_bug", "tag_invoice"] }
}

- `"mode": "ANY"` → task matches if it has **at least one** of the provided tags.
- `"mode": "ALL"` → task must have **every** tag in the list.

**Examples**
{ "field": "tags", "operator": "match", "value": { "mode": "ANY", "tag_ids": ["t1","t2"] } }
{ "field": "tags", "operator": "match", "value": { "mode": "ALL", "tag_ids": ["t1","t2"] } }
{ "field": "tags", "operator": "is_null", "value": true }

## Scoping (workspace → space → folder → list)

Provide exactly one (most specific wins). Priority: `list_id` → `folder_id` → `space_id` → `workspace_id`.

"scope": { "workspace_id": "ws_123", "space_id": null, "folder_id": null, "list_id": null }

## Sorting & Pagination
"sort": [
{ "field": "created_at", "direction": "desc" },
{ "field": "priority", "direction": "asc" }
],
"page": { "limit": 50, "offset": 0 }

Defaults (if omitted): `created_at desc`, `limit=50`, `offset=0`.

## End-to-end examples

**1) Sprint board**
{
"scope": { "space_id": "sp_marketing" },
"where": {
"op": "AND",
"filters": [
{ "field": "status", "operator": "in", "value": ["open","in_progress"] },
{ "field": "due_date", "operator": "between", "value": ["2025-08-01","2025-08-31"] },
{ "field": "tags", "operator": "match", "value": { "mode": "ANY", "tag_ids": ["tag_campaign","tag_design"] } }
]
},
"sort": [
{ "field": "priority", "direction": "desc" },
{ "field": "created_at", "direction": "desc" }
],
"page": { "limit": 100, "offset": 0 }
}

**2) Finance review**
{
"scope": { "folder_id": "fold_finance_q3" },
"where": {
"op": "AND",
"filters": [
{ "field": "tags", "operator": "match", "value": { "mode": "ALL", "tag_ids": ["tag_invoice","tag_payable"] } },
{ "field": "custom.cf_amount_usd", "operator": "between", "value": [1000, 10000] },
{ "field": "assignees", "operator": "in", "value": ["usr_sara","usr_ali"] },
{
"op": "OR",
"filters": [
{ "field": "custom.cf_due_quarter", "operator": "eq", "value": "Q3" },
{ "field": "due_date", "operator": "between", "value": ["2025-07-01","2025-09-30"] }
]
}
]
},
"sort": [{ "field": "updated_at", "direction": "desc" }],
"page": { "limit": 50, "offset": 0 }
}

**3) Hygiene**
{
"scope": { "workspace_id": "ws_core" },
"where": {
"op": "OR",
"filters": [
{ "field": "due_date", "operator": "is_null", "value": true },
{ "field": "assignees", "operator": "is_null", "value": true }
]
},
"sort": [{ "field": "created_at", "direction": "desc" }],
"page": { "limit": 25, "offset": 0 }
}

**4) Text search**
{
"scope": { "list_id": "list_ops" },
"where": {
"op": "AND",
"filters": [
{
"op": "OR",
"filters": [
{ "field": "title", "operator": "contains", "value": "renewal" },
{ "field": "description", "operator": "contains", "value": "renewal" }
]
}
]
},
"sort": [{ "field": "created_at", "direction": "desc" }],
"page": { "limit": 20, "offset": 0 }
}

## Validation & constraints
- Unknown fields/operators → `400 Bad Request` with a clear message.
- `between` requires a 2-element array (`[min,max]`) of numbers or ISO dates.
- For `match` on tags: `tag_ids` must be non-empty; `mode` is `ANY` or `ALL`.
- `page.limit` is capped by server (e.g., 200). Negative offsets are rejected.
- If multiple scope IDs are provided, server **uses the most specific** (list > folder > space > workspace).

## Curl snippets
Basic: status IN + sort + paging
curl -s -X POST http://localhost:8000/api/tasks/search \
-H "Content-Type: application/json" \
-d '{ "scope": { "space_id": "sp_prod" },
"where": { "op": "AND", "filters": [
{ "field": "status", "operator": "in", "value": ["open","in_progress"] }
]},
"sort": [{ "field": "created_at", "direction": "desc" }],
"page": { "limit": 50, "offset": 0 } }'

Tags ALL with custom field
curl -s -X POST http://localhost:8000/api/tasks/search \
-H "Content-Type: application/json" \
-d '{ "scope": { "folder_id": "fold_finance_q3" },
"where": { "op": "AND", "filters": [
{ "field": "tags", "operator": "match", "value": {"mode":"ALL","tag_ids":["tag_invoice","tag_payable"]} },
{ "field": "custom.cf_amount_usd", "operator": "gte", "value": 1000 }
]},
"sort": [{ "field": "updated_at", "direction": "desc" }],
"page": { "limit": 25, "offset": 0 } }'

## Response (shape example )
{
"items": [
{
"id": "tsk_abc123",
"title": "Finalize Q3 invoice batch",
"status": "in_progress",
"priority": 3,
"assignees": ["usr_sara"],
"tags": ["tag_invoice", "tag_payable"],
"due_date": "2025-08-20",
"custom": { "cf_amount_usd": 2400, "cf_billable": true },
"created_at": "2025-08-05T10:01:00Z",
"updated_at": "2025-08-12T07:45:10Z"
}
],
"page": { "limit": 50, "offset": 0, "total": 137 }
}

## Changelog (doc)
- **v1.0**: Initial public spec for Phase-5, including Tags `ANY/ALL`, custom fields, scoping, sorting, pagination, and examples.
