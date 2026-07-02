---
title: regions
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# regions

## Purpose

Lookup table of sales regions (e.g. North America, Europe, Asia
Pacific). Five rows, rarely changes.

## Valid join paths

- `stores.region_id = regions.region_id` — the correct path for
  attributing an order to a region. See [[tables/orders]] and
  [[tables/stores]].
- `warehouses.region_id = regions.region_id` — describes warehouse
  location only; do not use for "sales by region." See
  [[tables/warehouses]].

## Gotchas

- None beyond the join-path warning above — this table is just a
  name lookup.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 5 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `region_id` | INTEGER | no | yes | 1, 2, 3 |
| `name` | TEXT | yes | no | 'North America', 'Europe', 'Asia Pacific' |

<!-- AUTO-GENERATED:SCHEMA END -->
