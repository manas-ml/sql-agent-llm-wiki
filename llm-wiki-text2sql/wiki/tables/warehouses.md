---
title: warehouses
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# warehouses

## Purpose

Fulfillment warehouses. Used for logistics/shipping questions only.

## Valid join paths

- `orders.warehouse_id = warehouses.warehouse_id` — valid for
  fulfillment/logistics questions ("which warehouse shipped order
  X"), but **not** valid as a stand-in for the order's sales region.
  See [[tables/orders]] for the full explanation of why
  `orders -> warehouses -> regions` is the wrong path for regional
  reporting (nulls + cross-region overflow routing).
- `warehouses.region_id = regions.region_id` describes where the
  warehouse itself is located, not where the order it fulfilled was
  sold.

## Gotchas

- `orders.warehouse_id` is nullable and NULL for roughly half of all
  orders — a warehouse-fulfillment tracking field, not a required
  attribute of an order.
- Do not use this table to compute "sales by region." Use
  [[tables/stores]] instead.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 8 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `warehouse_id` | INTEGER | no | yes | 1, 2, 3 |
| `name` | TEXT | yes | no | 'Regional DC 1', 'Regional DC 2', 'Overflow Depot' |
| `region_id` | INTEGER | yes | no | 1, 2, 3 |

<!-- AUTO-GENERATED:SCHEMA END -->
