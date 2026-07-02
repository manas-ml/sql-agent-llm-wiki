---
title: refunds
type: table
updated: 2025-08-01
sources: [raw_sources/schema_dump.sql]
---

# refunds

## Purpose

One row per refund issued against an order. Needed to compute net
revenue — see [[concepts/revenue]].

## Valid join paths

- `refunds.order_id = orders.order_id` (see [[tables/orders]]). A
  single order can have zero, one, or (rarely) more than one refund
  row; sum `amount` per order if you need an order-level refund total.
- `refunds` has no rows for `orders_legacy` orders — legacy data
  predates refund tracking.

## Gotchas

- `amount` is in **dollars** (decimal), same unit as
  `orders.total_amount` — no cents conversion needed.
- A refund can be a **partial** refund (amount less than the order's
  `total_amount`); never assume a refund zeroes out the whole order.
- Use `refund_date` (not `order_date`) if a question asks specifically
  when refunds were *issued*, as opposed to when the refunded order was
  *placed*. For "net revenue for period X", the convention (see
  [[concepts/revenue]]) is to attribute refunds to the period of the
  underlying order's `order_date`, not the refund's own date.

<!-- AUTO-GENERATED:SCHEMA START -->

*Auto-generated from live schema. 30 rows.*

| Column | Type | Not Null | Primary Key | Sample values |
|---|---|---|---|---|
| `refund_id` | INTEGER | no | yes | 1, 2, 3 |
| `order_id` | INTEGER | yes | no | 29, 85, 42 |
| `amount` | REAL | yes | no | 183.05, 31.83, 67.95 |
| `refund_date` | TEXT | yes | no | '2024-08-28', '2024-10-31', '2024-09-25' |

<!-- AUTO-GENERATED:SCHEMA END -->
