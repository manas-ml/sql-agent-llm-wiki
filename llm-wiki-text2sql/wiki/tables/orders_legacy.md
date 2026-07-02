---
title: orders_legacy
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# orders_legacy

## Purpose

Pre-migration order archive. Kept for historical/audit purposes only.
It is a snapshot of the old order system before the store/warehouse
migration, not a live operational table.

## Valid join paths

- `orders_legacy.customer_id = customers.customer_id` is valid (customer
  IDs were preserved across the migration).
- **There is no `store_id` or `warehouse_id` column** — `orders_legacy`
  predates that part of the schema. It CANNOT be joined to `stores`,
  `warehouses`, or `regions`. Do not attempt a regional breakdown of
  legacy orders; the data to do so does not exist.
- `orders_legacy` has no corresponding `order_items` or `refunds` rows
  — those tables only track current (post-migration) orders.

## Gotchas

- **Excluded from "current" / default totals.** Any question about
  "our orders", "total revenue", "how many orders", etc. without an
  explicit historical/all-time qualifier should query `orders` only —
  never `orders_legacy`, and never a `UNION` of both.
- **Only include `orders_legacy` when the question explicitly asks for
  historical, archived, or "all-time" data** (e.g. "including
  pre-migration orders", "all-time revenue since the company started").
  In that case, sum `orders.total_amount` and `orders_legacy.total_amount`
  separately (they use the same dollar unit) and add them — do not
  `UNION` the tables since their columns don't match
  (`orders_legacy` has no `store_id`/`warehouse_id`).
- `orders_legacy.total_amount` is in dollars, same unit as
  `orders.total_amount` — no cents conversion needed here.
- Date range is pre-migration only (roughly 2022–mid-2023); it does not
  overlap with `orders`, so there's no double-counting risk when adding
  the two totals together.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 40 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `order_id` | INTEGER | no | yes | 1, 2, 3 |
| `customer_id` | INTEGER | yes | no | 46, 33, 30 |
| `order_date` | TEXT | yes | no | '2023-05-16', '2023-04-02', '2022-05-16' |
| `total_amount` | REAL | yes | no | 50.01, 326.35, 212.6 |

<!-- AUTO-GENERATED:SCHEMA END -->
