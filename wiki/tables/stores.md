---
title: stores
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# stores

## Purpose

Physical/online storefronts where orders are placed. Every order is
attributed to exactly one store.

## Valid join paths

- `orders.store_id = stores.store_id` (see [[tables/orders]]).
- `stores.region_id = regions.region_id` — **this is the correct and
  only reliable path from an order to a region.** See
  [[tables/orders]] for why the alternative path through `warehouses`
  is wrong.

## Gotchas

- `store_id` on `orders` is never null — every order has a store.
- A store's region is fixed; it does not vary by order.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 10 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `store_id` | INTEGER | no | yes | 1, 2, 3 |
| `name` | TEXT | yes | no | 'Downtown Flagship', 'Riverside Mall', 'Airport Kiosk' |
| `region_id` | INTEGER | yes | no | 1, 2, 3 |

<!-- AUTO-GENERATED:SCHEMA END -->
