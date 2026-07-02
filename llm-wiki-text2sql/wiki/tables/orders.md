---
title: orders
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# orders

## Purpose

One row per customer order. The transactional core of the schema —
almost every business question ("revenue", "sales by region", "order
count") starts here.

## Valid join paths

- **To customers:** `orders.customer_id = customers.customer_id`.
- **To region — CORRECT PATH:** `orders.store_id = stores.store_id`,
  then `stores.region_id = regions.region_id`. Every order was placed
  at (or attributed to) a store, and every store has exactly one
  region. This is the only reliable path from an order to a region.
- **To region — TEMPTING BUT WRONG:** `orders.warehouse_id =
  warehouses.warehouse_id`, then `warehouses.region_id =
  regions.region_id`. Do not use this path for regional reporting, for
  two independent reasons:
  1. `orders.warehouse_id` is **NULL for roughly half of all orders**
     (fulfillment-warehouse tracking was only added partway through the
     order history). Joining through it silently drops those orders
     from any aggregate.
  2. Even when `warehouse_id` is non-null, the fulfilling warehouse is
     not necessarily in the same region as the order's store — overflow
     orders are routed to whichever warehouse has capacity, which is
     frequently in a different region. Using the warehouse's region as
     "the order's region" misattributes real orders to the wrong
     region.
  `warehouse_id` is useful for fulfillment/logistics questions
  ("which warehouse shipped this order"), never for "what region did
  this sale belong to."
- **To products/line items:** via `order_items.order_id = orders.order_id`
  (see [[tables/order_items]]).
- **To refunds:** `refunds.order_id = orders.order_id` (see
  [[tables/refunds]]; needed for net-revenue calculations, see
  [[concepts/revenue]]).

## Gotchas

- `total_amount` is in **dollars** (decimal), NOT cents. Contrast with
  [[tables/products]].`price_cents`, which is in cents. Do not combine
  the two without converting (`price_cents / 100.0`).
- `order_date` is the order placement date, stored as `YYYY-MM-DD` text.
  For fiscal-period questions ("last quarter", "this fiscal year"), see
  [[concepts/fiscal-calendar]] — the business's fiscal year does not
  start January 1.
- `orders` holds only **current** (post-migration) orders. Pre-migration
  history lives in the separate [[tables/orders_legacy]] table and is
  excluded from "current"/default totals unless a question explicitly
  asks for historical or all-time data.
- `warehouse_id` is nullable; `store_id` is not.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 200 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `order_id` | INTEGER | no | yes | 1, 2, 3 |
| `customer_id` | INTEGER | yes | no | 38, 41, 3 |
| `store_id` | INTEGER | yes | no | 4, 1, 6 |
| `warehouse_id` | INTEGER | no | no | 1, 3, 4 |
| `order_date` | TEXT | yes | no | '2024-06-04', '2024-09-26', '2024-07-07' |
| `total_amount` | REAL | yes | no | 109.98, 288.86, 797.89 |

<!-- AUTO-GENERATED:SCHEMA END -->
